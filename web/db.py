"""
db.py — camada SQLite3 do morfocampo-web.

Schema derivado diretamente do TreeRecord.hpp do núcleo C++.
Preserva raw_input e audio_file como evidência documental digital
complementar ao registro em papel.
"""

import sqlite3
import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id              TEXT NOT NULL,
    campaign_id             TEXT NOT NULL,
    area                    TEXT NOT NULL DEFAULT '',
    max_cap_cm              REAL,
    max_dap_cm              REAL,
    max_height_m            REAL,
    max_crown_m             REAL,
    mode                    TEXT NOT NULL DEFAULT 'integrated',
    context_id              TEXT,
    research_activity_id    TEXT,
    operational_activity_id TEXT,
    morfonode_id            TEXT,
    context_revision        INTEGER DEFAULT 1,
    created_at              TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(project_id, campaign_id)
);

-- MC-NEXO-01: Identidade local persistente do MorfoNode
CREATE TABLE IF NOT EXISTS morfonode_identity (
    morfonode_id        TEXT PRIMARY KEY,
    hardware_serial     TEXT NOT NULL,
    credential_id       TEXT NOT NULL,
    credential_token    TEXT NOT NULL,
    registration_state  TEXT NOT NULL DEFAULT 'registered',
    registered_at       TEXT DEFAULT (datetime('now','localtime')),
    updated_at          TEXT DEFAULT (datetime('now','localtime'))
);

-- MC-NEXO-02: Cache local de Collection Context provisionado pelo Nexo
CREATE TABLE IF NOT EXISTS collection_contexts (
    context_id               TEXT PRIMARY KEY,
    project_id               TEXT NOT NULL,
    research_activity_id     TEXT NOT NULL,
    operational_activity_id  TEXT,
    morfonode_id             TEXT NOT NULL,
    status                   TEXT NOT NULL DEFAULT 'active',
    valid_from               TEXT NOT NULL,
    valid_until              TEXT,
    revision                 INTEGER NOT NULL DEFAULT 1,
    payload_json             TEXT NOT NULL DEFAULT '{}',
    cached_at                TEXT DEFAULT (datetime('now','localtime'))
);

-- MC-NEXO-06: Fila persistente de sincronização (Outbox durável)
CREATE TABLE IF NOT EXISTS outbox_packages (
    package_id      TEXT PRIMARY KEY,
    campaign_fk     INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    context_id      TEXT NOT NULL,
    checksum        TEXT NOT NULL,
    artifact_path   TEXT NOT NULL,
    state           TEXT NOT NULL DEFAULT 'pending',
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    receipt_id      TEXT,
    error_message   TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_outbox_state ON outbox_packages(state);
CREATE INDEX IF NOT EXISTS idx_outbox_campaign ON outbox_packages(campaign_fk);

CREATE TABLE IF NOT EXISTS tree_records (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_fk           INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    plot                  TEXT NOT NULL DEFAULT '',
    transect              TEXT NOT NULL DEFAULT '',
    tree_id               TEXT NOT NULL,
    species               TEXT NOT NULL DEFAULT '',
    cap_cm                REAL,
    dap_cm                REAL,
    cap_source            TEXT NOT NULL DEFAULT 'missing',
    dap_source            TEXT NOT NULL DEFAULT 'missing',
    total_height_m        REAL,
    crown_height_m        REAL,
    crown_diameter_ns_m   REAL,
    crown_diameter_ew_m   REAL,
    condition             TEXT NOT NULL DEFAULT '',
    observer              TEXT NOT NULL DEFAULT '',
    date                  TEXT NOT NULL DEFAULT '',
    latitude              REAL,
    longitude             REAL,
    notes                 TEXT NOT NULL DEFAULT '',
    source                TEXT NOT NULL DEFAULT 'web_voice',
    confidence_flag       TEXT NOT NULL DEFAULT 'ok',
    raw_input             TEXT NOT NULL DEFAULT '',
    audio_file            TEXT,
    -- Campos específicos do protocolo IRDER
    stem_height_m         REAL,
    crown_insertion_m     REAL,
    crown_density         INTEGER,
    stem_form             TEXT NOT NULL DEFAULT '',
    sociological_position TEXT NOT NULL DEFAULT '',
    trait_1               TEXT NOT NULL DEFAULT '',
    trait_2               TEXT NOT NULL DEFAULT '',
    created_at            TEXT DEFAULT (datetime('now','localtime')),
    updated_at            TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS validation_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_fk    INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    run_at         TEXT DEFAULT (datetime('now','localtime')),
    report_md      TEXT NOT NULL DEFAULT '',
    total_records  INTEGER NOT NULL DEFAULT 0,
    error_count    INTEGER NOT NULL DEFAULT 0,
    warning_count  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tree_records_campaign ON tree_records(campaign_fk);
CREATE INDEX IF NOT EXISTS idx_tree_records_tree_id  ON tree_records(campaign_fk, plot, tree_id);
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Inicializa schema e migra colunas contextuais e IRDER se necessário."""
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate_campaign_columns(conn)
    _migrate_irder_columns(conn)


# Migração segura: adiciona colunas de contexto institucional (MC-NEXO-03)
_CAMPAIGN_COLUMNS = [
    ("mode", "TEXT NOT NULL DEFAULT 'integrated'"),
    ("context_id", "TEXT"),
    ("research_activity_id", "TEXT"),
    ("operational_activity_id", "TEXT"),
    ("morfonode_id", "TEXT"),
    ("context_revision", "INTEGER DEFAULT 1"),
]


def _migrate_campaign_columns(conn: sqlite3.Connection) -> None:
    """MC-NEXO-03: Garante colunas de contexto do Nexo em bancos existentes."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(campaigns)").fetchall()}
    for col_name, col_type in _CAMPAIGN_COLUMNS:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE campaigns ADD COLUMN {col_name} {col_type}")
    conn.commit()


