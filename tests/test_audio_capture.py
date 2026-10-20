import io
import math
import struct
import threading
import time
import unittest

from phreqed_dmx.audio_analysis import SILENT_AUDIO
from phreqed_dmx.audio_capture import ArecordAudioSource, Pcm16MonoAnalyzer


def tone(frequency: float, *, amplitude: int = 1_000, frames: int = 4_410) -> bytes:
    return b"".join(
        struct.pack(
            "<h", round(math.sin(2.0 * math.pi * frequency * frame / 44_100) * amplitude)
        )
        for frame in range(frames)
    )


class BlockingStream:
    def __init__(self, first_chunk: bytes) -> None:
        self.first_chunk = first_chunk
        self.first_read = threading.Event()
        self.released = threading.Event()

    def read(self, size: int = -1) -> bytes:
        if self.first_chunk:
            chunk, self.first_chunk = self.first_chunk, b""
            self.first_read.set()
            return chunk
        self.released.wait(2.0)
        return b""


class FakeProcess:
    def __init__(self, pcm: bytes) -> None:
        self.stdout = BlockingStream(pcm)
        self.stderr = io.BytesIO()
        self.alive = True
        self.terminated = False

    def poll(self) -> int | None:
        return None if self.alive else 0

    def terminate(self) -> None:
        self.terminated = True
        self.alive = False
        self.stdout.released.set()

    def kill(self) -> None:
        self.terminate()


class PcmAnalysisTests(unittest.TestCase):
    def test_tone_bands_are_distinct_deterministic_and_normalized(self) -> None:
        analyses = []
        for frequency in (100.0, 800.0, 6_000.0):
            pcm = tone(frequency)
            first = Pcm16MonoAnalyzer().process(pcm)
            repeated = Pcm16MonoAnalyzer().process(pcm)
            self.assertEqual(first, repeated)
            self.assertTrue(
                all(
                    0.0 <= value <= 1.0
                    for value in (
                        first.loudness,
                        first.onset,
                        first.bands.bass,
                        first.bands.mid,
                        first.bands.treble,
                    )
                )
            )
            analyses.append(first)

        self.assertGreater(analyses[0].bands.bass, analyses[0].bands.mid)
        self.assertGreater(analyses[1].bands.mid, analyses[1].bands.bass)
        self.assertGreater(analyses[2].bands.treble, analyses[2].bands.mid)

    def test_silence_and_malformed_pcm_are_safe(self) -> None:
        analyzer = Pcm16MonoAnalyzer()
        silent = analyzer.process(bytes(2_048))
        self.assertEqual(silent.loudness, 0.0)
        self.assertEqual(silent.bands.bass, 0.0)
        with self.assertRaises(ValueError):
            analyzer.process(b"")
        with self.assertRaises(ValueError):
            analyzer.process(b"\x00")
        with self.assertRaises(TypeError):
            analyzer.process(bytearray(2))  # type: ignore[arg-type]

    def test_configuration_boundaries_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            Pcm16MonoAnalyzer(sample_rate=7_999)
        with self.assertRaises(ValueError):
            Pcm16MonoAnalyzer(sensitivity=50.0)
        with self.assertRaises(ValueError):
            ArecordAudioSource("")
        with self.assertRaises(ValueError):
            ArecordAudioSource("default", chunk_frames=64)


class ArecordSourceTests(unittest.TestCase):
    def test_device_is_not_opened_until_explicit_start(self) -> None:
        calls = []

        def factory(*args, **kwargs):
            calls.append((args, kwargs))
            return FakeProcess(tone(100.0))

        source = ArecordAudioSource(
            "plughw:CARD=Snowball,DEV=0", process_factory=factory
        )
        self.assertEqual(calls, [])
        self.assertEqual(source.sample(0.0), SILENT_AUDIO)
        self.assertFalse(source.status().running)

    def test_worker_uses_safe_mono_format_and_stops_at_silence(self) -> None:
        captured = {}
        process = FakeProcess(tone(100.0, frames=1_024))

        def factory(command, **kwargs):
            captured["command"] = command
            captured["kwargs"] = kwargs
            return process

        source = ArecordAudioSource(
            "plughw:CARD=Snowball,DEV=0", process_factory=factory
        )
        source.start()
        self.assertTrue(process.stdout.first_read.wait(1.0))
        deadline = time.monotonic() + 1.0
        while source.status().chunks_processed == 0 and time.monotonic() < deadline:
            time.sleep(0.005)

        self.assertEqual(
            captured["command"],
            [
                "arecord",
                "-q",
                "-D",
                "plughw:CARD=Snowball,DEV=0",
                "-f",
                "S16_LE",
                "-c",
                "1",
                "-r",
                "44100",
                "-t",
                "raw",
            ],
        )
        self.assertGreater(source.sample(0.5).loudness, 0.0)
        self.assertTrue(source.status().healthy)
        source.close()
        self.assertTrue(process.terminated)
        self.assertEqual(source.sample(1.0), SILENT_AUDIO)
        self.assertFalse(source.status().running)

    def test_start_failure_is_reported_without_leaving_capture_active(self) -> None:
        def factory(*args, **kwargs):
            raise FileNotFoundError("arecord missing")

        source = ArecordAudioSource("default", process_factory=factory)
        with self.assertRaisesRegex(RuntimeError, "could not start arecord"):
            source.start()
        self.assertFalse(source.status().running)
        self.assertIn("failed", source.status().message)


if __name__ == "__main__":
    unittest.main()
