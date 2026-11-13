# Adaptive stage control

Last updated: 2026-11-13

## Delivered software baseline

The browser controller is one adaptive application for the 10.1-inch
Waveshare touchscreen, phones, and desktop browsers. The reference touchscreen
viewport is 1280 x 800 landscape. The shared application has five workspaces:

- **Perform** is the stage-first dashboard. Manual mode keeps scene transport,
  run/hold, tap tempo, quick looks, master brightness, fixture thumbnails,
  output state, health, and blackout in one view. Setlist mode replaces scene
  transport with current/next song, progress, remaining time, and explicit
  start/stop. Selection never starts playback.
- **Setlist** separates Songs/cue-sheet authoring and ordered Setlist editing
  into two full-width touch screens. Neither workflow shares a compressed split
  pane with the other.
- **Build** contains searchable Looks and the focused manual Scene editor.
  Editors are panels or drawers rather than one long stack of unrelated controls.
- **Settings** contains RGB power, contrast, browser-only preview brightness, audio
  response, segmented whites, venue tuning profiles, and the live-output
  boundary. Rehearsal is 25%, Small Stage is 49% (approximately three quarters
  of the persistent safe range), and Large Stage is the full persistent 65%
  range. Atomic user profiles capture the current bounded Settings values.
- **Operations** contains structured health, local display brightness, four
  fixed network actions, recovery status, and confirmed clean shutdown.

Desktop uses split panes, the touchscreen uses a fixed stage dashboard, and
phones use bottom workspace navigation with drill-in content. All show and
authoring capabilities are shared. Only operating-system display and network
mutations are restricted to loopback.

At 1280 x 800 and 100% zoom, automated Chromium inspection records a document
height of 800 pixels, a viewport height of 800 pixels, and equal Perform
workspace scroll/client heights. Perform therefore has no vertical scroll.
The 390 x 844 layout exposes all five workspaces, persistent blackout, and
reachable Build/Settings/Operations controls. Both layouts produced zero browser
console errors in simulation.

## Interaction and accessibility contract

- Primary actions have a minimum 56-pixel touch target; other buttons are at
  least 52 pixels and stage transport is 62 pixels.
- Scrollbars use a 20-pixel touch target, native select controls are avoided for
  frequently used profile selection, and Settings controls are at least 56
  pixels high.
- Every state has text as well as color. The health strip and detailed health
  view report `healthy`, `warning`, `offline`, or `unknown` semantics.
- Keyboard focus is visible. Every action is a button, input, or select; no
  operation depends only on hover, swipe, or long press.
- Blackout is fixed above the application on every viewport. Live output,
  current power profile, lease count, and controller connection remain visible.
- When output is live, leaving Perform opens a deliberate confirmation. This
  is a stage lock, not authentication. Confirming unlocks the requested setup
  workspace while blackout remains available.
- Monitor brightness changes only browser canvas pixels. Local backlight
  brightness is a separate loopback-only operating-system action.

## Control leases and kiosk

The controller holds a registry of named five-second leases rather than a
single browser deadline. Every remote browser renews its own remote lease. A
native `kiosk-supervisor.py` process waits until the loopback controller is
reachable, starts Chromium in kiosk application mode, and renews a local lease
while that Chromium process is alive. Browser timer throttling therefore cannot
pretend that a blanked local display is healthy.

Live output remains active while at least one trusted lease is current. Losing
one phone does not stop output while the kiosk is healthy. Losing every lease
uses the existing fail-dark path: stop the timeline, blackout, close Art-Net,
disarm whites, and reset Show power. The kiosk service is optional, ordered
after the controller, and only wanted by the graphical target. Missing
Chromium, a GUI, or a display cannot delay or stop headless show control.

## Local Operations boundary

`/api/local/state` and `/api/local/action` reject non-loopback callers. Local
operations are absent unless the controller starts with explicit
`live --web --allow-local-operations`. The endpoint accepts only:

- display brightness `20`, `40`, `60`, `80`, or `100`;
- network actions `stage`, `wifi`, `enable-stage`, or `disable-stage`.

There is no command string or shell input. Network changes require typing the
displayed fixed action and are rejected while fixture output or a song timeline
is active. The Python process can request only whitelisted systemd template
units; the polkit rule independently lists every allowed unit and the exact
`start` verb. Those helpers never enable Art-Net. Clean shutdown retains its
separate exact `SHUTDOWN` confirmation and helper.

## Sprint status

1. **UX foundation:** implemented and browser-validated.
2. **Performance dashboard:** implemented; Pi touch/readability validation
   remains.
3. **Trusted kiosk control:** implemented with automated lease tests; Pi
   Chromium crash, blank/wake, and service-order tests remain.
4. **Browser and authoring parity:** implemented and browser-validated.
5. **Settings and local Operations:** implemented; Pi backlight and NetworkManager
   helper validation remains.
6. **Hardware hardening:** not complete. The display must not become
   show-critical until the acceptance run below is recorded.

## Raspberry Pi acceptance run

1. Install with `bash scripts/pi-install-show-service.sh --enable-kiosk` and
   keep `PHREQED_ALLOW_LOCAL_OPERATIONS=0` for the first boot.
2. Confirm QLC+ and `phreqed-dmx.service` reach ready state when no graphical
   session or Chromium is available. Confirm output remains stopped.
3. Enable the kiosk and inspect 1280 x 800 at 100% zoom. Verify touch calibration,
   every 56-pixel primary target, keyboard focus, stage-distance readability,
   and no Perform scroll.
4. With safe live output, connect a phone and the kiosk. Close only the phone;
   output must continue. Crash only Chromium; after the native local lease
   stops, the healthy phone must preserve output. Remove every lease; within
   five seconds the controller must stop the timeline, fail dark, and disarm
   whites.
5. Blank and wake the LCD for longer than the previous suspend interval. QLC+,
   Art-Net, audio, MIDI, the timeline, leases, and 25 FPS output must continue.
   This test also supplies the remaining `OPS-005` evidence.
6. Enable local operations. Verify each backlight level, stage hotspot, saved
   Wi-Fi, boot preference, and loopback continuity while output is stopped.
   Confirm each request is rejected from a phone, for an unknown action, for
   shell-like input, and while output or a timeline is active.
7. Perform the guarded clean shutdown and confirm blackout precedes power loss.
8. Run the complete test suite and readiness checks, then record CPU, memory,
   missed frame slots, temperature, inhibitor release, journal evidence, and
   recovery steps in the show log.

The physical target and backlight commands follow the
[Waveshare RPI-HMI-080D/101D documentation](https://www.waveshare.com/wiki/RPI-HMI-080D-101D).
