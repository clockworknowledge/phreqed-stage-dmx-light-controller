#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is not installed." >&2
    echo "Install it with: sudo apt install -y git" >&2
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "ERROR: The repository contains local or untracked changes." >&2
    echo "The updater will not overwrite or mix them with a deployment." >&2
    echo "Preserve the files elsewhere, commit them, or clean the checkout first." >&2
    git status --short >&2
    exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "${CURRENT_BRANCH}" != "main" ]]; then
    echo "ERROR: Expected the main branch; currently on '${CURRENT_BRANCH}'." >&2
    exit 1
fi

echo "Fetching and fast-forwarding origin/main"
git fetch origin main
git merge --ff-only origin/main

bash "${REPO_ROOT}/scripts/pi-install.sh"

# An editable install updates files on disk, but a running Python process keeps
# its already-imported modules. Restart the managed controller only after the
# complete hardware-free test suite succeeds. systemd sends SIGTERM, allowing
# the existing process to request blackout before it exits.
if systemctl cat phreqed-dmx.service >/dev/null 2>&1; then
    echo "Restarting the managed Phreqed controller"
    sudo systemctl restart phreqed-dmx.service
    if ! sudo systemctl is-active --quiet phreqed-dmx.service; then
        echo "ERROR: phreqed-dmx.service did not become active after update." >&2
        sudo systemctl status phreqed-dmx.service --no-pager >&2 || true
        exit 1
    fi
    sudo systemctl status phreqed-dmx.service --no-pager -n 12
else
    echo "No phreqed-dmx.service is installed; no running controller was restarted."
fi