# Migração segura: adiciona colunas IRDER em bancos existentes
_IRDER_COLUMNS = [
    ("stem_height_m",         "REAL"),
    ("crown_insertion_m",     "REAL"),
    ("crown_density",         "INTEGER"),
    ("stem_form",             "TEXT NOT NULL DEFAULT ''"),
    ("sociological_position", "TEXT NOT NULL DEFAULT ''"),
    ("trait_1",               "TEXT NOT NULL DEFAULT ''"),
    ("trait_2",               "TEXT NOT NULL DEFAULT ''"),
]


def _migrate_irder_columns(conn: sqlite3.Connection) -> None:
    """Adiciona colunas IRDER em bancos legados que não as têm ainda."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(tree_records)").fetchall()}
    for col_name, col_type in _IRDER_COLUMNS:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE tree_records ADD COLUMN {col_name} {col_type}")
    conn.commit()



# ---------------------------------------------------------------------------
# MC-NEXO-01: Identidade local do MorfoNode
# ---------------------------------------------------------------------------

def get_hardware_serial(data_dir: Optional[Path] = None) -> str:
    """MC-NEXO-01: Recupera o número de série físico do MorfoNode (RPi5 ou fallback estável)."""
    # 1. Tentar ler de /proc/cpuinfo (Raspberry Pi hardware serial)
    try:
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.exists():
            for line in cpuinfo.read_text(encoding="utf-8").splitlines():
                if line.startswith("Serial"):
                    parts = line.split(":")
                    if len(parts) == 2:
                        serial = parts[1].strip()
                        if serial and serial != "0000000000000000":
                            return serial
    except Exception:
        pass

    # 2. Tentar ler /etc/machine-id
    try:
        mid = Path("/etc/machine-id")
        if mid.exists():
            serial = mid.read_text(encoding="utf-8").strip()
            if serial:
                return serial
    except Exception:
        pass

    # 3. Fallback persistido localmente
    base_dir = data_dir or Path(__file__).resolve().parent
    serial_file = base_dir / ".morfonode_hardware_serial"
    if serial_file.exists():
        content = serial_file.read_text(encoding="utf-8").strip()
        if content:
            return content

    import uuid
    generated = f"rpi-hw-{uuid.uuid4().hex[:12]}"
    try:
        serial_file.write_text(generated, encoding="utf-8")
    except Exception:
        pass
    return generated


def get_node_identity(conn: sqlite3.Connection) -> Optional[dict]:
    """MC-NEXO-01: Retorna a identidade institucional do MorfoNode cadastrada."""
    row = conn.execute(
        "SELECT * FROM morfonode_identity ORDER BY registered_at DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def set_node_identity(
    conn: sqlite3.Connection,
    morfonode_id: str,
    hardware_serial: str,
    credential_id: str,
    credential_token: str,
    registration_state: str = "registered",
) -> dict:
    """MC-NEXO-01: Persiste a identidade e material de credencial autenticado do MorfoNode."""
    conn.execute(
        """INSERT INTO morfonode_identity(
               morfonode_id, hardware_serial, credential_id,
               credential_token, registration_state, updated_at
           )
           VALUES(?,?,?,?,?,datetime('now','localtime'))
           ON CONFLICT(morfonode_id)
           DO UPDATE SET hardware_serial=excluded.hardware_serial,
                         credential_id=excluded.credential_id,
                         credential_token=excluded.credential_token,
                         registration_state=excluded.registration_state,
                         updated_at=datetime('now','localtime')""",
        (morfonode_id, hardware_serial, credential_id, credential_token, registration_state),
    )
    conn.commit()
    return get_node_identity(conn)


def revoke_node_identity(conn: sqlite3.Connection, morfonode_id: str) -> None:
    """MC-NEXO-01: Marca a credencial do MorfoNode como revogada sem apagar dados locais."""
    conn.execute(
        """UPDATE morfonode_identity
           SET registration_state='revoked', updated_at=datetime('now','localtime')
           WHERE morfonode_id=?""",
        (morfonode_id,),
    )
    conn.commit()


def is_node_registered(conn: sqlite3.Connection) -> bool:
    """MC-NEXO-01: Verifica se o nó possui registro ativo válido."""
    ident = get_node_identity(conn)
    return bool(ident and ident.get("registration_state") == "registered")


def is_node_revoked(conn: sqlite3.Connection) -> bool:
    """MC-NEXO-01: Verifica se a credencial do MorfoNode foi revogada."""
    ident = get_node_identity(conn)
    return bool(ident and ident.get("registration_state") == "revoked")


# ---------------------------------------------------------------------------
# MC-NEXO-02: Cache de Collection Context
# ---------------------------------------------------------------------------

def upsert_collection_context(conn: sqlite3.Connection, ctx: dict) -> dict:
    """MC-NEXO-02: Armazena ou atualiza um Collection Context provisionado pelo Nexo."""
    required = ["context_id", "project_id", "research_activity_id", "morfonode_id", "valid_from"]
    for field in required:
        if not ctx.get(field):
            raise ValueError(f"Campo obrigatório '{field}' ausente no Collection Context")

    payload_json = json.dumps(ctx, ensure_ascii=False)
    conn.execute(
        """INSERT INTO collection_contexts(
               context_id, project_id, research_activity_id, operational_activity_id,
               morfonode_id, status, valid_from, valid_until, revision, payload_json, cached_at
           )
           VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))
           ON CONFLICT(context_id)
           DO UPDATE SET
               project_id=excluded.project_id,
               research_activity_id=excluded.research_activity_id,
               operational_activity_id=excluded.operational_activity_id,
               morfonode_id=excluded.morfonode_id,
               status=excluded.status,
               valid_from=excluded.valid_from,
               valid_until=excluded.valid_until,
               revision=excluded.revision,
               payload_json=excluded.payload_json,
               cached_at=datetime('now','localtime')""",
        (
            ctx["context_id"],
            ctx["project_id"],
            ctx["research_activity_id"],
            ctx.get("operational_activity_id"),
            ctx["morfonode_id"],
            ctx.get("status", "active"),
            ctx["valid_from"],
            ctx.get("valid_until"),
            int(ctx.get("revision", 1)),
            payload_json,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM collection_contexts WHERE context_id=?", (ctx["context_id"],)
    ).fetchone()
    return dict(row)


def get_collection_context(conn: sqlite3.Connection, context_id: str) -> Optional[dict]:
    """MC-NEXO-02: Retorna um Collection Context pelo ID."""
    row = conn.execute(
        "SELECT * FROM collection_contexts WHERE context_id=?", (context_id,)
    ).fetchone()
    return dict(row) if row else None


def list_collection_contexts(conn: sqlite3.Connection, only_active: bool = False) -> list[dict]:
    """MC-NEXO-02: Lista os contextos em cache local (offline-first)."""
    if only_active:
        rows = conn.execute(
            "SELECT * FROM collection_contexts WHERE status='active' ORDER BY cached_at DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM collection_contexts ORDER BY cached_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------

def create_campaign(
    conn: sqlite3.Connection,
    project_id: str,
    campaign_id: str,
    area: str = "",
    max_cap_cm: Optional[float] = None,
    max_dap_cm: Optional[float] = None,
    max_height_m: Optional[float] = None,
    max_crown_m: Optional[float] = None,
    *,
    mode: str = "integrated",
    context_id: Optional[str] = None,
    research_activity_id: Optional[str] = None,
    operational_activity_id: Optional[str] = None,
    morfonode_id: Optional[str] = None,
    context_revision: Optional[int] = None,
) -> int:
    """MC-NEXO-03: Cria campanha vinculada ao contexto institucional do Nexo."""
    if mode == "integrated":
        if not context_id:
            active_contexts = list_collection_contexts(conn, only_active=True)
            if active_contexts:
                raise ValueError("MC-NEXO-03: Selecione um Collection Context provisionado pelo Nexo.")
            else:
                # Se ainda não há contextos no nó recém-instalado, opera como standalone
                mode = "standalone"
        else:
            ctx = get_collection_context(conn, context_id)
            if not ctx:
                raise ValueError(f"MC-NEXO-03: Contexto '{context_id}' não encontrado no cache local.")
            if ctx.get("status") != "active":
                raise ValueError(f"MC-NEXO-03: Contexto '{context_id}' está inativo.")
            project_id = ctx["project_id"]
            research_activity_id = ctx["research_activity_id"]
            operational_activity_id = ctx.get("operational_activity_id")
            morfonode_id = ctx["morfonode_id"]
            context_revision = ctx["revision"]

    conn.execute(
        """INSERT INTO campaigns(
               project_id, campaign_id, area,
               max_cap_cm, max_dap_cm, max_height_m, max_crown_m,
               mode, context_id, research_activity_id, operational_activity_id,
               morfonode_id, context_revision
           )
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(project_id, campaign_id)
           DO UPDATE SET area=excluded.area,
               max_cap_cm=excluded.max_cap_cm,
               max_dap_cm=excluded.max_dap_cm,
               max_height_m=excluded.max_height_m,
               max_crown_m=excluded.max_crown_m,
               mode=excluded.mode,
               context_id=excluded.context_id,
               research_activity_id=excluded.research_activity_id,
               operational_activity_id=excluded.operational_activity_id,
               morfonode_id=excluded.morfonode_id,
               context_revision=excluded.context_revision""",
        (
            project_id, campaign_id, area,
            max_cap_cm, max_dap_cm, max_height_m, max_crown_m,
            mode, context_id, research_activity_id, operational_activity_id,
            morfonode_id, context_revision or 1,
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM campaigns WHERE project_id=? AND campaign_id=?",
        (project_id, campaign_id),
    ).fetchone()
    return row[0]



def list_campaigns(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT c.*, COUNT(r.id) AS record_count
           FROM campaigns c
           LEFT JOIN tree_records r ON r.campaign_fk = c.id
           GROUP BY c.id
           ORDER BY c.created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_campaign(conn: sqlite3.Connection, campaign_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    return dict(row) if row else None


def get_campaign_by_ids(conn: sqlite3.Connection, project_id: str,
                         campaign_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM campaigns WHERE project_id=? AND campaign_id=?",
        (project_id, campaign_id)
    ).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Tree Records
# ---------------------------------------------------------------------------

def insert_record(conn: sqlite3.Connection, campaign_fk: int,
                  record: dict, audio_file: Optional[str] = None) -> int:
    cur = conn.execute(
        """INSERT INTO tree_records(
               campaign_fk, plot, transect, tree_id, species,
               cap_cm, dap_cm, cap_source, dap_source,
               total_height_m, crown_height_m,
               crown_diameter_ns_m, crown_diameter_ew_m,
               condition, observer, date,
               latitude, longitude, notes,
               source, confidence_flag, raw_input, audio_file,
               stem_height_m, crown_insertion_m, crown_density,
               stem_form, sociological_position, trait_1, trait_2)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            campaign_fk,
            record.get("plot", ""),
            record.get("transect", ""),
            record.get("tree_id", ""),
            record.get("species", ""),
            record.get("cap_cm"),
            record.get("dap_cm"),
            record.get("cap_source", "missing"),
            record.get("dap_source", "missing"),
            record.get("total_height_m"),
            record.get("crown_height_m"),
            record.get("crown_diameter_ns_m"),
            record.get("crown_diameter_ew_m"),
            record.get("condition", ""),
            record.get("observer", ""),
            record.get("date", ""),
            record.get("latitude"),
            record.get("longitude"),
            record.get("notes", ""),
            record.get("source", "web_voice"),
            record.get("confidence_flag", "ok"),
            record.get("raw_input", ""),
            audio_file,
            # IRDER
            record.get("stem_height_m"),
            record.get("crown_insertion_m"),
            record.get("crown_density"),
            record.get("stem_form", ""),
            record.get("sociological_position", ""),
            record.get("trait_1", ""),
            record.get("trait_2", ""),
        )
    )
    conn.commit()
    return cur.lastrowid


