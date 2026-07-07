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
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    area        TEXT NOT NULL DEFAULT '',
    max_cap_cm  REAL,
    max_dap_cm  REAL,
    max_height_m REAL,
    max_crown_m  REAL,
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    UNIQUE(project_id, campaign_id)
);

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
    """Inicializa schema se ainda não existir e migra colunas IRDER se necessário."""
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate_irder_columns(conn)


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
# Campaigns
# ---------------------------------------------------------------------------

def create_campaign(conn: sqlite3.Connection, project_id: str, campaign_id: str,
                    area: str = "", max_cap_cm: Optional[float] = None,
                    max_dap_cm: Optional[float] = None,
                    max_height_m: Optional[float] = None,
                    max_crown_m: Optional[float] = None) -> int:
    conn.execute(
        """INSERT INTO campaigns(project_id, campaign_id, area,
               max_cap_cm, max_dap_cm, max_height_m, max_crown_m)
           VALUES(?,?,?,?,?,?,?)
           ON CONFLICT(project_id, campaign_id)
           DO UPDATE SET area=excluded.area,
               max_cap_cm=excluded.max_cap_cm,
               max_dap_cm=excluded.max_dap_cm,
               max_height_m=excluded.max_height_m,
               max_crown_m=excluded.max_crown_m""",
        (project_id, campaign_id, area, max_cap_cm, max_dap_cm, max_height_m, max_crown_m)
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM campaigns WHERE project_id=? AND campaign_id=?",
        (project_id, campaign_id)
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


def export_csv_lines(conn: sqlite3.Connection, campaign_fk: int) -> list[str]:
    """Retorna linhas CSV compatíveis com o formato nativo do morfocampo C++."""
    camp = get_campaign(conn, campaign_fk)
    if not camp:
        return []
    records = list_records(conn, campaign_fk)
    lines = [",".join(CSV_COLUMNS)]
    for r in records:
        row = [
            camp["project_id"], camp["campaign_id"], camp["area"],
            r.get("plot", ""), r.get("transect", ""), r.get("tree_id", ""),
            r.get("species", ""),
            str(r["cap_cm"]) if r["cap_cm"] is not None else "",
            str(r["dap_cm"]) if r["dap_cm"] is not None else "",
            str(r["total_height_m"]) if r["total_height_m"] is not None else "",
            str(r["crown_height_m"]) if r["crown_height_m"] is not None else "",
            str(r["crown_diameter_ns_m"]) if r["crown_diameter_ns_m"] is not None else "",
            str(r["crown_diameter_ew_m"]) if r["crown_diameter_ew_m"] is not None else "",
            r.get("condition", ""), r.get("observer", ""), r.get("date", ""),
            str(r["latitude"]) if r["latitude"] is not None else "",
            str(r["longitude"]) if r["longitude"] is not None else "",
            r.get("notes", ""),
            r.get("source", "web_voice"),
            r.get("confidence_flag", "ok"),
            r.get("raw_input", ""),
            # IRDER
            str(r["stem_height_m"]) if r.get("stem_height_m") is not None else "",
            str(r["crown_insertion_m"]) if r.get("crown_insertion_m") is not None else "",
            str(r["crown_density"]) if r.get("crown_density") is not None else "",
            r.get("stem_form", ""),
            r.get("sociological_position", ""),
            r.get("trait_1", ""),
            r.get("trait_2", ""),
        ]
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="")
        writer.writerow(row)
        lines.append(out.getvalue())
    return lines


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
