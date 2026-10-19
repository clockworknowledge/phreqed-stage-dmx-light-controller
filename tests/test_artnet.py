import unittest

from phreqed_dmx.artnet import ArtNetSender, build_artdmx_packet


class FakeSocket:
    def __init__(self, *args: object) -> None:
        self.sent: list[tuple[bytes, tuple[str, int]]] = []
        self.closed = False

    def sendto(self, data: bytes, address: tuple[str, int]) -> None:
        self.sent.append((data, address))

    def close(self) -> None:
        self.closed = True


class ArtNetPacketTests(unittest.TestCase):
    def test_builds_complete_artdmx_packet(self) -> None:
        payload = bytes(range(256)) * 2
        packet = build_artdmx_packet(payload, universe=0, sequence=7)

        self.assertEqual(packet[0:8], b"Art-Net\x00")
        self.assertEqual(packet[8:10], b"\x00\x50")
        self.assertEqual(packet[10:12], b"\x00\x0e")
        self.assertEqual(packet[12], 7)
        self.assertEqual(packet[14:16], b"\x00\x00")
        self.assertEqual(packet[16:18], b"\x02\x00")
        self.assertEqual(packet[18:], payload)

    def test_rejects_invalid_payload_sizes(self) -> None:
        for payload in (b"", bytes(3), bytes(514)):
            with self.subTest(length=len(payload)), self.assertRaises(ValueError):
                build_artdmx_packet(payload)

    def test_sender_targets_configured_endpoint_and_blackouts_on_close(self) -> None:
        fake = FakeSocket()
        sender = ArtNetSender(
            "127.0.0.1", 6454, 0, socket_factory=lambda *args: fake
        )
        sender.send(bytes([10]) * 512)
        sender.close()

        self.assertEqual(len(fake.sent), 2)
        self.assertEqual(fake.sent[0][1], ("127.0.0.1", 6454))
        self.assertEqual(fake.sent[1][0][18:], bytes(512))
        self.assertTrue(fake.closed)

    def test_sender_rejects_partial_universe(self) -> None:
        sender = ArtNetSender(
            "127.0.0.1", 6454, 0, socket_factory=lambda *args: FakeSocket()
        )
        try:
            with self.assertRaisesRegex(ValueError, "512-channel"):
                sender.send(bytes(510))
        finally:
            sender.close(blackout=False)


if __name__ == "__main__":
    unittest.main()
