# Integrated Lighting and Video VFX sprint

Date: 2026-11-17  
Cards: `VFX-001`, `VFX-002`, `SHOW-006`, `SHOW-007`
Reference song: **Travelling on a Floating Rock**

## Goal

Make the Betopper cubes and projection feel like one choreographed visual
instrument. Short VFX phrases should occupy selected spaces between primary
band-video clips, answer Lighting events, and occasionally appear to travel
from a fixture to the screen and back. The performer remains the focus and
intentional black remains part of the composition.

The primary reusable media unit is a **visual storylet**: a self-contained,
audio-free, 10–30 second rendered clip with a simple readable setup, action,
impact, and return to black. Storylets may contain characters, props, abstract
effects, or a short visual joke. Full-song and continuous video remain valid
choices, but they are secondary treatments rather than the default Stage media
model.

The first sprint uses the proven offline EDL/package path. It does not add live
Pi compositing, a second show clock, or an audio-to-video control loop. Lighting
and the pre-rendered Video package receive deterministic events from the same
song timeline; Video failure remains contained from Lighting.

## Performer and designer stories

- As a performer, I see visual motion pass between Lighting and projection in a
  way that supports musical accents without requiring another control surface.
- As an audience member, I can read an intentional call, response, throw, or
  impact across the whole stage rather than seeing unrelated loops.
- As a show designer, I can place short VFX phrases between primary clips and
  preserve darkness/rest instead of filling every available second.
- As a show designer, I can reuse one 10–30 second storylet in different songs
  by aligning its named event markers to different Lighting cues without
  editing the source master.
- As a show designer, I can reuse a small choreography vocabulary across songs
  while changing palette, asset, direction, intensity, and timing.
- As an operator, Start, Stop, Blackout, song selection, Video-disabled mode,
  and projector failure retain their current safe behavior.
- As a Studio designer, I can later represent the proven patterns as editable
  cross-surface cues rather than reverse-engineering one-off rendered videos.

## Reusable storylet contract

Each storylet is versioned independently from a song and contains:

- stable storylet ID, revision, title, duration, rights/source provenance, and
  source hashes;
- one primary action and a compact setup/action/impact/decay structure;
- named event markers such as `reveal`, `ignite`, `handoff`, `impact`, `decay`,
  and `black`, expressed as seconds from the storylet start;
- portrait rendition now and optional landscape rendition later, with the same
  semantic markers even when framing differs;
- dominant palette, energy, motion direction, mood, intensity range, and
  suitability tags for deterministic search and later AI-assisted proposals;
- explicit first/last black frames, no audio, bounded transitions, and a black
  fallback;
- an optional companion Lighting recipe that references existing scenes or
  deterministic pattern parameters but never DMX addresses or live-output
  authority.

A song placement references the storylet revision, start time, selected
rendition/surface, palette/intensity variant, and marker-to-Lighting
assignments. It does not copy the media or mutate the published storylet.
Multiple placements may reuse the same rendered asset when their pixel output
is identical. Song-specific cross-surface lead-ins and tails remain Lighting
cues around the placement.

Storylets compile into the existing pre-rendered, hash-verified Stage package
and Video Show contracts. Stage does not fetch remote media, interpret an AI
proposal, or wait for a media callback before advancing Lighting.

## Visual asset families

The library should support related but distinct assets instead of forcing every
idea into one clip type:

| Family | Typical duration | Purpose | Example |
| --- | ---: | --- | --- |
| Narrative storylet | 10–30 seconds | Readable setup, action, impact, and payoff | Fuse Bomb or Santa Arrival |
| Character interaction | 8–30 seconds | A character appears to affect the physical stage | Evil Cyborg lightning attack |
| Transition bridge | 2–10 seconds | Carries motion or palette between primary clips | Energy throw or shockwave |
| Impact accent | 0.5–4 seconds | One musical hit or section boundary | Screen burst plus cube blast |
| Scene-fill phrase | 2–16 seconds, optionally loopable | Texture, particles, smoke, energy, or colour that augments a Lighting scene | Electric ribbons behind Wave Rider |
| Primary clip | Variable | Band/character footage where the screen is intentionally the focus | Selected Travelling fragments |

