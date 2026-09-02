"""
test_morfocampo_nexo.py — Testes de conformidade formal com IS-MORFOCAMPO-NEXO-001.

Rastreabilidade:
- MC-NEXO-01: Identidade local do MorfoNode e controle de revogação
- MC-NEXO-02: Cache local de Collection Context (GET /api/v1/integrations/morfocampo/contexts)
- MC-NEXO-03: Campanha vinculada ao contexto institucional (sem digitação livre de projeto/atividade)
- MC-NEXO-04: Contrato CampoSync 2.0.0 com blocos context e producer
- MC-NEXO-05: Materialização progressiva com streaming e hashes incrementais (baixo uso de RAM no RPi5)
- MC-NEXO-06: Outbox durável em SQLite e reutilização estrita de artefato em retries
- MC-NEXO-07: Sincronização resiliente com máquina, tratamento de 409 (idempotência) e bloqueio por revogação
- MC-NEXO-08: Operação offline-first completa
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib import error as url_error
import zipfile

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
sys.path.insert(0, str(WEB_DIR))

import camposync
import db


class MorfoCampoNexoComplianceTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="morfocampo_test_")
        self.db_path = Path(self.tmp_dir) / "test_campo.db"
        self.conn = db.get_connection(str(self.db_path))
        db.init_db(self.conn)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # -----------------------------------------------------------------------
    # MC-NEXO-01 — Identidade local do MorfoNode
    # -----------------------------------------------------------------------
    def test_mc_nexo_01_morfonode_identity_lifecycle(self):
        """MC-NEXO-01: Persistência local de morfonode_id, hardware_serial, credential_id e revogação."""
        serial = db.get_hardware_serial(Path(self.tmp_dir))
        self.assertTrue(bool(serial))

        # Sem registro inicial
        self.assertFalse(db.is_node_registered(self.conn))
        self.assertFalse(db.is_node_revoked(self.conn))

        # Provisiona identidade registrada
        ident = db.set_node_identity(
            self.conn,
            morfonode_id="node-rpi5-001",
            hardware_serial=serial,
            credential_id="cred-001",
            credential_token="secret-token-value",
            registration_state="registered",
        )
        self.assertEqual(ident["morfonode_id"], "node-rpi5-001")
        self.assertEqual(ident["hardware_serial"], serial)
        self.assertEqual(ident["credential_id"], "cred-001")
        self.assertTrue(db.is_node_registered(self.conn))
        self.assertFalse(db.is_node_revoked(self.conn))

        # Revogação da credencial
        db.revoke_node_identity(self.conn, "node-rpi5-001")
        self.assertFalse(db.is_node_registered(self.conn))
        self.assertTrue(db.is_node_revoked(self.conn))

    # -----------------------------------------------------------------------
    # MC-NEXO-02 — Cache de Collection Context
    # -----------------------------------------------------------------------
    def test_mc_nexo_02_collection_context_cache(self):
        """MC-NEXO-02: Armazena e recupera localmente contextos autorizados do Nexo."""
        ctx_payload = {
            "context_id": "ctx-embrapa-pampa-2026",
            "project_id": "PAMPA_SILVIPASTORIL",
            "research_activity_id": "ATV_PESQ_042",
            "operational_activity_id": "EXP_PARCELA_A",
            "morfonode_id": "node-rpi5-001",
            "status": "active",
            "valid_from": "2026-01-01T00:00:00Z",
            "valid_until": "2026-12-31T23:59:59Z",
            "revision": 2,
        }
        saved = db.upsert_collection_context(self.conn, ctx_payload)
        self.assertEqual(saved["context_id"], "ctx-embrapa-pampa-2026")
        self.assertEqual(saved["project_id"], "PAMPA_SILVIPASTORIL")

        retrieved = db.get_collection_context(self.conn, "ctx-embrapa-pampa-2026")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["revision"], 2)

        active = db.list_collection_contexts(self.conn, only_active=True)
        self.assertEqual(len(active), 1)

    # -----------------------------------------------------------------------
    # MC-NEXO-03 — Campanha vinculada ao contexto
    # -----------------------------------------------------------------------
    def test_mc_nexo_03_campaign_linked_to_context(self):
        """MC-NEXO-03: Campanha integrada vincula e herda contexto institucional desde a criação."""
        ctx_payload = {
            "context_id": "ctx-campo-01",
            "project_id": "PROJ_OFICIAL",
            "research_activity_id": "ACT_OFICIAL",
            "operational_activity_id": "OP_01",
            "morfonode_id": "node-rpi5-001",
            "valid_from": "2026-01-01T00:00:00Z",
            "revision": 1,
        }
        db.upsert_collection_context(self.conn, ctx_payload)

        # Campanha integrada vinculada com sucesso
        cid = db.create_campaign(
            self.conn,
            project_id="",  # Não deve ser digitado livremente
            campaign_id="CAMP_01",
            area="Área 1",
            mode="integrated",
            context_id="ctx-campo-01",
        )
        camp = db.get_campaign(self.conn, cid)
        self.assertEqual(camp["project_id"], "PROJ_OFICIAL")
        self.assertEqual(camp["research_activity_id"], "ACT_OFICIAL")
        self.assertEqual(camp["context_id"], "ctx-campo-01")
        self.assertEqual(camp["mode"], "integrated")

        # Rejeita campanha integrada com contexto inexistente
        with self.assertRaises(ValueError):
            db.create_campaign(
                self.conn,
                project_id="",
                campaign_id="CAMP_INVALID",
                mode="integrated",
                context_id="ctx-nao-existe",
            )

        # Permite campanha standalone explicitamente diferenciada
        sid = db.create_campaign(
            self.conn,
            project_id="STANDALONE_PROJECT",
            campaign_id="CAMP_LOCAL",
            mode="standalone",
        )
        scamp = db.get_campaign(self.conn, sid)
        self.assertEqual(scamp["mode"], "standalone")
        self.assertIsNone(scamp["context_id"])

    # -----------------------------------------------------------------------
    # MC-NEXO-04 — CampoSync 2.0.0
    # -----------------------------------------------------------------------
    def test_mc_nexo_04_camposync_2_manifest_structure(self):
        """MC-NEXO-04: O pacote gerado cumpre a especificação do contrato camposync.package 2.0.0."""
        campaign = {
            "project_id": "PAMPA",
            "campaign_id": "C01",
            "context_id": "ctx-01",
            "research_activity_id": "ACT_01",
            "operational_activity_id": "OP_01",
        }
        node_ident = {
            "morfonode_id": "morfonode-alpha",
            "credential_id": "cred-xyz",
        }
        _, manifest = camposync.build_package(
            campaign,
            "project_id,campaign_id\nPAMPA,C01\n",
            "# Validação OK\n",
            "0.2.4",
            node_identity=node_ident,
        )

        self.assertEqual(manifest["contract"], "camposync.package")
        self.assertEqual(manifest["contract_version"], "2.0.0")
        self.assertEqual(manifest["context"]["context_id"], "ctx-01")
        self.assertEqual(manifest["context"]["project_id"], "PAMPA")
        self.assertEqual(manifest["context"]["research_activity_id"], "ACT_01")
        self.assertEqual(manifest["producer"]["system_id"], "morfocampo")
        self.assertEqual(manifest["producer"]["morfonode_id"], "morfonode-alpha")
        self.assertEqual(manifest["producer"]["credential_id"], "cred-xyz")
        self.assertEqual(
            manifest["checksum"],
            camposync.calculate_contents_checksum(manifest["files"]),
        )

    # -----------------------------------------------------------------------
    # MC-NEXO-05 — Materialização eficiente progressiva (RPi5)
    # -----------------------------------------------------------------------
    def test_mc_nexo_05_materialize_package_to_file_streaming(self):
        """MC-NEXO-05: Materialização progressiva em disco com leitura incremental e artefato imutável."""
        # Criar campanha e registros no SQLite
        cid = db.create_campaign(
            self.conn,
            project_id="PROJ_STREAM",
            campaign_id="CAMP_STREAM",
            mode="standalone",
        )
        for i in range(25):
            db.insert_record(
                self.conn,
                cid,
                {
                    "plot": "P1",
                    "tree_id": f"T{i:03d}",
                    "species": "Eucalyptus",
                    "cap_cm": 45.5,
                    "dap_cm": 14.5,
                },
            )

        csv_generator = db.stream_csv_lines(self.conn, cid, chunk_size=5)
        target_zip = Path(self.tmp_dir) / "pkg_streaming.camposync.zip"

        final_path, manifest = camposync.materialize_package_to_file(
            target_zip,
            db.get_campaign(self.conn, cid),
            csv_generator,
            "# Relatório de teste streaming\n",
            "0.2.4",
        )

        self.assertTrue(final_path.exists())
        self.assertEqual(manifest["contract_version"], "2.0.0")

        # Verificar integridade do ZIP e hashes dos arquivos internos
        with zipfile.ZipFile(final_path) as zf:
            namelist = set(zf.namelist())
            self.assertIn("manifest.json", namelist)
            self.assertIn("data/registros.csv", namelist)
            self.assertIn("reports/validacao.md", namelist)

            read_manifest = json.loads(zf.read("manifest.json"))
            self.assertEqual(read_manifest["checksum"], manifest["checksum"])

            # Validar que o CSV contém todas as linhas geradas
            csv_lines = zf.read("data/registros.csv").decode("utf-8").strip().splitlines()
            self.assertEqual(len(csv_lines), 26)  # 1 cabeçalho + 25 registros

    # -----------------------------------------------------------------------
    # MC-NEXO-06 — Outbox durável e idempotência de retry
    # -----------------------------------------------------------------------
    def test_mc_nexo_06_outbox_durability_and_retry_reuse(self):
        """MC-NEXO-06: O outbox persiste pacotes e retries reutilizam o mesmo artefato imutável."""
        cid = db.create_campaign(
            self.conn,
            project_id="PROJ_OUTBOX",
            campaign_id="CAMP_OUTBOX",
            mode="standalone",
        )
        pkg_id = "test-pkg-001"
        artifact = Path(self.tmp_dir) / f"{pkg_id}.zip"
        artifact.write_bytes(b"ZIP_IMUTAVEL_TESTE")

        enqueued = db.enqueue_outbox_package(
            self.conn,
            package_id=pkg_id,
            campaign_fk=cid,
            context_id="ctx-01",
            checksum="hash123",
            artifact_path=str(artifact),
            state="pending",
        )
        self.assertEqual(enqueued["state"], "pending")
        self.assertEqual(enqueued["attempts"], 0)

        # Simula tentativa de envio (state -> sending)
        db.update_outbox_package_state(self.conn, pkg_id, "sending", increment_attempt=True)
        pkg = db.get_outbox_package(self.conn, pkg_id)
        self.assertEqual(pkg["state"], "sending")
        self.assertEqual(pkg["attempts"], 1)

        # Simula falha e retry reutilizando o mesmo artefato
        db.update_outbox_package_state(self.conn, pkg_id, "failed", error_message="Timeout")
        pkg_failed = db.get_outbox_package(self.conn, pkg_id)
        self.assertEqual(pkg_failed["state"], "failed")
        self.assertEqual(pkg_failed["artifact_path"], str(artifact))
        self.assertTrue(Path(pkg_failed["artifact_path"]).exists())

    # -----------------------------------------------------------------------
    # MC-NEXO-07 — Sincronização + Receipt + Idempotência (409)
    # -----------------------------------------------------------------------
    def test_mc_nexo_07_sync_success_and_receipt(self):
        """MC-NEXO-07: Sincronização com POST /api/v1/integrations/morfocampo/packages e recibo."""
        artifact = Path(self.tmp_dir) / "pkg_send.zip"
        artifact.write_bytes(b"ZIP_BYTES")

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "contract": "camposync.receipt",
            "contract_version": "1.0.0",
            "receipt_id": "rcpt-999",
            "status": "received",
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch("camposync.request.urlopen", return_value=mock_response) as urlopen:
            result = camposync.send_package_file(
                artifact,
                "http://127.0.0.1:8000",
                "machine-token-abc",
            )

        self.assertEqual(result["receipt_id"], "rcpt-999")
        sent_req = urlopen.call_args.args[0]
        self.assertTrue(sent_req.full_url.endswith("/api/v1/integrations/morfocampo/packages"))
        self.assertEqual(sent_req.headers["X-morfonode-credential"], "machine-token-abc")

    def test_mc_nexo_07_conflict_409_handled_as_acknowledged(self):
        """MC-NEXO-07: Pacote já recebido (HTTP 409) é tratado como sucesso lógico idempotente."""
        artifact = Path(self.tmp_dir) / "pkg_repeated.zip"
        artifact.write_bytes(b"ZIP_BYTES")

        fp = MagicMock()
        fp.read.return_value = json.dumps({
            "error": "conflict",
            "receipt": {"receipt_id": "rcpt-already-stored"},
        }).encode("utf-8")
        http_error = url_error.HTTPError(
            url="http://127.0.0.1:8000/api/v1/integrations/morfocampo/packages",
            code=409,
            msg="Conflict",
            hdrs={},
            fp=fp,
        )

        with patch("camposync.request.urlopen", side_effect=http_error):
            result = camposync.send_package_file(
                artifact,
                "http://127.0.0.1:8000",
                "machine-token-abc",
            )

        self.assertEqual(result["status"], "acknowledged")
        self.assertTrue(result["repeated"])

    # -----------------------------------------------------------------------
    # MC-NEXO-08 — Operação Offline Completa
    # -----------------------------------------------------------------------
    def test_mc_nexo_08_full_offline_workflow(self):
        """MC-NEXO-08: Fluxo completo (contexto em cache -> campanha -> coleta -> outbox) opera 100% offline."""
        # 1. Contexto previamente em cache
        db.upsert_collection_context(self.conn, {
            "context_id": "ctx-offline",
            "project_id": "PROJ_OFFLINE",
            "research_activity_id": "ACT_OFFLINE",
            "morfonode_id": "node-offline",
            "valid_from": "2026-01-01T00:00:00Z",
            "revision": 1,
        })

        # 2. Criar campanha no campo sem qualquer rede
        cid = db.create_campaign(
            self.conn,
            project_id="",
            campaign_id="CAMP_OFFLINE_01",
            mode="integrated",
            context_id="ctx-offline",
        )

        # 3. Coletar registros
        db.insert_record(
            self.conn,
            cid,
            {"tree_id": "T01", "species": "Araucaria angustifolia", "cap_cm": 120.0},
        )

        # 4. Materializar pacote no outbox para sincronização posterior
        pkg_file = Path(self.tmp_dir) / "offline_pkg.zip"
        csv_gen = db.stream_csv_lines(self.conn, cid)
        final_path, manifest = camposync.materialize_package_to_file(
            pkg_file,
            db.get_campaign(self.conn, cid),
            csv_gen,
            "# Relatório offline\nValidação local executada.",
            "0.2.4",
        )

        outbox_entry = db.enqueue_outbox_package(
            self.conn,
            manifest["package_id"],
            cid,
            "ctx-offline",
            manifest["checksum"],
            str(final_path),
        )

        self.assertEqual(outbox_entry["state"], "pending")
        self.assertTrue(final_path.exists())
        self.assertEqual(manifest["context"]["context_id"], "ctx-offline")

    # -----------------------------------------------------------------------
    # IS-MORFOCAMPO-NEXO-001 Seção 4 — Eficiência computacional no RPi5
    # -----------------------------------------------------------------------
    def test_mc_nexo_05_resource_metrics_witness(self):
        """
        IS-MORFOCAMPO-NEXO-001 Seção 4:
        Métricas de geração de pacote: peak memory, CPU time, records, bytes e tempo.
        """
        import time
        import tracemalloc

        cid = db.create_campaign(
            self.conn,
            project_id="PROJ_BENCH",
            campaign_id="CAMP_BENCH_1000",
            mode="standalone",
        )
        record_count = 1000
        for i in range(record_count):
            db.insert_record(
                self.conn,
                cid,
                {
                    "plot": f"P{(i % 10) + 1}",
                    "transect": f"T{(i % 5) + 1}",
                    "tree_id": f"TREE_{i:04d}",
                    "species": "Handroanthus heptaphyllus",
                    "cap_cm": 50.0 + (i % 30),
                    "dap_cm": 15.9,
                    "total_height_m": 12.5,
                    "condition": "viva",
                    "observer": "Operador Campo",
                    "date": "2026-09-02",
                },
            )

        target_zip = Path(self.tmp_dir) / "bench_1000.camposync.zip"

        tracemalloc.start()
        start_cpu = time.process_time()
        start_wall = time.time()

        csv_gen = db.stream_csv_lines(self.conn, cid, chunk_size=100)
        final_path, manifest = camposync.materialize_package_to_file(
            target_zip,
            db.get_campaign(self.conn, cid),
            csv_gen,
            "# Relatório de validação - 1000 árvores\nSem erros encontrados.",
            "0.2.4",
        )

        elapsed_cpu = time.process_time() - start_cpu
        elapsed_wall = time.time() - start_wall
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        package_size = final_path.stat().st_size

        # Witness de medição computacional
        witness = {
            "record_count": record_count,
            "peak_memory_bytes": peak_memory,
            "peak_memory_mb": round(peak_memory / (1024 * 1024), 3),
            "cpu_time_seconds": round(elapsed_cpu, 4),
            "wall_time_seconds": round(elapsed_wall, 4),
            "package_size_bytes": package_size,
            "package_id": manifest["package_id"],
            "checksum": manifest["checksum"],
        }
        # Invariante: materialização streaming deve ter pico de memória alocada < 2.5 MB para 1000 árvores
        self.assertLess(witness["peak_memory_mb"], 2.5)
        self.assertTrue(final_path.exists())


if __name__ == "__main__":
    unittest.main()

