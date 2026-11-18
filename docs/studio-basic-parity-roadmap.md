# Phreqed Studio Basic parity roadmap

Date: 2026-11-18
Status: Planned; repository foundation in progress
Primary card: `STUDIO-007`
Related cards: `MEDIA-004`, `STUDIO-001/002/003/004`, `MEDIA-001/002/003`,
`PUBLISH-001`, `SYNC-002`, `STAGE-001`, `SAAS-001/002`, `STAGE-LINK-001`

## Outcome

Deliver a genuinely usable local **Studio Basic** application that can import
the current Stage libraries, author and preview complete lighting/video shows,
manage media, songs, cue sheets, setlists, and venue profiles, validate every
reference, and publish a deterministic package for Stage.

Relate is the primary metadata repository for Studio Basic and the Stage unit.
Content-addressed media remains outside the graph. Stage still executes the
published package's validated manifests and ordered cue arrays without a graph
query in the real-time rendering path.

Higher tiers preserve the same domain IDs, revision model, package contract,
and user journeys while moving collaborative/larger graph workloads to Neo4j
Aura and adding storage, processing, AI, device, history, and team capacity.

## What parity means

Parity means Studio can perform every **authoring and show-management** task
currently possible on Stage before advanced features replace the local tools.
It does not mean exposing live fixture control in Studio.

| Current Stage capability | Studio Basic destination | Studio behavior |
| --- | --- | --- |
| Looks and layered effects | Lighting library | Search, copy, edit, preview, revise, retire |
| Manual scene list | Lighting scenes | Compose ordered look cues with holds and transitions |
| Song library | Songs | Metadata, duration, style, notes, revisions |
| Cue sheets/timeline | Show composer | Full-width lighting lane with draft/publish workflow |
| Setlist builder/copy | Setlists | Search, add, repeat, reorder, copy, revise, publish |
| Venue/tuning profiles | Profiles | Design bounded RGB/audio/white settings and shortcuts |
| Fixture preview | Preview | Deterministic injected-time simulator only |
| Video Show sidecar | Video lane | Video Scenes, Storylets, placements, black gaps |
| Projection layouts | Surfaces | Portrait/landscape, front/rear, crop/fit/focal framing |
| Current JSON libraries | Import/migration | Idempotent migration into Relate with backup/report |
| Health/package readiness | Publish validation | Missing reference, media, fixture, and compatibility checks |
| Live transport/blackout | Not a Studio feature | Preview transport cannot acquire Stage output authority |
| Display/network/shutdown | Device management status only | Pi-local mutations remain on Stage |

Stage authoring remains available until the corresponding Studio workflow,
import/export round trip, package publication, and rollback are accepted.

## Product structure

Studio Basic uses persistent top-level navigation:

1. **Home** — recent workspaces, shows, validation status, packages, and Stage
   connection summaries.
2. **Shows** — show identity, revisions, fixture design, surfaces, songs,
   setlists, and published package history.
3. **Lighting** — Looks, Lighting Scenes, effect catalog, palettes, and reusable
   companion lighting recipes.
4. **Media** — source assets, clips, Storylets, fills, renditions, rights,
   markers, and Video Scenes.
5. **Songs & Setlists** — song metadata, reusable cue sheets, setlist revisions,
   ordering, and show assignment.
6. **Composer** — full-width shared song ruler with Lighting and Video lanes,
   selection inspector, preview, validation, and revision controls.
7. **Profiles** — venue/tuning profiles and bounded RGB, audio, white, fixture,
   and projection defaults.
8. **Publish** — validation, package contents, target compatibility, export,
   device delivery, activation eligibility, and rollback history.

Studio has no Start Live, Show Power, Arm Whites, network-switch, backlight,
shutdown, or global live Blackout command. Preview is always visibly simulated.

## UX principles

- Desktop authoring is primary, with tablet/touch support; Stage remains the
  performance-first 1280×800 interface.
