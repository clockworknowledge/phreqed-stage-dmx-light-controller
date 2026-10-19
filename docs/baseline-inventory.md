# Reconstructed baseline inventory

The files under `phreqed-stage-dmx-baseline/` were reconstructed from ChatGPT
conversation snippets on October 19, 2026. They are evidence of reported
working behavior, not direct Raspberry Pi exports. Do not edit or import these
scripts: most create sockets at module load and several immediately enter live
transmission loops.

| File | Role | Reported status |
| --- | --- | --- |
| `phreqed_test.py` | Two-zone RGB and Art-Net diagnostic | Worked after stopping OLA |
| `phreqed_map.py` | Sequential 48-zone mapper | Worked on Cube A |
| `phreqed_wave.py` | Psychedelic rainbow wave | Worked on Cube A |
| `phreqed_dual_test.py` | Independent cubes and mirrored rainbow | Worked after A153 correction |
| `phreqed_visuals_v2.py` | Plasma, tunnel, pulse, chase, cross-cube and cube modes | Most complete live baseline; reported likely working |
| `phreqed_sprite.py` | Walking stickman across a virtual 16x6 surface | Experimental and visually unclear |
| `phreqed_smiley.py` | Static cyan smiley on Cube A | Experimental; no confirmed result |

The baseline protocol is a 512-byte ArtDMX payload sent to `127.0.0.1:6454`,
universe 0. It maps Cube A at zero-based offset 0 and Cube B at offset 152. The
package preserves these values through validated, one-based fixture settings.

## Recorded SHA-256 hashes

```text
README.md                         C80AAAACB616774D00F8CC0A2A7B0E3BA78C6B28D57283DC6217DD8D027401EA
docs/RECONSTRUCTION_NOTES.md      EB5CD5338855BEF11716B77F51CC6C2066E076469E9AD70B5FF529AE531443FC
scripts/phreqed_dual_test.py      E6CFF5B75CA70ECE3C3B72E9BBA11A0EEE08060F7C47BC1BEA8BCD971CCDA113
scripts/phreqed_map.py            D302C40C9105B2419078E3F6264BFB73815F1F52DA8E528FE566284067EC0729
scripts/phreqed_smiley.py         09EB411F404F3927D0003E168C7001768F398F8B3126F0D1DC3FCDA23A6A2197
scripts/phreqed_sprite.py         2B4B27354C33986A63A20B0636EE9A35755B89191B9DD2D807CCF0CAB78BC8AA
scripts/phreqed_test.py           240515E431C6262749BDB658CCDFC003FF475FE21696559CFF148A582447C040
scripts/phreqed_visuals_v2.py     4DC252B495F7C92D308B415342BF1C185B0B62131C2BEE8A81B743DB1CB61B73
scripts/phreqed_wave.py           67A7937ACB00CAACDCADE2AA9527019C3B51733A27BFB7F08C1B421AAAA1878B
phreqed-stage-dmx-baseline.zip     54C49013C9EF53634295AD7BD34BBFCFC0A16FF4A4E8E0378F6FB281ECC7B6A4
```
