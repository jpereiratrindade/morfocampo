#!/usr/bin/env bash
set -euo pipefail

LOCAL_NAME="${MORFOCAMPO_LOCAL_NAME:-morfocampo.local}"
LOCAL_IP="${MORFOCAMPO_LOCAL_IP:-}"
AVAHI_HOSTS="/etc/avahi/hosts"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute como root: sudo deploy/configure_mdns_alias.sh" >&2
  exit 1
fi

if [[ -z "${LOCAL_IP}" ]]; then
  LOCAL_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}')"
fi

if [[ -z "${LOCAL_IP}" ]]; then
  LOCAL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi

if [[ -z "${LOCAL_IP}" ]]; then
  echo "Não foi possível detectar o IP local. Defina MORFOCAMPO_LOCAL_IP." >&2
  exit 1
fi

touch "${AVAHI_HOSTS}"

tmp="$(mktemp)"
grep -vE "[[:space:]]${LOCAL_NAME//./\\.}$" "${AVAHI_HOSTS}" > "${tmp}" || true
printf '%s %s\n' "${LOCAL_IP}" "${LOCAL_NAME}" >> "${tmp}"
install -m 0644 "${tmp}" "${AVAHI_HOSTS}"
rm -f "${tmp}"

systemctl enable --now avahi-daemon
systemctl restart avahi-daemon

echo "Alias mDNS configurado: ${LOCAL_NAME} -> ${LOCAL_IP}"
echo "Teste: avahi-resolve-host-name ${LOCAL_NAME}"
