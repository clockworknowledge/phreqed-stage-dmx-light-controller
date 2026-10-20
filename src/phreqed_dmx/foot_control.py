"""Dependency-free MIDI input for transport-independent foot control."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import select
import sys
import threading
from typing import Callable, Iterable, Literal, Protocol


MidiType = Literal["note_off", "note_on", "control_change", "program_change"]
FootAction = Literal[
    "previous_scene",
    "next_scene",
    "tap_tempo",
    "blackout_on",
    "blackout_off",
]


class FootCommands(Protocol):
    def previous_scene(self) -> object: ...
    def next_scene(self) -> object: ...
    def tap_tempo(self, timestamp: float | None = None) -> float: ...
    def blackout(self, enabled: bool = True) -> None: ...


@dataclass(frozen=True, slots=True)
class MidiMessage:
    """One normalized MIDI channel message."""

    message_type: MidiType
    channel: int
    data1: int
    data2: int = 0

    def __post_init__(self) -> None:
        if not 1 <= self.channel <= 16:
            raise ValueError("MIDI channel must be between 1 and 16")
        if not 0 <= self.data1 <= 127 or not 0 <= self.data2 <= 127:
            raise ValueError("MIDI data values must be between 0 and 127")


class MidiStreamParser:
    """Parse standard MIDI bytes, including running status and real-time bytes."""

    _TYPE_BY_NIBBLE: dict[int, MidiType] = {
        0x80: "note_off",
        0x90: "note_on",
        0xB0: "control_change",
        0xC0: "program_change",
    }

    def __init__(self) -> None:
        self._status: int | None = None
        self._data: list[int] = []

    def feed(self, data: bytes | bytearray | Iterable[int]) -> tuple[MidiMessage, ...]:
        messages: list[MidiMessage] = []
        for value in data:
            if not 0 <= value <= 255:
                raise ValueError("MIDI bytes must be between 0 and 255")
            if value >= 0xF8:
                # MIDI clock and other real-time bytes may appear between data bytes.
                continue
            if value & 0x80:
                self._data.clear()
                self._status = value if value < 0xF0 else None
                continue
            if self._status is None:
                continue
            self._data.append(value)
            required = 1 if self._status & 0xE0 == 0xC0 else 2
            if len(self._data) < required:
                continue
            status = self._status
            payload = self._data[:required]
            self._data.clear()
            message_type = self._TYPE_BY_NIBBLE.get(status & 0xF0)
            if message_type is not None:
                messages.append(
                    MidiMessage(
                        message_type=message_type,
                        channel=(status & 0x0F) + 1,
                        data1=payload[0],
                        data2=payload[1] if len(payload) == 2 else 0,
                    )
                )
        return tuple(messages)


@dataclass(frozen=True, slots=True)
class MidiBinding:
    message_type: MidiType
    channel: int
    data1: int
    minimum: int
    maximum: int
    action: FootAction

    def __post_init__(self) -> None:
        if not 1 <= self.channel <= 16:
            raise ValueError("MIDI binding channel must be between 1 and 16")
        if not 0 <= self.data1 <= 127:
            raise ValueError("MIDI binding data1 must be between 0 and 127")
        if not 0 <= self.minimum <= self.maximum <= 127:
            raise ValueError("MIDI binding range must be within 0 through 127")

    def matches(self, message: MidiMessage) -> bool:
        return (
            message.message_type == self.message_type
            and message.channel == self.channel
            and message.data1 == self.data1
            and self.minimum <= message.data2 <= self.maximum
        )


class AmperoControlMapper:
    """Map the documented Phreqed Ampero bank onto show-control actions."""

    def __init__(self, channel: int = 1) -> None:
        if not 1 <= channel <= 16:
            raise ValueError("Ampero MIDI channel must be between 1 and 16")
        self.bindings = (
            MidiBinding("note_on", channel, 60, 1, 127, "previous_scene"),
            MidiBinding("note_on", channel, 61, 1, 127, "next_scene"),
            MidiBinding("note_on", channel, 62, 1, 127, "tap_tempo"),
            MidiBinding("control_change", channel, 23, 64, 127, "blackout_on"),
            MidiBinding("control_change", channel, 23, 0, 63, "blackout_off"),
        )

    def map(self, message: MidiMessage) -> FootAction | None:
        for binding in self.bindings:
            if binding.matches(message):
                return binding.action
        return None


def dispatch_foot_action(
    commands: FootCommands, action: FootAction, *, timestamp: float | None = None
) -> None:
    """Apply one normalized foot action without knowing about DMX or Art-Net."""

    if action == "previous_scene":
        commands.previous_scene()
    elif action == "next_scene":
        commands.next_scene()
    elif action == "tap_tempo":
        commands.tap_tempo(timestamp)
    elif action == "blackout_on":
        commands.blackout(True)
    elif action == "blackout_off":
        commands.blackout(False)
    else:  # pragma: no cover - exhaustive guard for callers without type checking
        raise ValueError(f"unknown foot action: {action}")


class RawMidiFootController:
    """Read an ALSA raw-MIDI device in a background thread.

    Linux ALSA exposes USB MIDI devices as ``/dev/snd/midiC*D*``. Opening the
    device is always explicit; constructing this adapter has no hardware side
    effects and never creates a network socket.
    """

    def __init__(
        self,
        device: str | Path,
        commands: FootCommands,
        *,
        channel: int = 1,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.device = Path(device)
        self.commands = commands
        self.mapper = AmperoControlMapper(channel)
        self.on_error = on_error or (lambda message: print(message, file=sys.stderr))
        self._parser = MidiStreamParser()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._file_descriptor: int | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("foot controller is already running")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
        self._file_descriptor = os.open(self.device, flags)
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="phreqed-foot-control", daemon=True
        )
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._file_descriptor is not None:
            os.close(self._file_descriptor)
            self._file_descriptor = None

    def __enter__(self) -> RawMidiFootController:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def handle_message(self, message: MidiMessage) -> bool:
        """Dispatch one parsed message; expected command errors do not stop input."""

        action = self.mapper.map(message)
        if action is None:
            return False
        try:
            dispatch_foot_action(self.commands, action)
        except (ValueError, RuntimeError) as exc:
            self.on_error(f"Foot action {action} ignored: {exc}")
            return False
        return True

    def _run(self) -> None:
        descriptor = self._file_descriptor
        if descriptor is None:  # pragma: no cover - guarded by start
            return
        try:
            while not self._stop.is_set():
                readable, _, _ = select.select((descriptor,), (), (), 0.2)
                if not readable:
                    continue
                chunk = os.read(descriptor, 256)
                if not chunk:
                    raise OSError("MIDI device disconnected")
                for message in self._parser.feed(chunk):
                    self.handle_message(message)
        except OSError as exc:
            if not self._stop.is_set():
                self.on_error(f"Foot controller stopped: {exc}")
