# Phreqed Studio and Stage publishing roadmap

Last updated: 2026-11-13

## Product boundary

Phreqed will separate show design from show execution before the authoring
surface grows into advanced lighting, video, and projection workflows.

- **Phreqed Studio** is a desktop/browser-first design application for songs,
  setlists, looks, scenes, lighting timelines, media, projection, analysis, and
  reviewed AI proposals.
- **Phreqed Stage** is the Raspberry Pi control appliance for choosing and
  running a published show, making bounded venue adjustments, monitoring
  health, and recovering safely.

The current Setlist and Build workspaces remain available until Studio reaches
feature parity and the package round trip is proven. Removing authoring from
Stage before that acceptance would strand existing workflows.

```text
authoritative Studio library
        |
        | validate and publish an immutable show package
        v
Stage import area -> explicit activation -> active runtime snapshot
        |                                      |
        | local adjustment journal             | lighting / projection cues
        v                                      v
reviewable change set ------------------> deterministic show processes
        |
        | import, compare, accept or reject
        v
new Studio library revision
```

The graph sidecar may index Studio data, evidence, and agent memory. It is not
the publishing or synchronization protocol and never becomes a Stage runtime
dependency.

## Authority and synchronization rules

1. Studio owns editable library history. Stable object IDs and monotonic
   revisions identify shows, songs, setlists, looks, scenes, cues, fixture
   layouts, projection designs, and media manifests.
2. A published show package is immutable. Stage imports into a staging area,
   validates the complete package, and activates it only through an explicit
   stopped-output operation. The previously active package remains available
   for rollback.
3. Stage never edits the active package in place. Local changes are recorded as
   a separate adjustment journal against the package and base object revisions.
4. A return sync produces a reviewable change set. Studio performs a three-way
   comparison against the recorded base, exposes conflicts at object/field
   level, and requires an explicit accept, reject, or manual resolution. There
   is no silent last-writer-wins merge.
5. LAN transfer and removable-media transfer use the same package and change-set
   formats. Neither path may require Internet access.
6. Media bytes live in a content-addressed asset store outside JSON and outside
   the graph. Packages contain bounded relative asset IDs, hashes, sizes, media
   types, and compatibility metadata; no arbitrary shell command or remote URL
   is executable.
7. Import, export, graph availability, video decode, and projection failure
   cannot delay DMX, leases, blackout, audio, MIDI, or clean shutdown.

## User stories

### STUDIO-001 — Shared domain identity and revision model

- As a show designer, I can edit an object repeatedly while its stable ID
  remains unchanged, so cues and analysis do not lose their references.
- As a Stage operator, I can see the exact show and revision loaded on the unit.
- As a maintainer, I can migrate the current atomic JSON libraries without
  changing their live behavior or losing existing Pi data.

Acceptance:

- Define stable IDs, object revisions, library revision, schema version,
  origin-library ID, creation time, author note, and supersession metadata.
- Preserve compatibility with existing `library.json`, `songs.json`, and
  `tuning-profiles.json`; migration is explicit, backed up, and idempotent.
- Validate duplicate IDs, missing references, revision regressions, unknown
  schema versions, fixture bounds, and reserved-channel constraints.
- Keep the core model independent of HTTP, graph storage, Art-Net, and media
  decoding.

### PUBLISH-001 — Immutable show package lifecycle

- As a designer, I can validate a candidate package and see every error before
  sending it to a Stage unit.
- As an operator, I can import a package without changing the running show,
  activate it deliberately while output is stopped, and roll back.
- As a technician, I can transfer the same package over the trusted LAN or by
  removable media and verify its identity and integrity.

Acceptance:

- Specify a deterministic manifest containing show data, fixture requirements,
  cue targets, asset hashes, compatibility bounds, and package checksum.
- Import writes to a separate staging directory and atomically promotes only a
  fully validated package. Interrupted imports leave the active show unchanged.
- Activation is rejected while live output or any timeline is active and never
  starts output or playback.
- Retain at least one known-good rollback package and record import, activation,
  rejection, and rollback events without storing secrets.
- Reject path traversal, unbounded archives, duplicate manifest entries,
  unexpected executable content, missing assets, and incompatible fixtures.

### SYNC-002 — Stage-local adjustment journal and reviewed return sync

- As a performer, I can make a bounded venue correction on Stage without
  rewriting the published show.
- As a designer, I can bring those corrections back into Studio and review the
  differences before creating a new revision.
- As an offline operator, I can perform the same round trip with a file when no
  LAN is available.

Acceptance:

- Define allowed adjustment types initially: setlist order/omission, cue timing,
  scene/master scaling within ceilings, tuning profile selection/copy, fixture
  substitution from an approved map, and operator notes.
- Every adjustment records unit ID, package ID, base revision, object ID,
  previous value, proposed value, time, and operator note where applicable.
