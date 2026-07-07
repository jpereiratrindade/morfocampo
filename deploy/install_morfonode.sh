#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root: sudo deploy/install_morfonode.sh" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${MORFOCAMPO_INSTALL_DIR:-/opt/morfocampo}"
VENV_DIR="${MORFOCAMPO_VENV_DIR:-/opt/morfocampo-venv}"
STATE_DIR="${MORFOCAMPO_STATE_DIR:-/var/lib/morfocampo}"
CONFIG_DIR="${MORFOCAMPO_CONFIG_DIR:-/etc/morfocampo}"
SERVICE_FILE="/etc/systemd/system/morfocampo.service"
SERVICE_USER="morfocampo"
SSID="${MORFOCAMPO_WIFI_SSID:-MORFOCAMPO}"
WIFI_PASSWORD="${MORFOCAMPO_WIFI_PASSWORD:-labecomc}"
WIFI_IFACE="${MORFOCAMPO_WIFI_IFACE:-}"
AUTH_TOKEN="${MORFOCAMPO_AUTH_TOKEN:-}"
HOSTNAME_TARGET="${MORFOCAMPO_HOSTNAME:-morfocampo}"
PORT="${MORFOCAMPO_PORT:-8011}"
WHISPER_MODEL="${MORFOCAMPO_WHISPER_MODEL:-small}"
SKIP_WHISPER_DOWNLOAD="${MORFOCAMPO_SKIP_WHISPER_DOWNLOAD:-0}"
HF_TOKEN_FOR_DOWNLOAD="${MORFOCAMPO_HF_TOKEN:-${HF_TOKEN:-}}"
LOG_FILE="${STATE_DIR}/install.log"
INFO_FILE="${STATE_DIR}/morfonode-info.txt"
QR_URL="${MORFOCAMPO_QR_URL:-https://morfocampo.local:${PORT}}"
QR_SVG="${STATE_DIR}/morfonode-access-qr.svg"
QR_SITE_NAMED_PNG="${STATE_DIR}/morfonode-site-qr.png"
QR_SITE_PNG="${STATE_DIR}/morfonode-access-qr.png"
QR_WIFI_PNG="${STATE_DIR}/morfonode-wifi-qr.png"

mkdir -p "${STATE_DIR}"
touch "${LOG_FILE}"
exec > >(tee -a "${LOG_FILE}") 2>&1

fail() {
  echo "ERRO: $*" >&2
  exit 1
}

warn() {
  echo "Aviso: $*" >&2
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "comando obrigatório não encontrado: $1"
}

detect_wifi_iface() {
  if [[ -n "${WIFI_IFACE}" ]]; then
    echo "${WIFI_IFACE}"
    return
  fi

  if command -v nmcli >/dev/null 2>&1; then
    nmcli -t -f DEVICE,TYPE device status | awk -F: '$2 == "wifi" {print $1; exit}'
    return
  fi

  iw dev 2>/dev/null | awk '$1 == "Interface" {print $2; exit}'
}

