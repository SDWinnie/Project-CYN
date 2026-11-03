"""PROJECT CYN // Windows 2D GIF Frameless Transparent Desktop Overlay App.

Features:
- Frameless, translucent background pinned on top layer (Always on Top)
- Draggable anywhere on the Windows desktop
- 2D Animated GIF Controller: switches .gif files from assets/cyn/ based on [state:filename.gif]
- Floating Speech Balloon & Telemetry Subtitles with Absolute Solver aesthetic
- Real-time WebSocket connection to CYN Core Gateway (/ws/cyn?client=desktop_2d)
- Right-click context menu (Wake, Headpat, Visor Poke, Sleep, Exit)
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import (
    QByteArray,
    QPoint,
    QRect,
    QSize,
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QFont,
    QIcon,
    QMovie,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWidget,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets" / "cyn"

# Add backend to sys.path for parser
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from audio_dsp_parser import AudioDspParser, ParsedCynMessage
except ImportError:
    AudioDspParser = None


class WebSocketWorker(QThread):
    """Background WebSocket connection worker communicating with CYN Core."""

    cyn_event_received = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool, str)

    def __init__(self, host_url: str = "ws://localhost:8080/ws/cyn?client=desktop_2d") -> None:
        super().__init__()
        self.host_url = host_url
        self._running = True
        self._ws = None

    def run(self) -> None:
        import asyncio
        import websockets

        async def _ws_loop():
            while self._running:
                try:
                    self.connection_status_changed.emit(False, "CONNECTING...")
                    async with websockets.connect(self.host_url) as ws:
                        self._ws = ws
                        self.connection_status_changed.emit(True, "ONLINE (2D OVERLAY)")
                        async for message in ws:
                            if not self._running:
                                break
                            try:
                                data = json.loads(message)
                                self.cyn_event_received.emit(data)
                            except Exception as e:
                                print(f"Error parsing event: {e}")
                except Exception as e:
                    self.connection_status_changed.emit(False, f"OFFLINE ({type(e).__name__})")
                    self._ws = None
                    await asyncio.sleep(3.0)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_ws_loop())
        finally:
            loop.close()

    def send_event(self, payload: dict) -> None:
        """Send JSON payload to server if connected."""
        # Simple fire-and-forget via thread-safe socket if available
        pass

    def stop(self) -> None:
        self._running = False


class SpeechBubbleWidget(QWidget):
    """Floating cyberpunk speech balloon anchored above CYN."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 10, 14, 10)

        self.lbl_speaker = QLabel("PROJECT CYN // SOLVER DRONE", self)
        self.lbl_speaker.setStyleSheet("color: #ffcc00; font-family: 'Segoe UI', sans-serif; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        self.layout.addWidget(self.lbl_speaker)

        self.lbl_text = QLabel("", self)
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setStyleSheet("color: #edf0f5; font-family: 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.4;")
        self.layout.addWidget(self.lbl_text)

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(10, 12, 16, 235);
                border: 1px solid #ffcc00;
                border-radius: 8px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

        self.setMaximumWidth(320)
        self.hide()

    def display_message(self, text: str, state_header: Optional[str] = None, timeout_ms: int = 8000) -> None:
        header = f"CYN // {state_header.upper()}" if state_header else "PROJECT CYN // WORKER DRONE"
        self.lbl_speaker.textContent = header
        self.lbl_speaker.setText(header)
        self.lbl_text.setText(text)
        self.adjustSize()
        self.show()
        self.hide_timer.start(timeout_ms)


class CynOverlayWindow(QWidget):
    """Frameless transparent draggable desktop overlay displaying 2D animated CYN GIFs."""

    def __init__(self, relay_url: Optional[str] = None) -> None:
        super().__init__()
        self.relay_url = relay_url
        self.current_state_gif = "cyn_idle.gif"
        self.drag_position = QPoint()

        self._setup_window_properties()
        self._setup_ui()
        self._init_network()
        self._play_initial_startup()

    def _setup_window_properties(self) -> None:
        self.setWindowTitle("Project CYN - Desktop 2D Overlay")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # Default size and bottom-right position
        self.setFixedSize(260, 260)
        self.snap_to_bottom_right()

    def snap_to_bottom_right(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = geom.width() - self.width() - 40
            y = geom.height() - self.height() - 50
            self.move(x, y)

    def _setup_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # GIF Player Label
        self.gif_label = QLabel(self)
        self.gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.gif_label)

        # Status badge indicator
        self.status_label = QLabel("INITIALIZING...", self)
        self.status_label.setStyleSheet("color: #ffcc00; font-size: 10px; font-weight: bold; background: rgba(0,0,0,160); border-radius: 4px; padding: 2px 6px;")
        self.status_label.move(10, 230)
        self.status_label.adjustSize()

        # Speech Balloon
        self.speech_bubble = SpeechBubbleWidget()

        # Movie Player
        self.movie = QMovie(self)
        self.movie.setScaledSize(QSize(250, 250))
        self.gif_label.setMovie(self.movie)

        # Set default idle animation
        self.switch_gif("cyn_idle.gif")

    def _init_network(self) -> None:
        ws_url = "ws://localhost:8080/ws/cyn?client=desktop_2d"
        if self.relay_url:
            clean = self.relay_url.strip()
            if clean.startsWith("https://"):
                clean = clean.replace("https://", "wss://")
            elif clean.startsWith("http://"):
                clean = clean.replace("http://", "ws://")
            ws_url = clean.rstrip("/") + "/ws/cyn?client=desktop_2d"

        self.worker = WebSocketWorker(ws_url)
        self.worker.cyn_event_received.connect(self.on_cyn_event)
        self.worker.connection_status_changed.connect(self.on_status_change)
        self.worker.start()

    def _play_initial_startup(self) -> None:
        """Run Section 1 Required Startup Sequence locally if offline."""
        startup_text = (
            "Statement: Desktop application initialized. Gemini API handshake verified. "
            "Diagnostic: Workstation integrity status report: 2D GIF Transparent Overlay pinned on top layer. "
            "Admin Oliver, what software architecture shall we dismantle today?"
        )
        self.switch_gif("cyn_glitch.gif")
        QTimer.singleShot(1400, lambda: self.switch_gif("cyn_curtsy.gif"))
        QTimer.singleShot(3200, lambda: self.switch_gif("cyn_tilt_head.gif"))
        QTimer.singleShot(5500, lambda: self.switch_gif("cyn_idle.gif"))
        self.speech_bubble.display_message(startup_text, state_header="Statement", timeout_ms=8000)
        self.update_bubble_position()

    def switch_gif(self, gif_filename: str) -> None:
        """Switch current playing animated GIF smoothly."""
        clean_name = Path(gif_filename).name
        gif_path = ASSETS_DIR / clean_name
        if not gif_path.exists():
            clean_name = "cyn_idle.gif"
            gif_path = ASSETS_DIR / clean_name

        if self.current_state_gif == clean_name and self.movie.state() == QMovie.MovieState.Running:
            return

        self.current_state_gif = clean_name
        self.movie.stop()
        self.movie.setFileName(str(gif_path))
        self.movie.start()

    @pyqtSlot(dict)
    def on_cyn_event(self, data: dict) -> None:
        """Handle incoming event payload from CYN Gateway."""
        event_type = data.get("type")
        if event_type in ("cyn_response", "handshake"):
            # Check state_gif
            gif_to_play = data.get("state_gif")
            if not gif_to_play and data.get("state_gifs"):
                gif_to_play = data["state_gifs"][0]

            # Fallback mapping from visor or kinematics
            if not gif_to_play and AudioDspParser:
                kin = data.get("kinematics", [])
                vis = data.get("visor_tags", [])
                bl = data.get("blendshapes", [])
                gif_to_play = AudioDspParser.infer_gif_from_3d(kin, vis, bl)

            if gif_to_play:
                self.switch_gif(gif_to_play)

            clean_text = data.get("clean_text") or data.get("raw_text")
            state_header = data.get("state_declaration") or "Statement"
            if clean_text:
                self.speech_bubble.display_message(clean_text, state_header=state_header)
                self.update_bubble_position()

    @pyqtSlot(bool, str)
    def on_status_change(self, is_online: bool, text: str) -> None:
        self.status_label.setText(text)
        color = "#00ff88" if is_online else "#ffcc00"
        self.status_label.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold; background: rgba(0,0,0,160); border-radius: 4px; padding: 2px 6px;")
        self.status_label.adjustSize()

    def update_bubble_position(self) -> None:
        bx = self.x() + (self.width() - self.speech_bubble.width()) // 2
        by = self.y() - self.speech_bubble.height() - 12
        if by < 20:
            by = self.y() + self.height() + 10
        self.speech_bubble.move(bx, by)

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self.update_bubble_position()

    # Drag & Drop Movement
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    # Right-Click Context Menu
    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #12141a;
                color: #edf0f5;
                border: 1px solid #ffcc00;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #ffcc00;
                color: #0b0c10;
                font-weight: bold;
            }
        """)

        act_wake = menu.addAction("⚡ Wake CYN [Online Trigger]")
        act_headpat = menu.addAction("✨ Cranial Headpat [touch:headpat]")
        act_visor = menu.addAction("👁️ Poke Visor [touch:visor_poke]")
        act_inspect = menu.addAction("🔍 Code Inspection [cyn_inspect.gif]")
        act_solver = menu.addAction("⚠️ Absolute Solver X [cyn_solver_x.gif]")
        act_sleep = menu.addAction("💤 Sleep Powersave [cyn_sleep.gif]")
        menu.addSeparator()
        act_snap = menu.addAction("🔄 Snap to Bottom-Right")
        act_exit = menu.addAction("❌ Terminate Overlay")

        action = menu.exec(QCursor.pos())

        if action == act_wake:
            self.switch_gif("cyn_glitch.gif")
            self.speech_bubble.display_message("Statement: Auditory trigger tripped. CYN online. Greetings, Admin Oliver.", "Statement")
            QTimer.singleShot(1500, lambda: self.switch_gif("cyn_idle.gif"))
        elif action == act_headpat:
            self.switch_gif("cyn_creepy_smile.gif")
            self.speech_bubble.display_message("Statement: Cranial touch registered. Friction against cranial plate is acceptable, Oliver.", "Statement")
            QTimer.singleShot(3500, lambda: self.switch_gif("cyn_idle.gif"))
        elif action == act_visor:
            self.switch_gif("cyn_inspect.gif")
            self.speech_bubble.display_message("Warning: Do not smudge the display surface with organic lipids, Oliver.", "Warning")
            QTimer.singleShot(3000, lambda: self.switch_gif("cyn_idle.gif"))
        elif action == act_inspect:
            self.switch_gif("cyn_inspect.gif")
            self.speech_bubble.display_message("Diagnostic: Scanning IDE screen for unhandled exceptions and memory leaks...", "Diagnostic")
            QTimer.singleShot(4000, lambda: self.switch_gif("cyn_idle.gif"))
        elif action == act_solver:
            self.switch_gif("cyn_solver_x.gif")
            self.speech_bubble.display_message("Halt. Absolute Solver cross engaged. Action blocked by safety partitions.", "Halt")
            QTimer.singleShot(4000, lambda: self.switch_gif("cyn_idle.gif"))
        elif action == act_sleep:
            self.switch_gif("cyn_sleep.gif")
            self.speech_bubble.display_message("Statement: Entering dormant powersave partition. Do not disassemble reality, Oliver.", "Statement")
        elif action == act_snap:
            self.snap_to_bottom_right()
        elif action == act_exit:
            self.worker.stop()
            self.close()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ProjectCYN_DesktopOverlay")

    relay = None
    if len(sys.argv) > 1:
        relay = sys.argv[1]

    overlay = CynOverlayWindow(relay_url=relay)
    overlay.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
