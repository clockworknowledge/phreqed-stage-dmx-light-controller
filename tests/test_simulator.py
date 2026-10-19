import tempfile
import unittest
from pathlib import Path

from phreqed_dmx.color import NormalizedGrid, NormalizedRGB
from phreqed_dmx.simulator import export_scene_ppm


class SimulatorExportTests(unittest.TestCase):
    def test_exports_both_fixture_grids_as_ppm(self) -> None:
        scene = {
            "Cube A": NormalizedGrid(1, 1, NormalizedRGB(1.0, 0.0, 0.0)),
            "Cube B": NormalizedGrid(1, 1, NormalizedRGB(0.0, 0.0, 1.0)),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preview.ppm"
            export_scene_ppm(scene, path, pixel_size=2, gap=1)
            content = path.read_bytes()

        header = b"P6\n5 2\n255\n"
        self.assertTrue(content.startswith(header))
        self.assertEqual(len(content) - len(header), 5 * 2 * 3)
        self.assertEqual(content[len(header) : len(header) + 3], bytes((255, 0, 0)))

    def test_rejects_empty_scene_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                export_scene_ppm({}, Path(directory) / "empty.ppm")


if __name__ == "__main__":
    unittest.main()
