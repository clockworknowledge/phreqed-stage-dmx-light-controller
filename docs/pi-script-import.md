# Raspberry Pi source comparison checklist

Reconstructed conversation snapshots are now present under
`phreqed-stage-dmx-baseline/`, but they were not copied directly from the Pi.
Before treating the migration as hardware-authoritative, copy the actual Pi
files into an isolated directory such as `legacy/pi-import/YYYY-MM-DD/` without
editing or overwriting either source set.

Collect:

- all Python scripts and local modules used to launch the show;
- configuration, service files, shell launchers, and environment-variable names;
- the exact Python version and installed package list;
- QLC+ workspace/input/output configuration or screenshots;
- fixture mode and address photos or notes;
- the command used to start each working demonstration;
- sample output or short videos when behavior is hard to infer from code.

Do not collect credentials, unrelated home-directory content, or generated
virtual environments. Record file hashes after copying so the imported baseline
stays identifiable.

Then compare hashes and diffs against the reconstructed baseline. Inventory any
behavioral differences in rainbow, plasma, tunnel, pulse, chase, mirrored,
complementary, independent, cross-cube, stickman, smiley, and shutdown logic.
Add behavioral tests before reconciling those differences in the package.