- Editing remains atomic; corrupt journals are quarantined rather than applied.
- Studio shows clean changes separately from conflicts and never silently
  overwrites a newer library revision.
- Accepted changes create a new Studio revision; rejected changes remain in the
  audit record and never alter the published package.

### STUDIO-002 — Browser Studio foundation and authoring migration

- As a designer, I have a spacious desktop application for managing shows
  without exposing live-output controls.
- As an existing operator, I can migrate songs, setlists, looks, scenes, and
  tuning profiles from the current libraries without re-entering them.
- As a maintainer, I can share validation and domain code with Stage without
  duplicating controller logic.

Acceptance:

- Provide library/show navigation, search, master-detail editors, autosaved
  drafts, explicit publish state, validation results, and revision history.
- Reuse the shared domain and validation modules; Studio cannot construct an
  `ArtNetSender` or acquire a Stage control lease.
- Import current JSON stores and export a byte-stable normalized representation
  suitable for package generation and backup.
- Retain current Stage authoring until representative Studio workflows and the
  round trip pass; publish deprecation guidance before removing anything.

### STUDIO-003 — Lighting timeline and preview designer

- As a lighting designer, I can arrange cues on a song timeline without long
  forms or nested scrolling.
- As a designer, I can scrub and preview lighting deterministically without
  sending fixture output.
- As a future projection designer, I can align lighting and media lanes to the
  same song clock while preserving independent runtime failure boundaries.

Acceptance:

- Provide zoomable time ruler, cue/scene lanes, selection inspector, snapping,
  keyboard and touch editing, undo/redo, copy/paste, and validation markers.
- Preview uses injected time and the simulator only; scrubbing cannot enable
  live output, white channels, or projection hardware.
- Cues reference immutable published look/scene revisions or explicit drafts;
  missing and superseded references are visible before publish.
- Timeline data stays transport-independent and can address lighting plus an
  optional projection cue without putting video work on the DMX thread.

### MEDIA-001 — Content-addressed media asset library

- As a designer, I can import video, image, and later audio assets once and
  reuse them across shows without accidental duplication.
- As a Stage operator, I can know whether every required asset is present before
  activating a show.
- As a technician, I can move a package between machines and verify each asset.

Acceptance:

- Hash imported bytes and store them outside the source repository under a
  configured asset root; keep original name only as display metadata.
- Record size, media type, duration/dimensions when available, provenance, and
  compatibility metadata. Do not execute embedded commands or fetch remote URLs.
- Package validation reports missing, mismatched, unsupported, and oversized
  assets before activation.
- Garbage collection is explicit and reference-aware; no asset used by a
  retained package or revision can be removed.

### STUDIO-004 — Video and projection design surface

- As a show designer, I can place clips, stills, black frames, and projection
  presets on the unified timeline.
- As a designer, I can preview crop, fit, loop, opacity, fades, and overlays
  without requiring the Stage projector.
- As an operator, missing or failed video fails black without interrupting the
  lighting cue.

Acceptance:

- Build on `MEDIA-001`, `PROJ-001`, `PROJ-002`, and `SHOW-002`; do not create a
  second projection runtime or cue model.
- Export projection presets and media references through the show manifest.
- Preview and Stage use an explicitly versioned interpretation of crop/fit,
  timing, looping, transitions, intensity, and black fallback.
- A safe non-flashing test clip completes an end-to-end Studio publish and Pi
  playback while the DMX 25 FPS soak remains within its existing limits.

### AI-DATA-002 — Studio knowledge graph and agent-memory integration

- As a designer, I can ask how a cue proposal relates to song sections,
  evidence, past shows, and my approvals.
- As a reviewer, I can distinguish measured facts, generated proposals,
  superseded knowledge, and approved published data.
- As an operator, I can remove or rebuild the graph without affecting Studio
  library data or any Stage show.

Acceptance:

- Begin only after stable IDs and revisions from `STUDIO-001` exist and after
  the `AI-DATA-001` feasibility gates relevant to the chosen host pass.
- One controlled writer indexes library revisions, analysis evidence, cue
  proposals, reviews, assets, packages, and adjustment change sets.
- Agent access is read-only where possible. A reviewed proposal still becomes
  only a draft and requires the normal explicit publish operation.
- Export the graph to versioned JSON and rebuild it from authoritative Studio
  data plus exported evidence. Graph loss or schema migration cannot block
  package publishing from ordinary library data.
- Do not store media bytes, credentials, live leases, or mutable Stage runtime
  state in the graph.

### STAGE-001 — Runtime-focused Stage interface

- As a performer, I see only the controls and status required to run the show
  safely under stage conditions.
- As a technician, I can make approved local adjustments and see clearly that
  they are unreviewed changes against a published revision.
- As an existing user, I do not lose authoring capability until Studio and sync
  are accepted.

Acceptance:

- Target navigation becomes Perform, Shows, Adjust, Settings, and Operations
  after Studio feature parity; persistent blackout and local-only operations
  remain unchanged.
