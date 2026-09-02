"""
test_server_endpoints.py — Testes funcionais dos endpoints FastAPI de integracao Nexo.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
sys.path.insert(0, str(WEB_DIR))

import server
import db


class ServerEndpointsTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="morfocampo_server_test_")
        self.db_path = Path(self.tmp_dir) / "test_api.db"
        self.conn = db.get_connection(str(self.db_path))
        db.init_db(self.conn)

        # Injetar banco de teste no servidor
        server._conn = self.conn
        server.DB_PATH = str(self.db_path)
        server.OUTBOX_DIR = Path(self.tmp_dir) / "outbox"
        server.OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        self.client = TestClient(server.app)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_morfonode_identity_endpoints(self):
        """Testa endpoints /api/morfonode/status, /identity e /revoke."""
        res = self.client.get("/api/morfonode/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["is_registered"])

        # Registrar nó
        res_post = self.client.post("/api/morfonode/identity", json={
            "morfonode_id": "rpi5-node-99",
            "credential_id": "cred-99",
            "credential_token": "token-99",
            "registration_state": "registered",
        })
        self.assertEqual(res_post.status_code, 200)

        res_after = self.client.get("/api/morfonode/status")
        self.assertTrue(res_after.json()["is_registered"])

        # Revogar nó
        res_rev = self.client.post("/api/morfonode/revoke", json={"morfonode_id": "rpi5-node-99"})
        self.assertEqual(res_rev.status_code, 200)
        self.assertTrue(self.client.get("/api/morfonode/status").json()["is_revoked"])

    def test_contexts_and_integrated_campaign(self):
        """Testa provisionamento de contexto em cache e criação de campanha vinculada."""
        # Salva contexto
        db.upsert_collection_context(self.conn, {
            "context_id": "ctx-cerrado-01",
            "project_id": "CERRADO_2026",
            "research_activity_id": "ACT_CERRADO",
            "morfonode_id": "rpi5-node-99",
            "valid_from": "2026-01-01T00:00:00Z",
            "revision": 1,
        })

        res_ctx = self.client.get("/api/contexts")
        self.assertEqual(res_ctx.status_code, 200)
        self.assertEqual(len(res_ctx.json()), 1)

        # Criar campanha integrada
        res_camp = self.client.post("/api/campaigns", json={
            "campaign_id": "CAMP_CERRADO_A",
            "area": "Goiás",
            "mode": "integrated",
            "context_id": "ctx-cerrado-01",
        })
        self.assertEqual(res_camp.status_code, 201)
        camp_data = res_camp.json()
        self.assertEqual(camp_data["project_id"], "CERRADO_2026")
        self.assertEqual(camp_data["context_id"], "ctx-cerrado-01")

        # Inserir registro
        db.insert_record(self.conn, camp_data["id"], {
            "tree_id": "T01",
            "species": "Caryocar brasiliense",
            "cap_cm": 80.0,
        })

        # Materializar no outbox
        res_outbox = self.client.post(f"/api/campaigns/{camp_data['id']}/outbox")
        self.assertEqual(res_outbox.status_code, 200)
        pkg_info = res_outbox.json()
        self.assertEqual(pkg_info["status"], "enqueued")
        self.assertTrue(Path(pkg_info["artifact_path"]).exists())

        # Listar outbox
        res_list = self.client.get("/api/outbox")
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.json()), 1)
        self.assertEqual(res_list.json()[0]["state"], "pending")

        # Baixar CampoSync 2.0.0
        res_dl = self.client.get(f"/api/campaigns/{camp_data['id']}/export.camposync")
        self.assertEqual(res_dl.status_code, 200)
        self.assertEqual(res_dl.headers.get("x-camposync-contract-version"), "2.0.0")


if __name__ == "__main__":
    unittest.main()
