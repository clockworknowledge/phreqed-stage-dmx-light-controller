# Sprite authoring

The production sprite renderer is in `src/phreqed_dmx/sprites.py`. It operates
on logical top-left coordinates and normalized RGB grids; it has no fixture
addresses, DMX channels, sockets, or transport behavior.

Each fixture has only four RGB rows. Use bold silhouettes, keep every important
feature at least one pixel wide, and prefer motion between distinct poses over
fine detail. A figure can span both fixtures by treating them as one 24-by-4
canvas. The renderer clips pixels safely at the outer edges and fixture seam.

## Define a figure

`#` is an illuminated pixel and any other character is transparent:

```python
from phreqed_dmx.sprites import Sprite, SpriteAnimation

arms_up = Sprite((
    ".#.",
    "###",
    ".#.",
    "#.#",
))
arms_down = Sprite((
    ".#.",
    ".#.",
    "###",
    "#.#",
))
dancer = SpriteAnimation((arms_up, arms_down), frame_seconds=0.2)
```

Animation frames must have identical dimensions. Frame selection depends only
on supplied animation time, so previews and automated tests are repeatable.

## Built-in catalog

- `bird`: two wing positions;
- `stickman`: two walking positions;
- `triangle`, `circle`, and `diamond`: static geometric outlines.

`draw_normalized_sprite` supports integer scaling, horizontal/vertical flips,
palette-selected colours supplied by the effect, placement, and clipping.
`render_cross_fixture_sprite` draws onto a combined left-to-right surface and
returns independent grids for Cube A and Cube B.

The browser Look editor exposes these figures through the `Sprite Parade`
effect. Select a figure, direction, travel rate, animation rate, and spacing,
then save it like any other look. Normal master brightness, contrast, audio
dynamics, blackout, and Art-Net safety boundaries continue to apply.
