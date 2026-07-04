#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${MORFOCAMPO_STATE_DIR:-/var/lib/morfocampo}"
BACKUP_DIR="${MORFOCAMPO_BACKUP_DIR:-${STATE_DIR}/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
HOST="$(hostname -s 2>/dev/null || echo morfonode)"
ARCHIVE="${BACKUP_DIR}/morfocampo_backup_${HOST}_${STAMP}.tar.gz"

if [[ ! -d "${STATE_DIR}" ]]; then
  echo "Diretório de estado não encontrado: ${STATE_DIR}" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

tmpdir="$(mktemp -d)"
cleanup() {
  rm -rf "${tmpdir}"
}
trap cleanup EXIT

manifest="${tmpdir}/MANIFEST.txt"
{
  echo "Morfocampo backup"
  echo "Criado em: $(date -Iseconds)"
  echo "Host: ${HOST}"
  echo "State dir: ${STATE_DIR}"
} > "${manifest}"

paths=()
for item in \
  campo.db \
  campo.db-shm \
  campo.db-wal \
  audio_files \
  certs \
  morfonode-info.txt \
  install.log; do
  if [[ -e "${STATE_DIR}/${item}" ]]; then
    paths+=("${item}")
    echo "Incluído: ${item}" >> "${manifest}"
  fi
done

if [[ ${#paths[@]} -eq 0 ]]; then
  echo "Nenhum arquivo conhecido para backup em ${STATE_DIR}" >&2
  exit 1
fi

staging="${tmpdir}/backup"
mkdir -p "${staging}/state"
cp "${manifest}" "${staging}/MANIFEST.txt"
for item in "${paths[@]}"; do
  cp -a "${STATE_DIR}/${item}" "${staging}/state/"
done

tar -C "${staging}" -czf "${ARCHIVE}" MANIFEST.txt state

chmod 0600 "${ARCHIVE}"
echo "${ARCHIVE}"
