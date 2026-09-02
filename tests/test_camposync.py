from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
import zipfile


WEB_DIR = Path(__file__).resolve().parents[1] / "web"
sys.path.insert(0, str(WEB_DIR))

from camposync import build_package, calculate_contents_checksum, send_package


class CampoSyncExportTests(unittest.TestCase):
    def test_builds_idempotent_contract_package(self):
        campaign = {
            "project_id": "MORFO_CAMPO_2026",
            "campaign_id": "C01",
        }
        first, first_manifest = build_package(
            campaign, "project_id,campaign_id\nP,C01\n", "# Validado\n", "0.2.4"
        )
        _, second_manifest = build_package(
            campaign, "project_id,campaign_id\nP,C01\n", "# Validado\n", "0.2.4"
        )
        self.assertEqual(first_manifest["package_id"], second_manifest["package_id"])
        self.assertEqual(first_manifest["checksum"], second_manifest["checksum"])
        self.assertEqual(
            first_manifest["checksum"],
            calculate_contents_checksum(first_manifest["files"]),
        )
        with zipfile.ZipFile(first) as archive:
            self.assertEqual(
                json.loads(archive.read("manifest.json"))["contract"],
                "camposync.package",
            )
            self.assertEqual(
                set(archive.namelist()),
                {"manifest.json", "data/registros.csv", "reports/validacao.md"},
            )

    def test_api_channel_transports_the_same_zip(self):
        package, _ = build_package(
            {"project_id": "PAMPA", "campaign_id": "C01"},
            "project_id,campaign_id\nPAMPA,C01\n",
            "# Validado\n",
            "0.2.4",
        )
        response = MagicMock()
        response.read.return_value = b'{"status":"validated","repeated":false}'
        response.__enter__.return_value = response
        with patch("camposync.request.urlopen", return_value=response) as urlopen:
            result = send_package(
                package,
                "http://127.0.0.1:8013",
                "service-token",
            )
        sent = urlopen.call_args.args[0]
        self.assertEqual(sent.data, package.getvalue())
        self.assertEqual(sent.headers["X-sister-campo-token"], "service-token")
        self.assertEqual(result["status"], "validated")

    def test_rejects_cleartext_remote_api(self):
        package, _ = build_package(
            {"project_id": "PAMPA", "campaign_id": "C01"},
            "a,b\n",
            "# Validado\n",
            "0.2.4",
        )
        with self.assertRaises(ValueError):
            send_package(package, "http://192.0.2.10:8013", "service-token")


if __name__ == "__main__":
    unittest.main()
