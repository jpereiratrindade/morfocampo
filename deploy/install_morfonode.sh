#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root: sudo deploy/install_morfonode.sh" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/morfocampo"
VENV_DIR="/opt/morfocampo-venv"
STATE_DIR="/var/lib/morfocampo"
CONFIG_DIR="/etc/morfocampo"
SERVICE_FILE="/etc/systemd/system/morfocampo.service"
SERVICE_USER="morfocampo"
SSID="${MORFOCAMPO_WIFI_SSID:-MORFOCAMPO}"
WIFI_PASSWORD="${MORFOCAMPO_WIFI_PASSWORD:-morfocampo2026}"
AUTH_TOKEN="${MORFOCAMPO_AUTH_TOKEN:-}"

echo "==> Instalando dependências de sistema"
apt-get update
apt-get install -y \
  avahi-daemon \
  build-essential \
  cmake \
  network-manager \
  openssl \
  python3 \
  python3-pip \
  python3-venv \
  rsync

echo "==> Criando usuário e diretórios"
if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home "${STATE_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

mkdir -p "${STATE_DIR}/audio_files" "${STATE_DIR}/certs" "${CONFIG_DIR}"
if [[ -z "${AUTH_TOKEN}" ]]; then
  AUTH_TOKEN="$(openssl rand -hex 16)"
fi

echo "==> Instalando código em ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"
rsync -a --delete \
  --exclude ".git" \
  --exclude "build" \
  --exclude ".venv" \
  --exclude "venv" \
  "${REPO_ROOT}/" "${INSTALL_DIR}/"

echo "==> Preparando ambiente Python"
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${INSTALL_DIR}/web/requirements.txt"

echo "==> Compilando núcleo C++"
cmake -S "${INSTALL_DIR}" -B "${INSTALL_DIR}/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "${INSTALL_DIR}/build" --parallel

echo "==> Gerando certificado local"
if [[ ! -f "${STATE_DIR}/certs/cert.pem" || ! -f "${STATE_DIR}/certs/key.pem" ]]; then
  openssl req -x509 -newkey rsa:2048 \
    -keyout "${STATE_DIR}/certs/key.pem" \
    -out "${STATE_DIR}/certs/cert.pem" \
    -days 3650 -nodes \
    -subj "/CN=morfocampo.local" \
    -addext "subjectAltName=DNS:morfocampo.local,DNS:localhost,IP:127.0.0.1"
fi

echo "==> Instalando configuração"
install -m 0644 "${INSTALL_DIR}/deploy/morfonode.env.example" "${CONFIG_DIR}/morfonode.env"
grep -v '^MORFOCAMPO_AUTH_TOKEN=' "${CONFIG_DIR}/morfonode.env" > "${CONFIG_DIR}/morfonode.env.tmp"
printf 'MORFOCAMPO_AUTH_TOKEN=%s\n' "${AUTH_TOKEN}" >> "${CONFIG_DIR}/morfonode.env.tmp"
mv "${CONFIG_DIR}/morfonode.env.tmp" "${CONFIG_DIR}/morfonode.env"
install -m 0644 "${INSTALL_DIR}/deploy/morfocampo.service" "${SERVICE_FILE}"

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${STATE_DIR}"
chown -R root:root "${INSTALL_DIR}" "${VENV_DIR}" "${CONFIG_DIR}"
chmod 0640 "${CONFIG_DIR}/morfonode.env"

echo "==> Configurando hostname local"
hostnamectl set-hostname morfocampo
systemctl enable --now avahi-daemon

echo "==> Configurando hotspot Wi-Fi"
systemctl enable --now NetworkManager
if command -v nmcli >/dev/null 2>&1; then
  if ! nmcli connection show "${SSID}" >/dev/null 2>&1; then
    nmcli device wifi hotspot ifname wlan0 ssid "${SSID}" password "${WIFI_PASSWORD}" || \
      echo "Aviso: não foi possível criar hotspot automaticamente. Configure manualmente com nmcli."
  fi
else
  echo "Aviso: nmcli não encontrado. Hotspot não configurado."
fi

echo "==> Habilitando serviço morfocampo"
systemctl daemon-reload
systemctl enable --now morfocampo

echo
echo "MorfoNode instalado."
echo "Wi-Fi: ${SSID}"
echo "URL: https://morfocampo.local:8011"
echo "Token local: ${AUTH_TOKEN}"
echo "Status: sudo systemctl status morfocampo"
