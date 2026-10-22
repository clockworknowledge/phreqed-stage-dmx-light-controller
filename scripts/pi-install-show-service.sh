#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
SERVICE_SOURCE="${REPO_ROOT}/config/systemd/phreqed-dmx.service"
ENV_SOURCE="${REPO_ROOT}/config/systemd/phreqed-dmx.env.example"
SERVICE_TARGET="/etc/systemd/system/phreqed-dmx.service"
ENV_TARGET="/etc/default/phreqed-dmx"
QLC_SOURCE="${REPO_ROOT}/config/qlc/qlcplus.service"
QLC_TARGET="/etc/systemd/system/qlcplus.service"
QLC_BACKUP="/etc/systemd/system/qlcplus.service.before-show-sequence"
START_NOW=0

if [[ "${1:-}" == "--start" ]]; then
    START_NOW=1
elif [[ -n "${1:-}" ]]; then
    echo "Usage: bash scripts/pi-install-show-service.sh [--start]" >&2
    exit 2
fi

if [[ "$(id -un)" != "mmorley" ]]; then
    echo "ERROR: This commissioned service is configured for user mmorley." >&2
    echo "Run it from the mmorley account, not with sudo." >&2
    exit 1
fi
if [[ "${REPO_ROOT}" != "/home/mmorley/phreqed-stage-dmx-light-controller" ]]; then
    echo "ERROR: Expected repository at /home/mmorley/phreqed-stage-dmx-light-controller." >&2
    echo "Current repository: ${REPO_ROOT}" >&2
    exit 1
fi
if [[ ! -x "${REPO_ROOT}/.venv/bin/phreqed-dmx" ]]; then
    echo "ERROR: Install the controller first with bash scripts/pi-install.sh." >&2
    exit 1
fi
if [[ ! -x "/usr/bin/qlcplus" ]]; then
    echo "ERROR: /usr/bin/qlcplus is not installed." >&2
    exit 1
fi
if [[ ! -f "/home/mmorley/.qlcplus/autostart.qxw" ]]; then
    echo "ERROR: The commissioned QLC+ runtime workspace is missing." >&2
    echo "Expected /home/mmorley/.qlcplus/autostart.qxw" >&2
    exit 1
fi

echo "Validating systemd units"
systemd-analyze verify "${QLC_SOURCE}" "${SERVICE_SOURCE}"

if sudo test -f "${QLC_TARGET}" \
        && ! sudo test -f "${QLC_BACKUP}" \
        && ! sudo cmp -s "${QLC_SOURCE}" "${QLC_TARGET}"; then
    echo "Backing up the existing QLC+ unit to ${QLC_BACKUP}"
    sudo cp -p "${QLC_TARGET}" "${QLC_BACKUP}"
fi

echo "Installing ${QLC_TARGET}"
sudo install -m 0644 "${QLC_SOURCE}" "${QLC_TARGET}"
echo "Installing ${SERVICE_TARGET}"
sudo install -m 0644 "${SERVICE_SOURCE}" "${SERVICE_TARGET}"
if [[ ! -e "${ENV_TARGET}" ]]; then
    echo "Installing safe default settings at ${ENV_TARGET}"
    sudo install -m 0644 "${ENV_SOURCE}" "${ENV_TARGET}"
else
    echo "Preserving existing ${ENV_TARGET}"
fi

sudo systemctl daemon-reload
sudo systemctl enable qlcplus.service phreqed-dmx.service

if (( START_NOW )); then
    echo "Starting the headless show sequence"
    sudo systemctl restart qlcplus.service
    sudo systemctl restart phreqed-dmx.service
else
    echo "Services enabled for the next boot; they were not started now."
fi

cat <<EOF

Review the active settings:
  sudoedit ${ENV_TARGET}

Check the boot sequence:
  systemctl status qlcplus.service phreqed-dmx.service --no-pager
  journalctl -u qlcplus.service -u phreqed-dmx.service -b --no-pager -n 100
  curl -I http://127.0.0.1:9999
  curl -I http://127.0.0.1:8080

Phreqed starts with browser live capability available but fixture output stopped.
Art-Net begins only after the operator presses Start live in the browser.
EOF
