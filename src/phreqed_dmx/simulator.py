"""Tkinter preview for logical fixture grids. This module has no network output."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import Controller


class TkSimulator:
    def __init__(self, controller: Controller, *, cell_size: int = 52) -> None:
        try:
            import tkinter as tk
        except ImportError as exc:
            raise RuntimeError("Tkinter is required for simulation preview") from exc

        self._controller = controller
        self._root = tk.Tk()
        self._root.title("Phreqed DMX Simulator - no Art-Net output")
        self._started = time.monotonic()
        self._canvases: dict[str, Any] = {}
        self._cells: dict[str, list[int]] = {}

        container = tk.Frame(self._root, padx=12, pady=12)
        container.pack()
        for column, fixture in enumerate(controller.config.fixtures):
            panel = tk.Frame(container, padx=8)
            panel.grid(row=0, column=column)
            tk.Label(panel, text=fixture.name, font=("TkDefaultFont", 12, "bold")).pack()
            canvas = tk.Canvas(
                panel,
                width=fixture.width * cell_size,
                height=fixture.height * cell_size,
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
                            x * cell_size + margin,
                            y * cell_size + margin,
                            (x + 1) * cell_size - margin,
                            (y + 1) * cell_size - margin,
                            fill="#000000",
                            outline="#333333",
                        )
                    )
            self._canvases[fixture.name] = canvas
            self._cells[fixture.name] = cells

        tk.Label(
            self._root,
            text="SIMULATION - Art-Net transmission is disabled",
            foreground="#dddddd",
            background="#222222",
            padx=8,
            pady=5,
        ).pack(fill="x")

    def run(self) -> None:
        self._update()
        self._root.mainloop()

    def _update(self) -> None:
        elapsed = time.monotonic() - self._started
        self._controller.render(elapsed)
        for fixture in self._controller.config.fixtures:
            canvas = self._canvases[fixture.name]
            grid = self._controller.grids[fixture.name]
            colors = (color for row in grid.rows() for color in row)
            for index, color in enumerate(colors):
                canvas.itemconfigure(
                    self._cells[fixture.name][index],
                    fill=f"#{color.red:02x}{color.green:02x}{color.blue:02x}",
                )
        delay_ms = max(1, round(1000 / self._controller.config.fps))
        self._root.after(delay_ms, self._update)
