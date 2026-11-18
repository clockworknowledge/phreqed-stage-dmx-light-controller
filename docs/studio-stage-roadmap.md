# Phreqed Studio and Stage publishing roadmap

Last updated: 2026-11-16

## Product boundary

Phreqed will separate show design from show execution before the authoring
surface grows into advanced lighting, video, and projection workflows.

- **Phreqed Studio** is a hosted, browser-first SaaS design application for
  songs, setlists, looks, scenes, lighting timelines, media, projection,
  analysis, and reviewed AI proposals. It is multi-tenant and subscription
  aware, with a curated shared catalog plus private customer libraries.
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

## Hosted product model

The initial reference customer is a higher-tier band account with access to
private media upload, large storage, clip preparation, complete lighting and
video authoring, revision history, AI-assisted proposals, and multiple paired
Stage units. The architecture must still express lower tiers through
entitlements rather than separate applications or forked code.

Working tiers, names, prices, and exact quotas remain product configuration:

| Tier | Initial capability envelope |
| --- | --- |
| Free | Curated public looks, scenes, VFX clips, and deterministic song templates; limited projects, storage, exports, and device registrations. |
| Artist (`$`) | Private uploads, non-destructive clip extraction, larger storage, complete manual show authoring, more published packages, and one or more paired Stage units. |
| Pro (`$$$`) | Highest storage and processing quotas, AI analysis/authoring allowance, deeper revision history, multiple workspaces/devices, team roles, and priority export/processing. |

Entitlements are named capabilities and numeric quotas such as
`private_media_upload`, `ai_proposal_minutes`, `storage_bytes`,
`published_packages`, `stage_devices`, and `revision_retention_days`. Studio
checks them at upload, job creation, authoring, and publish boundaries. A fully
published and downloaded package carries an entitlement snapshot and remains
playable on Stage without an Internet or billing check.

Base catalog assets require explicit ownership/licensing metadata and a tier
entitlement. Private customer assets remain isolated to their tenant and are
never silently promoted into the shared catalog. Account cancellation or quota
reduction cannot invalidate a package already activated for a show; retention,
export, and deletion policies apply to the hosted library separately.

## Hosted architecture

```text
browser Studio
      |
      v
authenticated tenant API
  |          |             |                 |
  v          v             v                 v
metadata   object       job queue         derived graph
revisions  storage      + workers         / AI memory
  |          |        probe/transcode/AI        |
  +----------+-------------+--------------------+
                         |
                         v
                 package registry
                         |
                 signed device delivery
                         |
                         v
              Stage staging/cache/rollback
                         |
            lighting runner | video process
```

- The transactional metadata/revision store is authoritative for tenant,
  library, show, entitlement, package, and audit records.
- Media bytes and derived renditions live in private object storage. The graph
  stores relationships and evidence only, never media or credentials.
- Probe, thumbnail, storyboard, transcode, shot-boundary, and AI work runs as
  idempotent asynchronous jobs with visible status, cancellation, retry, and
  quota accounting.
- Stage delivery uses short-lived pairing and package credentials. Stage never
  receives a general Studio session, billing secret, or object-store listing
  credential.
- Every package required for a performance is downloaded, hash-verified, and
  preflighted before activation. Playback never streams show-critical video
  from the SaaS service.

## Lighting and video show model

A song revision owns one shared duration and deterministic transport plus two
independent authored tracks:

```text
Song revision / shared clock
  |
  +-- Lighting track: timed references to lighting scenes/looks
  |
  +-- Video track: timed references to reusable Video Scenes
```

- A **Video Scene** is a reusable revisioned visual definition. It can contain a
  clip range, still, colour/black layer, crop/fit, loop behavior, opacity,
  intensity, fades, and later bounded overlays. It references immutable asset
  and rendition hashes rather than copying media or storing a remote URL.
- A **Video cue** places a Video Scene on a song range. A song may intentionally
  contain black gaps. Overlaps require an explicit composition rule; accidental
  overlap is a validation error.
