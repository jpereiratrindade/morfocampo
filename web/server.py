"""
server.py — API FastAPI do morfocampo-web.

Uso:
  python server.py --db campo.db --bin ../build/morfocampo --port 8000

Acesso no celular (mesma rede WiFi):
  http://<IP-do-notebook>:8000
"""

import argparse
import os
import re
import sys
import zipfile
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Módulos locais
sys.path.insert(0, str(Path(__file__).parent))
import db
import transcriber
from morfocampo_bridge import MorfocampoBridge


# ---------------------------------------------------------------------------
# Argumentos CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="morfocampo web server")
    p.add_argument("--db",   default="campo.db",         help="Caminho do banco SQLite3")
    p.add_argument("--bin",  default="../build/morfocampo", help="Caminho do binário morfocampo C++")
    p.add_argument("--port", type=int, default=8000,      help="Porta HTTP/HTTPS")
    p.add_argument("--host", default="0.0.0.0",           help="Host (0.0.0.0 para aceitar celulares na rede)")
    p.add_argument("--audio-dir", default="audio_files",  help="Diretório para armazenar áudios gravados")
    p.add_argument("--ssl-keyfile", default=None,         help="Caminho para chave SSL")
    p.add_argument("--ssl-certfile", default=None,        help="Caminho para certificado SSL")
    return p.parse_args()


args = parse_args()

# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

DB_PATH   = args.db
AUDIO_DIR = Path(args.audio_dir)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

_conn = db.get_connection(DB_PATH)
db.init_db(_conn)

bridge = MorfocampoBridge(args.bin)

app = FastAPI(
    title="morfocampo Web",
    description="Coleta de dados morfométricos de campo com áudio e SQLite",
    version="0.2.0",
)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Root — serve o SPA
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>morfocampo web</h1><p>static/index.html não encontrado.</p>")


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def status():
    return {
        "ok": True,
        "version": "0.2.0",
        "db": DB_PATH,
        "binary": args.bin,
        "transcription": transcriber.get_model_status(),
        "timestamp": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------

class CampaignCreate(BaseModel):
    project_id: str
    campaign_id: str
    area: str = ""
    max_cap_cm: Optional[float] = None
    max_dap_cm: Optional[float] = None
    max_height_m: Optional[float] = None
    max_crown_m: Optional[float] = None


@app.get("/api/campaigns")
async def list_campaigns():
    return db.list_campaigns(_conn)


@app.post("/api/campaigns", status_code=201)
async def create_campaign(body: CampaignCreate):
    cid = db.create_campaign(
        _conn,
        body.project_id, body.campaign_id, body.area,
        body.max_cap_cm, body.max_dap_cm,
        body.max_height_m, body.max_crown_m,
    )
    return db.get_campaign(_conn, cid)


@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int):
    camp = db.get_campaign(_conn, campaign_id)
    if not camp:
        raise HTTPException(404, "Campanha não encontrada")
    return camp


# ---------------------------------------------------------------------------
# Transcrição de áudio
# ---------------------------------------------------------------------------

@app.post("/api/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(default="pt"),
):
    """
    Recebe blob de áudio (.webm / .wav / .ogg) e retorna transcrição.
    Usado quando o browser não tem Web Speech API ou está offline.
    """
    audio_bytes = await audio.read()
    result = transcriber.transcribe_bytes(audio_bytes, language=language)
    if not result.get("ok"):
        raise HTTPException(503, detail=result.get("error", "Transcrição falhou"))
    return result


# ---------------------------------------------------------------------------
# Parse — interpreta fala (texto já transcrito)
# ---------------------------------------------------------------------------

class ParseRequest(BaseModel):
    text: str
    defaults: dict = {}


@app.post("/api/parse")
async def parse_voice(body: ParseRequest):
    """
    Recebe texto (já transcrito) e retorna campos interpretados pelo núcleo C++.
    """
    if not body.text.strip():
        raise HTTPException(400, "Texto vazio")
    result = bridge.parse_voice_text(body.text, body.defaults)
    return result