- Use searchable master-detail libraries and dedicated editors. Do not recreate
  long card stacks, nested scrolling, native precision dropdowns, or editors
  opening below their lists.
- Composer and media preparation are full-screen tasks with a persistent
  inspector and one main scroll/zoom surface.
- A selected object always shows its stable ID, draft/published state,
  validation, dependencies, revision, and unsaved state without relying on
  colour alone.
- Draft edits autosave transactionally. Publish is always separate, explicit,
  validated, and reversible.
- Use undo/redo for editing gestures; destructive delete becomes retirement
  when a published revision or package references the object.
- Keyboard and pointer workflows are dense and efficient; essential actions
  retain touch-sized targets and never depend only on hover, drag, swipe, or
  long press.
- Preview must be deterministic at a supplied time and must never open Art-Net,
  arm white channels, or launch the commissioned projector output.

## User stories and acceptance

### 1. Workspace, show, and revision management

- As a local designer, I can create and rename a workspace and keep multiple
  shows separate.
- As an existing Stage user, I can import `library.json`, `songs.json`,
  `tuning-profiles.json`, and the Video Show sidecar without re-entering data.
- As a designer, I can see Draft, Valid, Published, Superseded, and Retired
  states and compare revisions.
- As an operator, I can identify exactly which show/package revision is active
  on a Stage unit.

Acceptance:

- Migration takes backups, is idempotent, preserves stable legacy IDs and all
  values, and produces an itemized warning/error report.
- Relate uniqueness constraints reject duplicate workspace-scoped IDs and
  revision regressions.
- Every edit records actor/process, base revision, created/updated time, and
  supersession lineage.
- Published revisions are immutable; editing creates a draft successor.

### 2. Lighting Looks

- As a lighting designer, I can search built-in and user Looks and filter by
  palette, effect, energy, motion, fixture compatibility, and publication state.
- As a designer, I can create or copy a Look, edit its name/description/output
  brightness, and add, remove, reorder, enable, and target layers.
- As a designer, I can select each layer's effect, palette, blend, opacity,
  fixture target, speed, level, and validated effect-specific parameters.
- As a designer, I can scrub a deterministic preview across both Betopper cubes
  before saving a revision.

Acceptance:

- Studio exposes every field currently accepted by `parse_preset` and every
  registered effect's metadata and parameters.
- Built-ins are copied before editing; saved brightness remains within the
  persistent 0.65 ceiling.
- Missing effects, invalid parameters, fixture mismatches, and referenced
  retired Looks remain visible and block publication.
- Preview and thumbnails use normalized rendering only and construct no output
  sender.

### 3. Lighting Scenes and reusable recipes

- As a designer, I can create, copy, rename, reorder, and retire Lighting
  Scenes that reference explicit Look revisions.
- As a designer, I can edit hold time, entry transition, notes, and semantic
  purpose without losing the selected Look.
- As a media designer, I can save a bounded companion Lighting recipe for a
  Storylet marker such as `impact`, `pulse`, or `discharge`.

Acceptance:

- Scene durations and transitions retain current Stage validation bounds.
- Reordering has keyboard buttons in addition to drag-and-drop.
- Referenced scenes cannot be destructively deleted; retirement and dependency
  impact are graph queries.
- Recipes never contain live-output authority or higher safety ceilings.

### 4. Songs and cue sheets

- As a show designer, I can create and revise song title, artist, duration,
  style, notes, and stable identity.
- As a designer, I can generate a deterministic style-based baseline as a
  draft, copy a published cue sheet, or start empty.
- As a designer, I can add, split, remove, resize, and reorder Lighting cues and
  edit their Look/Scene reference and transition.
- As a reviewer, I can preview any cue or scrub the whole song without starting
  fixture or projection output.

Acceptance:

- Cue coverage reconciles exactly to song duration; gaps or overlaps follow an
  explicit lane policy and are visible.
