#!/usr/bin/env bash

# Start the commissioned Pi-hosted stage network from a local console.
# The underlying helper refuses to replace wlan0 when the current SSH session
# depends on it, so this wrapper is safe to keep in the project checkout.

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HOTSPOT_HELPER="${PROJECT_DIR}/scripts/pi-stage-hotspot.sh"
READINESS_CHECK="${PROJECT_DIR}/scripts/show-readiness.py"
PYTHON="${PROJECT_DIR}/.venv/bin/python"

if [[ ! -f "${HOTSPOT_HELPER}" ]]; then
    echo "ERROR: Missing hotspot helper: ${HOTSPOT_HELPER}" >&2
    exit 1
fi

echo "Starting the private Phreqed stage network..."
bash "${HOTSPOT_HELPER}" activate

echo
bash "${HOTSPOT_HELPER}" status

echo
if [[ -x "${PYTHON}" && -f "${READINESS_CHECK}" ]]; then
    "${PYTHON}" "${READINESS_CHECK}" \
        --startup-defaults \
        --require-stage-lan
else
    echo "WARNING: Project virtual environment is unavailable; readiness check skipped." >&2
fi

cat <<'EOF'

Stage network is ready.
  iPhone Wi-Fi: Phreqed-Stage
  Controller:  http://10.42.0.1:8080
  QLC+ recovery: http://10.42.0.1:9999

If iOS says the network has no internet, choose to remain connected.
Fixture output still starts stopped and requires Start live in the controller.
EOF