Scene-fill phrases are deliberately lighter-weight than storylets. They may be
recoloured, cropped, intensity-scaled, shortened, or tiled during offline
composition, and they inherit the current Lighting scene's palette and energy
role. They must not silently become continuous wallpaper: every placement has
a start, end, visual purpose, and black fallback. A fill can support a scene
without requiring a narrative payoff or a fixture response.

The asset catalog records family, loop safety, transparent/black background
behavior, dominant motion, edge entry/exit, palette compatibility, focal load,
and suggested Lighting scenes. This lets Studio later propose “low-motion cool
fill for Wave Rider” separately from “play the Fuse Bomb storylet.”

## Reference interaction concepts

### Santa Arrival

Santa or a sleigh approaches through the portrait screen while the Betopper
cubes behave like theatrical aircraft landing lights. Alternating low-level
approach pulses establish distance; the lights converge and brighten as Santa
descends; a landing marker triggers a warm bounded arrival wash; snow/embers
settle and the screen returns to black. The sequence must read as a stage gag,
not simulate real navigation lighting or require sustained high-output whites.

### Evil Cyborg Attack

Use an owned band character/video asset. The cyborg charges on screen, aims an
animated lightning bolt toward the audience viewpoint, and fires. The screen
provides the direction and bolt illusion while the Betopper cubes answer the
named `fire` and `impact` markers with palette-matched flashes, chases, or
bounded white accents. No fixture is instructed to target or “zap” a person;
the audience effect is created compositionally under the existing ceilings,
arming, flash-rate, and blackout controls.

These concepts should support low, medium, and high-energy recipes without
changing their media or semantic markers.

## Choreography vocabulary

The first implementation should prove a small, named language:

- **Echo:** a Lighting accent is answered by a related screen event after a
  reviewed short delay, followed by an optional low-level Lighting tail.
- **Throw:** a directional Lighting sweep starts on Cube A or B, crosses the
  projector frame, and resolves on the opposite cube.
- **Catch:** a screen object or energy path reaches an edge and triggers a
  bounded fixture bloom, chase, or authored white impact.
- **Ping-pong:** two to four clearly timed exchanges move between one cube, the
  screen, and the other cube; it stops before becoming visual noise.
- **Bridge:** a short abstract VFX phrase occupies selected space between two
  primary band-video clips and carries palette or motion into the next scene.
- **Unison:** Lighting and Video strike together for an important section or
  ending. Use sparingly so it remains meaningful.
- **Counterpoint:** Video sustains one slow motion while Lighting performs a
  related faster rhythm, or vice versa, without competing focal motion.

These names are authoring semantics, not new Stage runtime commands. The first
versions compile to ordinary Lighting cues and a hash-verified Video package.

## Timing and layout contract

- Use the authoritative song clock and absolute cue times. Do not derive Stage
  behavior from media-player completion callbacks or live network messages.
- Record musical anchor, direction, initiating surface, receiving surface,
  expected visual path, Video interval, Lighting scene/pattern, and transition
  for every cross-surface phrase.
- Author with the commissioned physical layout: Cube A, portrait projector,
  Cube B. The projector render retains the clockwise rear-screen transform;
  authoring coordinates remain upright portrait coordinates.
- Treat Lighting at 25 FPS and Video at 30 FPS as separate render rates. Judge
  perceptual alignment at rehearsal and record measured start/end drift rather
  than requiring frame-number equality.
- Keep most handoffs between one and eight seconds. Longer passages require an
  explicit reason and a low-motion/rest treatment.
- Preserve intentional black and visual rests. VFX cycling means curated
  phrases, not a continuously occupied projector.
- Use existing RGB master/ceiling controls and the White Output contract.
  Deliberate white impacts remain governed by white arm, prepared level, power
  mode, blackout, pulse shaping, and existing high-output acknowledgement.

## Sprint plan

### Slice 1 — Layout calibration and four proof loops

Create a simple physical stage map and four short review loops: left-to-screen,
screen-to-right, full left-screen-right throw, and a two-exchange ping-pong.
Use simple high-contrast energy shapes so timing and direction can be judged
without relying on the artistic quality of a source clip.

Deliverables:

- authored cue-table format for cross-surface events;
- projector edge/focal calibration for the portrait screen;
- four fixed-time Lighting regression sequences and Video proxies;
- one repeatable bench checklist for perceptual handoff timing.