- Shows exposes installed packages, validation state, active revision,
  activation, and rollback only while output/timelines are stopped.
- Adjust exposes only the `SYNC-002` allowlist and keeps changes separate from
  immutable package files. It cannot raise safety ceilings or auto-arm whites.
- Legacy Setlist/Build authoring is hidden or removed only after migration,
  publish, rollback, local-adjustment, and return-sync acceptance is recorded.

### STUDIO-005 — End-to-end release and recovery validation

- As a show operator, I can prepare a show on Studio, transfer it, rehearse it,
  run it, return corrections, republish it, and recover the previous version.
- As a maintainer, I can prove Studio, graph, media, and projection failures do
  not weaken Stage lighting safety.

Acceptance:

- Exercise LAN and removable-media package transfer, interrupted import,
  invalid package, activation, rollback, clean sync, conflicting sync, and
  corrupt adjustment recovery.
- Run the complete automated, Chromium, Pi, 25 FPS, lease-loss, blackout,
  reserved-channel, white-output, kiosk, and shutdown suites.
- Run projection failure, missing-media, player-crash, and display-disconnect
  checks while lighting remains controllable and on time.
- Document show preparation, transfer, activation, fallback, return sync, and
  emergency procedures before Stage authoring is reduced.

## Sprint plan

### Sprint 0 — Contracts and migration proof

Cards: `STUDIO-001`.

Freeze the Stage/Studio boundary, stable IDs, revision semantics, schema
migration path, and representative legacy fixtures. Deliver design records,
schemas, validators, migration dry-run, backups, and round-trip tests before UI
or graph work relies on the new model.

### Sprint 1 — Safe package publishing

Cards: `PUBLISH-001`.

Implement deterministic package creation, validation, staging, explicit
activation, inventory, and rollback. Prove interrupted and malicious imports
cannot change the active show or start output.

### Sprint 2 — Local adjustment and return sync

Cards: `SYNC-002`.

Implement the allowlisted Stage adjustment journal, change-set export/import,
three-way comparison, conflict presentation, and explicit merge decisions.
Support LAN and removable-media round trips through the same formats.

### Sprint 3 — Studio application foundation

Cards: `STUDIO-002`.

Build the browser Studio shell and migrate songs, setlists, looks, scenes, and
tuning-profile authoring. Add draft/revision history, validation, and package
publishing without any live-output capability.

### Sprint 4 — Lighting design surface

Cards: `STUDIO-003`.

Deliver the zoomable multi-lane lighting timeline, inspector, simulator scrub,
undo/redo, reference validation, and touch/keyboard workflows. Publish and run
a lighting-only show package before adding media.

### Sprint 5 — Media and projection vertical slice

Cards: `MEDIA-001`, `STUDIO-004`, `PROJ-001`, and the necessary subset of
`SHOW-002`.

Add the content-addressed asset library, a basic projection track, deterministic
clip interpretation, manifest transfer, Stage playback/black fallback, and one
safe test clip. Measure the combined Pi workload without advanced overlays.

### Sprint 6 — Projection composition and unified cues

Cards: `PROJ-002`, `SHOW-002`, and `VIDEO-001` where video-to-fixture sampling
is still desired.

Add projection presets, bounded overlays, independent projection blanking, and
unified cue transitions while keeping lighting and projection failure domains
separate. Video-to-grid remains an optional lighting input, not the media store.

### Parallel Sprint A — Graph memory and AI-assisted design

Cards: `AI-DATA-001`, `AI-DATA-002`, `ANALYSIS-001`, and `AI-SONG-001`.

Start graph integration only after Sprint 0 produces stable IDs. Evaluate the
graph on the Studio host first, index evidence and revisions, expose read-only
recall, and keep every generated cue in the existing review/publish workflow.
This sprint never blocks a lighting-only package or Stage startup.

### Sprint 7 — Runtime-focused Stage transition

Cards: `STAGE-001`.

Add Shows and Adjust runtime workspaces, record feature-parity evidence, publish
migration guidance, and then reduce heavy Stage authoring. Preserve a rollback
release until at least one rehearsal and one show complete with Studio packages.

### Sprint 8 — Integrated acceptance and operating handbook

Cards: `STUDIO-005` and the final acceptance portions of all linked projection,
sync, and Stage cards.

Complete recovery, conflict, media, projection, hardware, safety, and offline
tests. Document the full design-to-stage-to-Studio loop before declaring the
new control plane show-critical.

## Explicit non-goals for the first release

- Real-time multi-user collaborative editing.
- Cloud accounts or Internet-required publishing.
- Editing the active Stage package in place.
- Automatic conflict resolution or last-writer-wins synchronization.
- Graph replication as package transfer or Stage state storage.
- Letting Studio, AI, media import, or projection start live lighting output.
- Moving video decode, projection composition, or graph queries onto the DMX
  render thread.
