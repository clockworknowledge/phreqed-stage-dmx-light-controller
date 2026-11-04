# Song Builder and Setlist Performance Roadmap

Status: proposed architecture and sprint plan (2026-11-04)

## Product goal

Add a second, deterministic show-control workflow without weakening the current
manual scene controller:

- **Manual performance** keeps the existing previous scene, next scene, tap
  tempo, and blackout workflow.
- **Setlist performance** lets the operator select a song, explicitly start or
  stop its prepared cue timeline, and move to the previous or next song.
- **AI Song Builder** analyzes either an uploaded MP3 or a deliberate rehearsal
  listening session before a show, proposes a baseline scene timeline, and lets
  the operator edit, simulate, approve, and publish it.
- **Setlist Builder** orders approved songs and presents a large current/next
  song view for the performer.

The AI and audio-analysis paths are authoring tools. They must never be required
by the Raspberry Pi during a performance.

## Supported analysis inputs

The initial product will not accept Apple Music, Spotify, or other streaming
links. It supports two band-controlled inputs:

1. A user-owned or licensed **MP3 upload**.
2. A deliberate **rehearsal listening session** captured from the configured
   microphone while the band performs the complete song.

Streaming links remain explicitly out of scope because they must not be treated
as permission or as an audio-download source.

- Spotify's current [Developer Policy](https://developer.spotify.com/policy)
  prohibits downloading Spotify content, analyzing Spotify content, and using
  Spotify content to train or otherwise ingest into AI/ML models. Spotify also
  restricts synchronizing sound recordings with visual media. Its Web API can
  supply permitted catalog metadata, subject to attribution and platform rules.
