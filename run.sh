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

# ── Cores ────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RESET='\033[0m'

# ── 1. Build C++ (pula se já existe e não foi pedido --rebuild) ───
if [[ "$1" == "--rebuild" ]] || [[ ! -f "$BIN" ]]; then
  echo -e "${YELLOW}⟳  Compilando núcleo C++...${RESET}"
  cmake -S "$ROOT" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Release -q
  cmake --build "$ROOT/build" --parallel
  echo -e "${GREEN}✓  Binário: $BIN${RESET}"
else
  echo -e "${GREEN}✓  Binário já compilado: $BIN${RESET}"
fi

# ── 2. Dependências Python ────────────────────────────────
echo -e "${YELLOW}⟳  Verificando dependências Python...${RESET}"
pip install -q -r "$WEB/requirements.txt"
echo -e "${GREEN}✓  Dependências OK${RESET}"

# ── 3. Informa endereços de acesso ───────────────────────
LOCAL_IP=$(ip addr show 2>/dev/null \
  | grep "inet " \
  | grep -v "127.0.0.1" \
  | awk '{print $2}' \
  | cut -d/ -f1 \
  | head -1)

echo ""
echo -e "${GREEN}🌿 morfocampo web${RESET}"
echo -e "   Banco:    ${CYAN}$DB${RESET}"
echo -e "   Binário:  ${CYAN}$BIN${RESET}"
echo ""
echo -e "   Acesso local:   ${CYAN}http://localhost:$PORT${RESET}"
if [[ -n "$LOCAL_IP" ]]; then
  echo -e "   Acesso celular: ${CYAN}http://$LOCAL_IP:$PORT${RESET}  ← copie para o celular"
fi
echo ""

# ── 4. Inicia servidor ────────────────────────────────────
cd "$WEB"
exec python3 server.py \
  --db "$DB" \
  --bin "$BIN" \
  --host "$HOST" \
  --port "$PORT"
