# Phreqed Studio + Relate reference story

Date: 2026-11-18
Status: executable local foundation; Relate evaluation next

## The story

Phreqed is building a show-authoring system in which lighting, short-form video,
projection surfaces, songs, performers, and reusable visual Storylets become
one connected creative language. A designer should be able to ask:

> Find a reviewed 15-second visual that can move energy from the left lighting
> cube onto the portrait screen, expose an impact marker, fit the current song
> section, respect our rights and projection constraints, and finish black.

A useful answer is not only a file search. It crosses source provenance,
derived clips, semantic markers, lighting recipes, projection renditions, song
sections, prior placements, approvals, performance observations, rights, and
the exact Stage packages that contain them. This connected context is the case
for a graph.

## Why Relate

Relate gives the project an embedded Cypher relationship layer without making
the Stage controller depend on a separate database server. The intended use is
digital-asset lineage, semantic discovery, impact analysis, approval memory,
and evidence for AI-assisted proposals.

Relate is deliberately not the media store or the live sequencer. Original and
derived bytes are content-addressed outside the graph. Relate may own the
authoritative graph-native Studio metadata and creative history, protected by
durable backups, exports, and migrations. Immutable published package manifests
remain the authoritative Stage execution contract.

This separation creates a strong operational result: a Relate failure may pause
Studio metadata work until recovery, but it cannot delete content-addressed
media, change an active published show, interrupt playback, or prevent blackout.

## The onboard director

The proposed onboard director is a bounded recommendation and operational-
memory service, not an autonomous show operator. Its separate device-local
Relate store may:

- discover compatible Storylets, fills, lighting recipes, and projection
  renditions;
- explain a proposal using stable IDs, revisions, approvals, and rehearsal
  evidence;
- identify missing media, rights, capabilities, or unreviewed dependencies;
- compare a local Stage adjustment with the published show and prepare a change
  set for Studio review.
- record offline setlist changes, performer notes, rehearsal observations, and
  bounded adjustments as revisioned events for later Studio synchronization.

It cannot publish, activate, start, stop, blackout, arm whites, raise output
ceilings, access media bytes, or resolve a cue during playback. Stage executes
precompiled ordered arrays from one song clock with no graph query in the
25 FPS path.

## Reference demonstration

The executable local Studio foundation already provides the first graph-shaped
dataset:

1. **Fuse Bomb** — source concept, 15-second Storylet, reveal/ignite/impact/
   decay/black markers, and the future cube-to-screen-to-cube lighting recipe.
2. **Heart Zones** — source-preserved band artwork, 20-second looping Storylet,
   pulse/charge/discharge/recovery markers, and future electrical-pulse light
   synchronization.
3. **Travelling on a Floating Rock** — the next complete chain from owned
   source and VFX fragments through a sparse Video EDL, song placements,
   lighting cues, rendition, published package, and Pi observations.

The first local projection contains 15 nodes and 14 relationships. The Relate
sprint will ingest it with idempotent parameterized Cypher, then expand it to
the Travelling source-to-package chain.

## Demo questions

The reference graph should answer:

- Which source, markers, lighting recipe, rendition, placement, and package
  produced this moment in the show?
- What active packages are affected if a source, rights record, crop, or
  renderer revision changes?
- Which approved Storylets fit a portrait screen, a 10–20 second gap, a high-
  energy section, and a black ending?
- Which proposals were rejected for this song section, and what evidence was
  recorded?
- Which local Stage adjustments should return to Studio, and do they conflict
  with a newer revision?

Every answer returns stable IDs and revisions that open the corresponding
Studio records. Published packages retain everything required to reproduce a
show without contacting either graph.

## Evidence required before adoption

The `MEDIA-004` evaluation will pin and hash one Relate release; verify its
license, telemetry, installation, and interfaces; measure import, query,
checkpoint, cold-start, memory, and store growth; prove one-writer behavior,
backup/restore, migration, corruption recovery, deterministic rebuild, and
full removal; and test a strictly bounded ARM64 device store only if the
workstation results justify it.

The success claim is therefore measurable: Relate must make connected asset
discovery, provenance, impact analysis, and explainable agent proposals
materially improve connected authoring and device memory without becoming a
show-critical dependency.