validate_environment() {
  echo "==> Validando ambiente"

  if [[ ! -f /etc/os-release ]]; then
    fail "sistema sem /etc/os-release; esperado Raspberry Pi OS/Debian"
  fi

  # Raspberry Pi OS 64-bit usa aarch64; 32-bit usa armv7l. Permitimos x86_64
  # para teste controlado em desenvolvimento, mas avisamos.
  arch="$(uname -m)"
  case "${arch}" in
    aarch64|armv7l|armv6l)
      echo "Arquitetura detectada: ${arch}"
      ;;
    *)
      warn "arquitetura ${arch}; instalador foi pensado para Raspberry Pi"
      ;;
  esac

  if [[ ${#WIFI_PASSWORD} -lt 8 ]]; then
    fail "MORFOCAMPO_WIFI_PASSWORD precisa ter pelo menos 8 caracteres"
  fi

  if [[ ! -d "${REPO_ROOT}/web" || ! -f "${REPO_ROOT}/CMakeLists.txt" ]]; then
    fail "execute a partir de uma cópia completa do repositório Morfocampo"
  fi
}

install_dependencies() {
  echo "==> Instalando dependências de sistema"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y \
    avahi-daemon \
    build-essential \
    ca-certificates \
    cmake \
    git \
    iw \
    network-manager \
    openssl \
    python3 \
    python3-pip \
    python3-venv \
    rsync
}

create_user_and_dirs() {
  echo "==> Criando usuário e diretórios"
  if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
    useradd --system --home "${STATE_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
  fi

  mkdir -p "${STATE_DIR}/audio_files" "${STATE_DIR}/certs" "${CONFIG_DIR}"
}

install_code() {
  echo "==> Instalando código em ${INSTALL_DIR}"
  mkdir -p "${INSTALL_DIR}"
  rsync -a --delete \
    --exclude ".git" \
    --exclude "build" \
    --exclude ".venv" \
    --exclude "venv" \
    --exclude "__pycache__" \
    "${REPO_ROOT}/" "${INSTALL_DIR}/"
}

build_app() {
  echo "==> Preparando ambiente Python"
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install --upgrade pip
  "${VENV_DIR}/bin/pip" install -r "${INSTALL_DIR}/web/requirements.txt"

  echo "==> Compilando núcleo C++"
  cmake -S "${INSTALL_DIR}" -B "${INSTALL_DIR}/build" -DCMAKE_BUILD_TYPE=Release
  cmake --build "${INSTALL_DIR}/build" --parallel
}

preload_whisper_model() {
  if [[ "${SKIP_WHISPER_DOWNLOAD}" == "1" ]]; then
    warn "download antecipado do modelo Whisper foi pulado"
    return
  fi

  echo "==> Baixando modelo faster-whisper (${WHISPER_MODEL})"
  if [[ -n "${HF_TOKEN_FOR_DOWNLOAD}" ]]; then
    echo "    usando MORFOCAMPO_HF_TOKEN/HF_TOKEN para autenticar o download"
  fi
  MORFOCAMPO_WHISPER_MODEL="${WHISPER_MODEL}" HF_TOKEN="${HF_TOKEN_FOR_DOWNLOAD}" "${VENV_DIR}/bin/python" - <<'PY'
import os
from faster_whisper import WhisperModel

model_name = os.environ.get("MORFOCAMPO_WHISPER_MODEL", "small")
WhisperModel(model_name, device="cpu", compute_type="int8")
print(f"Modelo faster-whisper pronto: {model_name}")
PY
}

generate_cert() {
  echo "==> Gerando certificado local"
  if [[ ! -f "${STATE_DIR}/certs/cert.pem" || ! -f "${STATE_DIR}/certs/key.pem" ]]; then
    openssl req -x509 -newkey rsa:2048 \
      -keyout "${STATE_DIR}/certs/key.pem" \
      -out "${STATE_DIR}/certs/cert.pem" \
      -days 3650 -nodes \
      -subj "/CN=morfocampo.local" \
      -addext "subjectAltName=DNS:morfocampo.local,DNS:localhost,IP:127.0.0.1"
  fi
}

install_config() {
  echo "==> Instalando configuração"
  install -m 0644 "${INSTALL_DIR}/deploy/morfonode.env.example" "${CONFIG_DIR}/morfonode.env"
  grep -vE '^(MORFOCAMPO_AUTH_TOKEN|MORFOCAMPO_PORT|MORFOCAMPO_WHISPER_MODEL)=' "${CONFIG_DIR}/morfonode.env" > "${CONFIG_DIR}/morfonode.env.tmp"
  {
    printf 'MORFOCAMPO_PORT=%s\n' "${PORT}"
    printf 'MORFOCAMPO_WHISPER_MODEL=%s\n' "${WHISPER_MODEL}"
    printf 'MORFOCAMPO_AUTH_TOKEN=%s\n' "${AUTH_TOKEN}"
  } >> "${CONFIG_DIR}/morfonode.env.tmp"
  mv "${CONFIG_DIR}/morfonode.env.tmp" "${CONFIG_DIR}/morfonode.env"
  install -m 0644 "${INSTALL_DIR}/deploy/morfocampo.service" "${SERVICE_FILE}"
  install -m 0644 "${INSTALL_DIR}/deploy/morfocampo-update.service" /etc/systemd/system/morfocampo-update.service
  install -m 0644 "${INSTALL_DIR}/deploy/morfocampo-update.timer" /etc/systemd/system/morfocampo-update.timer
  install -m 0755 "${INSTALL_DIR}/deploy/backup_morfonode.sh" /usr/local/bin/morfocampo-backup
  install -m 0755 "${INSTALL_DIR}/deploy/update_morfonode.sh" /usr/local/bin/morfocampo-update

  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${STATE_DIR}"
  chown -R root:root "${INSTALL_DIR}" "${VENV_DIR}" "${CONFIG_DIR}"
  chmod 0640 "${CONFIG_DIR}/morfonode.env"
}

record_installed_version() {
  echo "==> Registrando versão instalada"
  {
    printf 'tag=%s\n' "$(git -C "${REPO_ROOT}" describe --tags --exact-match 2>/dev/null || true)"
    printf 'commit=%s\n' "$(git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || true)"
    printf 'installed_at=%s\n' "$(date -Iseconds)"
    printf 'repo=%s\n' "$(git -C "${REPO_ROOT}" config --get remote.origin.url 2>/dev/null || echo "https://github.com/jpereiratrindade/morfocampo.git")"
  } > "${STATE_DIR}/installed-version.txt"
  chown "${SERVICE_USER}:${SERVICE_USER}" "${STATE_DIR}/installed-version.txt"
  chmod 0644 "${STATE_DIR}/installed-version.txt"
}

generate_access_qr() {
  echo "==> Gerando QR codes de acesso"
  "${VENV_DIR}/bin/python" "${INSTALL_DIR}/deploy/generate_morfonode_qr.py" \
    --url "${QR_URL}" \
    --ssid "${SSID}" \
    --password "${WIFI_PASSWORD}" \
    --security WPA \
    --output-dir "${STATE_DIR}" \
    --prefix morfonode
  chown "${SERVICE_USER}:${SERVICE_USER}" "${QR_SVG}" "${QR_SITE_NAMED_PNG}" "${QR_SITE_PNG}" "${QR_WIFI_PNG}"
  chmod 0644 "${QR_SVG}" "${QR_SITE_NAMED_PNG}" "${QR_SITE_PNG}" "${QR_WIFI_PNG}"
}

configure_hostname() {
  echo "==> Configurando hostname local"
  hostnamectl set-hostname "${HOSTNAME_TARGET}"
  systemctl enable --now avahi-daemon
}

configure_hotspot() {
  echo "==> Configurando hotspot Wi-Fi"
  systemctl enable --now NetworkManager
  require_command nmcli

  WIFI_IFACE="$(detect_wifi_iface)"
  if [[ -z "${WIFI_IFACE}" ]]; then
    fail "nenhuma interface Wi-Fi detectada; defina MORFOCAMPO_WIFI_IFACE"
  fi

  nmcli radio wifi on || true
  nmcli connection delete "${SSID}" >/dev/null 2>&1 || true
  nmcli connection add type wifi ifname "${WIFI_IFACE}" con-name "${SSID}" autoconnect yes ssid "${SSID}"
  nmcli connection modify "${SSID}" \
    802-11-wireless.mode ap \
    802-11-wireless.band bg \
    ipv4.method shared \
    ipv6.method ignore \
    wifi-sec.key-mgmt wpa-psk \
    wifi-sec.psk "${WIFI_PASSWORD}" \
    connection.autoconnect yes
  nmcli connection up "${SSID}" || fail "falha ao ativar hotspot ${SSID} na interface ${WIFI_IFACE}"
}

enable_service() {
  echo "==> Habilitando serviço morfocampo"
  systemctl daemon-reload
  systemctl enable --now morfocampo
  systemctl enable --now morfocampo-update.timer
}

write_summary() {
  local ip_addr
  ip_addr="$(hostname -I 2>/dev/null | awk '{print $1}')"

  cat > "${INFO_FILE}" <<EOF
MorfoNode instalado

Wi-Fi: ${SSID}
Senha Wi-Fi: ${WIFI_PASSWORD}
URL principal: https://morfocampo.local:${PORT}
URL por IP: https://${ip_addr:-IP_DO_RASPBERRY}:${PORT}
QR code: ${QR_SVG}
QR code PNG do site: ${QR_SITE_NAMED_PNG}
QR code PNG do site (compatibilidade): ${QR_SITE_PNG}
QR code PNG do Wi-Fi: ${QR_WIFI_PNG}
URL do QR code: ${QR_URL}
Token local: ${AUTH_TOKEN:-desativado}
Modelo Whisper: ${WHISPER_MODEL}

Serviço:
  sudo systemctl status morfocampo
  sudo journalctl -u morfocampo -f

Log de instalação:
  ${LOG_FILE}

Backup manual:
  sudo morfocampo-backup

Atualização:
  sudo morfocampo-update
  sudo systemctl status morfocampo-update.timer
  Log: ${STATE_DIR}/update.log
EOF

  chown "${SERVICE_USER}:${SERVICE_USER}" "${INFO_FILE}"
  chmod 0640 "${INFO_FILE}"

  echo
  cat "${INFO_FILE}"
}

validate_environment
install_dependencies
create_user_and_dirs
install_code
build_app
preload_whisper_model
generate_cert
install_config
record_installed_version
generate_access_qr
configure_hostname
configure_hotspot
enable_service
write_summary
