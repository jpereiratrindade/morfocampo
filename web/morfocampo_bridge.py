"""
morfocampo_bridge.py — chama o binário C++ morfocampo via subprocess.

Mantém o núcleo C++ como fonte única de verdade para parsing e validação.
Nenhuma lógica de validação é duplicada aqui.
"""

import csv
import io
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class MorfocampoBridge:
    """Wrapper do binário morfocampo C++ para uso pela API web."""

    def __init__(self, binary_path: str):
        self.binary = Path(binary_path).resolve()
        if not self.binary.exists():
            raise FileNotFoundError(
                f"Binário morfocampo não encontrado em: {self.binary}\n"
                "Execute: cmake -S . -B build && cmake --build build"
            )

    # ------------------------------------------------------------------
    # parse_voice_text — interpreta uma linha de fala estruturada
    # ------------------------------------------------------------------

    def parse_voice_text(self, text: str, defaults: Optional[dict] = None) -> dict:
        """
        Envia uma linha de fala para morfocampo parse-voice e retorna
        o registro interpretado como dict.

        defaults: project_id, campaign_id, area, plot, transect, observer, date
        """
        defaults = defaults or {}

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "voice_line.txt"
            out_dir = Path(tmpdir) / "out"

            # Pré-preenche defaults na frase se não vierem já na voz
            prefix_parts = []
            for key, voice_key in [
                ("project_id", "projeto"),
                ("campaign_id", "campanha"),
                ("area", "area"),
                ("plot", "parcela"),
                ("transect", "transecto"),
                ("observer", "observador"),
                ("date", "data"),
            ]:
                val = defaults.get(key, "")
                if val and voice_key not in text.lower():
                    prefix_parts.append(f"{voice_key} {val}")

            full_line = "; ".join(prefix_parts + [text]) if prefix_parts else text
            input_file.write_text(full_line + "\n", encoding="utf-8")

            result = subprocess.run(
                [str(self.binary), "parse-voice",
                 "--input", str(input_file),
                 "--out", str(out_dir / "dados.csv")],
                capture_output=True, text=True, timeout=10
            )

            csv_path = out_dir / "dados.csv"
            if not csv_path.exists():
                return {
                    "ok": False,
                    "error": result.stderr.strip() or "parse-voice não gerou saída",
                    "raw_input": text,
                    "confidence_flag": "erro",
                }

            records = self._read_csv(csv_path)
            if not records:
                return {
                    "ok": False,
                    "error": "Nenhum registro interpretado",
                    "raw_input": text,
                    "confidence_flag": "erro",
                }

            rec = records[0]
            rec["ok"] = True
            rec["raw_input"] = text
            rec["warnings"] = [
                line.strip()
                for line in result.stderr.splitlines()
                if line.strip()
            ]
            return rec

    # ------------------------------------------------------------------
    # validate — valida todos os registros de uma campanha
    # ------------------------------------------------------------------

    def validate(self, csv_content: str,
                 max_cap: Optional[float] = None,
                 max_dap: Optional[float] = None,
                 max_height: Optional[float] = None,
                 max_crown: Optional[float] = None) -> dict:
        """
        Recebe conteúdo CSV (string) e executa morfocampo validate.
        Retorna dict com report_md, total, errors, warnings.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "records.csv"
            out_dir = Path(tmpdir) / "val"
            input_file.write_text(csv_content, encoding="utf-8")

            cmd = [
                str(self.binary), "validate",
                "--input", str(input_file),
                "--out", str(out_dir),
            ]
            for flag, val in [
                ("--max-cap", max_cap),
                ("--max-dap", max_dap),
                ("--max-height", max_height),
                ("--max-crown", max_crown),
            ]:
                if val is not None:
                    cmd += [flag, str(val)]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            report_path = out_dir / "relatorio_validacao.md"
            report_md = ""
            if report_path.exists():
                report_md = report_path.read_text(encoding="utf-8")

            # Extrai contagens do relatório
            total = errors = warnings = 0
            for line in report_md.splitlines():
                if line.startswith("- Total de registros:"):
                    try:
                        total = int(line.split(":")[-1].strip())
                    except ValueError:
                        pass
                elif line.startswith("- Erros:"):
                    try:
                        errors = int(line.split(":")[-1].strip())
                    except ValueError:
                        pass
                elif line.startswith("- Avisos:"):
                    try:
                        warnings = int(line.split(":")[-1].strip())
                    except ValueError:
                        pass

            return {
                "ok": result.returncode == 0 or report_md,
                "report_md": report_md,
                "total": total,
                "errors": errors,
                "warnings": warnings,
                "stderr": result.stderr.strip(),
            }

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _read_csv(path: Path) -> list[dict]:
        """Lê CSV gerado pelo morfocampo e retorna lista de dicts."""
        text = path.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in reader:
            parsed: dict = {}
            for key, val in row.items():
                val = val.strip()
                if key in {"cap_cm", "dap_cm", "total_height_m",
                           "crown_height_m", "crown_diameter_ns_m",
                           "crown_diameter_ew_m", "latitude", "longitude",
                           # Campos IRDER numéricos
                           "stem_height_m", "crown_insertion_m"}:
                    try:
                        parsed[key] = float(val) if val else None
                    except ValueError:
                        parsed[key] = None
                elif key == "crown_density":
                    try:
                        parsed[key] = int(val) if val else None
                    except ValueError:
                        parsed[key] = None
                else:
                    parsed[key] = val
            rows.append(parsed)
        return rows

    # ------------------------------------------------------------------
    # import_irder — importa CSV do protocolo IRDER
    # ------------------------------------------------------------------

    def import_irder(self, csv_bytes: bytes, filename: str,
                     project_id: str, campaign_id: str,
                     area: str, observer: str = "") -> dict:
        """
        Recebe bytes de um CSV IRDER, chama morfocampo import-irder
        e retorna dict com records (lista de dicts) + issues.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / safe_temp_filename(filename)
            out_dir    = Path(tmpdir) / "out"
            input_file.write_bytes(csv_bytes)

            cmd = [
                str(self.binary), "import-irder",
                "--input",   str(input_file),
                "--project", project_id,
                "--campaign", campaign_id,
                "--area",    area,
                "--out",     str(out_dir),
            ]
            if observer:
                cmd += ["--observer", observer]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            csv_out = out_dir / "arvores_irder.csv"
            if not csv_out.exists():
                return {
                    "ok": False,
                    "error": result.stderr.strip() or "import-irder não gerou saída",
                    "records": [],
                    "issues": [],
                }

            records = self._read_csv(csv_out)

            # Parseia avisos/erros do stderr
            issues = [
                line.strip()
                for line in result.stderr.splitlines()
                if line.strip()
            ]

            return {
                "ok": True,
                "records": records,
                "total": len(records),
                "issues": issues,
            }


def safe_temp_filename(filename: str, fallback: str = "upload.csv") -> str:
    name = Path(filename or fallback).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name or fallback
