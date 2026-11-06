#!/usr/bin/env bash

# Switch the commissioned Pi between its stage hotspot and saved private Wi-Fi.
# Network changes refuse to replace wlan0 when the current SSH session depends
# on it, so use the interactive menu from a local keyboard/screen.

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HOTSPOT_HELPER="${PROJECT_DIR}/scripts/pi-stage-hotspot.sh"
READINESS_CHECK="${PROJECT_DIR}/scripts/show-readiness.py"
PYTHON="${PROJECT_DIR}/.venv/bin/python"
INTERFACE="${PHREQED_HOTSPOT_INTERFACE:-wlan0}"
HOTSPOT_CONNECTION="${PHREQED_HOTSPOT_CONNECTION:-phreqed-stage-ap}"

if [[ ! -f "${HOTSPOT_HELPER}" ]]; then
    echo "ERROR: Missing hotspot helper: ${HOTSPOT_HELPER}" >&2
    exit 1
fi

usage() {
    cat <<'EOF'
Usage: ./local_network.sh [stage|wifi|status|enable-stage|disable-stage]

With no argument, an interactive local-console menu is displayed.

  stage          activate the private Phreqed-Stage hotspot now
  wifi           select and activate an existing saved Wi-Fi profile
  status         show hotspot and Wi-Fi status
  enable-stage   make the tested stage hotspot the next-boot default
  disable-stage  disable hotspot autostart without changing networks
EOF
}

ssh_uses_wifi() {
    local remote_ip route
    [[ -n "${SSH_CONNECTION:-}" ]] || return 1
    remote_ip="${SSH_CONNECTION%% *}"
    route="$(ip route get "${remote_ip}" 2>/dev/null || true)"
    [[ " ${route} " == *" dev ${INTERFACE} "* ]]
}

refuse_wifi_ssh_drop() {
    if ssh_uses_wifi; then
        echo "ERROR: This SSH session reaches the Pi through ${INTERFACE}." >&2
        echo "Switch networks from the Pi's local console or Ethernet SSH." >&2
        exit 1
    fi
}

show_status() {
    bash "${HOTSPOT_HELPER}" status
    echo
    echo "Active connections:"
    nmcli -t -f NAME,TYPE,DEVICE connection show --active || true
}

run_readiness() {
    if [[ -x "${PYTHON}" && -f "${READINESS_CHECK}" ]]; then
        "${PYTHON}" "${READINESS_CHECK}" \
            --startup-defaults \
            --require-stage-lan
    else
        echo "WARNING: Project virtual environment is unavailable; readiness check skipped." >&2
    fi
}

activate_stage() {
    echo "Starting the private Phreqed stage network..."
    bash "${HOTSPOT_HELPER}" activate

    echo
    show_status

    echo
    run_readiness

    cat <<'EOF'

Stage network is ready.
  iPhone Wi-Fi: Phreqed-Stage
  Controller:  http://10.42.0.1:8080
  QLC+ recovery: http://10.42.0.1:9999

If iOS says the network has no internet, choose to remain connected.
Fixture output still starts stopped and requires Start live in the controller.
EOF
}

saved_wifi_profiles() {
    nmcli -t -f NAME,TYPE connection show \
        | while IFS=: read -r name type; do
            if [[ "${name}" != "${HOTSPOT_CONNECTION}" \
                && ( "${type}" == "wifi" || "${type}" == "802-11-wireless" ) ]]; then
                printf '%s\n' "${name}"
            fi
        done
}

choose_wifi_profile() {
    local choice
    mapfile -t profiles < <(saved_wifi_profiles)
    if (( ${#profiles[@]} == 0 )); then
        echo "ERROR: No saved non-hotspot Wi-Fi profiles were found." >&2
        echo "Connect this Pi to the private/home Wi-Fi once before using this option." >&2
        return 1
    fi
    if (( ${#profiles[@]} == 1 )); then
        SELECTED_WIFI="${profiles[0]}"
        return
    fi

    echo "Saved Wi-Fi profiles:" >&2
    for (( choice = 0; choice < ${#profiles[@]}; choice++ )); do
        printf '  %d) %s\n' "$((choice + 1))" "${profiles[choice]}" >&2
    done
    read -r -p "Select a profile: " choice
    if [[ ! "${choice}" =~ ^[0-9]+$ ]] \
        || (( choice < 1 || choice > ${#profiles[@]} )); then
        echo "ERROR: Invalid Wi-Fi selection." >&2
        return 1
    fi
    SELECTED_WIFI="${profiles[choice - 1]}"
}

activate_saved_wifi() {
    refuse_wifi_ssh_drop
    choose_wifi_profile
    echo "Switching to saved Wi-Fi profile '${SELECTED_WIFI}'..."
    bash "${HOTSPOT_HELPER}" disable
    sudo nmcli connection up "${SELECTED_WIFI}"
    echo
    nmcli -f DEVICE,TYPE,STATE,CONNECTION device status \
        | grep -E "^DEVICE|^${INTERFACE}[[:space:]]" || true
    ip -4 address show dev "${INTERFACE}" || true
    echo
    echo "Private/home Wi-Fi is active. The controller remains output-stopped."
}

disable_stage_boot() {
    if ! nmcli -t -f NAME connection show | grep -Fqx "${HOTSPOT_CONNECTION}"; then
        echo "Hotspot profile is not configured."
        return
    fi
    sudo nmcli connection modify "${HOTSPOT_CONNECTION}" connection.autoconnect no
    echo "Stage hotspot autostart disabled; the active network was not changed."
}

menu() {
    local choice
    while true; do
        cat <<'EOF'

Phreqed network mode
  1) Start stage hotspot now
  2) Switch to saved private/home Wi-Fi
  3) Show network status
  4) Enable stage hotspot at boot
  5) Disable stage hotspot at boot
  6) Exit
EOF
        read -r -p "Choose 1-6: " choice
        case "${choice}" in
            1) activate_stage; return ;;
            2) activate_saved_wifi; return ;;
            3) show_status ;;
            4) bash "${HOTSPOT_HELPER}" enable ;;
            5) disable_stage_boot ;;
            6) return ;;
            *) echo "Invalid selection." >&2 ;;
        esac
    done
}

case "${1:-menu}" in
    stage) activate_stage ;;
    wifi) activate_saved_wifi ;;
    status) show_status ;;
    enable-stage) bash "${HOTSPOT_HELPER}" enable ;;
    disable-stage) disable_stage_boot ;;
    menu) menu ;;
    -h|--help|help) usage ;;
    *) usage >&2; exit 2 ;;
esac
