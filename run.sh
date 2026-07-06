#!/usr/bin/env bash
# run.sh — inicia o morfocampo web em 0.0.0.0:8011
# Uso: ./run.sh
#      ./run.sh --rebuild   (força recompilação do binário C++)

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BIN="$ROOT/build/morfocampo"
WEB="$ROOT/web"
DB="$WEB/campo.db"
PORT=8011
HOST="${MORFOCAMPO_HOST:-0.0.0.0}"
LOCAL_NAME="${MORFOCAMPO_LOCAL_NAME:-morfocampo.local}"
HOSTNAME_LOCAL="$(hostname -s 2>/dev/null || hostname 2>/dev/null || true)"
HOSTNAME_LOCAL="${HOSTNAME_LOCAL%%.*}"
if [[ -n "$HOSTNAME_LOCAL" ]]; then
  HOSTNAME_LOCAL="$HOSTNAME_LOCAL.local"
fi
PUBLISHED_HOSTNAME_LOCAL="$HOSTNAME_LOCAL"
CERT="$WEB/cert.pem"
KEY="$WEB/key.pem"
SHOW_QR="${MORFOCAMPO_SHOW_QR:-1}"
QR_URL="${MORFOCAMPO_QR_URL:-}"

# ── Cores ────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RESET='\033[0m'

# ── 1. Build C++ (pula se já existe e não foi pedido --rebuild) ───
if [[ "$1" == "--rebuild" ]] || [[ ! -f "$BIN" ]]; then
  echo -e "${YELLOW}⟳  Compilando núcleo C++...${RESET}"
  cmake -S "$ROOT" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Release
  cmake --build "$ROOT/build" --parallel
  echo -e "${GREEN}✓  Binário: $BIN${RESET}"
else
  echo -e "${GREEN}✓  Binário já compilado: $BIN${RESET}"
fi

# ── 2. Dependências Python ────────────────────────────────
echo -e "${YELLOW}⟳  Verificando dependências Python...${RESET}"
pip install -q -r "$WEB/requirements.txt"
echo -e "${GREEN}✓  Dependências OK${RESET}"

# ── 3. Descobre o IP da rede local ────────────────────────
LOCAL_IP=$(ip -4 route get 1.1.1.1 2>/dev/null \
  | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}')

if [[ -z "$LOCAL_IP" ]]; then
  LOCAL_IP=$(ip -4 addr show scope global 2>/dev/null \
  | grep "inet " \
  | grep -v "127.0.0.1" \
  | awk '{print $2}' \
  | cut -d/ -f1 \
  | head -1)
fi

if [[ -z "$LOCAL_IP" ]]; then
  LOCAL_IP=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.' | head -1)
fi

if [[ -n "$HOSTNAME_LOCAL" ]] && command -v avahi-resolve-host-name >/dev/null 2>&1; then
  RESOLVED_HOSTNAME_LOCAL=$(timeout 2 avahi-resolve-host-name "$HOSTNAME_LOCAL" 2>/dev/null | awk 'NR == 1 {print $1}' || true)
  if [[ -n "$RESOLVED_HOSTNAME_LOCAL" ]]; then
    PUBLISHED_HOSTNAME_LOCAL="$RESOLVED_HOSTNAME_LOCAL"
  fi
fi

# ── 4. Gera certificado SSL temporário (necessário p/ microfone)
NEEDS_CERT=0
if [[ ! -f "$CERT" || ! -f "$KEY" ]]; then
  NEEDS_CERT=1
elif ! openssl x509 -in "$CERT" -noout -ext subjectAltName 2>/dev/null | grep -q "DNS:$LOCAL_NAME"; then
  NEEDS_CERT=1
elif [[ -n "$HOSTNAME_LOCAL" ]] && ! openssl x509 -in "$CERT" -noout -ext subjectAltName 2>/dev/null | grep -q "DNS:$HOSTNAME_LOCAL"; then
  NEEDS_CERT=1
elif [[ -n "$PUBLISHED_HOSTNAME_LOCAL" ]] && ! openssl x509 -in "$CERT" -noout -ext subjectAltName 2>/dev/null | grep -q "DNS:$PUBLISHED_HOSTNAME_LOCAL"; then
  NEEDS_CERT=1
fi

