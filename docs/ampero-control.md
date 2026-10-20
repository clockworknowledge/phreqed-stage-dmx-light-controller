# Hotone Ampero Control

The Hotone Ampero Control is a four-switch programmable MIDI controller. The
manufacturer documents standard MIDI, USB MIDI, and Bluetooth MIDI output, with
PC, CC, Note On, and Note Off messages. Phreqed initially supports its USB MIDI
path through an ALSA raw-MIDI device on the Raspberry Pi.

USB is the recommended live-performance connection for the first release. It
powers the Ampero Control, avoids radio pairing and reconnection uncertainty,
and is easy to diagnose locally. Bluetooth remains a planned optional transport
after the wired mapping passes a rehearsal-length soak test.

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
phreqed-dmx web --foot-midi-device /dev/snd/midiC1D0
```

The browser should show `Preview · no output`. Confirm previous/next scene, tap
tempo, blackout on, and blackout off before testing live output.

Live browser control remains a separate, explicit choice:

```bash
phreqed-dmx live --web --foot-midi-device /dev/snd/midiC1D0
```

The pedal cannot start Art-Net transmission. Browser live confirmation and its
disconnect watchdog remain active.

## Bluetooth status

The Ampero Control supports Bluetooth MIDI and enters pairing mode by holding
FS2 and FS3. Direct BLE MIDI discovery and reconnect handling are not part of
this first adapter. Do not make Bluetooth the only show-control path until it
has deterministic reconnect behavior and a rehearsal-length soak test on the
actual Pi.
