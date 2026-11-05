# Setlist Performance Operation

Setlist performance is a deliberate operating mode. It does not enable Art-Net
and does not start a song when the mode, setlist, or song selection changes.
Live fixture output remains a separate explicit **Start live** action.

## Prepare a show

1. In **Songs**, create each song and a cue-sheet revision, preview it in
   simulation, and publish the approved revision.
2. Add the songs to a setlist in performance order.
3. In **Perform**, choose **Setlist performance** and select that setlist.
4. Confirm the displayed song number/title and use **Start Song** only when the
   band is ready.

When a song finishes, the next song becomes the selected armed song. It never
starts automatically. The performer must press Start again. The last song
finishes in the complete state.

## Ampero controls

| Switch | Manual scenes | Setlist performance |
| --- | --- | --- |
| FS1 | Previous scene | Previous song |
| FS2 | Next scene | Next song |
| FS3 | Tap tempo | Start/stop selected song |
| FS4 | Global blackout | Global blackout |

The application owns the setlist position; it is not stored in an Ampero bank.
Avoid adjacent-switch bank changes until the multi-bank safe profile in
`CONTROL-003` has passed its hardware acceptance test.

## Stop and recovery behavior

- **Blackout** stops a running song and blacks out output. Releasing blackout
  does not resume the timeline; Start Song must be pressed again.
- **Stop output**, a lost browser heartbeat, a render failure, or application
  shutdown stops the timeline and requests blackout before closing live output.
- After a browser reconnect, verify the displayed mode and selected song before
  restarting. Do not infer that the previous timeline is still running.
- After a Pi or service restart, the controller starts in Manual mode with no
  active song timeline and live output stopped. Re-select Setlist mode, the
  setlist, and the song, then explicitly start it.
- If the Ampero is missing or disconnects, the browser remains the independent
  previous/next/start-stop/blackout control path. Verify a mapped MIDI event
  after reconnection before relying on the pedal.

Before first live use on a new deployment, validate the complete workflow in
browser simulation, then repeat it on the Pi at low brightness with QLC+
blackout immediately available.

## SHOW-004 Pi acceptance sequence

1. Reboot with fixtures powered but browser live output stopped. Run
   `show-readiness.py --startup-defaults` and confirm Manual/inactive/stopped.
2. In simulation, select a multi-song setlist. Verify previous/next changes the
   armed song, FS3 starts/stops it, completing a song arms but does not start
   the next, and the last song reaches complete.
3. Disconnect and reconnect Ampero USB. Require a newly observed mapped action,
   not just a recreated device node. Repeat after deliberately selecting each
   CONTROL-003 fallback bank.
4. While a song runs in simulation, close all controller tabs or interrupt the
   network until the browser lease expires. Confirm the timeline stops and does
   not resume on reconnect.
5. Restart `phreqed-dmx.service` and repeat the startup-default check. Confirm
   the saved library/setlist remains but runtime position does not resume.
6. With QLC+ blackout immediately available and people warned, repeat one short
   setlist at a conservative RGB ceiling. Verify Stop output and global blackout
   both stop the timeline and request fixture blackout.

SHOW-004 was operator-accepted on the deployed Pi after the full rehearsal and
Setlist-mode check reported on 2026-11-05. Bank-duplication soak remains tracked
separately by CONTROL-003, and private-network/offline-boot checks remain
OPS-003; neither reopens the accepted performance-mode implementation.