def update_record(conn: sqlite3.Connection, record_id: int, patch: dict) -> bool:
    """Atualiza campos de um registro (correção). Só atualiza campos presentes em patch."""
    allowed = {
        "plot", "transect", "tree_id", "species",
        "cap_cm", "dap_cm", "total_height_m", "crown_height_m",
        "crown_diameter_ns_m", "crown_diameter_ew_m",
        "condition", "observer", "date", "latitude", "longitude",
        "notes", "confidence_flag", "raw_input",
        # IRDER
        "stem_height_m", "crown_insertion_m", "crown_density",
        "stem_form", "sociological_position", "trait_1", "trait_2",
    }
    fields = {k: v for k, v in patch.items() if k in allowed}
    if not fields:
        return False
    fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [record_id]
    conn.execute(f"UPDATE tree_records SET {set_clause} WHERE id=?", values)
    conn.commit()
    return True


def list_records(conn: sqlite3.Connection, campaign_fk: int,
                 plot: Optional[str] = None,
                 observer: Optional[str] = None) -> list[dict]:
    """Lista registros. Filtra por parcela e/ou observador (sessão exclusiva por observador)."""
    conditions = ["campaign_fk=?"]
    params: list = [campaign_fk]
    if plot:
        conditions.append("plot=?")
        params.append(plot)
    if observer:
        conditions.append("observer=?")
        params.append(observer)
    where = " AND ".join(conditions)
    rows = conn.execute(
        f"SELECT * FROM tree_records WHERE {where} ORDER BY created_at",
        params
    ).fetchall()
    return [dict(r) for r in rows]