The first complete storylet is **Fuse Bomb**. It uses an original cartoon round
bomb silhouette and long burning fuse—drawing on the general classic spy/cartoon
visual language without copying a protected character or a specific production
design. A cube accent ignites the fuse; the screen carries the fuse burn and
alternating sparks; the impact marker triggers the screen explosion and a
bounded full-stage Lighting blast; smoke/embers decay back to black. The clip
should be approximately 12–18 seconds, with the exact impact marker reusable at
different song positions.

Fuse Bomb must prove:

- readable bomb, fuse, spark, impact, and decay at projector distance;
- at least one light-to-screen ignition handoff and one screen-to-light impact;
- a companion low, medium, and high Lighting recipe governed by existing RGB
  and White Output controls;
- marker-accurate placement without embedding song-specific timing in the
  storylet itself;
- clean black before reveal and after decay so it can sit between other clips.

### Slice 2 — Travelling integrated revision

Create a new immutable Travelling Video/Lighting revision. Retain the primary
master-video phrases that passed review, then add selected VFX bridges in some
of the current black intervals. Include at least one Echo, Throw, Catch,
Ping-pong, and Counterpoint passage. Do not replace every black interval.

Review the revision with the song and both cubes before publishing it beside
the current hybrid revision. Record cue changes, visible duty cycle, package
hash, render cost, projector playback, and end-of-song drift.

### Slice 3 — Christmas mini-pack

Build four reusable visual motifs that fit the existing dark/acid stage
identity and can be recoloured for different songs:

1. **Santa Arrival:** Santa or the sleigh approaches while the cubes act as
   converging theatrical landing lights; a named landing marker releases a
   warm arrival wash before snow/embers decay to black.
2. **Neon Snow:** sparse cool-white/cyan particles fall on screen, land as
   short cube ripples, and occasionally reverse upward on a musical lift.
3. **Signal Garland:** red, green, gold, and acid-green pulses travel as a
   segmented garland from Cube A through the screen to Cube B; avoid constant
   red/green full-frame output.
4. **Electric Ornament / Starburst:** one screen object charges from alternating
   cube pulses and releases a bounded screen burst plus optional authored white
   impact on a major accent.

Optionally explore a darker **Krampus Signal** treatment for appropriate songs,
but keep it separate from the generally usable pack. Use owned/licensed source
material or procedural assets; do not introduce unverified seasonal footage or
music rights.

Each motif needs portrait and future landscape composition notes, palette and
intensity variants, a black fallback, and an example placement in at least one
real song. The pack must remain optional and removable from a show package.

### Slice 4 — Pi rehearsal and extraction for Studio

Run the integrated Travelling revision and selected Christmas motifs on the Pi
with projector, both cubes, audio, Ampero, browser, and kiosk active. Capture
operator notes and turn the vocabulary, cue fields, and preview needs into
requirements for the `STUDIO-004` Video Scene/timeline editor.

## Acceptance

- At least five named choreography patterns are recognizable in the full-stage
  rehearsal without explanation and feel intentionally timed to the song.
- Primary performer/video phrases remain legible; interstitial VFX support them
  and do not create continuous screen activity or obscure black rests.
- Directional throws read correctly across Cube A, portrait projector, and
  Cube B from the audience viewpoint, including rear-screen mirroring.
- Start, Stop, Blackout, no-autostart, song change, Video-disabled mode, player
  failure, and projector disconnect retain the accepted fail-black behavior.
- Lighting sustains 25 FPS with zero deadline misses while Video plays; CPU,
  RSS, temperature, player exit, and final Lighting/Video drift are recorded.
- Audio-reactive brightness/strobe behavior remains bounded by the current
  controls; no VFX cue can arm whites, enable live output, or raise a ceiling.
- The Travelling revision and Christmas pack publish as new immutable revisions
  with rollback to the currently accepted hybrid package.
- Fuse Bomb can be placed at two different absolute song times without
  re-rendering its media, and both placements trigger their Lighting recipes
  from the same named `impact` marker.
- The rehearsal produces a concrete Studio field list for cross-surface path,
  direction, timing anchor, initiating/receiving surface, palette, intensity,
  transition, and fallback—not a Stage dependency on Studio or AI.

## Explicit non-goals

- Live generative Video or real-time shader composition on the Pi.
- Beat detection directly controlling projector frames during a show.
- Filling all intentional-black intervals.
- Allowing projection failure or render load to influence Lighting timing.
- Replacing the existing deterministic package, sidecar, or rollback model.
