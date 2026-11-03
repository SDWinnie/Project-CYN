"""window.py - Transparent Always-on-Top Desktop Window for CYN.

Controls:
- Left-click on CYN: Toggle Cyberpunk Chat Terminal
- Left-click + drag: Move CYN anywhere on the Windows desktop
- Right-click: Context menu (Chat, Headpat, Poke, Sleep/Wake, Quit)
- Double left-click: Headpat affection reaction
- Idle timeout (60s): Enters dormant powersave sleep mode
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    from PySide6.QtCore import Qt, QTimer, QPoint, QSize
    from PySide6.QtGui import QMovie, QCursor, QColor
    from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QApplication
except ImportError:
    from PyQt6.QtCore import Qt, QTimer, QPoint, QSize
    from PyQt6.QtGui import QMovie, QCursor, QColor
    from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu, QApplication

from cyn_construct.character.controller import CharacterController, CynState

WINDOW_SIZE = QSize(220, 220)
BLINK_INTERVAL_MS = 6_000
HAPPY_HOLD_MS = 3_000
SLEEP_AFTER_MS = 60_000


class CynWindow(QWidget):
    """
    Borderless, transparent, always-on-top desktop window.
    Renders animated .gif files cleanly using QMovie.
    """

    def __init__(self, controller: CharacterController):
        super().__init__()
        self.controller = controller
        self._drag_start_pos: Optional[QPoint] = None
        self._press_global_pos: Optional[QPoint] = None
        self._chat_window = None
        self._is_sleeping = False

        self._setup_window()
        self._setup_ui()
        self._setup_timers()

        # Connect controller state changes
        self.controller.register_change_callback(self._update_gif)

        # Show initial animated GIF
        self._update_gif(self.controller.current_gif_path())

    def set_chat_window(self, chat_window) -> None:
        """Attach the cyberpunk terminal chat panel."""
        self._chat_window = chat_window

    def _toggle_chat(self) -> None:
        """Show or hide the chat panel when CYN is clicked."""
        if self._chat_window is None:
            return
        if self._chat_window.isVisible():
            self._chat_window.hide()
        else:
            self._chat_window._reposition()
            self._chat_window.show()
            self._chat_window.activateWindow()

    # -------------------------------------------------------------------------
    # Setup Window & UI
    # -------------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFixedSize(WINDOW_SIZE)

        # Position in bottom-right corner of screen
        self._snap_bottom_right()

    def _snap_bottom_right(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = geom.width() - self.width() - 40
            y = geom.height() - self.height() - 50
            self.move(x, y)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # GIF Player Label
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedSize(WINDOW_SIZE)
        layout.addWidget(self.label)

        # QMovie Player
        self.movie = QMovie(self)
        self.movie.setScaledSize(QSize(200, 200))
        self.label.setMovie(self.movie)

    def _setup_timers(self) -> None:
        # Subtle idle tilt timer
        self._tilt_timer = QTimer(self)
        self._tilt_timer.setInterval(BLINK_INTERVAL_MS)
        self._tilt_timer.timeout.connect(self._on_idle_tick)
        self._tilt_timer.start()

        # Inactivity sleep timer
        self._sleep_timer = QTimer(self)
        self._sleep_timer.setInterval(SLEEP_AFTER_MS)
        self._sleep_timer.timeout.connect(self._fall_asleep)
        self._sleep_timer.start()

    # -------------------------------------------------------------------------
    # Animation & State Handling
    # -------------------------------------------------------------------------

    def _update_gif(self, gif_path: str) -> None:
        if not gif_path or not Path(gif_path).is_file():
            return
        self.movie.stop()
        self.movie.setFileName(gif_path)
        self.movie.start()

    def _on_idle_tick(self) -> None:
        if self._is_sleeping:
            return
        if self.controller.current_state() == CynState.IDLE:
            # Brief head tilt in curiosity
            self.controller.set_state(CynState.BLINK)
            QTimer.singleShot(1200, lambda: self.controller.set_state(CynState.IDLE))

    def _fall_asleep(self) -> None:
        if not self._is_sleeping:
            self._is_sleeping = True
            self.controller.set_state(CynState.SLEEPING)

    def _wake_up(self) -> None:
        self._reset_sleep_timer()
        if self._is_sleeping:
            self._is_sleeping = False
            self.controller.set_state(CynState.GLITCH)
            QTimer.singleShot(1000, lambda: self.controller.set_state(CynState.IDLE))
        else:
            self.controller.set_state(CynState.IDLE)

    def _reset_sleep_timer(self) -> None:
        self._sleep_timer.start(SLEEP_AFTER_MS)

    # -------------------------------------------------------------------------
    # Mouse & Drag Interaction
    # -------------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._press_global_pos = event.globalPosition().toPoint()
            self._wake_up()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_start_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
            if self._chat_window and self._chat_window.isVisible():
                self._chat_window._reposition()
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if this was a click rather than a drag
            if self._press_global_pos:
                dist = (event.globalPosition().toPoint() - self._press_global_pos).manhattanLength()
                if dist < 6:
                    self._toggle_chat()
            self._drag_start_pos = None
            self._press_global_pos = None
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Double click = Cranial Headpat / Affection reaction
            self._wake_up()
            self.controller.set_state(CynState.HAPPY)
            QTimer.singleShot(HAPPY_HOLD_MS, lambda: self.controller.set_state(CynState.IDLE))
            event.accept()

    # -------------------------------------------------------------------------
    # Context Menu
    # -------------------------------------------------------------------------

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #08080f;
                color: #c8f0f5;
                border: 1px solid #00e5ff;
                border-radius: 6px;
                padding: 4px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #00e5ff;
                color: #000;
                font-weight: bold;
            }
        """)

        act_chat = menu.addAction("💬 Toggle Terminal Chat")
        menu.addSeparator()
        act_headpat = menu.addAction("✨ Cranial Headpat [Happy]")
        act_glitch = menu.addAction("⚡ Glitch Telemetry [Glitch]")
        act_solver = menu.addAction("⚠️ Absolute Solver X")
        act_sleep = menu.addAction("💤 Sleep Powersave" if not self._is_sleeping else "⚡ Wake Up")
        menu.addSeparator()
        act_snap = menu.addAction("🔄 Snap to Corner")
        act_quit = menu.addAction("✕ Terminate Construct")

        action = menu.exec(QCursor.pos())

        if action == act_chat:
            self._toggle_chat()
        elif action == act_headpat:
            self._wake_up()
            self.controller.set_state(CynState.HAPPY)
            QTimer.singleShot(HAPPY_HOLD_MS, lambda: self.controller.set_state(CynState.IDLE))
        elif action == act_glitch:
            self._wake_up()
            self.controller.set_state(CynState.GLITCH)
            QTimer.singleShot(2000, lambda: self.controller.set_state(CynState.IDLE))
        elif action == act_solver:
            self._wake_up()
            self.controller.set_state(CynState.SOLVER_X)
            QTimer.singleShot(3000, lambda: self.controller.set_state(CynState.IDLE))
        elif action == act_sleep:
            if self._is_sleeping:
                self._wake_up()
            else:
                self._fall_asleep()
        elif action == act_snap:
            self._snap_bottom_right()
            if self._chat_window and self._chat_window.isVisible():
                self._chat_window._reposition()
        elif action == act_quit:
            if self._chat_window:
                self._chat_window.close()
            self.close()
            QApplication.quit()
