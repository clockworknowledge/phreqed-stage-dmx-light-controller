# Hotone Ampero Control

The Hotone Ampero Control is a four-switch programmable MIDI controller. The
manufacturer documents standard MIDI, USB MIDI, and Bluetooth MIDI output, with
PC, CC, Note On, and Note Off messages. Phreqed initially supports its USB MIDI
path through an ALSA raw-MIDI device on the Raspberry Pi.

USB is the recommended live-performance connection for the first release. It
powers the Ampero Control, avoids radio pairing and reconnection uncertainty,
and is easy to diagnose locally. Bluetooth remains a planned optional transport
after the wired mapping passes a rehearsal-length soak test.

The tested pedal was updated to firmware 1.13 with iOS app 1.1.0. On the Pi it
enumerated as ALSA sequencer port `28:0`, raw device `hw:3,0,0`, and filesystem
path `/dev/snd/midiC3D0`. These numeric identifiers are observational, not a
stable deployment contract.

## Program the Phreqed bank

Use the Hotone Ampero Control mobile app and create a bank on MIDI channel 1.
Enable **USB** in `Output To` for every message.

| Switch | Ampero mode | MIDI message | Phreqed action |
| --- | --- | --- | --- |
| FS1 | Single | Note On, note 60, velocity 127 | Previous scene |
| FS2 | Single | Note On, note 61, velocity 127 | Next scene |
| FS3 | Single | Note On, note 62, velocity 127 | Tap tempo |
| FS4 | Toggle | A: CC 23 value 127; B: CC 23 value 0 | Blackout on/off |

The blackout binding uses explicit values rather than toggling application
state blindly. This makes duplicate MIDI messages idempotent. The pedal's bank
state and the controller state should still be checked after reconnecting.

## Discover the USB MIDI device on the Pi

Connect the Ampero Control to the Pi with its USB Type-B cable, then run:

```bash
sudo apt install alsa-utils
aconnect -l
amidi -l
ls -l /dev/snd/midiC*D*
```

Do not guess the path in a stage service: record the path reported for the
Ampero Control. ALSA card numbers can change when other USB audio/MIDI devices
are connected, so a stable udev link is required before unattended use.

## Hardware-free and pedal-only test

The automated parser and mapping tests run without MIDI or DMX hardware:

```bash
python -m unittest discover -s tests -v
```

For a pedal test with no Art-Net output, use browser simulation and the actual
raw-MIDI path:

```bash
phreqed-dmx web --foot-midi-device /dev/snd/midiC3D0
```

The browser should show `Preview · no output`. Confirm previous/next scene, tap
tempo, blackout on, and blackout off before testing live output.

Live browser control remains a separate, explicit choice:

```bash
phreqed-dmx live --web --foot-midi-device /dev/snd/midiC3D0
```

The pedal cannot start Art-Net transmission. Browser live confirmation and its
disconnect watchdog remain active.

The raw-MIDI reader automatically retries the same configured path after a
read, select, or device-disconnect error. A malformed command or UI-reporting
failure is contained and cannot terminate the input thread. Browser control
shows whether MIDI is connected, how many messages were received, and how many
disconnect cycles occurred. This addresses transient USB/ALSA failures, but it
does not solve Linux assigning the pedal a different card number. Use a stable
udev symlink for unattended stage operation.

The integrated soak report records all reconnect messages under `foot_events`,
only mapped-action failures under `foot_errors`, and the pre-shutdown device
state under `foot_final_status`. A recovered controlled reconnect is accepted;
missing switch actions or a final disconnected state still fails the test.

An open ALSA device is not a complete readiness signal. After startup and after
every reconnect, require at least one valid mapped MIDI message before declaring
the pedal functionally ready for a show. The browser remains the independent
backup control path.

On 2026-10-20 the operator observed `90 3C 7F`, `90 3D 7F`, `90 3E 7F`,
`B0 17 7F`, and `B0 17 00` from the raw device. All mapped actions passed in
trusted-LAN browser simulation, and guarded browser-live operation was reported
working. A later loss of pedal response exposed a reader thread that exited on
the first device error; automatic same-path reconnect and status reporting are
now implemented. A rehearsal-length USB soak and stable udev link remain
pending.