- Lighting and Video cues may have different boundaries. Both runners receive
  the same explicit start, pause, resume, seek, stop, and song-selection events
  from the transport-independent coordinator.
- Selecting or arming a song never starts either track. Moving to the next song
  does not auto-start it. A decoder may pre-roll into a non-presenting surface,
  but HDMI remains black until the explicit song start.
- Lighting remains authoritative for its own 25 FPS deadline. Video reports
  readiness, position, dropped frames, and failure through a separate health
  channel. Drift correction may seek/restart video at bounded checkpoints; it
  never delays or rewinds the lighting runner.
- Video failure, missing media, unsupported decode, or projector disconnect
  immediately requests black on the projection path and leaves lighting,
  audio, MIDI, leases, blackout, and song transport controllable.
- Published packages contain only the exact Stage renditions and clip ranges
  referenced by the chosen show/setlist plus manifest metadata required for
  preflight, reducing transfer and local storage use.

## Authority and synchronization rules

1. Studio owns editable library history. Stable object IDs and monotonic
   revisions identify shows, songs, setlists, looks, scenes, cues, fixture
   layouts, Lighting/Video tracks, Video Scenes, projection designs, catalog
   items, media assets/renditions/clips, and manifests.
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
5. Hosted delivery, trusted-LAN transfer, and removable-media transfer use the
   same package and change-set formats. A cloud outage may delay new delivery
   but cannot affect an already downloaded or active show.
6. Media bytes live in a content-addressed asset store outside JSON and outside
   the graph. Packages contain bounded relative asset IDs, hashes, sizes, media
   types, and compatibility metadata; no arbitrary shell command or remote URL
   is executable.
7. Import, export, graph availability, video decode, and projection failure
   cannot delay DMX, leases, blackout, audio, MIDI, or clean shutdown.
8. Every hosted read and write is scoped by tenant and workspace. Shared
   catalog access is explicit and read-only; private assets, drafts, prompts,
   analysis, packages, and audit events cannot cross tenant boundaries.
9. AI output is always a proposal with model, prompt-policy, evidence, cost,
   and source revision metadata. It cannot publish, pair a Stage unit, activate
   a package, or start lighting/video output.

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

### SAAS-001 — Tenant, workspace, identity, and role foundation

- As a subscriber, I can sign in and see only my bands, workspaces, shows,
  assets, devices, and team members.
- As an account owner, I can invite designers and operators with least-privilege
  roles and revoke their access without changing published Stage packages.
- As a maintainer, I can prove every hosted object and background job is tenant
  scoped.

Acceptance:

- Define tenant, workspace, membership, role, user, session, service identity,
  Stage device, audit event, and deletion/export request records.
- Initial roles are owner, administrator, designer, operator, and viewer with an
  explicit permission matrix; there is no client-only authorization.
- Tenant/workspace scope is required in database constraints, API access,
  object-store keys, job payloads, cache keys, logs, and tests.
- Provide account export, soft-delete/retention states, backup/restore, audit
  history, session revocation, and recovery paths before accepting production
  customer media.

### SAAS-002 — Subscription entitlements, quotas, and usage ledger

- As a free user, I can build with entitled base assets without seeing controls
  that will fail only at the end of the workflow.
- As a higher-tier customer, I can see storage, processing, AI, package, and
  Stage-device allowances and understand which action consumed them.
- As product operations, tier names, prices, and quotas can change without
  forking Studio or Stage code.

Acceptance:

- Define named boolean capabilities, numeric quotas, reservation/commit/release
  semantics for asynchronous jobs, and an append-only usage ledger.
- Enforce entitlements server-side at upload, processing, AI, publish, device
  pairing, and retention boundaries; the browser mirrors state but is not the
  authority.
- Quota retries are idempotent and cannot double-charge usage. Failed or
  cancelled work releases reservations according to a documented policy.
- Published offline packages are never disabled by subscription lookup,
  downgrade, SaaS outage, or billing-provider failure.

### CATALOG-001 — Curated base asset and scene catalog

