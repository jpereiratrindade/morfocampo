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
HOST="0.0.0.0"
LOCAL_NAME="${MORFOCAMPO_LOCAL_NAME:-morfocampo.local}"
CERT="$WEB/cert.pem"
KEY="$WEB/key.pem"

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
LOCAL_IP=$(ip addr show 2>/dev/null \
  | grep "inet " \
  | grep -v "127.0.0.1" \
  | awk '{print $2}' \
  | cut -d/ -f1 \
  | head -1)

if [[ -z "$LOCAL_IP" ]]; then
  LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi

# ── 4. Gera certificado SSL temporário (necessário p/ microfone)
NEEDS_CERT=0
if [[ ! -f "$CERT" || ! -f "$KEY" ]]; then
  NEEDS_CERT=1
elif ! openssl x509 -in "$CERT" -noout -ext subjectAltName 2>/dev/null | grep -q "DNS:$LOCAL_NAME"; then
  NEEDS_CERT=1
fi

if [[ "$NEEDS_CERT" -eq 1 ]]; then
  echo -e "${YELLOW}⟳  Gerando certificado SSL autoassinado para $LOCAL_NAME...${RESET}"
  SAN="DNS:$LOCAL_NAME,DNS:localhost,IP:127.0.0.1"
  if [[ -n "$LOCAL_IP" ]]; then
    SAN="$SAN,IP:$LOCAL_IP"
  fi
  openssl req -x509 -newkey rsa:2048 -keyout "$KEY" -out "$CERT" \
    -days 365 -nodes -subj "/CN=$LOCAL_NAME" \
    -addext "subjectAltName=$SAN" 2>/dev/null
  echo -e "${GREEN}✓  Certificado gerado com sucesso${RESET}"
fi

# ── 5. Informa endereços de acesso ───────────────────────
echo ""
echo -e "${GREEN}🌿 morfocampo web (Seguro/HTTPS)${RESET}"
echo -e "   Banco:    ${CYAN}$DB${RESET}"
echo -e "   Binário:  ${CYAN}$BIN${RESET}"
echo ""
echo -e "   Acesso local:   ${CYAN}https://localhost:$PORT${RESET}"
echo -e "   Nome local:     ${CYAN}https://$LOCAL_NAME:$PORT${RESET}"
if [[ -n "$LOCAL_IP" ]]; then
  echo -e "   Acesso celular: ${CYAN}https://$LOCAL_IP:$PORT${RESET}  ← copie para o celular"
  echo -e "   ${YELLOW}Nota: No celular, o aviso 'Sua conexão não é particular' é esperado.${RESET}"
  echo -e "         Clique em 'Avançado' -> 'Ir para $LOCAL_IP (inseguro)' para liberar o microfone."
fi
echo -e "   ${YELLOW}Para o celular resolver $LOCAL_NAME, use o MorfoNode com Avahi/mDNS ou configure o hostname do equipamento como 'morfocampo'.${RESET}"
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
