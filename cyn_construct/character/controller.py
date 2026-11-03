"""controller.py - Clean 2D Animated GIF Controller for Project CYN.

Plays animated .gif files directly in the desktop pet viewport.
Supports:
- IDLE: cyn-md.gif (Chibi Solver CYN default prototype)
- HAPPY / HEADPAT: cyn_creepy_smile.gif
- BLINK / TILT: cyn_tilt_head.gif
- SLEEPING: cyn_sleep.gif
- GLITCH: cyn_glitch.gif
- SOLVER_X: cyn_solver_x.gif
- INSPECT: cyn_inspect.gif
"""

from __future__ import annotations

import os
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional


class CynState(Enum):
    IDLE = auto()
    HAPPY = auto()
    BLINK = auto()
    SLEEPING = auto()
    GLITCH = auto()
    SOLVER_X = auto()
    INSPECT = auto()


STATE_GIFS = {
    CynState.IDLE: "cyn-md.gif",
    CynState.HAPPY: "cyn_creepy_smile.gif",
    CynState.BLINK: "cyn_tilt_head.gif",
    CynState.SLEEPING: "cyn_sleep.gif",
    CynState.GLITCH: "cyn_glitch.gif",
    CynState.SOLVER_X: "cyn_solver_x.gif",
    CynState.INSPECT: "cyn_inspect.gif",
}

FALLBACK_ORDER = [
    CynState.IDLE,
    CynState.HAPPY,
    CynState.BLINK,
    CynState.SLEEPING,
]


class CharacterController:
    """Manages CYN's animated GIF states and delegates display updates to the window."""

    def __init__(self, assets_dir: str):
        self.assets_dir = Path(assets_dir)
        self._state = CynState.IDLE
        self._on_change: Optional[Callable[[str], None]] = None

    def set_state(self, state: CynState) -> None:
        if state != self._state:
            self._state = state
            if self._on_change:
                self._on_change(self.current_gif_path())

    def set_state_by_name(self, name_or_tag: str) -> None:
        """Parse tag or name like '[state:cyn_glitch.gif]' or 'cyn_glitch.gif'."""
        cleaned = name_or_tag.lower().replace("[state:", "").replace("]", "").strip()
        for st, fname in STATE_GIFS.items():
            if fname.lower() in cleaned or st.name.lower() in cleaned:
                self.set_state(st)
                return
        # Default fallback
        if "sleep" in cleaned:
            self.set_state(CynState.SLEEPING)
        elif "glitch" in cleaned:
            self.set_state(CynState.GLITCH)
        elif "smile" in cleaned:
            self.set_state(CynState.HAPPY)
        elif "tilt" in cleaned:
            self.set_state(CynState.BLINK)
        elif "inspect" in cleaned:
            self.set_state(CynState.INSPECT)
        elif "solver" in cleaned:
            self.set_state(CynState.SOLVER_X)
        else:
            self.set_state(CynState.IDLE)

    def current_state(self) -> CynState:
        return self._state

    def current_gif_path(self) -> str:
        """Returns the absolute file path to the active animated GIF."""
        path = self._resolve_path(self._state)
        if path:
            return path

        for fallback in FALLBACK_ORDER:
            path = self._resolve_path(fallback)
            if path:
                return path

        return ""

    def register_change_callback(self, fn: Callable[[str], None]) -> None:
        self._on_change = fn

    def _resolve_path(self, state: CynState) -> str:
        filename = STATE_GIFS.get(state, "cyn-md.gif")
        full = self.assets_dir / filename
        if full.is_file():
            return str(full)
        # Fallback to cyn_idle.gif if cyn-md.gif missing
        fallback_file = self.assets_dir / "cyn_idle.gif"
        if fallback_file.is_file():
            return str(fallback_file)
        return ""