- As a new customer, I can start from useful lighting scenes, video scenes,
  VFX clips, and deterministic song templates without uploading media.
- As a catalog curator, I can publish, supersede, retire, and license a base
  asset without mutating a customer's existing show revision.
- As a higher-tier customer, I can copy an entitled catalog item into a private
  editable draft while preserving attribution and provenance.

Acceptance:

- Catalog items have stable IDs, immutable revisions, type, tags, preview,
  provenance, license/usage terms, entitlement, compatibility, and retirement
  metadata.
- Shows pin exact catalog revisions. A later catalog edit or entitlement change
  cannot silently change a draft or published package.
- Free and paid catalog access is testable without duplicating the underlying
  asset bytes; private customer assets never enter the catalog without a
  separate explicit curation workflow.
- Initial catalog taxonomy includes mood, energy, palette, motion, genre,
  tempo suitability, loopability, aspect ratio, and projection suitability.

### SAAS-003 — Hosted operations, audit, portability, and recovery

- As a subscriber, I can export my authoritative library and private asset
  manifest in a documented format.
- As an operator, I can recover from a failed deployment, worker outage, or
  storage incident without corrupting revisions or active Stage packages.
- As support, I can diagnose a job or publish failure without reading private
  media or prompts by default.

Acceptance:

- Define environment separation, secrets handling, migrations, backups,
  restore drills, retention, observability, rate limiting, abuse controls, and
  incident/audit access.
- Background jobs are idempotent, resumable where appropriate, and have dead-
  letter/replay procedures. Metadata commits never reference a derived asset
  until that object is durably stored and verified.
- Customer export includes versioned metadata, provenance, reviews, packages,
  and asset hashes; account deletion is staged, auditable, and blocked while a
  legal/operational hold applies.
- Disaster recovery targets and regional/data-residency requirements are
  selected before production launch rather than implied by a vendor default.

### PUBLISH-001 — Immutable show package lifecycle

- As a designer, I can validate a candidate package and see every error before
  sending it to a Stage unit.
- As an operator, I can import a package without changing the running show,
  activate it deliberately while output is stopped, and roll back.
- As a technician, I can transfer the same package over the trusted LAN or by
  removable media, or deliver it through the paired hosted service, and verify
  its identity and integrity.

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

### STAGE-LINK-001 — Secure Stage pairing and hosted package delivery

- As a higher-tier subscriber, I can pair a Stage unit to my workspace using a
  short, human-verifiable enrollment flow.
- As an operator, I can choose a published package for delivery, watch download
  and preflight progress, then activate it locally only while output is stopped.
- As a touring band, I can run the complete cached show after Internet loss and
  still use removable media as a recovery path.

Acceptance:

- Pairing uses short-lived enrollment authorization and creates a revocable
  per-device identity; no reusable user password, browser session, billing
  credential, or tenant-wide object-store credential is stored on Stage.
- Package manifests are signed, downloads are resumable and hash-verified, and
  every referenced rendition is present before a package becomes activatable.
- Hosted delivery writes only to the existing staging boundary. It cannot
  activate a show, start a timeline, enable Art-Net, arm whites, or open the
  projector remotely.
- Revocation blocks future delivery but does not interrupt an active or fully
  cached package. Clock skew, replay, partial download, expired credentials,
  cloud outage, and device replacement have explicit recovery tests.
- The same package validates identically over cloud, trusted LAN, and removable
  media; rollback remains local and independent of Studio availability.

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

- As a designer, I have a spacious tenant-aware browser workspace for managing
  shows without exposing live-output controls.
- As an existing operator, I can migrate songs, setlists, looks, scenes, and
  tuning profiles from the current libraries without re-entering them.
- As a maintainer, I can share validation and domain code with Stage without
  duplicating controller logic.

Acceptance:

- Provide workspace/library/show navigation, search, master-detail editors,
  autosaved drafts, explicit publish state, validation results, revision
  history, entitlement state, and usage/quota visibility.
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
- As a projection designer, I can align lighting and Video lanes to the same
  song clock while preserving independent runtime failure boundaries.

Acceptance:

- Provide zoomable time ruler, cue/scene lanes, selection inspector, snapping,
  keyboard and touch editing, undo/redo, copy/paste, and validation markers.
- Preview uses injected time and the simulator only; scrubbing cannot enable
  live output, white channels, or projection hardware.
- Cues reference immutable published look/scene revisions or explicit drafts;
  missing and superseded references are visible before publish.
- Timeline data stays transport-independent and provides the shared ruler and
  clock later used by the separate Video track without putting video work on
  the DMX thread.

### MEDIA-001 — Content-addressed media asset library

- As a designer, I can import video, image, and later audio assets once and
  reuse them across shows without accidental duplication.
- As a Stage operator, I can know whether every required asset is present before
  activating a show.
- As a technician, I can move a package between machines and verify each asset.

Acceptance:

- Hash imported bytes and store them outside the source repository in a tenant-
  scoped object store; local development may use a configured filesystem root.
  Keep original name only as display metadata.
- Record size, media type, duration/dimensions when available, provenance, and
  compatibility metadata. Do not execute embedded commands or fetch remote URLs.
- Package validation reports missing, mismatched, unsupported, and oversized
  assets before activation.
- Garbage collection is explicit and reference-aware; no asset used by a
  retained package or revision can be removed.

### MEDIA-002 — Hosted ingest, rendition, and clip-preparation pipeline

- As a higher-tier band, I can bulk upload our VFX files and videos, see reliable
  progress, and resume interrupted uploads.
- As a show designer, I can mark short reusable clip ranges without duplicating
  the original media and receive Stage-compatible renditions and previews.
- As a maintainer, malformed or hostile uploads cannot become executable or
  consume unbounded processing/storage.

Acceptance:

- Support resumable upload, declared and detected type validation, bounded
  media probing, checksum verification, duplicate detection within the tenant,
  quarantine, cancellation, retry, and explicit failure messages.
- Extract duration, dimensions, frame rate, codec, audio presence, aspect ratio,
  thumbnails, and storyboard. Original bytes remain immutable; a clip is a
  versioned in/out reference plus transformation metadata.
- Produce preview proxies and one conservative Stage rendition profile before
  supporting multiple quality targets. Renditions record tool/version/settings
  and content hash and are reproducible from the original.
- Manual tags cover mood, energy, palette, motion, tempo suitability,
  loopability, and rights/provenance. Automated shot/loop/tag proposals remain
  drafts and never overwrite human metadata.
- Enforce tenant storage/processing quotas before work starts, keep uploads and
  jobs idempotent, and prove one tenant cannot address another tenant's object.
- Bulk import the band's reference VFX suite, cut representative short clips,
  and successfully package/play them on the target Pi before accepting the
  pipeline.

### MEDIA-003 — Incremental cached composition renderer

- As a designer, I receive a low-resolution proxy quickly and can review a
  changed phrase without waiting for the entire song to render again.
- As an operator, I see staging, chunk, assembly, hash, and preflight progress;
  I can cancel, retry, or resume without losing valid completed chunks.
- As a platform operator, I can bound CPU, memory, temporary storage, wall time,
  and concurrent jobs per tenant while keeping render workers outside the web
  and Stage control processes.

The initial 2026-11-17 Travelling proof established the performance baseline:
180 seconds, 23 sparse layers, 720×1280 at 30 FPS, a 285 MB cloud-mounted master,
eight local VFX sources, and four FFmpeg 4.2.3 filter workers. The monolithic
graph remained stable but exceeded one hour, approached 4 GB RSS, and provided
no useful incremental artifact or frame progress before atomic completion. The
completed reference measurement was 70 minutes 48 seconds and 4.78 GiB observed
peak RSS for a 55.4 MB preflight-valid package, confirming that correctness is
adequate but the monolithic build architecture is not production-acceptable.

Acceptance:

- Stage and hash-verify remote/cloud-mounted originals into a local
  content-addressed source cache before decode.
- Compile the composition into disjoint active phrases and true-black gaps;
  render/cache phrases independently and assemble the exact song duration
  without cumulative drift or re-encoding unchanged chunks.
- Cache keys include every source hash, source range, transform, blend/fade,
  projection, renderer-version, and encoding input that affects pixels.
- Persist explicit queued/staging/probing/rendering/assembling/hashing/
  preflighting/complete/failed/cancelled states with progress and worker
  resource telemetry.
- On the reference worker, begin proxy review within 60 seconds, render a
  changed phrase within 30 seconds, and target the complete Travelling Stage
  package within 10 minutes and 4 GiB RSS. Any platform exception must be
  measured and reviewed rather than hidden behind an indefinite spinner.
- Cancellation and worker loss retain valid chunks but never expose a partial
  package. Corrupt cache, missing source, quota, and preflight failures are
  explicit and recoverable.
- Build on `MEDIA-001` and `MEDIA-002`; complete this before accepting
  `STUDIO-004` as a production authoring surface.

### STUDIO-004 — Video and projection design surface

- As a show designer, I can create reusable Video Scenes from clips, stills,
  black frames, colour fields, and projection presets.
- As a song designer, I can edit a Video track in parallel with the Lighting
  track while both remain aligned to one deterministic song clock.
- As a designer, I can preview crop, fit, loop, opacity, fades, and overlays
  without requiring the Stage projector.
- As a designer, I can target Stage Portrait (9:16) or Standard Landscape
  (16:9), preview the correct safe frame, and place characters at stage-sized
  scale with reviewed focal framing.
- As an operator, I can select front or rear projection independently from the
  authored layout, without editing or duplicating the source media.
- As a show designer, I can target named Portrait Character and Landscape Main
  surfaces from one Video Scene and preview them together on one song clock.
- As an operator, failure of one Stage surface blacks only that surface while
  lighting and every healthy surface continue.
- As an operator, missing or failed video fails black without interrupting the
  lighting cue.

Acceptance:

- Build on `MEDIA-001`, `MEDIA-002`, `MEDIA-003`, `PROJ-001`, and `SHOW-002`; do not create a
  second projection runtime or cue model. Overlay controls that require the
  compositor remain disabled until `PROJ-002` is available.
- Define a versioned Video Scene containing ordered visual layers, clip/range
  references, crop/fit, loop mode, opacity, fades, intensity, overlays, and
  black fallback. The scene never contains a remote stream URL or command.
- The song editor exposes Lighting and Video as separate lanes with independent
  cue boundaries, drag/trim/split, snapping, gaps, overlaps allowed only by an
  explicit composition rule, and a shared ruler/playhead/seek operation.
- Deterministic metadata templates can propose an initial video layout from song
  duration/sections plus clip mood, energy, palette, motion, tempo suitability,
  and loopability. The result is an editable draft, not an automatic publish.
- Export projection presets and media references through the show manifest.
- Preview and Stage use an explicitly versioned interpretation of crop/fit,
  timing, looping, transitions, intensity, and black fallback.
- Layout profile and projection side are separate versioned fields. Portrait
  defaults to full-height `cover` with a reviewed focal point; Landscape
  defaults to 16:9 `cover`; rear projection adds a horizontal output mirror.
  `contain` remains available as an explicit editorial choice.
- Published surface assignments use stable logical IDs and commissioned Stage
  connector mappings rather than desktop screen numbers. Each surface carries
  its own required rendition, fallback, health, and black state while receiving
  the shared transport events.
- Song start, stop, pause, seek, next-song selection, and no-autostart semantics
  address both track runners. Video may pre-roll for decode readiness but cannot
  present before explicit song start.
- A band's multi-clip song completes end-to-end Studio publish and Pi playback
  while the DMX 25 FPS soak remains within its existing limits. Killing the
  player fails the Video track black while Lighting stays on time.

Implementation seed (2026-11-16): the Stage-side `video-show.json` contract and
parallel runner now exist without changing `songs.json`. Travelling on a
Floating Rock is the first reference track, initially with one full-length
Stage Portrait scene at time zero. Studio must evolve that seed into editable
section cues and VFX layers rather than treating a monolithic video as the final
authoring experience.

Stage rehearsal seed (2026-11-17): `SHOW-006` will prove a reusable
cross-surface choreography vocabulary before the full editor is built. Studio
must be able to express Echo, Throw, Catch, Ping-pong, Bridge, Unison, and
Counterpoint patterns using an initiating surface, receiving surface, audience-
view direction/path, musical/absolute timing anchor, palette, intensity,
transition, and black fallback. These fields compile to ordinary deterministic
Lighting and Video tracks; they do not create a new Stage clock or live Studio
dependency. `SHOW-007` uses the same model for an optional Christmas mini-pack.
See [`integrated-vfx-sprint.md`](integrated-vfx-sprint.md).

Media-model refinement (2026-11-17): `VFX-001` makes the 10–30 second visual
storylet—not a continuous music video—the primary reusable Video asset. Studio
stores an immutable storylet revision with portrait/landscape renditions,
rights/source hashes, semantic event markers, palette/energy/motion tags,
black entry/exit, and optional companion Lighting recipes. Song tracks place
and variant-map storylets without copying them. The initial Fuse Bomb proof
must be reusable at two song positions from one rendition, with its named
impact marker aligning the bounded Lighting blast in both placements.

`VFX-002` adds a separate lightweight scene-fill family for particles, smoke,
energy, ribbons, colour fields, and impact accents. Studio must distinguish
primary clips, narrative storylets, character interactions, transition
bridges, impact accents, and scene-fill phrases. Fill placements inherit a
reviewed palette/energy role from a Lighting scene but retain explicit start,
end, intensity, purpose, rights/source identity, and black fallback. They never
become unbounded wallpaper or a live dependency between Video and Lighting.

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

### AI-STUDIO-001 — Reviewed AI show and video-layout proposals

- As a higher-tier designer, I can ask Studio to propose lighting and Video
  tracks from song structure, descriptive metadata, my private library, and
  entitled catalog assets.
- As a reviewer, I can see why each cue/clip was selected, its source evidence,
  rights/entitlement status, estimated processing usage, and differences from
  the current draft.
- As a band, our approvals and rejected patterns can inform later proposals
  without allowing the agent to publish or control Stage.

Acceptance:

- Inputs are explicit song revisions, analysis evidence, user instructions,
  allowed asset scopes, catalog/private tags, prior approved/rejected proposals,
  and a bounded usage reservation. Private tenant content never becomes global
  training/catalog data through this workflow.
- Output is a structured, schema-validated proposal for Lighting and Video lanes
  with stable references, timing, transitions, confidence/rationale, and
  evidence links. Missing assets, rights, entitlements, or compatibility are
  visible validation errors.
- Review supports preview, compare, accept selected items, reject with reason,
  and undo. Acceptance creates a new draft revision; publish remains the normal
  separate `PUBLISH-001` operation.
- Model/provider failure, timeout, unsafe output, graph loss, or exhausted quota
  leaves the current draft untouched and does not block manual authoring.
- Deterministic non-AI metadata templates remain available and testable for the
  same song/asset inputs.

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

- As a Pro subscriber, I can prepare a dual-track show on hosted Studio, deliver
  it, rehearse and run it offline, return corrections, republish it, and recover
  the previous version.
- As a maintainer, I can prove cross-tenant access, cloud, entitlement, graph,
  media, and projection failures do not weaken Stage lighting safety.

Acceptance:

- Exercise tenant isolation, entitlement/quota accounting, export/deletion,
  backup/restore, hosted/LAN/removable package delivery, cloud loss, interrupted
  import, invalid package, activation, rollback, clean/conflicting sync, and
  corrupt adjustment recovery.
- Run the complete automated, Chromium, Pi, 25 FPS, lease-loss, blackout,
  reserved-channel, white-output, kiosk, and shutdown suites.
- Run projection failure, missing-media, player-crash, display-disconnect, and
  video drift/resync checks while lighting remains controllable and on time.
- Document show preparation, transfer, activation, fallback, return sync, and
  emergency procedures before Stage authoring is reduced.

## Decisions required before implementation commitments

Sprint 0 must record these as explicit architecture/product decisions rather
than letting the first implementation choose them accidentally:

1. Hosted identity/session provider and account-recovery policy, including team
   invitation and support-access boundaries.
2. Tenant-isolation strategy for transactional metadata, object storage, jobs,
   caches, logs, analytics, and backups.
3. Billing integration boundary and the authoritative entitlement/usage model;
   exact tier prices and quotas can remain configuration.
4. Object-storage, resumable-upload, media-probe, transcode, thumbnail, and job-
   queue abstractions, plus the first canonical Stage rendition profile.
5. Stage device enrollment, package signing, credential rotation/revocation,
   and hosted delivery protocol while preserving LAN/file parity.
6. Pi projection backend selected from measured `mpv`, VLC, and GStreamer/
   direct-rendering probes, including HDMI ownership and black-screen recovery.
7. Initial projection contract: supported containers/codecs, resolution/frame-
   rate ceiling, aspect/crop semantics, audio treatment, transition set, and
   acceptable drift/resync behavior.
8. Customer-media privacy, rights/provenance, retention/export/deletion, AI
   provider/data-use policy, and whether any region-specific storage promise is
   made at launch.
9. Catalog curation and licensing process, including how an entitled catalog
   revision remains usable inside an already published offline package.
10. Initial Pro acceptance show: representative songs, lighting scenes, source
    VFX/videos, derived clips, projector/display, Stage unit, and rehearsal test
    conditions used as the vertical-slice fixture.

## Sprint plan

### Sprint 0 — Product, domain, and isolation contracts

Cards: `STUDIO-001`, design portion of `SAAS-001`.

Freeze the Stage/Studio boundary, stable IDs, revision semantics, tenant and
workspace model, role matrix, schema migration, entitlement vocabulary, media
identity, and representative legacy fixtures. Deliver design records, schemas,
validators, migration dry-run, backups, and tenant-isolation tests before UI,
packages, media jobs, or AI depend on the model.

### Sprint 1 — Hosted account and operations foundation

Cards: `SAAS-001`, foundation of `SAAS-003`.

Implement sign-in/session boundaries, tenant/workspace membership, server-side
authorization, tenant-scoped persistence/object keys/jobs, audit records,
environment migrations, backups, and a restore drill. Exit with two test
tenants that cannot observe or mutate one another through any supported path.

### Sprint 2 — Entitlements and starter catalog

Cards: `SAAS-002`, `CATALOG-001`.

Implement capability/quota evaluation, usage reservation/commit/release, and a
small versioned catalog of base lighting scenes, Video Scenes, clips, and song
templates. Exercise Free, Artist, and Pro configurations from the same code and
prove catalog updates do not mutate pinned customer revisions.

### Sprint 3 — Publishing, pairing, and offline delivery

Cards: `PUBLISH-001`, `STAGE-LINK-001`.

Implement deterministic package creation, validation, registry, short-lived
device pairing, resumable delivery, Stage staging, explicit local activation,
inventory, and rollback. The same package must pass through hosted, LAN, and
removable-media delivery, and the Stage must run it after network removal.

### Sprint 4 — Studio authoring and lighting vertical slice

Cards: `STUDIO-002`, `STUDIO-003`.

Build the tenant-aware Studio shell and migrate songs, setlists, looks, scenes,
and tuning profiles. Deliver revision history, autosaved drafts, validation,
the zoomable lighting timeline, simulator scrub, undo/redo, and package publish.
Publish and run a lighting-only higher-tier customer show before adding media.

### Sprint 5 — Private media, clip, and production-render pipeline

Cards: `MEDIA-001`, `MEDIA-002`, `MEDIA-003`.

Add resumable private upload, content addressing, probing, previews, storyboards,
manual tags, non-destructive clip ranges, cached phrase rendering, fast review
proxies, resumable Stage assembly, quota accounting, and reference-aware
retention. Bulk-import representative band VFX/video files and produce a
reusable short-clip library without placing media in Git or the graph.

