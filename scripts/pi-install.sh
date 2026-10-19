#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"

cd "${REPO_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is not installed." >&2
    echo "Install it with: sudo apt install -y python3 python3-venv" >&2
    exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
    echo "ERROR: Python 3.11 or newer is required." >&2
    python3 --version >&2
    exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
    echo "Creating virtual environment at ${VENV_DIR}"
    if ! python3 -m venv "${VENV_DIR}"; then
        echo "ERROR: Could not create the virtual environment." >&2
        echo "Install venv support with: sudo apt install -y python3-venv" >&2
        exit 1
    fi
fi

echo "Installing Phreqed Stage DMX into the virtual environment"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -e .

echo "Running hardware-free validation tests"
"${VENV_DIR}/bin/python" -m unittest discover -s tests -v

cat <<EOF

Installation and tests completed successfully.

Safe simulator command (requires a desktop and python3-tk):
  ${VENV_DIR}/bin/phreqed-dmx simulate

Low-brightness live validation command:
  ${VENV_DIR}/bin/phreqed-dmx live --effect plasma --speed 0.2 --brightness 0.25

Review docs/raspberry-pi-deployment.md and verify QLC+ before live output.
EOF
