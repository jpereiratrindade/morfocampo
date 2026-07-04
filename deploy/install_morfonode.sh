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
WIFI_PASSWORD="${MORFOCAMPO_WIFI_PASSWORD:-morfocampo2026}"
WIFI_IFACE="${MORFOCAMPO_WIFI_IFACE:-}"
AUTH_TOKEN="${MORFOCAMPO_AUTH_TOKEN:-}"
HOSTNAME_TARGET="${MORFOCAMPO_HOSTNAME:-morfocampo}"
PORT="${MORFOCAMPO_PORT:-8011}"
LOG_FILE="${STATE_DIR}/install.log"
INFO_FILE="${STATE_DIR}/morfonode-info.txt"

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
  if [[ -z "${AUTH_TOKEN}" ]]; then
    AUTH_TOKEN="$(openssl rand -hex 16)"
  fi
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
  grep -vE '^(MORFOCAMPO_AUTH_TOKEN|MORFOCAMPO_PORT)=' "${CONFIG_DIR}/morfonode.env" > "${CONFIG_DIR}/morfonode.env.tmp"
  {
    printf 'MORFOCAMPO_PORT=%s\n' "${PORT}"
    printf 'MORFOCAMPO_AUTH_TOKEN=%s\n' "${AUTH_TOKEN}"
  } >> "${CONFIG_DIR}/morfonode.env.tmp"
  mv "${CONFIG_DIR}/morfonode.env.tmp" "${CONFIG_DIR}/morfonode.env"
  install -m 0644 "${INSTALL_DIR}/deploy/morfocampo.service" "${SERVICE_FILE}"

  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${STATE_DIR}"
  chown -R root:root "${INSTALL_DIR}" "${VENV_DIR}" "${CONFIG_DIR}"
  chmod 0640 "${CONFIG_DIR}/morfonode.env"
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
Token local: ${AUTH_TOKEN}

Serviço:
  sudo systemctl status morfocampo
  sudo journalctl -u morfocampo -f

Log de instalação:
  ${LOG_FILE}
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
generate_cert
install_config
configure_hostname
configure_hotspot
enable_service
write_summary
