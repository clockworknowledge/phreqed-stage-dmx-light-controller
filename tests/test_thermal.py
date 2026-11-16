import tempfile
import unittest
from pathlib import Path

from phreqed_dmx.thermal import cpu_temperature_band, read_cpu_temperature_c


class ThermalTelemetryTests(unittest.TestCase):
    def test_reads_validated_millidegrees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "temp"
            path.write_text("49050\n", encoding="ascii")
            self.assertEqual(read_cpu_temperature_c(path), 49.05)

    def test_missing_malformed_and_out_of_range_sources_are_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "temp"
            self.assertIsNone(read_cpu_temperature_c(path))
            for value in ("not-a-number", "nan", "-1", "150001"):
                path.write_text(value, encoding="ascii")
                self.assertIsNone(read_cpu_temperature_c(path))

    def test_temperature_bands_have_explicit_boundaries(self) -> None:
        self.assertEqual(cpu_temperature_band(None), "unknown")
        self.assertEqual(cpu_temperature_band(69.99), "normal")
        self.assertEqual(cpu_temperature_band(70.0), "warm")
        self.assertEqual(cpu_temperature_band(79.99), "warm")
        self.assertEqual(cpu_temperature_band(80.0), "hot")
        with self.assertRaises(ValueError):
            cpu_temperature_band(float("nan"))


if __name__ == "__main__":
    unittest.main()