def get_record(conn: sqlite3.Connection, record_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM tree_records WHERE id=?", (record_id,)).fetchone()
    return dict(row) if row else None


def delete_record(conn: sqlite3.Connection, record_id: int) -> bool:
    conn.execute("DELETE FROM tree_records WHERE id=?", (record_id,))
    conn.commit()
    return True


# ---------------------------------------------------------------------------
# Validation runs
# ---------------------------------------------------------------------------

def save_validation_run(conn: sqlite3.Connection, campaign_fk: int,
                         report_md: str, total: int,
                         errors: int, warnings: int) -> int:
    cur = conn.execute(
        """INSERT INTO validation_runs(campaign_fk, report_md,
               total_records, error_count, warning_count)
           VALUES(?,?,?,?,?)""",
        (campaign_fk, report_md, total, errors, warnings)
    )
    conn.commit()
    return cur.lastrowid


def last_validation(conn: sqlite3.Connection,
                    campaign_fk: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM validation_runs WHERE campaign_fk=? ORDER BY run_at DESC LIMIT 1",
        (campaign_fk,)
    ).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "project_id", "campaign_id", "area", "plot", "transect", "tree_id",
    "species", "cap_cm", "dap_cm", "total_height_m", "crown_height_m",
    "crown_diameter_ns_m", "crown_diameter_ew_m", "condition",
    "observer", "date", "latitude", "longitude", "notes",
    "source", "confidence_flag", "raw_input",
    # IRDER
    "stem_height_m", "crown_insertion_m", "crown_density",
    "stem_form", "sociological_position", "trait_1", "trait_2",
]


