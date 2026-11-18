# Relate media DAM and provenance sprint

Date: 2026-11-17
Status: In progress
Primary card: `MEDIA-004`
Related cards: `AI-DATA-001`, `AI-DATA-002`, `MEDIA-001/002/003`, `VFX-001/002/003`, `STUDIO-001/004`

## Sprint outcome

Prove and define Relate as Phreqed Studio's durable graph-native metadata layer
for media digital-asset management, Storylet markers, edit decisions, Lighting/
Video associations, provenance, approvals, packages, and agent memory. Retain
deterministic exports and event/change-set boundaries for recovery, migration,
portability, and Stage publication.

The sprint does not move media bytes into a graph and does not make Relate a
Stage playback dependency. Content-addressed files/object storage remains the
media authority, and immutable published manifests remain the Stage authority.
The Pi continues to execute ordered cue arrays from one song clock.

## Implementation checkpoint — 2026-11-18

The first workstation slice is operational with `relate-db` 1.0.1. Studio uses
a durable directory store and the default `full` durability mode. A
parameterized transactional synchronizer creates stable identity schema and
idempotently writes Workspace, AssetRevision, StoryletRevision, Marker,
OWNS_ASSET, DERIVED_FROM, and HAS_MARKER records. It checkpoints explicitly;
subsequent state and allowlisted query calls reopen the store read-only.

The Fuse Bomb/Heart Zones reference graph synchronized repeatedly without
duplicates and recovered after close/reopen with 15 nodes and 14 relationships.
Bounded lineage and Storylet duration/loop queries returned the expected Heart
Zones asset, Storylet, and five ordered semantic markers. The Studio Graph
workspace synchronizes the same store and reports its durable state. Evidence
and workstation measurements are recorded in
[`validation/relate-studio-foundation-2026-11-18.md`](validation/relate-studio-foundation-2026-11-18.md).

## Product stories

- As a designer, I can find every source, derivative, storylet, rendition, EDL,
  song placement, Lighting recipe, show revision, and Stage package connected
  to an asset.
- As a designer, I can ask which short clips fit a song section by palette,
  energy, motion, duration, surface, rights, and prior approval evidence.
- As a media manager, I can see what must be rebuilt or withdrawn when a source,
  rights record, crop, projection profile, or renderer changes.
- As a reviewer, I can distinguish original facts, generated proposals,
  approved decisions, superseded revisions, and observed rehearsal results.
- As an agent, I can query connected context through a read-only surface without
  obtaining publish, playback, filesystem, or live-output authority.
- As an operator, an active Stage show continues to work if either Studio or
  its local Relate service is stopped, locked, corrupt, or unavailable.
- As a performer, I can change a setlist, record a bounded local adjustment, or
  add an observation offline; Stage stores it in a separate local graph/change
  journal and later synchronizes it to Studio without mutating the active
  package or querying the graph at a cue boundary.

## Technical facts to validate

Relate is an experimental Neo4j Labs project, not an embedded Neo4j server. It
is Apache-2.0 licensed and offers an embedded Cypher engine through CLI, Python,
Node, Rust, C, Java, Go, Swift, Bolt, HTTP, and MCP surfaces. A durable store may
be a directory or one `.rl` file. The complete graph and indexes reside in RAM;
one process owns the writable store; a directory store can support read-only
processes beside the writer. There is no cluster or replication protocol.

The sprint must re-verify these facts against the exact installed release and
record binary/package hashes. Useful upstream references:

- [Relate repository and Apache-2.0 license](https://github.com/relatedb/relate)
- [Limitations](https://relatedb.ai/docs/reference/limitations/)
- [Transactions and concurrency](https://relatedb.ai/docs/concepts/transactions-and-concurrency/)
- [Storage and durability](https://relatedb.ai/docs/concepts/storage-and-durability/)
- [Storage formats](https://relatedb.ai/docs/reference/storage/formats/)

## Work package A — Adoption and benchmark harness

1. Pin one Relate release and verify download signatures/checksums, license,
   supported workstation platform, Python compatibility, and offline install.
2. Disable CLI telemetry and external network listeners by default.
3. Create synthetic small/medium/large DAM datasets with sources, derivatives,
   markers, EDLs, placements, reviews, packages, and superseded revisions.
4. Measure import throughput, query latency, checkpoint time, cold start, WAL
   growth, store size, steady/peak RSS, and logical graph-size enforcement.
5. Record the largest safe graph for the Studio worker memory envelope.
6. Repeat only the bounded read-only subset on ARM64 if an on-Pi snapshot still
   has a concrete user story after workstation acceptance.

Exit gate: published artifacts install reproducibly; measured memory fits the
chosen Studio worker; unsupported or unstable surfaces are removed from scope.

## Work package B — Authoritative catalog event contract

Define append-only or revisioned authoritative events outside Relate:

- source ingested/verified/quarantined/deleted;
- asset/storylet/marker/rendition/EDL/placement revision created;
- rights or entitlement changed;
- review approved/rejected/superseded;
- track/show revision published or rolled back;
- Stage package assembled/preflighted/activated/retired;
- rehearsal observation and Stage adjustment returned.

Every event includes stable ID, revision, tenant, occurred/recorded time,
content or manifest hash, actor/tool identity, schema version, and provenance.
Replaying the event stream or scanning authoritative revision records must
rebuild an empty graph deterministically.

Exit gate: two independent rebuilds produce matching node/relationship counts,
identity sets, and canonical exports.

## Work package C — Media relationship schema and indexer

Implement the nodes and relationships defined in
[`media-control-architecture.md`](media-control-architecture.md). Add uniqueness
constraints and idempotent upserts keyed by tenant + stable ID + revision.

Required reference datasets:

- Travelling master, selected Infinity VFX, sparse hybrid EDL, renditions,
  published track, package, and Pi observations;
- Fuse Bomb source/concept, semantic markers, low/medium/high Lighting recipes,
  two placements, rendition, and package;
- Heart Zones supplied artwork, preserved source identity, pulse/electrical VFX
  loop revision, markers, Lighting recipe, and projection renditions.

Exit gate: the indexer can rebuild, incrementally apply events, reject an event
with missing/incorrect identity or hash, and safely repeat every event.

## Work package D — Query and agent surface

Deliver allowlisted application queries before exposing free-form Cypher:

- lineage from a source to every active package;
- reverse impact of a source, rights, rendition, or renderer change;
- storylets/fills matching duration, palette, motion, energy, surface, and
  rights constraints;
- placements aligned to a semantic marker and Lighting recipe;
- approved/rejected proposals and evidence for a song/section;
- superseded revisions and current published/activated versions;
- packages required by a show and their Stage preflight state.

Agent/MCP access is read-only, row/time bounded, tenant scoped, and unable to
publish, write catalog events, access media bytes, execute commands, or contact
Stage. Query results include stable IDs/revisions so Studio can open the
authoritative record.

Exit gate: authorization and tenant-isolation tests reject cross-tenant, write,
unbounded, unknown, and malformed requests.

## Work package E — Durability, migration, and removal

1. Kill the writer during writes and verify acknowledged transactions recover.
2. Prove a second writer is rejected and documented readers behave as expected.
3. Checkpoint, back up, restore to a separate path, and compare canonical
   exports and required queries.
4. Corrupt a disposable copy and document detection/rebuild behavior.
5. Run one reversible schema migration with pre/post counts and hashes.
6. Export/migrate all authoritative Studio metadata before removing Relate and
   prove published packages remain transferable, activatable, and reversible.

Exit gate: a graph failure blocks affected Studio metadata work until recovery,
but no content-addressed media or published Stage package is lost or changed,
and an active show remains operational.

## Work package F — Studio integration and bounded Pi store

Studio surfaces may use graph-backed discovery, lineage, impact warnings, and
agent context, but every edit opens/saves authoritative revisions through the
normal application service. Publish resolves and freezes all references into a
complete Stage package.

The Pi store is a separate device-local graph, not a shared writable Studio
store. It receives published context and records only allowlisted operational
changes and observations:

- import a versioned package-context snapshot only between publish operations;
- record setlist revisions, bounded adjustments, notes, observations, and exact
  performed-package identity as revisioned device events;
- synchronize idempotent outbound change sets and apply reviewed inbound state
  only to staging, never directly to the active package;
- use base revisions and three-way conflict handling in Studio;
- apply a strict graph-size and systemd memory limit;
- bind no LAN listener by default;
- keep it outside controller dependencies, leases, readiness, and cue loops;
- run it beside the full 25 FPS Lighting + Video + audio + MIDI soak;
- prove removal and corruption do not change show operation.

## Sprint acceptance

- Relate's exact release, hashes, license, install, telemetry, surfaces, and
  limitations are recorded.
- The reference DAM graph restores or migrates deterministically from its
  durable backup/export contract and reconciles hashes and revisions.
- Provenance, impact, discovery, approval-memory, and package queries pass on
  Travelling, Fuse Bomb, and Heart Zones reference chains.
- One writer, read-only agents, tenant boundaries, limits, backups, restore,
  migration, export, corruption recovery, and full removal are tested.
- No media bytes, credentials, live leases, mutable player state, or per-frame
  DMX/video telemetry enter the graph.
- Stage packages start, stop, blackout, fail black, and roll back with no graph
  process installed.
- Adoption requires measured value over a simpler catalog/query implementation;
  a no-go result preserves deterministic exports, media, and Stage packages.

## Explicit non-goals

- Using Relate as object storage, CDN, media transcoder, or render cache.
- Replicating a writable graph between Studio and Pi.
- Resolving cue order or media file paths with a graph query during a show.
- Letting an agent publish, activate, start, stop, or mutate Stage.
- Replacing immutable JSON manifests with graph-only state.
