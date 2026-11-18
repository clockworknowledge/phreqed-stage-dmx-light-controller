# Relate Studio foundation validation — 2026-11-18

## Scope

This checkpoint validates the first `MEDIA-004` workstation integration. It
does not claim ARM64/Pi acceptance, hosted tenancy, complete DAM schema,
backup/restore, corruption recovery, or bidirectional synchronization.

## Runtime

- Platform: Windows x86-64 development workstation
- Python: 3.12
- Package: `relate-db` 1.0.1 (`cp39-abi3-win_amd64`)
- Wheel SHA-256:
  `cae1e98c41420fac2d910b80ff0a38bfd2ac9cbaa206333eac3fd575e1dceec4`
- Store: durable directory layout
- Durability: Relate default `full`
- Studio dependency: optional extra `studio-graph`

## Reference graph

The ignored local Studio workspace contains two assets and two Storylets:

- Fuse Bomb keyframe concept and its 15-second one-shot marker sheet;
- Heart Zones artwork and its 20-second looping marker sheet.

The resulting graph contains 15 nodes and 14 relationships. Synchronizing the
same projection a second time preserved those counts. The writer flushed and
closed; a new read-only connection recovered the same counts.

The Heart Zones lineage query returned its Storylet and the ordered `pulse-a`,
`pulse-b`, `charge`, `discharge`, and `recover` markers. A bounded 10–30 second
loop query returned the Heart Zones Storylet only.

## Small-reference measurements

These timings include Python interpreter and application startup and therefore
are not engine-only benchmarks:

| Check | Observation |
| --- | ---: |
| Repeated transactional sync | 1,258.81 ms |
| Cold read-only state command | 332.77 ms |
| Durable store size | 9,557 bytes |

They establish a reproducible baseline, not a production sizing conclusion.
Synthetic medium/large graphs and resident-memory measurements remain required.

## Automated and browser evidence

- Relate-focused tests cover idempotent synchronization, full-durability state,
  close/reopen persistence, read-only lineage/discovery, browser-controller
  synchronization, invalid projections, and directory-only store policy.
- The broader Studio catalog and HTTP tests remain green.
- A headed Chromium check successfully opened the Graph workspace, displayed
  the recovered 15/14 store state, invoked **Sync durable Relate**, and received
  the success notice with zero console warnings or errors.
- The complete Windows Python 3.12 repository suite passed all 317 tests.

## Remaining gates

- rights, renditions, placements, reviews, packages, observations, and
  revision-aware Stage change sets;
- delete, retirement, and supersession reconciliation;
- one-writer/live-reader behavior and bounded read-only agent access;
- synthetic sizing, RAM, cold-start, checkpoint, and rebuild measurements;
- backup/restore, migration, killed-writer recovery, corruption, and removal;
- ARM64 installation and coexistence beside the complete Stage soak;
- explicit Studio/Stage event synchronization and conflict handling.
