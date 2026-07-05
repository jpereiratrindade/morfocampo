#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${MORFOCAMPO_CONFIG_FILE:-/etc/morfocampo/morfonode.env}"
if [[ -f "${CONFIG_FILE}" ]]; then
  # Arquivo controlado pelo instalador MorfoNode.
  # shellcheck disable=SC1090
  source "${CONFIG_FILE}"
fi

INSTALL_DIR="${MORFOCAMPO_INSTALL_DIR:-/opt/morfocampo}"
VENV_DIR="${MORFOCAMPO_VENV_DIR:-/opt/morfocampo-venv}"
STATE_DIR="${MORFOCAMPO_STATE_DIR:-/var/lib/morfocampo}"
SERVICE_NAME="${MORFOCAMPO_SERVICE_NAME:-morfocampo}"
REPO_URL="${MORFOCAMPO_UPDATE_REPO:-https://github.com/jpereiratrindade/morfocampo.git}"
REQUIRE_CI="${MORFOCAMPO_UPDATE_REQUIRE_CI:-1}"
RUN_TESTS="${MORFOCAMPO_UPDATE_RUN_TESTS:-1}"
UPDATE_ENABLED="${MORFOCAMPO_UPDATE_ENABLED:-0}"
GITHUB_TOKEN="${MORFOCAMPO_GITHUB_TOKEN:-${GITHUB_TOKEN:-}}"

CACHE_DIR="${STATE_DIR}/update-cache/repo"
STAGING_DIR="${STATE_DIR}/update-staging"
CODE_BACKUP_DIR="${STATE_DIR}/code-backups"
VERSION_FILE="${STATE_DIR}/installed-version.txt"
LOG_FILE="${STATE_DIR}/update.log"
LOCK_FILE="/run/lock/morfocampo-update.lock"

AUTO_MODE=0
if [[ "${1:-}" == "--auto" ]]; then
  AUTO_MODE=1
fi

mkdir -p "${STATE_DIR}"
touch "${LOG_FILE}"
exec >>"${LOG_FILE}" 2>&1

log() {
  printf '[%s] %s\n' "$(date -Iseconds)" "$*"
}

fail() {
  log "ERRO: $*"
  exit 1
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    fail "execute como root"
  fi
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "comando obrigatório não encontrado: $1"
}

internet_available() {
  python3 - <<'PY'
import sys
import urllib.request

try:
    urllib.request.urlopen("https://github.com", timeout=8).close()
except Exception:
    sys.exit(1)
PY
}

repo_slug() {
  python3 - "${REPO_URL}" <<'PY'
import re
import sys

url = sys.argv[1]
patterns = [
    r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$",
    r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$",
]
for pattern in patterns:
    match = re.search(pattern, url)
    if match:
        print(f"{match.group('owner')}/{match.group('repo')}")
        sys.exit(0)
sys.exit(1)
PY
}

prepare_cache() {
  mkdir -p "$(dirname "${CACHE_DIR}")"
  if [[ -d "${CACHE_DIR}/.git" ]]; then
    git -C "${CACHE_DIR}" remote set-url origin "${REPO_URL}"
    git -C "${CACHE_DIR}" fetch --force --prune --tags origin \
      '+refs/heads/*:refs/remotes/origin/*' \
      '+refs/tags/*:refs/tags/*'
  else
    rm -rf "${CACHE_DIR}"
    git clone --filter=blob:none --no-checkout "${REPO_URL}" "${CACHE_DIR}"
    git -C "${CACHE_DIR}" fetch --force --prune --tags origin \
      '+refs/heads/*:refs/remotes/origin/*' \
      '+refs/tags/*:refs/tags/*'
  fi
}

latest_tag() {
  git -C "${CACHE_DIR}" tag -l 'v*' --sort=-v:refname | head -n 1
}

current_version() {
  if [[ -f "${VERSION_FILE}" ]]; then
    awk -F= '$1 == "tag" {print $2}' "${VERSION_FILE}" | tail -n 1
  fi
}

tag_commit() {
  git -C "${CACHE_DIR}" rev-list -n 1 "$1"
}

ci_succeeded() {
  local slug="$1"
  local sha="$2"

  python3 - "${slug}" "${sha}" "${GITHUB_TOKEN}" <<'PY'
import json
import sys
import urllib.parse
import urllib.request

slug, sha, token = sys.argv[1], sys.argv[2], sys.argv[3]
query = urllib.parse.urlencode({
    "head_sha": sha,
    "status": "completed",
    "per_page": "30",
})
url = f"https://api.github.com/repos/{slug}/actions/runs?{query}"
headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "morfocampo-morfonode-updater",
}
if token:
    headers["Authorization"] = f"Bearer {token}"

try:
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as response:
        payload = json.load(response)
except Exception as exc:
    print(f"falha ao consultar GitHub Actions: {exc}", file=sys.stderr)
    sys.exit(2)

runs = payload.get("workflow_runs", [])
successful = [
    run for run in runs
    if run.get("head_sha") == sha and run.get("conclusion") == "success"
]
if successful:
    print(successful[0].get("html_url", "CI success"))
    sys.exit(0)

print("nenhum workflow concluído com sucesso para o commit", file=sys.stderr)
sys.exit(1)
PY
}

