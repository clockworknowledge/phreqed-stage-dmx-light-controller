# Reconstruction and next steps

These scripts were reconstructed from code snippets already supplied in the chat. They were not pulled from the Pi or the GitHub repository. The code in the archived snippets is preserved in behavior; comments and formatting have been normalized in some places.

**Confirmed by user:** One-fixture Python animation, zone mapper, rainbow wave, pixel chase, two-fixture independent addressing. User also said v2 "I think this is working". Sprite rendering looked like dispersed rectangles in a photo. The smiley test has not yet been evaluated.

**Important discovery:** OLA `olad` and QLC+ were both bound to Art-Net UDP 6454. Stopping OLA made Python Art-Net work with QLC+.

## Suggested Codex migration

1. Import these source baselines to git without overwriting actual Pi scripts.
2. Compare Pi originals with these snapshots (`diff` or Git diff).
3. Extract transport (`artnet.py`), fixture map (`fixture.py`), pure renderers (`effects/*.py`) and CLI (`app.py`).
4. Build an offline 8x6 per-cube simulator on Windows and unit tests for mappings/payload offsets.
5. Add a proper fixture DMX profile before working with the remaining 8 channels.
6. Give cross-cube sprites a physically-aware layout, not necessarily a contiguous image (cubes are physically separated).
7. Create a proper shutdown/watchdog strategy for live shows.
