"""
camposync.py — Geração e sincronização do pacote CampoSync 2.0.0 do MorfoCampo.

Atende aos requisitos de integração institucional com SisTer-Nexo:
- MC-NEXO-02: Consumo de contextos autorizados (GET /api/v1/integrations/morfocampo/contexts)
- MC-NEXO-04: Contrato CampoSync 2.0.0 com context e producer institucional
- MC-NEXO-05: Materialização progressiva com streaming de CSV e hashes incrementais (RPi5)
- MC-NEXO-06: Reutilização de artefato imutável no Outbox
- MC-NEXO-07: Sincronização via POST /api/v1/integrations/morfocampo/packages com receipt
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import ssl
import tempfile
from typing import Any, Callable, Iterable, Optional
from urllib import error as url_error, parse, request
import uuid
import zipfile


CONTRACT_ID = "camposync.package"
CONTRACT_VERSION = "2.0.0"
PACKAGE_NAMESPACE = uuid.UUID("8ec2544c-c9d7-4b2a-9078-cbc8f8c0f2d5")


def _file_entry(
    path: str,
    role: str,
    media_type: str,
    size: int,
    sha256: str,
    public_scope: str = "restricted",
) -> dict[str, Any]:
    return {
        "path": path,
        "role": role,
        "media_type": media_type,
        "size": size,
        "sha256": sha256,
        "public_scope": public_scope,
    }


def calculate_contents_checksum(files: list[dict[str, Any]]) -> str:
    """Calcula SHA-256 ordenado dos arquivos do pacote (path + NUL + sha256 + LF)."""
    digest = hashlib.sha256()
    for entry in sorted(files, key=lambda item: item["path"]):
        digest.update(entry["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_manifest_v2(
    campaign: dict[str, Any],
    files: list[dict[str, Any]],
    producer_version: str,
    node_identity: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    MC-NEXO-04: Constrói o manifesto CampoSync 2.0.0 com context e producer enriquecidos.
    """
    checksum = calculate_contents_checksum(files)

    # Contexto institucional
    context_id = campaign.get("context_id") or f"local-ctx-{campaign['campaign_id']}"
    project_id = str(campaign.get("project_id", "morfocampo_standalone"))
    research_activity_id = str(campaign.get("research_activity_id", "STANDALONE"))
    operational_activity_id = campaign.get("operational_activity_id")

    context_block = {
        "context_id": context_id,
        "project_id": project_id,
        "research_activity_id": research_activity_id,
    }
    if operational_activity_id:
        context_block["operational_activity_id"] = str(operational_activity_id)

    # Identidade do produtor (MorfoNode)
    morfonode_id = "standalone-morfonode"
    credential_id = "standalone-credential"
    if node_identity:
        morfonode_id = node_identity.get("morfonode_id", morfonode_id)
        credential_id = node_identity.get("credential_id", credential_id)
    elif campaign.get("morfonode_id"):
        morfonode_id = campaign["morfonode_id"]

    producer_block = {
        "system_id": "morfocampo",
        "system_version": producer_version,
        "morfonode_id": morfonode_id,
        "credential_id": credential_id,
    }

    campaign_identity = f"{project_id}/{campaign['campaign_id']}"
    package_id = uuid.uuid5(
        PACKAGE_NAMESPACE,
        f"morfocampo:{campaign_identity}:{checksum}",
    )

    return {
        "contract": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "package_id": str(package_id),
        "campaign_id": campaign_identity,
        "context": context_block,
        "producer": producer_block,
        "created_at": datetime.now().astimezone().isoformat(),
        "public_scope": "restricted",
        "files": files,
        "checksum": checksum,
    }


