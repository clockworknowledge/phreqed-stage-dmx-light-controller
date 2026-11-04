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