## Deferred configuration recovery sprint

On 2026-10-21 a controlled USB disconnect produced the expected reader events:
the old device failed with `Errno 19`, and the same path was reopened. The final
status said connected with one reconnect, but `messages_received` remained zero
and none of the five required actions occurred. Direct `amidi` and `aseqdump`
were also silent. Reinitializing the Ampero bank with the iOS application
restored MIDI output. This distinguishes operating-system reconnection from
functional pedal recovery and keeps the reconnect acceptance gate open.

Configuration recovery is tracked separately as `CONTROL-002`. Initial static,
read-only research used Hotone's official firmware-1.13 Android application
archive. The vendor ZIP was not added to this repository; its SHA-256 is
`3F8645221B4C6B8386211FFC914F751B79D6C54379E189464CE766EDFF5D6192`.
The application is built with Flutter, uses `flutter_blue`, and contains strings
for preset request/send acknowledgements, SysEx, CRC32, bank synchronization,
MIDI testing, and custom GATT UUIDs. These findings justify a protocol-research
sprint but do not justify transmitting unknown commands to the pedal.

Candidate UUID families extracted for later read-only comparison are
`36D70001-A25B-40FE-99A0-36453A1D8704` through the observed `...0006` members,
`36D71001-A25B-40FE-99A0-36453A1D8704` through `...1008`,
`4FC61110-16CC-4BEF-9629-0146097FC45C`,
`4FC669C6-16CC-4BEF-9629-0146097FC45C`, and the TI-style
`F000FFC0/1/2-0451-4000-B000-000000000000` group. They are leads, not confirmed
command channels. The official archive was obtained from Hotone's software
support page: <https://www.hotone.com/support/3>.

The existing `/dev/snd/by-id/usb-HOTONE_Ampero_Control-00` link resolves to the
ALSA control node (`controlC3`), not the raw MIDI node, so it cannot be passed to
`--foot-midi-device`. Creating a stable raw-MIDI udev link remains separate
deployment work.

The intended command surface is:

```text
phreqed-dmx ampero inspect
phreqed-dmx ampero verify config/ampero/light-control.toml
phreqed-dmx ampero restore config/ampero/light-control.toml
```

`inspect` and `verify` must be read-only. `restore` must remain unavailable
until the protocol framing and CRC are understood, the exact model and firmware
are validated, a backup can be read and parsed, a dry-run is available, writes
are explicitly confirmed and limited to one bank, and read-back proves a valid
round trip. Firmware-transfer endpoints are out of scope.

The planned investigation sequence is:

1. Extract protocol clues statically from the application.
2. Enumerate BLE GATT services and characteristics read-only on the Pi.
3. Identify command and notification characteristics.
4. Capture two app synchronizations whose banks differ by exactly one value.
5. Decode message boundaries, field encoding, acknowledgements, and CRC.
6. Implement and test read-only `inspect` and `verify` with a fake transport.
7. Only after those gates pass, design a separately authorized single-bank
   restore experiment with backup and read-back verification.

For the read-only Pi discovery step, disconnect the iPhone app, put the pedal in
pairing mode with FS2+FS3, confirm `bluetooth.service`, scan with
`bluetoothctl`, connect to the discovered address, then use `menu gatt` and
`list-attributes`. Disconnect without issuing characteristic writes. A later
differential capture should compare two otherwise identical banks that differ
by one note or velocity value.

This work is intentionally deferred while the current lighting, audio, and
pedal bench sequence continues.

## Bluetooth status

The Ampero Control supports Bluetooth MIDI and enters pairing mode by holding
FS2 and FS3. Direct BLE MIDI discovery and reconnect handling are not part of
this first adapter. Do not make Bluetooth the only show-control path until it
has deterministic reconnect behavior and a rehearsal-length soak test on the
actual Pi.
