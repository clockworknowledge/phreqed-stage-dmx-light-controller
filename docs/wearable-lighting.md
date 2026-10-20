# Wireless wearable lighting roadmap

Wearable lighting can extend the two LF4808 fixtures and future projector output
onto the performers themselves. The initial design must prioritize unrestricted
playing, low weight, electrical and battery safety, predictable radio behavior,
and graceful failure over pixel count or maximum brightness.

## Recommended physical concept

Start with one 20-to-50-pixel prototype rather than a full suit:

- guitarist/bassist: a diffused LED channel integrated into the instrument
  strap, with all electronics toward the rear waist;
- vocalist: removable lapel, shoulder, or torso channels on a vest or jacket;
- drummer: torso/back or shoulder accents only, with no forearm, wrist, or loose
  cable elements; and
- every performer: a compact controller and protected power pack in a secured
  rear belt pouch, one accessible local power switch, strain relief, and a
  breakaway or quick-disconnect garment connection.

Avoid hands, wrists, forearms, neck loops, loose wires, rigid chest matrices,
and anything that crosses an instrument's controls or strap adjustment path.
Electronics must be removable before washing. Route switching power and LED data
away from guitar pickups and instrument/audio wiring, then test specifically for
audible noise.

Diffused flexible strip or widely spaced flexible pixels should produce a
stronger silhouette with fewer LEDs than a dense matrix. Lower pixel count means
less battery weight, less heat, longer runtime, and lower failure exposure.
Adafruit's wearable guidance similarly recommends designing around fewer pixels
rather than compensating with a large body-worn lithium pack.

## Candidate control systems

| Approach | Strengths | Risks and fit |
| --- | --- | --- |
| ESP32 running WLED | Fastest prototype; effects render locally; UDP sync, JSON control, E1.31, Art-Net, and DDP are available; automatic current limiting | Ordinary 2.4 GHz Wi-Fi can be congested; pin firmware and presets; raw boards need proper level shifting, fuse/protection, and an enclosure |
| Custom ESP32 + ESP-NOW | Low-latency connectionless transport without a venue router; compact cue packets; local patterns can coast through brief loss | Requires wearable firmware and a USB-connected ESP32 gateway because the Pi is not itself an ESP-NOW radio |
| Pixelblaze | Matchbox-sized Wi-Fi controller, local pattern engine, 2D/3D mapping, web API, and rapid visual iteration | Another proprietary runtime to integrate and validate; still uses 2.4 GHz Wi-Fi |
| Professional wireless DMX pixel receiver | Established theatrical cue workflow and purpose-built costume/prop hardware; systems such as RC4 offer pixel drivers and non-2.4 GHz options | Highest cost and more equipment; verify receiver, pixel-driver, battery, antenna, and licensing/ecosystem as a complete package |

The recommended development path is WLED for one physical proof of concept,
followed by a measured decision between hardened WLED networking, custom
ESP-NOW, and professional wireless DMX. Do not purchase a full-band system until
the prototype passes movement, comfort, RF, runtime, heat, and audio-noise tests.

Primary references:

- [WLED E1.31, Art-Net, and DDP support](https://kno.wled.ge/interfaces/e1.31-dmx/)
- [WLED UDP device synchronization](https://kno.wled.ge/interfaces/udp-notifier/)
- [WLED current limiting and ESP-NOW settings](https://kno.wled.ge/features/settings/)
- [Espressif ESP-NOW overview](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/espnow.html)
- [Pixelblaze capabilities](https://electromage.com/pixelblaze/)
- [RC4 costume and prop wireless control](https://rc4wireless.com/)
- [Adafruit wearable NeoPixel power guidance](https://learn.adafruit.com/sipping-power-with-neopixels/overview)
- [Adafruit NeoPixel electrical best practices](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices)

## Synchronization architecture

```text
audio analysis / tempo / show cue
               |
               v
        show coordinator
         |      |       |
         v      v       v
        DMX  projector  wearable transmitter
                         |
                   cue + phase + level
                         |
             local wearable renderers
```

Wearables should render effects locally. The Pi sends compact state containing
cue ID, palette, intensity, tempo/phase, bounded audio bands, sequence number,
and intended start time. Periodic phase packets correct drift. This uses much
less airtime than streaming every pixel and lets an effect continue smoothly
through a brief missed packet.

The wearable transport remains separate from Art-Net/QLC+ and from the 25 FPS
DMX deadline. It must never bind QLC+'s localhost Art-Net port or change the
known-good fixture universe. A lost wearable link fades that unit to black; it
does not stop or alter the primary lights.

The existing Ampero pedal can control unified show cues, so a second pedal is
not needed initially. Previous/next selects lighting, projector, and wearable
states together; tap tempo supplies their shared phase. The current blackout
must remain lighting-only until wearable fade-to-black and acknowledgement have
their own tests. Independent wearable-only triggers can later use another
Ampero bank or a second pedal if performance workflow shows a need.

## Electrical, battery, and performer safety

- Use a protected, reputable battery or power bank in a mechanically secured
  pouch; avoid large exposed LiPo pouches against the body.
- Fuse or current-limit each unit and set a conservative software current and
  brightness ceiling. Addressable RGB can approach 60 mA per pixel at full
  white, so design against worst case even when show content is dimmer.
- Follow pixel-controller guidance for bulk capacitance, data-line resistance,
  common ground, level shifting, and short controller-to-first-pixel wiring.
- Enclose every board and solder joint; add strain relief and sweat protection;
  prevent metal edges or hot components from contacting skin.
- Provide local physical power-off, a heartbeat watchdog, startup-black state,
  low-battery reporting, and fade-to-black on communication or renderer failure.
- Default to low brightness and continuous motion. Do not introduce rapid
  high-intensity body-worn flashes or lights aimed toward performers' eyes.
- Run full-motion instrument rehearsals, snag checks, quick-removal drills, and
  battery temperature checks before any audience use.
- Charge and inspect packs off the garment using the manufacturer's procedure;
  retire swollen, damaged, wet, or abnormally warm batteries immediately.

## Prototype acceptance

1. One performer can wear and remove the unit without help and play a complete
   rehearsal without restricted movement, snagging, pressure points, or heat.
2. The unit runs black until explicitly armed and fades black after a missed
   heartbeat, low-battery threshold, local fault, or show shutdown.
3. A private stage-network or gateway test measures latency, packet loss,
   recovery, range, and behavior amid audience Wi-Fi congestion.
4. Lighting, audio, MIDI, browser control, and future projector timing continue
   normally when the wearable is absent, powered off, or failing.
5. Current, battery runtime, connector temperature, enclosure temperature, and
   RF performance are recorded under worst-case permitted brightness.
6. Guitar/bass testing confirms no audible pickup, pedalboard, or wireless-audio
   interference.
7. Only after these checks should the design be replicated for other members.