- Generated style revisions are drafts and never publish automatically.
- Published cue sheets are immutable and show dependency impact.
- The editor provides snapping, numeric timing, keyboard movement, undo/redo,
  and validation markers; drag is optional rather than required.

### 5. Setlists

- As a show designer, I can create, copy, rename, revise, and retire setlists.
- As a designer, I can search the song library, add repeated songs for encores,
  reorder or omit songs, and see total show duration.
- As a performer, I can use a local Stage setlist change during a show and later
  return it to Studio for review.

Acceptance:

- Setlist edits never mutate song or cue-sheet revisions.
- Copy creates a new stable setlist identity with explicit origin lineage.
- Published packages pin exact song/cue revisions rather than resolving latest
  at runtime.
- Stage changes carry package/base revisions and merge through `SYNC-002`.

### 6. Venue and tuning Profiles

- As a designer, I can reproduce the Rehearsal, Small Stage, and Large Stage
  baselines and create custom profiles.
- As a designer, I can edit bounded RGB master/contrast, audio auto-level and
  quiet response, white drive/power preparation, threshold/levels, preview
  defaults, projection layout, and Perform-shortcut intent.
- As an operator, I can understand which settings are merely prepared and which
  still require local Stage arming or Show-power confirmation.

Acceptance:

- Studio exposes every persisted field in the current tuning-profile schema,
  validates the same bounds, and never stores an armed-output state.
- Profile preview simulates segmented whites but cannot address physical white
  channels.
- Import/export round-trips existing profiles byte-equivalently after canonical
  normalization.
- Stage retains final local authority for RGB Show power and white arming.

### 7. Media assets and Storylets

- As a media designer, I can import images/video once, detect duplicates by
  hash, inspect probe facts and thumbnails, and record title, family, source,
  rights, tags, and notes.
- As a designer, I can define a non-destructive clip or 10–30 second Storylet,
  set duration/loop/black entry/exit, and author ordered semantic markers.
- As a designer, I can request portrait/landscape and front/rear renditions
  while preserving the immutable original.
- As a designer, I can find compatible assets by duration, palette, energy,
  motion, surface, rights, approval, and prior usage.

Acceptance:

- Relate is authoritative for asset/revision/marker/provenance metadata; bytes
  are SHA-256-addressed in configured filesystem/object storage.
- Import, probe, thumbnail, rendition, and render jobs are resumable and never
  run inside the Studio web or Stage control process.
- Every derived file records source hashes, tool/version/settings, output hash,
  and lineage.
- Reference-aware retirement/garbage collection cannot remove bytes required by
  retained revisions or packages.

### 8. Video Scenes and projection surfaces

- As a projection designer, I can create a Video Scene from clips, Storylets,
  stills, fills, black frames, colour fields, and ordered overlay layers.
- As a designer, I can edit ranges, crop/fit/focal point, opacity, blend, fades,
  loop mode, intensity, and black fallback.
- As a designer, I can preview Stage Portrait and Landscape Main surfaces and
  choose front/rear projection independently.

Acceptance:

- Surface assignments use stable logical IDs, not desktop display numbers.
- Portrait and landscape rendition requirements are explicit before publish.
- Missing media or unsupported composition blocks publish and previews a black
  fallback rather than silently inheriting output.
- Multi-surface failure isolation compiles into the package contract.

### 9. Unified show Composer

- As a show designer, I can edit Lighting and Video lanes against one song
  ruler and playhead.
- As a designer, I can place the same Storylet revision multiple times and map
  its semantic markers to Lighting scenes/recipes without re-rendering it.
- As a designer, I can author Lights, Video, Both, or Black participation and
  preview Echo, Throw, Catch, Ping-pong, Bridge, Unison, and Counterpoint.
- As a reviewer, I can inspect dependencies, validation, changes from published,
  and estimated package/render work before accepting a revision.

Acceptance:

- Friendly participation compiles to explicit `select`, `hold`, or `black`
  actions per lane; contradictory or inherited state is rejected.
- Both lanes use one monotonic song clock and deterministic supplied-time
  preview.
- Timeline operations include zoom, snap, split, trim, move, keyboard controls,
  undo/redo, copy/paste, and numeric inspector editing.
- Video gaps are intentionally black unless an explicit `hold` is authored.

### 10. Validate, publish, deliver, and recover

- As a designer, I can validate a show and see every blocking error and warning
  connected to the exact object that must be fixed.
- As an operator, I can inspect package contents, hashes, target fixture/surface
  requirements, estimated size, and compatibility before export.
- As a Stage operator, I can import over trusted LAN or removable media without
  changing the active show, then explicitly activate or roll back while stopped.

Acceptance:

- Package creation pins all revisions and copies every required media rendition;
  it never contains remote stream URLs or resolves `latest` on Stage.
- Interrupted/rejected imports leave the active package unchanged.
- Studio cannot remotely start output, arm whites, release blackout, or activate
  a package during playback.
- The same package validates identically through local file, LAN, and future
  hosted delivery.

### 11. Stage Relate operational state and bidirectional sync

- As a performer, I can reorder/omit a setlist item, select/copy a profile, make
  an allowlisted bounded timing/scaling adjustment, and add a note offline.
- As a designer, I can receive those changes in Studio, see clean changes and
  conflicts against the original package revision, and accept or reject each.
- As an operator, I can continue the show if Relate, sync, Studio, or the network
  is unavailable.

Acceptance:

- Stage Relate is primary for installed-package inventory, active revision,
  setlist operational state, allowlisted adjustments, observations, and sync
  outbox/inbox—not for frame rendering or cue advancement.
- Every event has a globally stable ID, device/workspace, package/base revision,
  entity/revision, old/new value, actor, occurred/recorded time, and status.
- Sync is idempotent and resumable; Studio performs a three-way merge and never
  overwrites a newer revision silently.
- Accepted changes create new Studio drafts; reviewed inbound packages enter
  Stage staging and never mutate the active package automatically.

## Relate and Aura repository model

### Studio Basic

- One local Relate directory store owns graph-native metadata and revisions.
- One application writer serializes changes; bounded read-only queries support
  discovery and the director.
- Content-addressed media uses a configurable local filesystem root.
- Local backup/export and package transfer work without an account or cloud.

### Stage

- A separate bounded Relate directory store owns device operational metadata,
  installed packages, active selection, setlist state, adjustments,
  observations, and sync events.
- Published package manifests and ordered arrays remain the execution authority.
- The controller can start, perform, blackout, stop, and roll back with the
  graph service unavailable by loading the already activated package contract.

### Higher tiers with Neo4j Aura

- Preserve stable IDs, revisions, relationship vocabulary, event envelopes, and
  package schemas so Basic workspaces can migrate without rebuilding shows.
- Add hosted identity, collaboration, roles, larger libraries/graphs, multiple
  devices/workspaces, deeper history, cloud media processing, AI allowances,
  analytics, and managed backup/recovery according to entitlements.
- Aura is not contacted by the Stage cue loop. Stage synchronizes explicit
  change sets and packages through a service boundary.
- Tier downgrade or cloud loss cannot disable an already downloaded package.

## Initial tier envelope

| Capability | Basic/local | Artist/Aura | Pro/Aura |
| --- | --- | --- | --- |
| Lighting, songs, setlists, profiles | Included | Included | Included |
| Local Relate metadata store | Included | Import/export | Import/export |
| Media import and manual Storylets | Included with local storage | Hosted storage/processing quota | Higher quota/batch processing |
| Deterministic preview/package export | Included | Included | Included |
| Paired Stage units | One initial target | Configurable allowance | Multiple devices/workspaces |
| Revision history | Bounded local | Extended | Deep/team audit history |
| Collaboration and roles | Single-user | Limited team | Full roles/workspaces |
| AI-assisted analysis/authoring | Deterministic templates | Allowance | Higher allowance/private memory |
| Multi-surface/advanced projection | Basic portrait/landscape | Expanded | Full advanced composition |