def materialize_package_to_file(
    target_zip_path: Path | str,
    campaign: dict[str, Any],
    csv_line_generator: Iterable[str],
    validation_report: str,
    producer_version: str,
    node_identity: Optional[dict[str, Any]] = None,
) -> tuple[Path, dict[str, Any]]:
    """
    MC-NEXO-05: Materialização progressiva em disco para eficiência extrema no RPi5.
    Lê SQLite por streaming, calcula hashes em chunks e produz artefato imutável.
    """
    target_zip_path = Path(target_zip_path)
    target_zip_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="morfocampo_pkg_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        tmp_csv_path = tmp_dir / "registros.csv"
        tmp_report_path = tmp_dir / "validacao.md"
        tmp_output_zip = tmp_dir / "output.zip"

        # 1. Escrever CSV incrementalmente enquanto calcula SHA-256 e tamanho
        csv_hasher = hashlib.sha256()
        csv_size = 0
        with tmp_csv_path.open("wb") as csv_out:
            for line in csv_line_generator:
                encoded = line.encode("utf-8")
                csv_hasher.update(encoded)
                csv_size += len(encoded)
                csv_out.write(encoded)

        # 2. Escrever Relatório de Validação
        report_bytes = validation_report.encode("utf-8")
        report_hasher = hashlib.sha256(report_bytes)
        tmp_report_path.write_bytes(report_bytes)

        # 3. Montar descritores de arquivos
        files = [
            _file_entry(
                "data/registros.csv",
                "observations",
                "text/csv",
                csv_size,
                csv_hasher.hexdigest(),
                "restricted",
            ),
            _file_entry(
                "reports/validacao.md",
                "validation_report",
                "text/markdown",
                len(report_bytes),
                report_hasher.hexdigest(),
                "restricted",
            ),
        ]

        # 4. Construir manifesto 2.0.0
        manifest = build_manifest_v2(campaign, files, producer_version, node_identity)

        # 5. Criar ZIP progressivamente
        with zipfile.ZipFile(tmp_output_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
            archive.writestr("manifest.json", manifest_json.encode("utf-8"))
            archive.write(tmp_csv_path, "data/registros.csv")
            archive.write(tmp_report_path, "reports/validacao.md")

        # 6. Mover atomicamente para o destino imutável (MC-NEXO-06)
        shutil.move(str(tmp_output_zip), str(target_zip_path))

    return target_zip_path, manifest


def build_package(
    campaign: dict[str, Any],
    csv_content: str,
    validation_report: str,
    producer_version: str,
    node_identity: Optional[dict[str, Any]] = None,
) -> tuple[io.BytesIO, dict[str, Any]]:
    """
    Construtor em memória compatível com chamadas diretas e testes unitários.
    Gera CampoSync 2.0.0.
    """
    csv_bytes = csv_content.encode("utf-8")
    report_bytes = validation_report.encode("utf-8")
    payloads = {
        "data/registros.csv": csv_bytes,
        "reports/validacao.md": report_bytes,
    }
    files = [
        _file_entry(
            "data/registros.csv",
            "observations",
            "text/csv",
            len(csv_bytes),
            hashlib.sha256(csv_bytes).hexdigest(),
            "restricted",
        ),
        _file_entry(
            "reports/validacao.md",
            "validation_report",
            "text/markdown",
            len(report_bytes),
            hashlib.sha256(report_bytes).hexdigest(),
            "restricted",
        ),
    ]

    manifest = build_manifest_v2(campaign, files, producer_version, node_identity)

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
    """Lê token de serviço ou credencial de máquina de arquivo protegido."""
    token = Path(path).read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError("arquivo de token vazio")
    return token


def fetch_contexts_from_nexo(
    base_url: str,
    token: str,
    *,
    ca_file: Optional[str] = None,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    """
    MC-NEXO-02: Consome GET /api/v1/integrations/morfocampo/contexts do Nexo.
    """
    parsed = parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL do Nexo inválida")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("HTTP sem TLS é permitido somente em loopback")

    endpoint = base_url.rstrip("/") + "/api/v1/integrations/morfocampo/contexts"
    req = request.Request(
        endpoint,
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "X-MorfoNode-Credential": token,
        },
    )
    context = ssl.create_default_context(cafile=ca_file) if parsed.scheme == "https" else None
    with request.urlopen(req, timeout=timeout_seconds, context=context) as response:
        payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, dict) and "contexts" in payload:
            return payload["contexts"]
        if isinstance(payload, list):
            return payload
        return [payload]


def send_package_file(
    artifact_path: Path | str,
    base_url: str,
    token: str,
    *,
    ca_file: Optional[str] = None,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """
    MC-NEXO-07: Envia o pacote CampoSync 2.0.0 para o Nexo com tolerância e receipt.
    POST /api/v1/integrations/morfocampo/packages
    Trata 409 (já recebido) como sucesso lógico (idempotência).
    """
    parsed = parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL de sincronização inválida")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("HTTP sem TLS é permitido somente em loopback")

    # Suporta rota padrão Nexo /api/v1/integrations/morfocampo/packages e fallback para base informada
    if base_url.rstrip("/").endswith("/packages"):
        endpoint = base_url.rstrip("/")
    else:
        endpoint = base_url.rstrip("/") + "/api/v1/integrations/morfocampo/packages"

    artifact = Path(artifact_path)
    if not artifact.exists():
        raise FileNotFoundError(f"Artefato não encontrado: {artifact_path}")

    content = artifact.read_bytes()
    upload = request.Request(
        endpoint,
        data=content,
        method="POST",
        headers={
            "Content-Type": "application/zip",
            "Authorization": f"Bearer {token}",
            "X-MorfoNode-Credential": token,
            "X-SisTer-Campo-Token": token,  # Compatibilidade transitória
        },
    )
    context = ssl.create_default_context(cafile=ca_file) if parsed.scheme == "https" else None

    try:
        with request.urlopen(upload, timeout=timeout_seconds, context=context) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except url_error.HTTPError as exc:
        if exc.code == 409:
            # Idempotência: o Nexo já possui este pacote; trata como sucesso lógico
            try:
                body = json.loads(exc.read().decode("utf-8"))
            except Exception:
                body = {}
            return {
                "status": "acknowledged",
                "repeated": True,
                "receipt": body.get("receipt", {}),
                "message": "Pacote já registrado no Nexo (idempotência garantida)",
            }
        raise


def send_package(
    package: io.BytesIO,
    base_url: str,
    token: str,
    *,
    ca_file: Optional[str] = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Wrapper compatível aceitando io.BytesIO."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(package.getvalue())
        tmp_path = Path(tmp.name)
    try:
        return send_package_file(
            tmp_path,
            base_url,
            token,
            ca_file=ca_file,
            timeout_seconds=timeout_seconds,
        )
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass

