# Media management and unified Stage control architecture

Date: 2026-11-17

## Decision summary

Phreqed treats Lighting and Video as coordinated lanes of one song/scene show,
not as two unrelated applications. Authoring may expose separate lanes, but the
performer starts, stops, advances, and blackouts one show. Each published scene
explicitly participates as **Lights**, **Video**, **Both**, or **Black**.

Media bytes live in a content-addressed file/object store. Relate may be the
authoritative Studio store for graph-native metadata, revisions, relationships,
rights, approvals, and agent memory, with deterministic exports and migrations
for recovery and portability. It does not store media bytes or resolve live
cues on the Pi. Immutable published manifests and packages remain the Stage
execution contract.

## Authoritative media chain

1. **Source blob:** immutable uploaded/imported media addressed by SHA-256, with
   size, media type, probe facts, owner/tenant, rights, and retention state.
2. **Asset revision:** human meaning and provenance for a source or generated
   result: title, family, tags, palette, motion, focal load, and review state.
3. **Clip/storylet revision:** non-destructive source ranges or generated
   media, semantic markers, variants, black entry/exit, and Lighting recipes.
4. **Rendition:** derived proxy or Stage file for a named layout, surface,
   codec, dimensions, frame rate, crop, mirror, and renderer version.
5. **EDL/composition revision:** ordered/overlapping references to immutable
   asset revisions with transforms, blends, fades, and absolute/relative time.
6. **Song placement:** a storylet, fill, primary clip, or black interval placed
   on a song clock, with marker-to-Lighting assignments.
7. **Track/show revision:** reviewed immutable Lighting and Video lanes plus the
   selected output participation for each scene.
8. **Stage package:** fully downloaded, hash-verified media and deterministic
   JSON manifests required for offline playback.

Media blobs are never stored in the graph, Git, `songs.json`, or an EDL. The
graph stores stable IDs, relationships, facts, hashes, review evidence, and
provenance. Losing the Studio graph may require restoring or rebuilding Studio
metadata, but it cannot delete content-addressed media or invalidate an already
published Stage package.

## Relate boundary

Relate is an embedded Cypher graph engine from Neo4j Labs, not a small embedded
Neo4j server. It is Apache-2.0 and supports durable directory or single-file
stores, but the complete graph and its indexes live in RAM and only one process
may own a writable store. A server surface still fronts one engine/store; it is
not clustering or replication.

Good Relate uses:

- trace source blob -> generated asset -> storylet -> rendition -> EDL -> song
  placement -> track revision -> Stage package;
- find every published package affected by a source, rights, or rendition
  problem;
- relate song sections, visual energy, palette, motion, prior approvals, and
  rejected AI proposals;
- remember which storylets and Lighting recipes worked in rehearsals/shows;
- explain why an agent proposed an asset and what evidence/revision it used;
- index returned Stage adjustment change sets for Studio review.

Relate must not:

- store video/image/audio bytes;
- be the only copy of authoritative media, rights, EDL, or package metadata;
- advance the song clock, resolve the next cue, or gate Start/Stop/Blackout;
- be required for controller startup, package preflight, leases, or fail-black;
- receive live per-frame Lighting or player telemetry as unbounded graph data;
- share one writable store between Studio and Stage.

Studio is the preferred writer for the hosted creative library. A separate Pi
Relate store may support offline search, diagnostics, setlist changes,
performance observations, and a revision-aware outbound change journal, but
Stage playback uses only local immutable manifests and ordered arrays. Studio
and Stage exchange explicit events/change sets rather than sharing or directly
replicating one writable store.

## Proposed media graph

Nodes:

- `SourceBlob`, `AssetRevision`, `StoryletRevision`, `Marker`, `LightingRecipe`
- `Rendition`, `ProjectionProfile`, `Surface`, `EDLRevision`, `Placement`
- `Song`, `Section`, `LightingTrackRevision`, `VideoTrackRevision`, `Scene`
- `ShowRevision`, `StagePackage`, `RightsRecord`, `Review`, `Evidence`
- `AdjustmentChangeSet`, `DeviceCapability`, `PerformanceObservation`

Core relationships:

- `DERIVED_FROM`, `HAS_MARKER`, `HAS_RENDITION`, `TARGETS_SURFACE`
- `USES_ASSET`, `PLACES`, `ALIGNS_MARKER_TO`, `USES_RECIPE`
- `BELONGS_TO_SECTION`, `COMPILES_TO`, `PUBLISHED_AS`, `SUPERSEDES`
- `GOVERNED_BY_RIGHTS`, `SUPPORTED_BY`, `REVIEWED_AS`, `OBSERVED_ON`
- `REQUIRES_CAPABILITY`, `ADJUSTS`

Every node that mirrors authoritative data records the stable ID and revision,
content/manifest hash, source system, and indexed time. Graph updates are
idempotent projections of catalog events; graph loss is recovered by replaying
those events or re-indexing authoritative records.

## Unified song/scene control

The performer-facing model has one song transport. Video does not gain a second
Start button, independent song selection, or separate footswitch timeline.

Every authored scene selects one friendly participation mode:

| Mode | Lighting lane | Video lane |
| --- | --- | --- |
| Lights | Select/run the Lighting scene | Explicitly black |
| Video | Explicitly black Lighting | Select/run the Video scene/storylet |
| Both | Select/run both lanes from the same song clock | Select/run both lanes from the same song clock |
| Black | Explicitly black | Explicitly black |

The compiled representation remains explicit per lane rather than relying on
implicit state:

```json
{
  "at_seconds": 42.0,
  "participation": "both",
  "lighting": {
    "action": "select",
    "scene_id": "scene-wave-rider"
  },
  "video": {
    "action": "select",
    "placement_id": "placement-fuse-bomb-01"
  }
}
```

Allowed lane actions are fixed enums: `select`, `hold`, or `black`. Published
data must agree with the friendly participation mode; validation rejects a
Lights scene that leaves Video holding accidentally, or a Video scene that
silently leaves Lighting active.

## Pi control surface

Perform remains song/setlist-first:

- **Start/Stop/Previous/Next/Blackout** operate the combined show.
- Pre-show lane selectors choose **Lights + Video** (default), **Lights only**,
  or **Video only** for testing or venue constraints. They do not change the
  published show and cannot enable live Art-Net by themselves.
- During a running song, a lane may be muted immediately: Lighting mute sends
  its existing blackout; Video mute stops the player and exposes the black
  underlay. Re-enabling requires an explicit **Rejoin** action or waits for the
  next authored scene boundary; it never silently restarts live output.
- Status always names the active scene and independently reports Lighting and
  Video as Active, Held, Black, Muted, Disabled, or Error.
- Manual mode selects a combined authored scene. An advanced diagnostic drawer
  may preview Video or Lighting independently only when output authority and
  existing safety gates allow it.
- Foot control remains show-level. It does not need separate Video switches for
  the primary workflow.

If Video is absent, muted, disabled, corrupt, or crashes, Lighting follows its
song track. If Lighting is not live or is muted, Video may continue only when
the selected pre-show lane policy includes it. Global Blackout always blacks
both lanes and releasing it never auto-starts either lane.

## Delivery increments

1. Extend the versioned show schema with explicit per-scene participation and
   per-lane fixed actions; add validation and migration for existing tracks.
2. Add Perform lane selectors, immediate mute, explicit rejoin, independent
   status, and foot-control regression tests.
3. Define authoritative content-addressed media catalog records and event
   export before adding a graph.
4. Prototype the proposed graph from synthetic and current Travelling/Fuse Bomb
   data on the Studio workstation; measure memory, cold start, writes, queries,
   checkpoint, backup, restore, migration, and full rebuild.
5. Only if justified, test a bounded read-only ARM64 snapshot beside the 25 FPS
   Pi soak. Its absence and removal must be operationally invisible.

## Acceptance

- The same song can contain Lights, Video, Both, and Black scenes with one
  monotonic clock and no independent transport drift.
- Lane selection/mute/rejoin cannot enable live output, bypass blackout, arm
  whites, raise a ceiling, or autostart a song.
- Video failure never stops Lighting; Lighting failure blacks its output and
  does not strand the projector outside its explicit policy.
- Every media/package relationship can be rebuilt from authoritative catalog
  records without Relate.
- The Studio graph answers provenance and impact queries but is not queried in
  the Stage cue loop.
- Pi operation, show startup, and rollback pass with no graph installed.