if [[ "$NEEDS_CERT" -eq 1 ]]; then
  echo -e "${YELLOW}⟳  Gerando certificado SSL autoassinado para $LOCAL_NAME...${RESET}"
  SAN="DNS:$LOCAL_NAME,DNS:localhost,IP:127.0.0.1"
  if [[ -n "$HOSTNAME_LOCAL" && "$HOSTNAME_LOCAL" != "$LOCAL_NAME" ]]; then
    SAN="$SAN,DNS:$HOSTNAME_LOCAL"
  fi
  if [[ -n "$PUBLISHED_HOSTNAME_LOCAL" && "$PUBLISHED_HOSTNAME_LOCAL" != "$LOCAL_NAME" && "$PUBLISHED_HOSTNAME_LOCAL" != "$HOSTNAME_LOCAL" ]]; then
    SAN="$SAN,DNS:$PUBLISHED_HOSTNAME_LOCAL"
  fi
  if [[ -n "$LOCAL_IP" ]]; then
    SAN="$SAN,IP:$LOCAL_IP"
  fi
  openssl req -x509 -newkey rsa:2048 -keyout "$KEY" -out "$CERT" \
    -days 365 -nodes -subj "/CN=$LOCAL_NAME" \
    -addext "subjectAltName=$SAN" 2>/dev/null
  echo -e "${GREEN}✓  Certificado gerado com sucesso${RESET}"
fi

# ── 5. Informa endereços de acesso ───────────────────────
print_qr_code() {
  local url="$1"
  if [[ "$SHOW_QR" != "1" ]]; then
    return
  fi
  python3 - "$url" <<'PY'
import sys

try:
    import qrcode
except Exception as exc:
    print(f"   QR code indisponível: instale a dependência Python 'qrcode' ({exc})")
    raise SystemExit(0)

url = sys.argv[1]
qr = qrcode.QRCode(border=1)
qr.add_data(url)
qr.make(fit=True)
print("")
print(f"   QR code para acesso pelo celular: {url}")
qr.print_ascii(out=sys.stdout, tty=sys.stdout.isatty())
PY
}

echo ""
echo -e "${GREEN}🌿 morfocampo web (Seguro/HTTPS)${RESET}"
echo -e "   Banco:    ${CYAN}$DB${RESET}"
echo -e "   Binário:  ${CYAN}$BIN${RESET}"
echo ""
echo -e "   Acesso local:   ${CYAN}https://localhost:$PORT${RESET}"
echo -e "   Nome local:     ${CYAN}https://$LOCAL_NAME:$PORT${RESET}"
if [[ -n "$HOSTNAME_LOCAL" && "$HOSTNAME_LOCAL" != "$LOCAL_NAME" ]]; then
  echo -e "   Host atual:     ${CYAN}https://$HOSTNAME_LOCAL:$PORT${RESET}"
fi
if [[ -n "$PUBLISHED_HOSTNAME_LOCAL" && "$PUBLISHED_HOSTNAME_LOCAL" != "$HOSTNAME_LOCAL" && "$PUBLISHED_HOSTNAME_LOCAL" != "$LOCAL_NAME" ]]; then
  echo -e "   mDNS publicado: ${CYAN}https://$PUBLISHED_HOSTNAME_LOCAL:$PORT${RESET}"
fi
if [[ -n "$LOCAL_IP" ]]; then
  MOBILE_URL="https://$LOCAL_IP:$PORT"
  echo -e "   Acesso celular: ${CYAN}$MOBILE_URL${RESET}  ← escaneie o QR code ou copie para o celular"
  echo -e "   ${YELLOW}Nota: No celular, o aviso 'Sua conexão não é particular' é esperado.${RESET}"
  echo -e "         Clique em 'Avançado' -> 'Ir para $LOCAL_IP (inseguro)' para liberar o microfone."
  print_qr_code "${QR_URL:-$MOBILE_URL}"
fi
echo -e "   ${YELLOW}Para o celular resolver $LOCAL_NAME, use o MorfoNode com Avahi/mDNS ou configure o hostname do equipamento como 'morfocampo'.${RESET}"
echo -e "   ${YELLOW}Se um nome .local falhar nesta máquina, use o IP acima; mDNS pode variar por firewall, IPv6 ou conflito de hostname.${RESET}"
echo ""

# ── 6. Inicia servidor ────────────────────────────────────
cd "$WEB"
exec python3 server.py \
  --db "$DB" \
  --bin "$BIN" \
  --host "$HOST" \
  --port "$PORT" \
  --ssl-keyfile "$KEY" \
  --ssl-certfile "$CERT"
