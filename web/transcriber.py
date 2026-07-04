"""
transcriber.py — transcrição de áudio local com faster-whisper.

Estratégia:
  1. Cliente usa Web Speech API do browser (zero custo de servidor, tempo real).
  2. Se offline ou browser não suportar → envia blob de áudio para /api/transcribe.
  3. Servidor usa faster-whisper (modelo 'small', pt-BR, offline).

Se faster-whisper não estiver instalado, retorna erro descritivo com instrução
de instalação — o sistema continua funcional via Web Speech API.
"""

import io
import os
import tempfile
from pathlib import Path
from typing import Optional

_whisper_available = False
_whisper_model = None
_whisper_model_size = os.environ.get("MORFOCAMPO_WHISPER_MODEL", "small")

try:
    from faster_whisper import WhisperModel  # type: ignore
    _whisper_available = True
except ImportError:
    pass


def is_available() -> bool:
    return _whisper_available


def get_model_status() -> dict:
    return {
        "available": _whisper_available,
        "model_size": _whisper_model_size if _whisper_available else None,
        "message": (
            "faster-whisper disponível — transcrição offline ativa"
            if _whisper_available
            else "faster-whisper não instalado. Execute: pip install faster-whisper\n"
                 "O sistema funciona via Web Speech API do browser enquanto isso."
        ),
    }


def _load_model() -> Optional["WhisperModel"]:  # type: ignore
    global _whisper_model
    if not _whisper_available:
        return None
    if _whisper_model is None:
        # Carrega na primeira chamada; baixa o modelo se necessário.
        _whisper_model = WhisperModel(
            _whisper_model_size,
            device="cpu",
            compute_type="int8",  # eficiente em CPU, sem GPU necessária
        )
    return _whisper_model


def transcribe_bytes(audio_bytes: bytes, language: str = "pt") -> dict:
    """
    Transcreve áudio (bytes de .webm/.wav/.ogg) com faster-whisper.

    Retorna dict com:
      - text: transcrição
      - language: idioma detectado
      - confidence: confiança média (0-1)
      - segments: lista de segmentos
    """
    if not _whisper_available:
        return {
            "ok": False,
            "error": "faster-whisper não instalado no servidor. Use Web Speech API no browser.",
            "install_hint": "pip install faster-whisper",
        }

    model = _load_model()

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments_gen, info = model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,  # filtra silêncio — importante em campo
            vad_parameters={"min_silence_duration_ms": 300},
        )
        segments = list(segments_gen)
        full_text = " ".join(s.text.strip() for s in segments).strip()
        avg_confidence = (
            sum(getattr(s, "avg_logprob", 0.0) for s in segments) / len(segments)
            if segments else 0.0
        )
        return {
            "ok": True,
            "text": full_text,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "confidence": round(float(avg_confidence), 3),
            "segments": [
                {
                    "start": round(s.start, 2),
                    "end": round(s.end, 2),
                    "text": s.text.strip(),
                }
                for s in segments
            ],
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)
