import unittest
from unittest.mock import patch

from phreqed_dmx.foot_control import (
    AmperoControlMapper,
    MidiMessage,
    MidiStreamParser,
    RawMidiFootController,
    dispatch_foot_action,
)


class FakeCommands:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def previous_scene(self) -> str:
        self.calls.append(("previous_scene",))
        return "previous"

    def next_scene(self) -> str:
        self.calls.append(("next_scene",))
        return "next"

    def tap_tempo(self, timestamp: float | None = None) -> float:
        self.calls.append(("tap_tempo", timestamp))
        return 120.0

    def blackout(self, enabled: bool = True) -> None:
        self.calls.append(("blackout", enabled))


class MidiStreamParserTests(unittest.TestCase):
    def test_fragmented_and_running_status_messages(self) -> None:
        parser = MidiStreamParser()
        self.assertEqual(parser.feed(bytes((0x90, 60))), ())
        self.assertEqual(
            parser.feed(bytes((127, 61, 100))),
            (
                MidiMessage("note_on", 1, 60, 127),
                MidiMessage("note_on", 1, 61, 100),
            ),
        )

    def test_realtime_bytes_do_not_interrupt_channel_message(self) -> None:
        parser = MidiStreamParser()
        self.assertEqual(
            parser.feed(bytes((0xB2, 23, 0xF8, 127))),
            (MidiMessage("control_change", 3, 23, 127),),
        )

    def test_program_change_uses_one_data_byte(self) -> None:
        parser = MidiStreamParser()
        self.assertEqual(
            parser.feed(bytes((0xC0, 7, 8))),
            (
                MidiMessage("program_change", 1, 7),
                MidiMessage("program_change", 1, 8),
            ),
        )


class AmperoControlTests(unittest.TestCase):
    def test_default_bank_maps_switches_and_explicit_blackout_values(self) -> None:
        mapper = AmperoControlMapper(channel=1)
        self.assertEqual(mapper.map(MidiMessage("note_on", 1, 60, 127)), "previous_scene")
        self.assertEqual(mapper.map(MidiMessage("note_on", 1, 61, 127)), "next_scene")
        self.assertEqual(mapper.map(MidiMessage("note_on", 1, 62, 127)), "tap_tempo")
        self.assertEqual(mapper.map(MidiMessage("control_change", 1, 23, 127)), "blackout_on")
        self.assertEqual(mapper.map(MidiMessage("control_change", 1, 23, 0)), "blackout_off")

    def test_release_and_other_channels_are_ignored(self) -> None:
        mapper = AmperoControlMapper(channel=1)
        self.assertIsNone(mapper.map(MidiMessage("note_on", 1, 60, 0)))
        self.assertIsNone(mapper.map(MidiMessage("note_on", 2, 60, 127)))

    def test_dispatch_remains_transport_independent(self) -> None:
        commands = FakeCommands()
        dispatch_foot_action(commands, "previous_scene")
        dispatch_foot_action(commands, "next_scene")
        dispatch_foot_action(commands, "tap_tempo", timestamp=12.5)
        dispatch_foot_action(commands, "blackout_on")
        dispatch_foot_action(commands, "blackout_off")
        self.assertEqual(
            commands.calls,
            [
                ("previous_scene",),
                ("next_scene",),
                ("tap_tempo", 12.5),
                ("blackout", True),
                ("blackout", False),
            ],
        )

    def test_device_is_not_opened_until_explicit_start(self) -> None:
        commands = FakeCommands()
        with patch("phreqed_dmx.foot_control.os.open") as open_device:
            RawMidiFootController("/dev/snd/midiC1D0", commands)
            open_device.assert_not_called()

    def test_expected_command_error_does_not_disable_later_messages(self) -> None:
        class EmptySceneCommands(FakeCommands):
            def next_scene(self) -> str:
                raise ValueError("add a scene first")

        errors: list[str] = []
        commands = EmptySceneCommands()
        controller = RawMidiFootController(
            "/dev/snd/midiC1D0", commands, on_error=errors.append
        )
        self.assertFalse(controller.handle_message(MidiMessage("note_on", 1, 61, 127)))
        self.assertTrue(controller.handle_message(MidiMessage("note_on", 1, 62, 127)))
        self.assertIn("add a scene first", errors[0])
        self.assertEqual(commands.calls, [("tap_tempo", None)])


if __name__ == "__main__":
    unittest.main()