# ---------------------------------------------------------------------------
# Records — CRUD
# ---------------------------------------------------------------------------

class RecordCreate(BaseModel):
    campaign_id: int
    parsed: dict          # campos interpretados pelo parse_voice
    audio_filename: Optional[str] = None


class RecordPatch(BaseModel):
    patch: dict


@app.get("/api/campaigns/{campaign_id}/records")
async def list_records(campaign_id: int, plot: Optional[str] = None,
                       observer: Optional[str] = None):
    camp = db.get_campaign(_conn, campaign_id)
    if not camp:
        raise HTTPException(404, "Campanha não encontrada")
    records = db.list_records(_conn, campaign_id, plot, observer)
    return {"campaign": camp, "records": records, "total": len(records)}


@app.post("/api/records", status_code=201)
async def create_record(body: RecordCreate):
    camp = db.get_campaign(_conn, body.campaign_id)
    if not camp:
        raise HTTPException(404, "Campanha não encontrada")
    record_id = db.insert_record(_conn, body.campaign_id, body.parsed, body.audio_filename)
    return db.get_record(_conn, record_id)


@app.patch("/api/records/{record_id}")
async def patch_record(record_id: int, body: RecordPatch):
    existing = db.get_record(_conn, record_id)
    if not existing:
        raise HTTPException(404, "Registro não encontrado")
    db.update_record(_conn, record_id, body.patch)
    return db.get_record(_conn, record_id)


@app.delete("/api/records/{record_id}", status_code=204)
async def delete_record(record_id: int):
    if not db.get_record(_conn, record_id):
        raise HTTPException(404, "Registro não encontrado")
    db.delete_record(_conn, record_id)


# ---------------------------------------------------------------------------
# Upload de áudio vinculado a registro (evidência documental)
# ---------------------------------------------------------------------------

