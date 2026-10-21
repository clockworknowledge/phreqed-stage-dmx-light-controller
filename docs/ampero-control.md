# Hotone Ampero Control

The Hotone Ampero Control is a four-switch programmable MIDI controller. The
manufacturer documents standard MIDI, USB MIDI, and Bluetooth MIDI output, with
PC, CC, Note On, and Note Off messages. Phreqed initially supports its USB MIDI
path through an ALSA raw-MIDI device on the Raspberry Pi.

USB is the recommended live-performance connection for the first release. It
powers the Ampero Control, avoids radio pairing and reconnection uncertainty,
and is easy to diagnose locally. Bluetooth remains a planned optional transport
after the wired mapping passes a rehearsal-length soak test.

The tested pedal was updated to firmware 1.1.8 with iOS app 1.1.0. On the Pi it
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

On 2026-10-20 the operator observed `90 3C 7F`, `90 3D 7F`, `90 3E 7F`,
`B0 17 7F`, and `B0 17 00` from the raw device. All mapped actions passed in
trusted-LAN browser simulation, and guarded browser-live operation was reported
working. A later loss of pedal response exposed a reader thread that exited on
the first device error; automatic same-path reconnect and status reporting are
now implemented. A rehearsal-length USB soak and stable udev link remain
pending.

## Bluetooth status

The Ampero Control supports Bluetooth MIDI and enters pairing mode by holding
FS2 and FS3. Direct BLE MIDI discovery and reconnect handling are not part of
this first adapter. Do not make Bluetooth the only show-control path until it
has deterministic reconnect behavior and a rehearsal-length soak test on the
actual Pi.
