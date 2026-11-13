# Relate AI memory feasibility spike

Last updated: 2026-11-13

## Decision

Relate is a plausible **optional offline sidecar** for song-analysis evidence,
agent memory, and cue proposals. It is not adopted as a show dependency. The
existing atomic `library.json` and `songs.json` stores remain authoritative,
and only reviewed, explicitly published cue sheets may cross into live-show
data.

The planned Studio/Stage split makes the Studio workstation the preferred first
host. Relate may index library revisions, package manifests, analysis evidence,
and returned Stage adjustment change sets, but it does not replicate Stage
state or perform synchronization. Immutable packages and explicit reviewed
change sets remain the transfer boundary described in
[`studio-stage-roadmap.md`](studio-stage-roadmap.md).

This boundary is architectural, not temporary. Relate holds the complete graph
in RAM, one process owns a writable store, and there is no replication or
cluster failover. Those properties fit one analysis tool on one Pi or
workstation, but not the availability and fail-dark requirements of fixture
control. The current documentation is verified against Relate 1.0.1, so schema
and store migrations must be treated as part of every upgrade.

Sources:

- [Where Relate fits](https://relatedb.ai/docs/concepts/where-relate-fits/)
- [Model agent memory](https://relatedb.ai/docs/guides/agents/model-agent-memory/)

## Proposed graph

| Node | Required identity and role |
| --- | --- |
| `Song` | Existing `song_id`; never stores audio media |
| `AnalysisRun` | Tool/model version, settings, timestamps, input hash, status |
| `Section` | Start/end time, label, confidence, analysis run |
| `Feature` | Tempo, key, dynamics, timbre, onset density, or another measured value |
| `CueProposal` | Proposed look, transition, timestamp, rationale, confidence, status |
| `Evidence` | Source/tool result, content hash, recorded time, provenance |
| `Review` | Operator approval/rejection, note, reviewer, timestamp |
| `Fact` | Agent memory slot with valid/recorded time and optional embedding |

Relationships include `ANALYZES`, `HAS_SECTION`, `MEASURED`, `PROPOSES`,
`SUPPORTED_BY`, `REVIEWS`, `ABOUT`, `FROM`, and `SUPERSEDES`. Corrections close
old facts and proposals rather than deleting evidence. A proposal has no route
to playback until an application-layer review action converts it into a draft
cue sheet; a second existing publish action is still required.

## Process and storage boundary

- Use a directory store so checkpoints are inspectable and backups are simple.
- One controlled analysis service owns the writable store. Agent/MCP recall is
  read-only (`relate serve --mcp stdio --database ... --read-only`) wherever
  possible.
- Run the service outside `phreqed-dmx.service`; it must not be a `Requires`,
  `Wants`, startup condition, health gate, or control lease.
- Set a conservative logical graph size limit and a systemd memory ceiling.
  Stop accepting analysis writes before the graph threatens controller memory.
- Disable telemetry, external model calls, and network listeners by default.
  If embeddings are used, record the model identifier and dimensions with every
  index migration.
- Back up only while the writer is stopped or through a documented consistent
  export/checkpoint procedure. Test restore into a separate path before relying
  on it.
- Export proposals and evidence as versioned JSON so removal of Relate does not
  strand reviewed work.

## Spike protocol and acceptance

The spike remains in Validation until it produces a dated report with all of
the following:

1. Install the published ARM64 artifact on the target Raspberry Pi OS baseline;
   record binary/package hashes, version, installed size, and whether an
   offline installation can be reproduced.
2. Import a synthetic catalog of at least 100 songs, 1,000 sections, 10,000
   features/facts, and 2,000 cue proposals. Record store size, checkpoint time,
   cold-start time, peak RSS, steady RSS, query latency, and write latency.
3. Run the graph beside a socket-blocked 25 FPS show smoke. It passes only if
   the show has no missed frame slots, output changes, lease changes, or
   reserved-channel output and if memory remains inside the Pi budget.
4. Kill the writer during a committed write, restart it, and verify acknowledged
   data, constraints, and supersession links. Corrupt a copy and document the
   actual recovery/export behavior without touching the original.
5. Prove that a second writer is rejected and that MCP agent access exposes
   only read tools. Attempt unknown and write statements through the read-only
   surface.
6. Upgrade one schema version with a reversible migration and export the graph
   to JSON. Rebuild a clean store from that export and compare counts and hashes.
7. Disable or remove the sidecar and run the full controller, authoring,
   setlist, blackout, and restart suites. Every live-show capability must remain
   unchanged.

## Go/no-go gate

Adopt only if ARM64 support, durability, restore, memory headroom, MCP
read-only behavior, schema migration, and removable JSON export all pass. A
failure is a no-go for on-Pi deployment, not a reason to weaken controller
safety. A workstation-only analysis sidecar remains a valid alternative.
