"""Minimal Art-Net ArtDMX packet construction and UDP output."""

from __future__ import annotations

import socket
from collections.abc import Callable
from types import TracebackType
from typing import Protocol

ARTNET_HEADER = b"Art-Net\x00"
ARTDMX_OPCODE = 0x5000
PROTOCOL_VERSION = 14
DEFAULT_PORT = 6454


def build_artdmx_packet(
    dmx_data: bytes,
    *,
    universe: int = 0,
    sequence: int = 0,
    physical: int = 0,
) -> bytes:
    length = len(dmx_data)
    if not 2 <= length <= 512 or length % 2:
        raise ValueError("ArtDMX data length must be even and between 2 and 512 bytes")
    if not 0 <= universe <= 32767:
        raise ValueError("Art-Net universe must be between 0 and 32767")
    if not 0 <= sequence <= 255:
        raise ValueError("sequence must be between 0 and 255")
    if not 0 <= physical <= 255:
        raise ValueError("physical must be between 0 and 255")

    subuni = universe & 0xFF
    net = (universe >> 8) & 0x7F
    header = bytearray(18)
    header[0:8] = ARTNET_HEADER
    header[8:10] = ARTDMX_OPCODE.to_bytes(2, "little")
    header[10:12] = PROTOCOL_VERSION.to_bytes(2, "big")
    header[12] = sequence
    header[13] = physical
    header[14] = subuni
    header[15] = net
    header[16:18] = length.to_bytes(2, "big")
    return bytes(header) + dmx_data


class DatagramSocket(Protocol):
    def sendto(self, data: bytes, address: tuple[str, int]) -> object: ...

    def close(self) -> object: ...


class ArtNetSender:
    """A live UDP sender. Create only after explicit live-mode selection."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        universe: int = 0,
        *,
        socket_factory: Callable[..., DatagramSocket] = socket.socket,
    ) -> None:
        if not host:
            raise ValueError("host cannot be empty")
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if not 0 <= universe <= 32767:
            raise ValueError("universe must be between 0 and 32767")
        self._address = (host, port)
        self._universe = universe
        self._sequence = 1
        self._socket = socket_factory(socket.AF_INET, socket.SOCK_DGRAM)
        self._closed = False

    def send(self, dmx_data: bytes) -> None:
        if self._closed:
            raise RuntimeError("Art-Net sender is closed")
        if len(dmx_data) != 512:
            raise ValueError("live output requires a complete 512-channel DMX frame")
        packet = build_artdmx_packet(
            dmx_data, universe=self._universe, sequence=self._sequence
        )
        self._socket.sendto(packet, self._address)
        self._sequence = 1 if self._sequence == 255 else self._sequence + 1

    def blackout(self) -> None:
        self.send(bytes(512))

    def close(self, *, blackout: bool = True) -> None:
        if self._closed:
            return
        try:
            if blackout:
                try:
                    self.blackout()
                except OSError:
                    # Shutdown blackout is best-effort; always release the socket.
                    pass
        finally:
            self._socket.close()
            self._closed = True

    def __enter__(self) -> ArtNetSender:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close(blackout=True)
