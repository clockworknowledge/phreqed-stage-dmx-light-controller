# Codex Resume: Raspberry Pi Commissioning

Last updated: 2026-10-20

This is the short operational handoff for a new Codex session. Read
`AGENTS.md`, this file, and `docs/kanban.md` before taking action. The detailed
design remains in `docs/architecture.md`, `docs/effects.md`, and
`docs/raspberry-pi-deployment.md`.

## Objective in progress

Commission the Phase 2 controller on the Raspberry Pi 5 without making live
output automatic. Finish the headless QLC+ service, verify the package and tests
on the Pi, run a 25 FPS soak test, and only then perform a controlled,
low-brightness two-fixture smoke test.

Do not start live Art-Net output merely to inspect the installation.

## Verified repository state

- The Phase 2 engine, simulator, effects, compositor, show-control interfaces,
  tests, documentation, and independent Pi deployment scripts are implemented.
- The Windows validation suite last passed all 57 tests under Python 3.12.
- `scripts/pi-install.sh` creates `.venv`, installs the package, and runs tests.
- `scripts/pi-update.sh` accepts only a clean `main` checkout and a fast-forward
  from `origin/main` before reinstalling and testing.
- The imported baseline directory and ZIP remain immutable.
- The known-good QLC+ workspace is now stored at
  `config/qlc/phreqed_qlc_workspace.qxw`.
- The workspace is valid XML and contains no password, token, API key, private
  path, or web-auth credential fields.
- Its QLC+ configuration records:
  - workspace creator version 4.14.1;
  - universe 0 (`Universe 1`) with passthrough enabled;
  - Art-Net input at `127.0.0.1`, line/universe 0;
  - DMX USB output through `FT232R USB UART (S/N: BH00M7BV)`.

The FTDI serial is a machine-specific device identifier, not an authentication
secret. Keep QLC+ password/authentication files outside Git.

## Verified Raspberry Pi state

- Hostname: `raspberrypi`
- Last observed address: `192.168.1.89` (may change if DHCP changes it)
- User: `mmorley`
- Repository: `/home/mmorley/phreqed-stage-dmx-light-controller`
- SSH access works.
- QLC+ was observed running as:

  ```text
  qlcplus -platform offscreen --nowm --web --operate --open /home/mmorley/.qlcplus/autostart.qxw
  ```

- QLC+ returned HTTP 200 on local TCP port 9999.
- QLC+ owned UDP port 6454 for Art-Net input.
- `/home/mmorley/.qlcplus/autostart.qxw` is the runtime workspace.
- No `qlcplus.service` unit existed when checked; the observed process was not
  managed by systemd.
- The current QLC+ command enables unauthenticated web access. Keep it on a
  trusted private LAN until web authentication or network isolation is added.

## Not yet verified

- A successful `bash scripts/pi-install.sh` run and 57 passing tests on the Pi
  have not been captured in this handoff.
- QLC+ restart and recovery through a systemd service have not been tested.
- The Phase 2 effects have not completed the Raspberry Pi 25 FPS soak test.
- The new controller has not completed a controlled physical-fixture smoke test.
- Shutdown blackout has not yet been observed on the physical fixtures.
- The original source files from the Raspberry Pi have not been imported and
  compared with the preserved reconstructed baseline.
- The eight unverified channels on each fixture remain intentionally unmapped.

## Important Git handoff detail

The QLC+ workspace originated as an untracked file in the Pi checkout and was
copied to the development checkout for review. After the commit containing the
workspace is pushed, the Pi may refuse to pull because its untracked file would
be overwritten. Preserve it outside the repository before pulling:

```bash
cd /home/mmorley/phreqed-stage-dmx-light-controller
mkdir -p /home/mmorley/phreqed-local-backups
mv config/qlc/phreqed_qlc_workspace.qxw \
  /home/mmorley/phreqed-local-backups/phreqed_qlc_workspace-before-git.qxw
git pull --ff-only origin main
cmp config/qlc/phreqed_qlc_workspace.qxw \
  /home/mmorley/phreqed-local-backups/phreqed_qlc_workspace-before-git.qxw
```

`cmp` exits silently with status 0 when the files are identical. Do not delete
the backup until the committed file and runtime configuration are verified.

## Next actions, in order

1. From the development computer, commit and push the reviewed QLC+ workspace,
   this resume file, and the Kanban update.
2. On the Pi, preserve the untracked workspace as shown above, then pull the
   new commit and compare the files.
3. Confirm the runtime workspace still matches the committed master:

   ```bash
   cmp /home/mmorley/phreqed-stage-dmx-light-controller/config/qlc/phreqed_qlc_workspace.qxw \
     /home/mmorley/.qlcplus/autostart.qxw
   ```

4. With QLC+ blackout active, create and test `qlcplus.service` using the exact
   already-working offscreen command. The service must run as `mmorley`, set
   `HOME=/home/mmorley`, and open the runtime workspace, not the Git copy.
5. Run `bash scripts/pi-install.sh` and record the test count and result.
6. Run RPI-002, the simulation-only 25 FPS soak test.
7. Perform LIVE-001 only with QLC+ blackout immediately available, fixtures
   positioned safely, people warned, and brightness initially limited to 0.25.
8. Record results in `docs/phase-2-implementation-report.md` and update the
   corresponding Kanban cards.

## Safety invariants

- Simulation remains the default; live transmission requires the literal
  `live` command.
- Never probe or activate fixture channels 145-152. In the 512-channel universe
  these are 145-152 for Cube A and 297-304 for Cube B.
- Cube A remains at A001 and Cube B at A153, both in 152-channel mode.
- Keep the software brightness ceiling at 0.65 and begin hardware validation at
  0.25 or lower.
- Do not enable automatic startup of `phreqed-dmx live` until the manual smoke
  test and shutdown blackout checks have passed.
- Do not edit, import, execute, or reformat files under
  `phreqed-stage-dmx-baseline/` or its ZIP archive.

## Suggested prompt for a new Codex session

```text
Read AGENTS.md, RESUME.md, and docs/kanban.md completely. Verify git status,
hostname, the active QLC+ process, ports 6454 and 9999, and the Python test
environment before changing anything. Continue the Raspberry Pi commissioning
work from the first incomplete item in RESUME.md. Do not start live Art-Net or
modify the baseline. Preserve the untracked Pi workspace before pulling the
commit that first versions it.
```