### Sprint 6 — Projection playback foundation

Cards: `PROJ-001`, minimal runtime portion of `SHOW-002`.

Select the Pi playback backend from measured `mpv`/VLC/GStreamer probes. Add an
explicitly enabled separate player process, HDMI selection, load/play/pause/
stop/seek/loop/blank, fake-player tests, package preflight, and one conservative
clip. Prove player failure and display disconnect fail black without disturbing
the 25 FPS lighting loop.

### Sprint 7 — Video Scene manager and parallel song track

Cards: `STUDIO-004`, `SHOW-002`, `VFX-001`, `VFX-002`.

Deliver reusable Video Scenes and the separate Video lane beside Lighting with
a shared ruler, playhead, song transport, deterministic metadata templates,
preview, trim/split, transitions, gaps, and validation. Publish a multi-clip
band song; Lighting and Video start from the same explicit song event, while
video pre-roll remains invisible.

Treat reusable 10–30 second storylets as first-class library objects with named
event markers and companion Lighting recipes. Continuous video remains a valid
scene type, not the assumed unit of every song layout.

Expose scene-fill phrases as a separate searchable family so designers can
augment existing Lighting scenes without pretending every abstract texture is
a narrative clip. Preview must show focal load and the combined full-stage
result, not only the projector frame.

### Sprint 8 — Projection composition and optional video-to-grid

Cards: `PROJ-002`, optional `VIDEO-001`.

Add bounded overlays, colour/still layers, crop/fit, opacity, blend, intensity,
and transitions after the playback foundation is stable. Video-to-grid remains
an optional lighting input and never becomes the media store or show clock.

The earlier Stage-first `SHOW-006/007` rehearsal provides the cross-surface
vocabulary and perceptual timing evidence for this editor work. Preserve its
deterministic compiled-package implementation as the fallback even when Studio
later offers richer composition previews.

### Sprint 9 — AI-assisted authoring and memory

Cards: `AI-DATA-001`, `AI-DATA-002`, `ANALYSIS-001`, `AI-SONG-001`, and
`AI-STUDIO-001`.

Index stable Studio revisions and evidence, add rights-safe song analysis, and
produce structured Lighting/Video proposals with rationale, source and cost
metadata. Review may accept selected changes into a draft; AI cannot publish or
control Stage. Deterministic metadata templates remain the fallback and this
sprint never blocks manual authoring or Stage startup.

### Sprint 10 — Local adjustment, return sync, and Stage focus

Cards: `SYNC-002`, `STAGE-001`.

Implement the allowlisted adjustment journal, cloud/LAN/file change-set return,
three-way review, Shows/Adjust runtime workspaces, and explicit conflicts. Reduce
heavy Stage authoring only after migration, package, rollback, media, adjustment,
and return-sync evidence is recorded through a rehearsal and live show.

### Sprint 11 — Integrated acceptance and operating handbook

Cards: `STUDIO-005`, `SAAS-003`, and final acceptance for all linked cards.

Complete tenant-isolation, quota, export/deletion, recovery, package, conflict,
media, projection, cloud-offline, hardware, security-boundary, and show-safety
tests. Document onboarding, asset preparation, design, publish, delivery,
activation, fallback, return sync, and emergency operation before launch.

## Explicit non-goals for the first hosted release

- Real-time multi-user collaborative editing.
- Internet-dependent show playback or streaming show-critical media.
- Remote activation or remote start of lighting/video output from Studio.
- Hard-coded prices or separate application forks for subscription tiers.
- Automatic ingestion of customer assets into the shared catalog or model
  training corpus.
- Editing the active Stage package in place.
- Automatic conflict resolution or last-writer-wins synchronization.
- Graph replication as package transfer or Stage state storage.
- Letting Studio, AI, media import, or projection start live lighting output.
- Moving video decode, projection composition, or graph queries onto the DMX
  render thread.