Exact commercial names, prices, quotas, retention, and Aura topology remain
product configuration rather than hard-coded application forks.

## Sprint sequence

### Sprint 0 — Relate primary repository and migration

- Expand `MEDIA-004` beyond the projection into authoritative workspace, show,
  revision, lighting, song, setlist, profile, media, and package records.
- Add a single writer service, schema version, migrations, canonical export,
  backup/restore, and JSON import/reconciliation.
- Keep current JSON libraries untouched until round-trip evidence passes.

Exit: import the current complete Stage libraries into Relate, close/reopen,
export, compare every domain value, and rebuild the same package inputs.

### Sprint 1 — Studio shell and library parity

- Implement Home/Shows navigation, object state/revision UI, shared search,
  validation summaries, and autosaved drafts.
- Deliver Lighting Looks, Scenes, and Profiles master-detail workflows.

Exit: reproduce, preview, revise, and export representative current Looks,
Scenes, and all baseline/custom profiles without Stage output access.

### Sprint 2 — Songs and Setlists parity

- Deliver Songs, cue-sheet revisions, style drafts, Setlists, copy/reorder,
  total duration, dependency navigation, and deterministic preview.

Exit: import and rebuild the current setlist, preserve repeats/order, and
publish a lighting-only package equal to the current Stage behavior.

### Sprint 3 — Media and Storylet workspace

- Add probing, thumbnails, source/rights metadata, non-destructive clips,
  Storylet markers, fills, renditions, job state, and graph discovery.

Exit: author Fuse Bomb and Heart Zones records/renditions from source through
reviewed Storylets with complete lineage and black fallback.

### Sprint 4 — Unified Lighting/Video Composer

- Implement the shared ruler, two lanes, inspector, preview, Storylet placement,
  marker mapping, participation modes, and surface preview.

Exit: reproduce the sparse Travelling hybrid and place Fuse Bomb twice from one
rendition without changing Stage clock or safety behavior.

### Sprint 5 — Publish and Stage delivery

- Add package validation, deterministic assembly, target compatibility,
  export/import, device staging, explicit activation, and rollback.

Exit: Studio Basic creates a complete dual-lane show package that the Pi imports,
validates, activates while stopped, performs offline, and rolls back.

This is the **Studio Basic operating gate**. Advanced tier work must not delay
or destabilize it.

### Sprint 6 — Stage Relate and bidirectional adjustments

- Migrate installed-package/setlist/adjustment/observation state into the local
  Stage Relate store and implement event outbox/inbox plus Studio three-way
  review.

Exit: make an offline setlist and timing adjustment on Stage, continue the show,
sync it to Studio, resolve it, republish, and activate the new package without
modifying the original.

### Sprint 7 — Aura tiers and hosted scale

- Implement tenant/workspace identity, entitlements, Aura-backed repository
  adapter, object storage, hosted jobs, team roles, audit, pairing, and cloud
  package delivery using the same domain contracts.

Exit: migrate a Basic workspace to the hosted tier, compare canonical identity
and package output, operate offline on Stage, and export the customer workspace
without losing provenance or revisions.

## Studio Basic release acceptance

- All current Stage authoring capabilities have an accepted Studio workflow or
  a documented Stage-only operational reason for exclusion.
- Current libraries migrate without loss and remain recoverable throughout the
  transition.
- Relate is primary for Studio metadata; content-addressed bytes and published
  packages are independently durable and verifiable.
- A complete lighting/video show can be authored, previewed, validated,
  published, transferred, activated, performed offline, and rolled back.
- Studio cannot construct an Art-Net sender or mutate local Pi operations.
- Stage can execute the active package without Studio, Aura, network, sync, AI,
  or a graph query in the real-time path.
- Basic data can migrate to the Aura-backed tier without changing stable IDs or
  rebuilding authored shows.