build_candidate() {
  local tag="$1"

  rm -rf "${STAGING_DIR}"
  mkdir -p "${STAGING_DIR}/src"
  git -C "${CACHE_DIR}" archive "${tag}" | tar -C "${STAGING_DIR}/src" -xf -

  cmake -S "${STAGING_DIR}/src" -B "${STAGING_DIR}/src/build" -DCMAKE_BUILD_TYPE=Release
  cmake --build "${STAGING_DIR}/src/build" --parallel

  if [[ "${RUN_TESTS}" == "1" ]]; then
    ctest --test-dir "${STAGING_DIR}/src/build" --output-on-failure
    python3 -m py_compile \
      "${STAGING_DIR}/src/web/server.py" \
      "${STAGING_DIR}/src/web/morfocampo_bridge.py" \
      "${STAGING_DIR}/src/web/db.py" \
      "${STAGING_DIR}/src/web/transcriber.py"
  fi

  "${VENV_DIR}/bin/pip" install -r "${STAGING_DIR}/src/web/requirements.txt"
}

backup_state() {
  if [[ -x /usr/local/bin/morfocampo-backup ]]; then
    /usr/local/bin/morfocampo-backup
  else
    log "backup de estado pulado: /usr/local/bin/morfocampo-backup não encontrado"
  fi
}

backup_code() {
  mkdir -p "${CODE_BACKUP_DIR}"
  local archive="${CODE_BACKUP_DIR}/morfocampo_code_$(date +%Y%m%d_%H%M%S).tar.gz"
  tar -C "${INSTALL_DIR}" -czf "${archive}" .
  chmod 0600 "${archive}"
  printf '%s\n' "${archive}"
}

restore_code() {
  local archive="$1"
  log "restaurando código anterior: ${archive}"
  rm -rf "${INSTALL_DIR:?}/"*
  tar -C "${INSTALL_DIR}" -xzf "${archive}"
}

record_version() {
  local tag="$1"
  local sha="$2"
  {
    printf 'tag=%s\n' "${tag}"
    printf 'commit=%s\n' "${sha}"
    printf 'installed_at=%s\n' "$(date -Iseconds)"
    printf 'repo=%s\n' "${REPO_URL}"
  } > "${VERSION_FILE}"
  chmod 0644 "${VERSION_FILE}"
}

install_candidate() {
  local tag="$1"
  local sha="$2"
  local code_backup="$3"

  systemctl stop "${SERVICE_NAME}"
  if ! rsync -a --delete \
      --exclude ".git" \
      --exclude ".venv" \
      --exclude "venv" \
      --exclude "__pycache__" \
      "${STAGING_DIR}/src/" "${INSTALL_DIR}/"; then
    restore_code "${code_backup}"
    systemctl start "${SERVICE_NAME}" || true
    fail "falha ao copiar nova versão"
  fi

  chown -R root:root "${INSTALL_DIR}"
  record_version "${tag}" "${sha}"

  if ! systemctl start "${SERVICE_NAME}"; then
    restore_code "${code_backup}"
    systemctl start "${SERVICE_NAME}" || true
    fail "serviço não iniciou após atualização"
  fi

  sleep 5
  if ! systemctl is-active --quiet "${SERVICE_NAME}"; then
    restore_code "${code_backup}"
    systemctl restart "${SERVICE_NAME}" || true
    fail "serviço não permaneceu ativo após atualização"
  fi
}

main() {
  require_root
  require_command git
  require_command cmake
  require_command ctest
  require_command rsync
  require_command tar
  require_command python3

  exec 9>"${LOCK_FILE}"
  if ! flock -n 9; then
    log "outra atualização já está em execução"
    exit 0
  fi

  if [[ "${AUTO_MODE}" == "1" && "${UPDATE_ENABLED}" != "1" ]]; then
    log "atualização automática desabilitada"
    exit 0
  fi

  log "iniciando verificação de atualização"

  if ! internet_available; then
    log "sem internet disponível; mantendo versão atual"
    exit 0
  fi

  prepare_cache

  local tag
  tag="$(latest_tag)"
  if [[ -z "${tag}" ]]; then
    fail "nenhuma tag v* encontrada em ${REPO_URL}"
  fi

  local installed
  installed="$(current_version || true)"
  if [[ "${installed}" == "${tag}" ]]; then
    log "versão já instalada: ${tag}"
    exit 0
  fi

  local sha
  sha="$(tag_commit "${tag}")"
  log "candidata encontrada: ${tag} (${sha})"

  if [[ "${REQUIRE_CI}" == "1" ]]; then
    local slug
    slug="$(repo_slug)" || fail "repositório não parece ser GitHub: ${REPO_URL}"
    local ci_url
    ci_url="$(ci_succeeded "${slug}" "${sha}")" || fail "CI não aprovou ${tag}"
    log "CI aprovado: ${ci_url}"
  else
    log "trava de CI desabilitada por configuração"
  fi

  build_candidate "${tag}"
  backup_state

  local code_backup
  code_backup="$(backup_code)"
  install_candidate "${tag}" "${sha}" "${code_backup}"

  rm -rf "${STAGING_DIR}"
  log "atualização concluída: ${tag}"
}

main "$@"
