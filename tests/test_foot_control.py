import unittest
import time
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

    def test_missing_device_at_start_waits_and_reconnects_without_crashing(self) -> None:
        errors: list[str] = []
        controller = RawMidiFootController(
            "/dev/snd/midiC3D0",
            FakeCommands(),
            on_error=errors.append,
            reconnect_interval=0.001,
        )

        def select_device(readers, writers, errors_list, timeout):
            controller._stop.set()
            return (), (), ()

        with (
            patch(
                "phreqed_dmx.foot_control.os.open",
                side_effect=(FileNotFoundError("not enumerated"), 11),
            ) as opened,
            patch("phreqed_dmx.foot_control.os.close"),
            patch("phreqed_dmx.foot_control.select.select", side_effect=select_device),
        ):
            controller.start()
            self.assertTrue(controller.status().running)
            deadline = time.monotonic() + 1.0
            while controller._thread is not None and controller._thread.is_alive():
                if time.monotonic() >= deadline:
                    self.fail("MIDI startup reconnect thread did not finish")
                time.sleep(0.005)
            self.assertEqual(opened.call_count, 2)
            self.assertTrue(controller.status().connected)
            self.assertTrue(any("unavailable at startup" in item for item in errors))
            self.assertTrue(any("reconnected" in item for item in errors))
            controller.close()

    def test_device_disconnect_reopens_input_instead_of_ending_thread(self) -> None:
        errors: list[str] = []
        commands = FakeCommands()
        controller = RawMidiFootController(
            "/dev/snd/midiC1D0",
            commands,
            on_error=errors.append,
            reconnect_interval=0.001,
        )

        def select_device(readers, writers, errors_list, timeout):
            descriptor = readers[0]
            if descriptor == 10:
                raise OSError("USB MIDI disconnected")
            controller._stop.set()
            return (), (), ()

        with (
            patch("phreqed_dmx.foot_control.os.open", side_effect=(10, 11)) as opened,
            patch("phreqed_dmx.foot_control.os.close") as closed,
            patch("phreqed_dmx.foot_control.select.select", side_effect=select_device),
        ):
            controller.start()
            deadline = time.monotonic() + 1.0
            while controller._thread is not None and controller._thread.is_alive():
                if time.monotonic() >= deadline:
                    self.fail("MIDI reconnect thread did not finish")
                time.sleep(0.005)
            status = controller.status()
            self.assertEqual(opened.call_count, 2)
            self.assertEqual(status.reconnects, 1)
            self.assertTrue(status.connected)
            self.assertTrue(any("reconnecting" in message for message in errors))
            controller.close()
            self.assertGreaterEqual(closed.call_count, 2)


if __name__ == "__main__":
    unittest.main()
