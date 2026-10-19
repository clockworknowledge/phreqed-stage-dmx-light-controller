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

exec bash "${REPO_ROOT}/scripts/pi-install.sh"
