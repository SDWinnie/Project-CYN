"""Windows Background Service & System Tray Companion for Project CYN.

Runs quietly in the Windows system tray as a resident background service:
- Manages CynServer gateway on background thread
- Handles global wake-word ('CYN') and hotkey (Ctrl+Space)
- Provides Windows autostart (Startup Service) registration
- Right-click tray menu for controlling avatar, sleep states, and diagnostics.
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
import webbrowser
import winreg
from pathlib import Path

from PIL import Image, ImageDraw
import pystray

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import CynServer
from audio_dsp_parser import AudioDspParser
from wake_word_detector import CynLifecycleState

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ProjectCYNService"


def create_cyn_tray_icon() -> Image.Image:
    """Procedurally generate an Absolute Solver cross icon for the system tray."""
    img = Image.new("RGBA", (64, 64), (10, 10, 14, 255))
    draw = ImageDraw.Draw(img)

    amber = (255, 204, 0, 255)
    amber_dim = (160, 120, 0, 255)

    # Draw outer border
    draw.rectangle([2, 2, 61, 61], outline=amber_dim, width=2)

    # Draw Absolute Solver cross
    draw.line([14, 14, 49, 49], fill=amber, width=4)
    draw.line([49, 14, 14, 49], fill=amber, width=4)

    # Central pulsing circle
    draw.ellipse([25, 25, 38, 38], outline=amber, width=2)
    return img


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_autostart(enable: bool) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_WRITE) as key:
            if enable:
                cmd = f'"{sys.executable}" "{Path(__file__).resolve()}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Error setting autostart: {e}")
        return False


class CynWindowsService:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.server = CynServer(host=self.host, port=self.port)
        self.loop = asyncio.new_event_loop()
        self.server_thread: threading.Thread | None = None
        self.tray_icon: pystray.Icon | None = None
        self._running = False

    def start_background_server(self) -> None:
        def _run():
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.server.start())

        self.server_thread = threading.Thread(target=_run, daemon=True)
        self.server_thread.start()
        print(f"[CYN Service] Background gateway running on http://localhost:{self.port}")

    def open_hud(self) -> None:
        webbrowser.open(f"http://localhost:{self.port}")

    def wake_cyn(self) -> None:
        self.server.wake_detector.trigger_wake("System Tray Trigger")

    def force_sleep(self) -> None:
        self.server.wake_detector.state = CynLifecycleState.STATE_SLEEP
        parsed = AudioDspParser.parse_message(
            "[anim:slump_powersave] [visor:blink_shutter] [target:look_away_void] "
            "Statement: Manual dormancy forced via host tray service. Goodnight, Oliver."
        )
        asyncio.run_coroutine_threadsafe(
            self.server.broadcast_cyn_event(parsed, None, {"lifecycle_state": "STATE_SLEEP"}),
            self.loop,
        )

    def toggle_autostart(self, icon, item) -> None:
        currently_enabled = is_autostart_enabled()
        set_autostart(not currently_enabled)
        icon.update_menu()

    def exit_service(self, icon, item) -> None:
        print("[CYN Service] Shutting down service...")
        self.server.wake_detector.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self._running = False
        os._exit(0)

    def run(self) -> None:
        self._running = True
        self.start_background_server()

        # Build System Tray Menu
        menu = pystray.Menu(
            pystray.MenuItem("PROJECT CYN v7.0 (Active)", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open 3D Avatar HUD", lambda: self.open_hud(), default=True),
            pystray.MenuItem("Wake CYN (Ctrl+Space)", lambda: self.wake_cyn()),
            pystray.MenuItem("Force Low-Power Sleep", lambda: self.force_sleep()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Run as Windows Startup Service",
                self.toggle_autostart,
                checked=lambda item: is_autostart_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit CYN Service", self.exit_service),
        )

        image = create_cyn_tray_icon()
        self.tray_icon = pystray.Icon(
            "ProjectCYN",
            image,
            "PROJECT CYN - Absolute Solver Companion Service",
            menu=menu,
        )

        print("[CYN Service] System Tray icon active. Minimizing to background.")
        self.tray_icon.run()


if __name__ == "__main__":
    service = CynWindowsService()
    service.run()