def stream_csv_lines(conn: sqlite3.Connection, campaign_fk: int, chunk_size: int = 200):
    """MC-NEXO-05: Leitura incremental do SQLite para streaming sem carregar dataset em RAM."""
    camp = get_campaign(conn, campaign_fk)
    if not camp:
        return
    yield ",".join(CSV_COLUMNS) + "\n"
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tree_records WHERE campaign_fk=? ORDER BY id", (campaign_fk,))
    while True:
        rows = cursor.fetchmany(chunk_size)
        if not rows:
            break
        for r in rows:
            row = [
                camp["project_id"], camp["campaign_id"], camp["area"],
                r["plot"] or "", r["transect"] or "", r["tree_id"] or "",
                r["species"] or "",
                str(r["cap_cm"]) if r["cap_cm"] is not None else "",
                str(r["dap_cm"]) if r["dap_cm"] is not None else "",
                str(r["total_height_m"]) if r["total_height_m"] is not None else "",
                str(r["crown_height_m"]) if r["crown_height_m"] is not None else "",
                str(r["crown_diameter_ns_m"]) if r["crown_diameter_ns_m"] is not None else "",
                str(r["crown_diameter_ew_m"]) if r["crown_diameter_ew_m"] is not None else "",
                r["condition"] or "", r["observer"] or "", r["date"] or "",
                str(r["latitude"]) if r["latitude"] is not None else "",
                str(r["longitude"]) if r["longitude"] is not None else "",
                r["notes"] or "",
                r["source"] or "web_voice",
                r["confidence_flag"] or "ok",
                r["raw_input"] or "",
                # IRDER
                str(r["stem_height_m"]) if r["stem_height_m"] is not None else "",
                str(r["crown_insertion_m"]) if r["crown_insertion_m"] is not None else "",
                str(r["crown_density"]) if r["crown_density"] is not None else "",
                r["stem_form"] or "",
                r["sociological_position"] or "",
                r["trait_1"] or "",
                r["trait_2"] or "",
            ]
            out = io.StringIO()
            writer = csv.writer(out, lineterminator="")
            writer.writerow(row)
            yield out.getvalue() + "\n"


