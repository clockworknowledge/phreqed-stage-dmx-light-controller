#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CONTROLLER="${PHREQED_EXECUTABLE:-${REPO_ROOT}/.venv/bin/phreqed-dmx}"

if [[ ! -x "${CONTROLLER}" ]]; then
    echo "ERROR: Phreqed executable not found: ${CONTROLLER}" >&2
    echo "Run bash scripts/pi-install.sh first." >&2
    exit 1
fi

is_true() {
    case "${1:-0}" in
        1|true|TRUE|yes|YES|on|ON) return 0 ;;
        *) return 1 ;;
    esac
}

arguments=(
    live
    --web
    --host "${PHREQED_HOST:-0.0.0.0}"
    --port "${PHREQED_PORT:-8080}"
    --allow-network "${PHREQED_ALLOW_NETWORK:-192.168.1.0/24,10.42.0.0/24}"
    --rgb-ceiling "${PHREQED_RGB_CEILING:-0.65}"
    --white-ceiling "${PHREQED_WHITE_CEILING:-0.10}"
)

if [[ -n "${PHREQED_AUDIO_DEVICE:-}" ]]; then
    if command -v arecord >/dev/null 2>&1 \
            && arecord -L 2>/dev/null | grep -Fqx "${PHREQED_AUDIO_DEVICE}"; then
        arguments+=(--audio-device "${PHREQED_AUDIO_DEVICE}")
        arguments+=(--audio-sensitivity "${PHREQED_AUDIO_SENSITIVITY:-12}")
        if ! is_true "${PHREQED_AUDIO_AUTO_LEVEL:-1}"; then
            arguments+=(--no-audio-auto-level)
        fi
    elif is_true "${PHREQED_AUDIO_REQUIRED:-0}"; then
        echo "ERROR: Required audio device is unavailable: ${PHREQED_AUDIO_DEVICE}" >&2
        exit 1
    else
        echo "WARNING: Audio device unavailable; starting without audio: ${PHREQED_AUDIO_DEVICE}" >&2
    fi
fi

if [[ -n "${PHREQED_FOOT_MIDI_DEVICE:-}" ]]; then
    arguments+=(--foot-midi-device "${PHREQED_FOOT_MIDI_DEVICE}")
    arguments+=(--foot-midi-channel "${PHREQED_FOOT_MIDI_CHANNEL:-1}")
fi

if is_true "${PHREQED_ACKNOWLEDGE_HIGH_OUTPUT:-0}"; then
    arguments+=(--acknowledge-high-output)
fi
if is_true "${PHREQED_ACKNOWLEDGE_HIGH_OUTPUT_WHITES:-0}"; then
    arguments+=(--acknowledge-high-output-whites)
fi

exec "${CONTROLLER}" "${arguments[@]}"
