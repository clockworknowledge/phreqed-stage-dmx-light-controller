import unittest
from unittest.mock import patch

from phreqed_dmx.app import Controller, build_parser, main
from phreqed_dmx.config import load_config
from phreqed_dmx.engine import SceneEngine


class ConfigurationTests(unittest.TestCase):
    def test_repository_configuration_matches_confirmed_hardware(self) -> None:
        config = load_config()
        self.assertEqual(config.artnet_host, "127.0.0.1")
        self.assertEqual(config.artnet_port, 6454)
        self.assertEqual(config.universe, 0)
        self.assertEqual(config.fps, 25)
        self.assertEqual(
            [
                (fixture.name, fixture.start_address, fixture.width, fixture.height)
                for fixture in config.fixtures
            ],
            [("Cube A", 1, 12, 4), ("Cube B", 153, 12, 4)],
        )

    def test_command_line_defaults_to_simulation(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual(args.command, "simulate")
        self.assertIsNone(args.audio_device)
        self.assertIsNone(args.audio_sensitivity)

    def test_live_output_requires_explicit_command(self) -> None:
        args = build_parser().parse_args(["live", "--effect", "cross-cube"])
        self.assertEqual(args.command, "live")
        self.assertEqual(args.effect, "cross-cube")

    def test_cli_exposes_advanced_effects_and_presets(self) -> None:
        args = build_parser().parse_args(
            ["simulate", "--effect", "kaleidoscope", "--preset", "digital-storm"]
        )
        self.assertEqual(args.effect, "kaleidoscope")
        self.assertEqual(args.preset, "digital-storm")

    def test_simulation_path_never_constructs_artnet_sender(self) -> None:
        with (
            patch("phreqed_dmx.app.ArtNetSender") as sender,
            patch("phreqed_dmx.simulator.TkSimulator") as simulator,
        ):
            self.assertEqual(main(["simulate", "--effect", "plasma"]), 0)

        sender.assert_not_called()
        simulator.assert_called_once()
        simulator.return_value.run.assert_called_once_with()

    def test_explicit_foot_device_does_not_enable_artnet(self) -> None:
        with (
            patch("phreqed_dmx.app.ArtNetSender") as sender,
            patch("phreqed_dmx.app.RawMidiFootController") as foot,
            patch("phreqed_dmx.simulator.TkSimulator") as simulator,
        ):
            self.assertEqual(
                main(["simulate", "--foot-midi-device", "/dev/snd/midiC1D0"]),
                0,
            )

        sender.assert_not_called()
        foot.assert_called_once()
        foot.return_value.start.assert_called_once_with()
        foot.return_value.close.assert_called_once_with()
        simulator.return_value.run.assert_called_once_with()

    def test_explicit_audio_device_starts_capture_without_enabling_artnet(self) -> None:
        with (
            patch("phreqed_dmx.app.ArtNetSender") as sender,
            patch("phreqed_dmx.audio_capture.ArecordAudioSource") as capture,
            patch("phreqed_dmx.simulator.TkSimulator") as simulator,
        ):
            self.assertEqual(
                main(
                    [
                        "simulate",
                        "--audio-device",
                        "plughw:CARD=Snowball,DEV=0",
                        "--audio-sensitivity",
                        "9.5",
                    ]
                ),
                0,
            )

        sender.assert_not_called()
        capture.assert_called_once_with(
            "plughw:CARD=Snowball,DEV=0", sensitivity=9.5
        )
        capture.return_value.start.assert_called_once_with()
        capture.return_value.close.assert_called_once_with()
        simulator.assert_called_once()
        simulator.return_value.run.assert_called_once_with()

    def test_audio_sensitivity_requires_explicit_device(self) -> None:
        with self.assertRaises(SystemExit):
            main(["simulate", "--audio-sensitivity", "8"])

    def test_controller_blackout_produces_complete_zero_dmx_frame(self) -> None:
        config = load_config()
        engine = SceneEngine(config.fixtures)
        controller = Controller(config, engine)
        controller.show.blackout()

        self.assertEqual(controller.render_dmx(1.0), bytes(512))

    def test_controller_smoothly_transitions_between_effects(self) -> None:
        config = load_config()
        engine = SceneEngine(config.fixtures)
        controller = Controller(config, engine)
        engine.select_effect("Cube A", "plasma")
        engine.select_effect("Cube B", "plasma")
        before = controller.render_scene(0.0, apply_safety=False)
        controller.begin_transition(0.0, duration=1.0)
        engine.select_effect("Cube A", "fire")

        start = controller.render_scene(0.0, apply_safety=False)
        middle = controller.render_scene(0.5, apply_safety=False)
        end = controller.render_scene(1.0, apply_safety=False)

        self.assertEqual(start["Cube A"].rows(), before["Cube A"].rows())
        self.assertNotEqual(middle["Cube A"].rows(), start["Cube A"].rows())
        self.assertNotEqual(end["Cube A"].rows(), middle["Cube A"].rows())


if __name__ == "__main__":
    unittest.main()