def export_csv_lines(conn: sqlite3.Connection, campaign_fk: int) -> list[str]:
    """Retorna linhas CSV compatíveis com o formato nativo do morfocampo C++."""
    return [line.rstrip("\r\n") for line in stream_csv_lines(conn, campaign_fk)]


# ---------------------------------------------------------------------------
# MC-NEXO-06: Outbox durável
# ---------------------------------------------------------------------------

def enqueue_outbox_package(
    conn: sqlite3.Connection,
    package_id: str,
    campaign_fk: int,
    context_id: str,
    checksum: str,
    artifact_path: str,
    state: str = "pending",
) -> dict:
    """MC-NEXO-06: Enfileira um pacote imutável gerado para envio futuro."""
    conn.execute(
        """INSERT INTO outbox_packages(
               package_id, campaign_fk, context_id, checksum, artifact_path,
               state, attempts, created_at, updated_at
           )
           VALUES(?,?,?,?,?,?,0,datetime('now','localtime'),datetime('now','localtime'))
           ON CONFLICT(package_id)
           DO UPDATE SET
               artifact_path=excluded.artifact_path,
               checksum=excluded.checksum,
               updated_at=datetime('now','localtime')""",
        (package_id, campaign_fk, context_id, checksum, artifact_path, state),
    )
    conn.commit()
    pkg = get_outbox_package(conn, package_id)
    if not pkg:
        raise RuntimeError(f"Falha ao carregar pacote recém enfileirado: {package_id}")
    return pkg


