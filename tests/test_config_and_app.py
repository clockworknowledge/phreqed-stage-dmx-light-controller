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
            [(fixture.name, fixture.start_address) for fixture in config.fixtures],
            [("Cube A", 1), ("Cube B", 153)],
        )

    def test_command_line_defaults_to_simulation(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual(args.command, "simulate")

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

    def test_controller_blackout_produces_complete_zero_dmx_frame(self) -> None:
        config = load_config()
        engine = SceneEngine(config.fixtures)
        controller = Controller(config, engine)
        controller.show.blackout()

        self.assertEqual(controller.render_dmx(1.0), bytes(512))


if __name__ == "__main__":
    unittest.main()