- Apple's [Developer Program License Agreement](https://developer.apple.com/support/terms/apple-developer-program-license-agreement/)
  restricts downloading, modifying, and synchronizing MusicKit content. The
  [Apple Music API](https://developer.apple.com/documentation/AppleMusicAPI)
  is appropriate for catalog/library metadata and authorized playback, not for
  obtaining arbitrary raw audio for analysis.

Therefore the supported design is:

1. Accept only MP3 for uploaded-audio analysis, with an explicit rights
   attestation.
2. Offer rehearsal listening and fully manual song/timeline creation when no
   MP3 is available.
3. Keep uploaded MP3 files outside Git and out of diagnostic bundles. Give the
   user an explicit retention/delete policy.
4. Store time-indexed derived features from rehearsal listening; do not retain
   raw rehearsal audio by default.
5. Send derived features and a compact section summary to an LLM, not a
   streaming-service recording. Provider retention and rights still require
   review before enabling a hosted model.

This is a product/engineering constraint, not legal advice. Platform terms must
be reviewed again before shipping an integration.

## Analysis and performance pipeline

```text
MP3 upload --------------------+
                               +-> local feature extraction
Rehearsal microphone session --+      |
                                      v
                            versioned SongAnalysis
                                      |
                         structured AI cue proposal
                                      |
                         operator edit and simulation
                                      |
                          published baseline cue sheet
                                      |
                   explicit Start in Setlist performance mode
                                      |
             baseline scene changes + live microphone modulation
```

Local signal processing extracts timing, energy, onset, frequency-band, and
candidate section information. The LLM receives this bounded structure plus the
effect catalog and proposes scene choices; it is not responsible for live audio
capture or DMX output. Human review remains mandatory before publication.

During a show, the cue sheet controls baseline scene selection and transitions.
The existing low-latency microphone context independently adjusts bounded
brightness, movement, contrast, and permitted white accents so the visuals
still respond to the actual performance. The live modulation layer cannot
rewrite the cue sheet. Later SYNC-001 work may gently correct cue timing when
confidence is high.

## Proposed data model

The persisted library should be versioned, validated, and atomically replaced,
following the existing preset-library approach.

```text
Song
  id, title, artist, duration_s, notes
  analysis source type (mp3_upload, rehearsal_capture, or manual)
  local media reference/fingerprint (never the media bytes)
  active analysis version and active cue-sheet version

SongAnalysis
  analyzer/version, source type, duration, confidence
  tempo/beat/bar map
  section boundaries (intro, verse, chorus, bridge, solo, outro, custom)
  bounded energy, onset, and frequency-band curves
  capture health and timing discontinuities

SongCueSheet
  song id, version, created-by, published flag
  ordered cues in elapsed seconds and/or musical bars

SongCue
  position, preset id, transition duration
  optional bounded effect parameters, RGB level, and white-output policy

Setlist
  id, name, ordered song ids, notes, version
```

Cue sheets reference stable preset IDs. Missing or incompatible presets must be
reported before a setlist can be armed; they must never silently select a
different look.

## Runtime behavior

Setlist performance uses a monotonic injected clock and a prevalidated,
published cue sheet. There are no network or LLM calls in the playback loop.

Recommended end-of-song behavior is **stop and arm the next song without
starting it**. Bands change pacing, pause between songs, and sometimes skip
items, so automatic start is unsafe and surprising. A later setting may choose
whether the selection advances or remains on the completed song, but playback
must never auto-start by default.

The first timing implementation starts when the performer presses Start. An MP3
or rehearsal capture supplies baseline structure and cue timing, not an exact
promise about the live rendition. During performance the existing microphone
analysis continues to modulate brightness, motion, contrast, and bounded white
accents inside the active scene. It does not automatically replace the authored
scene sequence. Mic-based beat/onset phase correction is a later experimental
sprint with bounded corrections and an immediate fallback to the baseline
timeline.

Blackout remains global, immediate, and available in every mode. Changing mode,
selecting a song, or loading a setlist cannot enable Art-Net. Setlist playback
can change scenes only after the existing explicit browser live activation.

## Browser experience

### Song Library

- Create songs manually, upload an authorized MP3 to an operator-configured
  media directory, or start a rehearsal listening session.
- Show media/analysis/cue-sheet state and version.
- Analyze, reanalyze, delete local media/features, or open the timeline editor.

### Rehearsal Listening

- Require an explicit armed state and operator Start/Stop; never listen merely
  because the browser page is open.
- Show input device, level, clipping, elapsed time, capture health, and a clear
  recording/listening indicator.
- Capture normalized feature frames and timing markers for the entire song.
- Detect gaps, device loss, and clipping and require operator review when the
  capture is incomplete.
- Retain derived features by default, not raw rehearsal audio.

### AI Song Builder

- Display sections, beat grid, energy curve, confidence, and warnings.
- Generate a structured cue proposal from derived features and the local effect
  catalog.
- Edit cue time, preset, transition, brightness, and permitted white accents.
- Simulate the proposal without constructing an Art-Net sender.
- Publish an immutable cue-sheet version only after operator review.

### Setlist Builder

- Search the song library and order songs by drag/drop or accessible buttons.
- Show total duration and validation errors.
- Save versioned setlists without embedding audio files.

### Performance View

- Deliberate Manual / Setlist mode selector.
- Large `03 / 12 - Song Name` current-song display and next-song preview.
- Clear `selected`, `armed`, `running`, `stopped`, and `complete` states.
- Previous song, next song, start/stop, elapsed/remaining position, and blackout.
- Persistent live/simulation, audio, pedal, QLC+, and output health indicators.

## Foot-control plan

The existing four-switch profile remains unchanged in Manual mode. The proposed
Setlist profile is:

| Switch | Manual mode | Setlist mode |
| --- | --- | --- |
| FS1 | Previous scene | Previous song |
| FS2 | Next scene | Next song |
| FS3 | Tap tempo | Start/stop selected song |
| FS4 | Explicit blackout on/off | Explicit blackout on/off |

Avoid simultaneous-switch chords in the show profile. The Ampero can change
banks when adjacent switches are pressed together; that accidental bank change
caused the previously observed loss of mapped actions. Configure every
reachable performance bank with the same safe mapping, or disable/avoid bank
navigation if the vendor application permits it. Returning to bank 0 is the
current recovery procedure.

The application should own the setlist index. Mapping one hardware bank per song
would recreate the accidental-bank problem and couple the show to pedal state.
The browser is the authoritative song-number display. Arbitrary host-controlled
text or song numbers on the Ampero display are not yet proven by the documented
MIDI interface; treat this as hardware research, with the browser as the
required fallback.

## Sprint sequence

### Sprint 0 - Consolidation and pedal hardening

- Fast-forward the validated feature work to `main` and remove generated local
  browser artifacts from version control.
- Document the accidental bank-switch root cause and recovery.
- Create and soak a performance-safe Ampero profile across reachable banks.
- Keep read-only configuration backup/recovery research separate from live use.

### Sprint 1 - Song domain and deterministic timeline (complete)

- Implement `Song`, `SongCueSheet`, `SongCue`, and `Setlist` validation and
  persistence with injected clocks.
- Implement start, stop, restart, previous/next selection, cue transitions,
  completion, and arm-next-without-autostart behavior.
- Add hardware-free tests for clock boundaries, missing presets, blackout,
  mode changes, restarts, and fixture independence.

Implemented by `songs.py` and `song_timeline.py`. The metadata store is atomic
and versioned, while the runner is clock/callback injected and has no rendering,
media, network, or transport dependency. The focused and complete Windows test
suites pass; browser integration begins in Sprint 2.

### Sprint 2 - Library, timeline, and setlist authoring UI

- Add Song Library, manual timeline editor, Setlist Builder, and simulation.
- Add version/publish workflow and large validation messages.
- Do not add AI or media decoding yet.

### Sprint 3 - Setlist performance mode

- Add transport-independent performance commands and browser Performance View.
- Add mode-specific Ampero mappings without changing global blackout semantics.
- Validate reboot, controller disconnect, browser loss, song skipping, and
  setlist completion on the Pi before live fixture use.

### Sprint 4A - Authorized MP3 analysis

- Add MP3-only upload/storage policy, rights attestation, file fingerprinting,
  validation, and safe deletion.
- Evaluate decoding and analysis in an optional offline worker rather than the
  25 FPS controller process.
- Produce deterministic tempo, beat/bar, energy/onset, and section artifacts.
- Benchmark on Windows first, then decide whether authoring belongs on the Pi or
  a more capable computer.

### Sprint 4B - Rehearsal listening analysis

- Add an explicitly armed microphone capture session separate from show-time
  audio modulation.
- Record a time-indexed feature timeline without retaining raw audio by default.
- Detect clipping, input loss, long silence, discontinuities, and incomplete
  captures before analysis can be published.
- Feed the same section detection and AI proposal pipeline used for MP3 input.
- Confirm that capture/analysis cannot enable Art-Net or interfere with an
  already-running controller.

### Sprint 5 - AI cue proposal and review

- Define a versioned JSON schema for LLM output.
- Send only bounded derived features, effect metadata, and operator preferences.
- Validate every response; reject unknown effects and unsafe parameters.
- Add proposal comparison, editing, simulation, approval, and audit metadata.
- Cache the published result so performance is fully offline and deterministic.

### Sprint 6 - Live-band adaptive synchronization

- Experiment with room-mic onset/beat tracking and bounded phase correction.
- Make correction confidence visible and fall back smoothly when confidence is
  low.
- Never let synchronization failure enable output, bypass limits, or stop manual
  control.

### Sprint 7 - Optional pedal feedback

- Determine whether the Ampero accepts documented, reversible MIDI feedback or
  display control.
- If unsupported, keep song number/name on the phone browser or add a dedicated
  small stage display. Do not reverse-engineer writes during show operation.

## Definition of done for the feature family

- Manual performance behavior remains backward compatible.
- Simulation is the default and proves zero network construction.
- AI and media services are absent from the live timing path.
- MP3 and rehearsal inputs produce the same validated `SongAnalysis` contract.
- Every setlist is usable offline after publishing.
- Start/stop remains explicit; completion never auto-starts another song.
- Blackout wins over every cue and survives missing media, pedal, browser, or
  analysis services.
- Uploaded MP3 files, raw capture buffers, and credentials are excluded from Git
  and logs; raw rehearsal audio is not retained by default.
- The complete Pi soak sustains 25 FPS with no reserved-channel activity and a
  verified normal-shutdown blackout.