def get_outbox_package(conn: sqlite3.Connection, package_id: str) -> Optional[dict]:
    """MC-NEXO-06: Busca item do outbox pelo package_id."""
    row = conn.execute("SELECT * FROM outbox_packages WHERE package_id=?", (package_id,)).fetchone()
    return dict(row) if row else None


def get_outbox_package_by_campaign(conn: sqlite3.Connection, campaign_fk: int) -> Optional[dict]:
    """MC-NEXO-06: Busca o pacote mais recente de uma campanha no outbox."""
    row = conn.execute(
        "SELECT * FROM outbox_packages WHERE campaign_fk=? ORDER BY created_at DESC LIMIT 1",
        (campaign_fk,),
    ).fetchone()
    return dict(row) if row else None


def list_outbox_packages(conn: sqlite3.Connection, state: Optional[str] = None) -> list[dict]:
    """MC-NEXO-06: Lista pacotes no outbox, opcionalmente filtrando por estado."""
    if state:
        rows = conn.execute(
            "SELECT * FROM outbox_packages WHERE state=? ORDER BY created_at ASC",
            (state,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM outbox_packages ORDER BY created_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_outbox_package_state(
    conn: sqlite3.Connection,
    package_id: str,
    state: str,
    *,
    receipt_id: Optional[str] = None,
    error_message: Optional[str] = None,
    increment_attempt: bool = False,
) -> Optional[dict]:
    """MC-NEXO-06: Atualiza o estado da sincronização do pacote de forma atômica."""
    att_clause = "attempts = attempts + 1," if increment_attempt else ""
    conn.execute(
        f"""UPDATE outbox_packages
           SET state=?,
               {att_clause}
               last_attempt_at=datetime('now','localtime'),
               receipt_id=COALESCE(?, receipt_id),
               error_message=?,
               updated_at=datetime('now','localtime')
           WHERE package_id=?""",
        (state, receipt_id, error_message, package_id),
    )
    conn.commit()
    return get_outbox_package(conn, package_id)



def export_campaign_sql(conn: sqlite3.Connection, campaign_fk: int) -> str:
    """Retorna dump SQL autocontido para uma campanha e seus registros."""
    camp = get_campaign(conn, campaign_fk)
    if not camp:
        return ""

    lines = [
        "-- Morfocampo campaign export",
        f"-- project_id={camp['project_id']} campaign_id={camp['campaign_id']}",
        "PRAGMA foreign_keys=OFF;",
        "BEGIN TRANSACTION;",
    ]
    for table in ("campaigns", "tree_records", "validation_runs"):
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if row and row["sql"]:
            lines.append(f"{row['sql']};")

    def insert_statement(table: str, row: sqlite3.Row) -> str:
        columns = row.keys()
        quoted_columns = ", ".join(f'"{col}"' for col in columns)
        values = ", ".join(
            "NULL" if row[col] is None else conn.execute("SELECT quote(?)", (row[col],)).fetchone()[0]
            for col in columns
        )
        return f'INSERT INTO "{table}" ({quoted_columns}) VALUES ({values});'

    campaign_row = conn.execute("SELECT * FROM campaigns WHERE id=?", (campaign_fk,)).fetchone()
    if campaign_row:
        lines.append(insert_statement("campaigns", campaign_row))

    for table in ("tree_records", "validation_runs"):
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE campaign_fk=? ORDER BY id",
            (campaign_fk,),
        ).fetchall()
        for row in rows:
            lines.append(insert_statement(table, row))

    lines.extend(["COMMIT;", "PRAGMA foreign_keys=ON;", ""])
    return "\n".join(lines)
