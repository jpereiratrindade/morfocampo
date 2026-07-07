#!/usr/bin/env python3
"""Generate MorfoNode QR codes for headless field access."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

import qrcode
import qrcode.image.svg

DEFAULT_PORT = "8011"
DEFAULT_HOSTNAME = "morfocampo"
DEFAULT_SSID = "MORFOCAMPO"
DEFAULT_WIFI_PASSWORD = "labecomc"
DEFAULT_ROOT_OUTPUT_DIR = Path("/var/lib/morfocampo")
DEFAULT_LOCAL_OUTPUT_DIR = Path("qr-codes")


def env_value(name: str, default: str) -> str:
    return os.environ.get(name, default)


def escape_wifi_field(value: str) -> str:
    escaped = []
    for char in value:
        if char in {'\\', ';', ',', ':', '"'}:
            escaped.append("\\")
        escaped.append(char)
    return "".join(escaped)


def wifi_payload(ssid: str, password: str, security: str, hidden: bool) -> str:
    security = security.strip().upper()
    if security in {"NONE", "NOPASS", "OPEN"}:
        security = "nopass"
        password_part = ""
    else:
        password_part = f"P:{escape_wifi_field(password)};"

    hidden_part = f"H:{'true' if hidden else 'false'};"
    return (
        "WIFI:"
        f"T:{escape_wifi_field(security)};"
        f"S:{escape_wifi_field(ssid)};"
        f"{password_part}"
        f"{hidden_part}"
        ";"
    )


def make_png(payload: str, output: Path) -> None:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=3,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    image.save(output)


def make_svg(payload: str, output: Path) -> None:
    image = qrcode.make(
        payload,
        image_factory=qrcode.image.svg.SvgPathImage,
        border=2,
    )
    with output.open("wb") as fh:
        image.save(fh)


def parse_args() -> argparse.Namespace:
    port = env_value("MORFOCAMPO_PORT", DEFAULT_PORT)
    hostname = env_value("MORFOCAMPO_HOSTNAME", DEFAULT_HOSTNAME)
    default_url = env_value("MORFOCAMPO_QR_URL", f"https://{hostname}.local:{port}")
    default_ssid = env_value("MORFOCAMPO_WIFI_SSID", DEFAULT_SSID)
    default_password = env_value("MORFOCAMPO_WIFI_PASSWORD", DEFAULT_WIFI_PASSWORD)
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        default_output_dir = DEFAULT_ROOT_OUTPUT_DIR
    else:
        default_output_dir = DEFAULT_LOCAL_OUTPUT_DIR

    parser = argparse.ArgumentParser(
        description="Gera QR codes PNG/SVG para acesso headless ao MorfoNode."
    )
    parser.add_argument(
        "--url",
        default=default_url,
        help=f"URL do app web. Padrao: {default_url}",
    )
    parser.add_argument(
        "--ssid",
        default=default_ssid,
        help=f"SSID da rede Wi-Fi. Padrao: {default_ssid}",
    )
    parser.add_argument(
        "--password",
        default=default_password,
        help="Senha da rede Wi-Fi. Padrao: valor de MORFOCAMPO_WIFI_PASSWORD ou senha do MorfoNode.",
    )
    parser.add_argument(
        "--security",
        default="WPA",
        help="Tipo de segurança do Wi-Fi: WPA, WEP ou nopass.",
    )
    parser.add_argument(
        "--hidden",
        action="store_true",
        help="Marca a rede Wi-Fi como oculta no payload do QR code.",
    )
    parser.add_argument(
        "--output-dir",
        default=default_output_dir,
        type=Path,
        help=f"Diretorio onde os arquivos serao salvos. Padrao: {default_output_dir}",
    )
    parser.add_argument(
        "--prefix",
        default="morfonode",
        help="Prefixo dos arquivos gerados.",
    )
    parser.add_argument(
        "--no-svg",
        action="store_true",
        help="Não gera SVG da URL de acesso.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    site_png = args.output_dir / f"{args.prefix}-site-qr.png"
    legacy_site_png = args.output_dir / f"{args.prefix}-access-qr.png"
    wifi_png = args.output_dir / f"{args.prefix}-wifi-qr.png"
    site_svg = args.output_dir / f"{args.prefix}-access-qr.svg"

    make_png(args.url, site_png)
    shutil.copyfile(site_png, legacy_site_png)
    make_png(
        wifi_payload(args.ssid, args.password, args.security, args.hidden),
        wifi_png,
    )
    if not args.no_svg:
        make_svg(args.url, site_svg)

    print(f"QR code do site salvo em: {site_png}")
    print(f"Copia compativel do QR code do site salva em: {legacy_site_png}")
    print(f"QR code do Wi-Fi salvo em: {wifi_png}")
    if not args.no_svg:
        print(f"QR code SVG do site salvo em: {site_svg}")
    print(f"URL do site: {args.url}")
    print(f"SSID Wi-Fi: {args.ssid}")
    print("Uso em campo: escaneie o QR do Wi-Fi e confirme a conexao; depois escaneie o QR do site para abrir o navegador.")
    print("Observacao: Android/iOS podem exigir toque em conectar/salvar rede; o QR nao consegue habilitar o Wi-Fi sozinho.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