@app.post("/api/audio")
async def upload_audio(audio: UploadFile = File(...)):
    """
    Salva o arquivo de áudio gravado no campo como evidência documental.
    Retorna o nome do arquivo para vincular ao registro.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    filename = f"audio_{ts}{suffix}"
    file_path = AUDIO_DIR / filename
    content = await audio.read()
    file_path.write_bytes(content)
    return {"filename": filename, "size_bytes": len(content)}


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------

@app.post("/api/campaigns/{campaign_id}/validate")
async def validate_campaign(campaign_id: int):
    camp = db.get_campaign(_conn, campaign_id)
    if not camp:
        raise HTTPException(404, "Campanha não encontrada")

    csv_lines = db.export_csv_lines(_conn, campaign_id)
    if len(csv_lines) <= 1:
        raise HTTPException(400, "Nenhum registro para validar")

    csv_content = "\n".join(csv_lines)
    result = bridge.validate(
        csv_content,
        max_cap=camp.get("max_cap_cm"),
        max_dap=camp.get("max_dap_cm"),
        max_height=camp.get("max_height_m"),
        max_crown=camp.get("max_crown_m"),
    )

    run_id = db.save_validation_run(
        _conn, campaign_id,
        result["report_md"],
        result["total"],
        result["errors"],
        result["warnings"],
    )

    return {
        "run_id": run_id,
        "total": result["total"],
        "errors": result["errors"],
        "warnings": result["warnings"],
        "report_md": result["report_md"],
    }


# ---------------------------------------------------------------------------
# Importação CSV IRDER
# ---------------------------------------------------------------------------

@app.post("/api/campaigns/{campaign_id}/import-irder", status_code=201)
async def import_irder(
    campaign_id: int,
    file: UploadFile = File(...),
    observer: str = Form(default=""),
):
    """
    Recebe um CSV exportado do LibreOffice no formato IRDER e importa
    todos os registros na campanha informada.
    """
    camp = db.get_campaign(_conn, campaign_id)
    if not camp:
        raise HTTPException(404, "Campanha não encontrada")

    csv_bytes = await file.read()
    filename  = file.filename or "irder_import.csv"

    result = bridge.import_irder(
        csv_bytes, filename,
        project_id  = camp["project_id"],
        campaign_id = camp["campaign_id"],
        area        = camp["area"],
        observer    = observer,
    )

    if not result["ok"]:
        raise HTTPException(422, detail=result.get("error", "Falha na importação IRDER"))

    inserted = 0
    for rec in result["records"]:
        try:
            db.insert_record(_conn, campaign_id, rec)
            inserted += 1
        except Exception:
            pass  # Ignora registros com falha individual

    return {
        "inserted": inserted,
        "total_parsed": result["total"],
        "issues": result["issues"],
    }


@app.get("/api/campaigns/{campaign_id}/validation/last")
async def last_validation(campaign_id: int):
    run = db.last_validation(_conn, campaign_id)
    if not run:
        raise HTTPException(404, "Nenhuma validação realizada ainda")
    return run


# ---------------------------------------------------------------------------
# Admin — visão consolidada de todos os observadores (sem filtro)
# ---------------------------------------------------------------------------

@app.get("/api/campaigns/{campaign_id}/admin/summary")
async def admin_summary(campaign_id: int):
    """
    Retorna todos os registros da campanha agrupados por observador.
    Usado pela tela de administração para visão consolidada.
    """
    camp = db.get_campaign(_conn, campaign_id)
    if not camp:
        raise HTTPException(404, "Campanha não encontrada")

    all_records = db.list_records(_conn, campaign_id)

    # Agrupa por observador
    by_observer: dict[str, list] = {}
    for r in all_records:
        obs = r.get("observer") or "(sem observador)"
        by_observer.setdefault(obs, []).append(r)

    # Conta flags
    flag_counts = {"ok": 0, "revisar": 0, "incompleto": 0, "erro": 0}
    for r in all_records:
        flag = r.get("confidence_flag", "ok")
        flag_counts[flag] = flag_counts.get(flag, 0) + 1

    last_run = db.last_validation(_conn, campaign_id)

    return {
        "campaign": camp,
        "total_records": len(all_records),
        "flag_counts": flag_counts,
        "by_observer": {
            obs: {"count": len(recs), "records": recs}
            for obs, recs in sorted(by_observer.items())
        },
        "last_validation": last_run,
    }


# ---------------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------------

@app.get("/api/campaigns/{campaign_id}/export")
async def export_campaign(campaign_id: int):
    """Exporta CSV + último relatório de validação como .zip."""
    camp = db.get_campaign(_conn, campaign_id)
    if not camp:
        raise HTTPException(404, "Campanha não encontrada")

    csv_lines = db.export_csv_lines(_conn, campaign_id)
    csv_content = "\n".join(csv_lines)

    last_run = db.last_validation(_conn, campaign_id)
    report_md = last_run["report_md"] if last_run else "# Sem validação\n\nRode /validate primeiro."

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        slug = f"{camp['project_id']}_{camp['campaign_id']}"
        zf.writestr(f"{slug}_registros.csv", csv_content)
        zf.writestr(f"{slug}_relatorio_validacao.md", report_md)

    zip_buffer.seek(0)
    filename = f"morfocampo_{camp['project_id']}_{camp['campaign_id']}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    protocol = "https" if args.ssl_certfile else "http"
    print(f"🌿 morfocampo web — {protocol}://{args.host}:{args.port}")
    print(f"   Banco:   {DB_PATH}")
    print(f"   Binário: {args.bin}")
    print(f"   Áudios:  {AUDIO_DIR}/")
    print(f"   Transcrição: {transcriber.get_model_status()['message']}")
    print()
    uvicorn_kwargs = {
        "host": args.host,
        "port": args.port,
        "log_level": "info",
    }
    if args.ssl_keyfile and args.ssl_certfile:
        uvicorn_kwargs["ssl_keyfile"] = args.ssl_keyfile
        uvicorn_kwargs["ssl_certfile"] = args.ssl_certfile
        
    uvicorn.run(app, **uvicorn_kwargs)
