"""Interactive Tkinter preview with no Art-Net or socket dependencies."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .color import NormalizedGrid
from .compositor import Scene
from .effect_library import EFFECT_REGISTRY

if TYPE_CHECKING:
    from .app import Controller


class TkSimulator:
    def __init__(self, controller: Controller, *, cell_size: int = 42) -> None:
        try:
            import tkinter as tk
            from tkinter import filedialog, ttk
        except ImportError as exc:
            raise RuntimeError("Tkinter is required for simulation preview") from exc

        self._tk = tk
        self._ttk = ttk
        self._filedialog = filedialog
        self._controller = controller
        self._cell_size = cell_size
        self._root = tk.Tk()
        self._root.title("Phreqed DMX Simulator - no Art-Net output")
        self._canvases: dict[str, Any] = {}
        self._cells: dict[str, list[int]] = {}
        self._parameter_frames: dict[str, Any] = {}
        self._effect_variables: dict[str, Any] = {}
        self._palette_variables: dict[str, Any] = {}
        self._current_scene: Scene | None = None
        self._animation_time = 0.0
        self._last_clock = time.monotonic()
        self._next_frame_due = self._last_clock
        self._paused = False
        self._suppress_callbacks = False
        self._frame_counter = 0
        self._fps_started = self._last_clock

        self._build_preview()
        self._build_global_controls()
        self._build_fixture_controls()
        tk.Label(
            self._root,
            text=(
                "SIMULATION - Art-Net disabled - RGB zones only; "
                "white strobes unavailable in this build"
            ),
            foreground="#eeeeee",
            background="#202020",
            padx=8,
            pady=5,
        ).pack(fill="x", side="bottom")

    def run(self) -> None:
        self._update()
        self._root.mainloop()

    def _build_preview(self) -> None:
        container = self._ttk.Frame(self._root, padding=10)
        container.pack(fill="x")
        for column, fixture in enumerate(self._controller.config.fixtures):
            panel = self._ttk.Frame(container, padding=5)
            panel.grid(row=0, column=column, sticky="n")
            self._ttk.Label(panel, text=fixture.name, font=("TkDefaultFont", 12, "bold")).pack()
            canvas = self._tk.Canvas(
                panel,
                width=fixture.width * self._cell_size,
                height=fixture.height * self._cell_size,
                background="#111111",
                highlightthickness=0,
            )
            canvas.pack(pady=(6, 0))
            cells: list[int] = []
            for y in range(fixture.height):
                for x in range(fixture.width):
                    margin = 2
                    cells.append(
                        canvas.create_rectangle(
                            x * self._cell_size + margin,
                            y * self._cell_size + margin,
                            (x + 1) * self._cell_size - margin,
                            (y + 1) * self._cell_size - margin,
                            fill="#000000",
                            outline="#333333",
                        )
                    )
            self._canvases[fixture.name] = canvas
            self._cells[fixture.name] = cells

    def _build_global_controls(self) -> None:
        controls = self._ttk.LabelFrame(self._root, text="Performance", padding=8)
        controls.pack(fill="x", padx=12, pady=(0, 6))

        self._ttk.Label(controls, text="Preset").grid(row=0, column=0, sticky="w")
        preset_variable = self._tk.StringVar(value=self._controller.engine.active_preset_id)
        preset = self._ttk.Combobox(
            controls,
            textvariable=preset_variable,
            values=self._controller.engine.preset_order,
            state="readonly",
            width=22,
        )
        preset.grid(row=0, column=1, padx=4)
        preset.bind(
            "<<ComboboxSelected>>",
            lambda event: self._preset_changed(preset_variable.get()),
        )

        self._ttk.Label(controls, text="Speed").grid(row=0, column=2, padx=(12, 0))
        speed = self._tk.Scale(
            controls,
            from_=0.1,
            to=5.0,
            resolution=0.1,
            orient="horizontal",
            length=140,
            command=lambda value: setattr(self._controller, "speed", float(value)),
        )
        speed.set(self._controller.speed)
        speed.grid(row=0, column=3)

        self._ttk.Label(controls, text="Global level").grid(row=0, column=4, padx=(12, 0))
        brightness = self._tk.Scale(
            controls,
            from_=0.0,
            to=self._controller.engine.compositor.maximum_brightness,
            resolution=0.01,
            orient="horizontal",
            length=140,
            command=lambda value: self._controller.engine.set_global_brightness(float(value)),
        )
        brightness.set(self._controller.engine.compositor.global_brightness)
        brightness.grid(row=0, column=5)

        self._pause_button = self._ttk.Button(controls, text="Pause", command=self._toggle_pause)
        self._pause_button.grid(row=1, column=0, pady=(7, 0))
        self._ttk.Button(controls, text="Step", command=self._step).grid(
            row=1, column=1, pady=(7, 0)
        )
        self._ttk.Button(controls, text="Screenshot", command=self._save_screenshot).grid(
            row=1, column=2, pady=(7, 0)
        )
        self._blackout_variable = self._tk.BooleanVar(value=False)
        self._ttk.Checkbutton(
            controls,
            text="Blackout",
            variable=self._blackout_variable,
            command=lambda: self._controller.show.blackout(self._blackout_variable.get()),
        ).grid(row=1, column=3, pady=(7, 0))
        self._fps_label = self._ttk.Label(controls, text="FPS: --")
        self._fps_label.grid(row=1, column=5, sticky="e", pady=(7, 0))

    def _build_fixture_controls(self) -> None:
        container = self._ttk.Frame(self._root, padding=(10, 0, 10, 8))
        container.pack(fill="both", expand=True)
        effect_ids = tuple(metadata.effect_id for metadata in EFFECT_REGISTRY.metadata())
        palette_values = (
            "spectrum", "magma", "ocean", "neon", "ember", "monochrome",
            "matrix",
        )
        for column, fixture in enumerate(self._controller.config.fixtures):
            panel = self._ttk.LabelFrame(container, text=f"{fixture.name} effect", padding=7)
            panel.grid(row=0, column=column, sticky="nsew", padx=4)
            container.columnconfigure(column, weight=1)
            selection = self._controller.engine.fixture_selections[fixture.name]
            effect_variable = self._tk.StringVar(value=selection.effect_id)
            palette_variable = self._tk.StringVar(value="spectrum")
            self._effect_variables[fixture.name] = effect_variable
            self._palette_variables[fixture.name] = palette_variable

            self._ttk.Label(panel, text="Effect").grid(row=0, column=0, sticky="w")
            effect_box = self._ttk.Combobox(
                panel, textvariable=effect_variable, values=effect_ids, state="readonly", width=20
            )
            effect_box.grid(row=0, column=1, sticky="ew")
            effect_box.bind(
                "<<ComboboxSelected>>",
                lambda event, name=fixture.name: self._effect_changed(name),
            )
            self._ttk.Label(panel, text="Palette").grid(row=1, column=0, sticky="w")
            palette_box = self._ttk.Combobox(
                panel,
                textvariable=palette_variable,
                values=palette_values,
                state="readonly",
                width=20,
            )
            palette_box.grid(row=1, column=1, sticky="ew")
            palette_box.bind(
                "<<ComboboxSelected>>",
                lambda event, name=fixture.name: self._palette_changed(name),
            )
            parameter_frame = self._ttk.Frame(panel)
            parameter_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
            self._parameter_frames[fixture.name] = parameter_frame
            self._rebuild_parameters(fixture.name)

    def _effect_changed(self, fixture_name: str) -> None:
        self._controller.begin_transition(self._animation_time)
        effect_id = self._effect_variables[fixture_name].get()
        self._controller.show.select_effect(fixture_name, effect_id)
        self._palette_variables[fixture_name].set("spectrum")
        self._rebuild_parameters(fixture_name)

    def _palette_changed(self, fixture_name: str) -> None:
        self._controller.begin_transition(self._animation_time)
        self._controller.show.update_parameter(
            fixture_name, "palette", self._palette_variables[fixture_name].get()
        )

    def _preset_changed(self, preset_id: str) -> None:
        self._controller.begin_transition(self._animation_time)
        self._controller.show.activate_preset(preset_id)

    def _rebuild_parameters(self, fixture_name: str) -> None:
        frame = self._parameter_frames[fixture_name]
        for child in frame.winfo_children():
            child.destroy()
        effect_id = self._effect_variables[fixture_name].get()
        metadata = EFFECT_REGISTRY.get(effect_id).metadata
        selection = self._controller.engine.fixture_selections[fixture_name]
        values = EFFECT_REGISTRY.parameters(effect_id, selection.parameters)
        numeric_specs = [parameter for parameter in metadata.parameters if not parameter.choices]
        self._suppress_callbacks = True
        try:
            for row, spec in enumerate(numeric_specs):
                self._ttk.Label(frame, text=spec.label).grid(row=row, column=0, sticky="w")
                scale = self._tk.Scale(
                    frame,
                    from_=spec.minimum,
                    to=spec.maximum,
                    resolution=spec.step,
                    orient="horizontal",
                    length=220,
                    command=lambda value, name=fixture_name, key=spec.key: self._parameter_changed(
                        name, key, float(value)
                    ),
                )
                scale.set(values.number(spec.key))
                scale.grid(row=row, column=1, sticky="ew")
        finally:
            self._suppress_callbacks = False

    def _parameter_changed(self, fixture_name: str, key: str, value: float) -> None:
        if self._suppress_callbacks:
            return
        self._controller.show.update_parameter(fixture_name, key, value)

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self._last_clock = time.monotonic()
        self._pause_button.configure(text="Resume" if self._paused else "Pause")

    def _step(self) -> None:
        if not self._paused:
            self._toggle_pause()
        self._animation_time += 1.0 / self._controller.config.fps
        self._draw_current_frame()

    def _save_screenshot(self) -> None:
        if self._current_scene is None:
            return
        filename = self._filedialog.asksaveasfilename(
            title="Export simulator screenshot",
            defaultextension=".ppm",
            filetypes=(("Portable Pixmap", "*.ppm"),),
        )
        if filename:
            export_scene_ppm(self._current_scene, Path(filename))

    def _update(self) -> None:
        now = time.monotonic()
        delta = min(now - self._last_clock, 0.1)
        self._last_clock = now
        if not self._paused:
            self._animation_time += delta
            self._draw_current_frame()
            self._frame_counter += 1
        elapsed = now - self._fps_started
        if elapsed >= 1.0:
            self._fps_label.configure(text=f"FPS: {self._frame_counter / elapsed:.1f}")
            self._frame_counter = 0
            self._fps_started = now
        interval = 1.0 / self._controller.config.fps
        self._next_frame_due += interval
        after_render = time.monotonic()
        while self._next_frame_due <= after_render:
            self._next_frame_due += interval
        delay_ms = max(1, round((self._next_frame_due - after_render) * 1000))
        self._root.after(delay_ms, self._update)

    def _draw_current_frame(self) -> None:
        self._current_scene = self._controller.render_scene(self._animation_time)
        for fixture in self._controller.config.fixtures:
            canvas = self._canvases[fixture.name]
            grid = self._current_scene[fixture.name]
            colors = (color for row in grid.rows() for color in row)
            for index, color in enumerate(colors):
                canvas.itemconfigure(
                    self._cells[fixture.name][index],
                    fill=f"#{round(color.red * 255):02x}{round(color.green * 255):02x}{round(color.blue * 255):02x}",
                )


def export_scene_ppm(
    scene: Scene, path: str | Path, *, pixel_size: int = 24, gap: int = 12
) -> None:
    """Export both fixture previews as a dependency-free binary PPM image."""
    if pixel_size <= 0 or gap < 0:
        raise ValueError("pixel_size must be positive and gap cannot be negative")
    grids = tuple(scene.values())
    if not grids:
        raise ValueError("cannot export an empty scene")
    image_width = sum(grid.width * pixel_size for grid in grids) + gap * (len(grids) - 1)
    image_height = max(grid.height for grid in grids) * pixel_size
    rows = bytearray()
    for image_y in range(image_height):
        grid_y = image_y // pixel_size
        for index, grid in enumerate(grids):
            for image_x in range(grid.width * pixel_size):
                grid_x = image_x // pixel_size
                color = grid[grid_x, min(grid_y, grid.height - 1)]
                rows.extend(
                    (round(color.red * 255), round(color.green * 255), round(color.blue * 255))
                )
            if index < len(grids) - 1:
                rows.extend((0, 0, 0) * gap)
    header = f"P6\n{image_width} {image_height}\n255\n".encode("ascii")
    Path(path).write_bytes(header + rows)
