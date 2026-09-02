"""Geracao do pacote interoperavel CampoSync do MorfoCampo."""

from __future__ import annotations

from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import ssl
from typing import Any
from urllib import parse, request
import uuid
import zipfile


CONTRACT_ID = "camposync.package"
CONTRACT_VERSION = "1.0.0"
PACKAGE_NAMESPACE = uuid.UUID("8ec2544c-c9d7-4b2a-9078-cbc8f8c0f2d5")


def _file_entry(
    path: str,
    role: str,
    media_type: str,
    content: bytes,
    public_scope: str,
) -> dict[str, Any]:
    return {
        "path": path,
        "role": role,
        "media_type": media_type,
        "size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "public_scope": public_scope,
    }


def calculate_contents_checksum(files: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(files, key=lambda item: item["path"]):
        digest.update(entry["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_package(
    campaign: dict[str, Any],
    csv_content: str,
    validation_report: str,
    producer_version: str,
) -> tuple[io.BytesIO, dict[str, Any]]:
    payloads = {
        "data/registros.csv": csv_content.encode("utf-8"),
        "reports/validacao.md": validation_report.encode("utf-8"),
    }
    files = [
        _file_entry(
            "data/registros.csv",
            "observations",
            "text/csv",
            payloads["data/registros.csv"],
            "restricted",
        ),
        _file_entry(
            "reports/validacao.md",
            "validation_report",
            "text/markdown",
            payloads["reports/validacao.md"],
            "restricted",
        ),
    ]
    checksum = calculate_contents_checksum(files)
    campaign_identity = f"{campaign['project_id']}/{campaign['campaign_id']}"
    package_id = uuid.uuid5(
        PACKAGE_NAMESPACE,
        f"morfocampo:{campaign_identity}:{checksum}",
    )
    manifest = {
        "contract": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "package_id": str(package_id),
        "campaign_id": campaign_identity,
        "project_id": str(campaign["project_id"]),
        "producer": {
            "system_id": "morfocampo",
            "system_version": producer_version,
        },
        "created_at": datetime.now().astimezone().isoformat(),
        "public_scope": "restricted",
        "files": files,
        "checksum": checksum,
    }

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        )
        for path, content in payloads.items():
            archive.writestr(path, content)
    output.seek(0)
    return output, manifest


def read_service_token(path: str) -> str:
    token = Path(path).read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError("arquivo de token vazio")
    return token


def send_package(
    package: io.BytesIO,
    base_url: str,
    token: str,
    *,
    ca_file: str | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    parsed = parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL do SisTer-Campo invalida")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("HTTP sem TLS e permitido somente em loopback")

    endpoint = base_url.rstrip("/") + "/api/v1/packages"
    upload = request.Request(
        endpoint,
        data=package.getvalue(),
        method="POST",
        headers={
            "Content-Type": "application/zip",
            "X-SisTer-Campo-Token": token,
        },
    )
    context = ssl.create_default_context(cafile=ca_file) if parsed.scheme == "https" else None
    with request.urlopen(upload, timeout=timeout_seconds, context=context) as response:
        return json.loads(response.read().decode("utf-8"))
