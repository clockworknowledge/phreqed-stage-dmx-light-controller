from __future__ import annotations

import runpy
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree


SCRIPT = runpy.run_path(
    str(Path(__file__).parents[1] / "scripts" / "configure-labwc-projection.py"),
    run_name="configure_labwc_projection",
)
main = SCRIPT["main"]


class ConfigureLabwcProjectionTests(unittest.TestCase):
    def test_repairs_only_projection_rule_and_removes_temporary_capture(self) -> None:
        source = """<?xml version="1.0"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <libinput><device category="default"><pointerSpeed>-0.74</pointerSpeed></device></libinput>
  <touch deviceName="Goodix" mapToOutput="DSI-1" mouseEmulation="yes"/>
  <core><errorCommand>sh -c 'echo %s &gt; /tmp/phreqed-labwc-config-errors.txt'</errorCommand></core>
  <windowRules>
    <windowRule identifier="other"><action name="MoveToOutput" output="DSI-1"/></windowRule>
    <windowRule identifier="vlc">
      <action name="MoveToOutput" output="DSI-1"/>
      <action name="SetFullscreen"/>
    </windowRule>
  </windowRules>
</openbox_config>
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rc.xml"
            path.write_text(source, encoding="utf-8")
            self.assertEqual(
                main(["--config", str(path), "--output", "HDMI-A-2"]), 0
            )
            self.assertEqual(
                main(["--config", str(path), "--output", "HDMI-A-2", "--check"]),
                0,
            )
            backups = list(path.parent.glob("rc.xml.before-phreqed-projection-*"))
            self.assertEqual(len(backups), 1)
            root = ElementTree.parse(path).getroot()
            rendered = path.read_text(encoding="utf-8")

        self.assertIn("pointerSpeed", rendered)
        self.assertIn('mapToOutput="DSI-1"', rendered)
        self.assertNotIn("phreqed-labwc-config-errors.txt", rendered)
        self.assertNotIn("SetFullscreen", rendered)
        self.assertIn('name="MoveToOutput" output="HDMI-A-2"', rendered)
        self.assertIn('name="ToggleFullscreen"', rendered)
        self.assertEqual(root.tag.rsplit("}", 1)[-1], "openbox_config")

    def test_is_idempotent_when_rule_is_already_current(self) -> None:
        source = """<openbox_config xmlns="http://openbox.org/3.4/rc">
  <windowRules><windowRule identifier="vlc">
    <action name="MoveToOutput" output="HDMI-A-2"/>
    <action name="ToggleFullscreen"/>
  </windowRule></windowRules>
</openbox_config>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rc.xml"
            path.write_text(source, encoding="utf-8")
            self.assertEqual(main(["--config", str(path)]), 0)
            self.assertEqual(
                list(path.parent.glob("rc.xml.before-phreqed-projection-*")), []
            )


if __name__ == "__main__":
    unittest.main()
