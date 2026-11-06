#!/usr/bin/env bash

set -Eeuo pipefail

CONNECTION_NAME="${PHREQED_HOTSPOT_CONNECTION:-phreqed-stage-ap}"
INTERFACE="${PHREQED_HOTSPOT_INTERFACE:-wlan0}"
SSID="${PHREQED_HOTSPOT_SSID:-Phreqed-Stage}"
ADDRESS="10.42.0.1/24"

usage() {
    cat <<EOF
Usage: bash scripts/pi-stage-hotspot.sh COMMAND

Commands:
  configure  Create/update the hotspot without activating it or enabling boot
  activate   Start the configured hotspot (refuses to drop the current SSH path)
  enable     Enable the tested hotspot at boot; does not activate it now
  disable    Stop the hotspot and disable it at boot
  status     Show hotspot, interface, address, and route status

Environment overrides:
  PHREQED_HOTSPOT_CONNECTION  NetworkManager profile (default: ${CONNECTION_NAME})
  PHREQED_HOTSPOT_INTERFACE   Wi-Fi interface (default: ${INTERFACE})
  PHREQED_HOTSPOT_SSID        SSID (default: ${SSID})
EOF
}

require_nmcli() {
    if ! command -v nmcli >/dev/null 2>&1; then
        echo "ERROR: NetworkManager/nmcli is required." >&2
        exit 1
    fi
    if ! nmcli -t -f DEVICE,TYPE device status | grep -Fqx "${INTERFACE}:wifi"; then
        echo "ERROR: Wi-Fi interface '${INTERFACE}' was not found." >&2
        nmcli device status >&2 || true
        exit 1
    fi
}

profile_exists() {
    nmcli -t -f NAME connection show | grep -Fqx "${CONNECTION_NAME}"
}

ssh_uses_interface() {
    local remote_ip route
    [[ -n "${SSH_CONNECTION:-}" ]] || return 1
    remote_ip="${SSH_CONNECTION%% *}"
    route="$(ip route get "${remote_ip}" 2>/dev/null || true)"
    [[ " ${route} " == *" dev ${INTERFACE} "* ]]
}

refuse_ssh_drop() {
    if ssh_uses_interface; then
        echo "ERROR: This SSH session reaches the Pi through ${INTERFACE}." >&2
        echo "Changing that interface would disconnect the session and may strand the Pi." >&2
        echo "Run this command from a local console or an Ethernet SSH session." >&2
        exit 1
    fi
}

configure() {
    local password
    read -r -s -p "WPA2 password for '${SSID}' (8-63 characters): " password
    echo
    if (( ${#password} < 8 || ${#password} > 63 )); then
        echo "ERROR: WPA2 password must contain 8 through 63 characters." >&2
        exit 2
    fi

    if ! profile_exists; then
        sudo nmcli connection add type wifi ifname "${INTERFACE}" \
            con-name "${CONNECTION_NAME}" ssid "${SSID}" autoconnect no
    fi
    sudo nmcli connection modify "${CONNECTION_NAME}" \
        connection.interface-name "${INTERFACE}" \
        connection.autoconnect no \
        802-11-wireless.mode ap \
        802-11-wireless.band bg \
        802-11-wireless.ssid "${SSID}" \
        802-11-wireless-security.key-mgmt wpa-psk \
        802-11-wireless-security.psk "${password}" \
        ipv4.method shared \
        ipv4.addresses "${ADDRESS}" \
        ipv6.method disabled
    unset password

    echo "Configured '${SSID}' at ${ADDRESS}; it is inactive and disabled at boot."
    echo "Test from Ethernet/local console with: bash scripts/pi-stage-hotspot.sh activate"
}

activate() {
    profile_exists || {
        echo "ERROR: Configure '${CONNECTION_NAME}' first." >&2
        exit 1
    }
    refuse_ssh_drop
    sudo nmcli connection up "${CONNECTION_NAME}"
    echo "Hotspot active. Join '${SSID}' and open http://10.42.0.1:8080"
}

enable() {
    profile_exists || {
        echo "ERROR: Configure and test '${CONNECTION_NAME}' first." >&2
        exit 1
    }
    sudo nmcli connection modify "${CONNECTION_NAME}" connection.autoconnect yes
    echo "Hotspot enabled for boot. The Pi will use ${SSID} instead of ${INTERFACE} as a normal Wi-Fi client."
}

disable() {
    profile_exists || {
        echo "Hotspot profile is not configured."
        return
    }
    refuse_ssh_drop
    sudo nmcli connection modify "${CONNECTION_NAME}" connection.autoconnect no
    if nmcli -t -f NAME connection show --active | grep -Fqx "${CONNECTION_NAME}"; then
        sudo nmcli connection down "${CONNECTION_NAME}"
    fi
    echo "Hotspot stopped and disabled at boot. The saved profile and key remain on the Pi."
}

status() {
    echo "Profile: ${CONNECTION_NAME}"
    echo "SSID: ${SSID}"
    echo "Expected controller: http://10.42.0.1:8080"
    if profile_exists; then
        nmcli -t -f NAME,TYPE,DEVICE,AUTOCONNECT connection show \
            | grep -F "${CONNECTION_NAME}:" || true
    else
        echo "State: not configured"
    fi
    nmcli -f DEVICE,TYPE,STATE,CONNECTION device status | grep -E "^DEVICE|^${INTERFACE}[[:space:]]" || true
    ip -4 address show dev "${INTERFACE}" || true
}

case "${1:-}" in
    configure|activate|enable|disable|status)
        require_nmcli
        "$1"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
