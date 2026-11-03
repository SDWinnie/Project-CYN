"""chat_window.py - Cyberpunk Terminal Chat Window with Live AI Model Selector.

Design:
- Compact cyberpunk terminal anchored beside CYN
- Live AI Model Selector Dropdown:
  * Gemini 2.5 Flash [Cloud - Fast & Smart] (Default)
  * Gemini 2.5 Pro [Cloud - Deep Reasoning]
  * Gemini 2.0 Flash / 1.5 Pro / 1.5 Flash
  * Ollama Local Models (gemma3, llama3.2, mistral, capri, etc.)
- Token-by-token real-time streaming output
- Synchronized 2D GIF state triggers during dialogue
- Monospace Consolas terminal typography
"""

from __future__ import annotations

import re
from typing import Optional

try:
    from PySide6.QtCore import Qt, QTimer, Signal, QObject
    from PySide6.QtGui import QColor, QTextCursor, QFont, QKeyEvent
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout,
        QTextEdit, QLineEdit, QLabel, QPushButton,
        QApplication, QSizePolicy, QFrame, QComboBox,
    )
except ImportError:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal as Signal, QObject
    from PyQt6.QtGui import QColor, QTextCursor, QFont, QKeyEvent
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout,
        QTextEdit, QLineEdit, QLabel, QPushButton,
        QApplication, QSizePolicy, QFrame, QComboBox,
    )

C_BG = "#08080f"
C_BORDER = "#00e5ff"
C_ACCENT = "#ffcc00"
C_CYAN = "#00e5ff"
C_PINK = "#ff2d78"
C_TEXT = "#c8f0f5"
C_DIM = "#253545"
C_GREEN = "#00ff88"
C_USER = "#ffcc00"

FONT_FAMILY = "Consolas, 'Courier New', monospace"
FONT_SIZE = 11

WINDOW_STYLE = f"""
QWidget#ChatPanel {{
    background: {C_BG};
    border: 2px solid {C_BORDER};
    border-radius: 4px;
}}
QScrollBar:vertical {{
    background: {C_BG};
    width: 6px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {C_DIM};
    min-height: 20px;
    border-radius: 3px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""

LOG_STYLE = f"""
QTextEdit {{
    background: {C_BG};
    color: {C_TEXT};
    border: none;
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE}px;
    padding: 10px;
    selection-background-color: {C_DIM};
}}
"""

INPUT_STYLE = f"""
QLineEdit {{
    background: {C_BG};
    color: {C_ACCENT};
    border: none;
    border-top: 1px solid {C_DIM};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE}px;
    padding: 8px 10px;
}}
QLineEdit:focus {{
    border-top: 1px solid {C_CYAN};
}}
"""

COMBO_STYLE = f"""
QComboBox {{
    background: #10141f;
    color: {C_ACCENT};
    border: 1px solid {C_DIM};
    border-radius: 3px;
    padding: 2px 6px;
    font-family: {FONT_FAMILY};
    font-size: 10px;
    font-weight: bold;
    min-width: 140px;
}}
QComboBox:hover {{
    border: 1px solid {C_CYAN};
}}
QComboBox::drop-down {{
    border: none;
    width: 16px;
}}
QComboBox QAbstractItemView {{
    background: #0d1017;
    color: {C_TEXT};
    border: 1px solid {C_CYAN};
    selection-background-color: {C_CYAN};
    selection-color: #000;
    font-family: {FONT_FAMILY};
    font-size: 10px;
    padding: 4px;
}}
"""


class _SignalBridge(QObject):
    append_token = Signal(str)
    append_error = Signal(str)
    set_status = Signal(str, str)
    generation_done = Signal(str)
    set_mic_state = Signal(bool)


class ChatWindow(QWidget):
    """Cyberpunk terminal chat window with live model switcher and streaming generation."""

    def __init__(self, ai_client, character_controller, parent_window, stt=None, tts=None, ptt=None):
        super().__init__()
        self._ai = ai_client
        self._ctrl = character_controller
        self._parent = parent_window
        self._stt = stt
        self._tts = tts
        self._ptt = ptt
        self._generating = False
        self._current_reply_buf = ""
        self._bridge = _SignalBridge()

        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        self._populate_models()
        self._check_connection()

        if self._ptt:
            self._ptt._on_press = self._ptt_pressed
            self._ptt._on_release = self._ptt_released
            self._ptt.start()

    def _setup_window(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setObjectName("ChatPanel")
        self.setStyleSheet(WINDOW_STYLE)
        self.setFixedSize(460, 540)
        self._reposition()

    def _reposition(self):
        if self._parent:
            p = self._parent.pos()
            screen = QApplication.primaryScreen().availableGeometry()
            x = p.x() - self.width() - 14
            if x < 10:
                x = p.x() + self._parent.width() + 14
            y = p.y() - self.height() + self._parent.height()
            y = max(10, min(y, screen.height() - self.height() - 10))
            self.move(x, y)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._make_header())
        root.addWidget(self._make_log())
        root.addWidget(self._make_divider())
        root.addWidget(self._make_input_bar())

    def _make_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        header.setStyleSheet(f"background: {C_BG}; border-bottom: 1px solid {C_DIM};")
        header.setFixedHeight(36)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(6)

        title = QLabel("CYN // TERMINAL")
        title.setStyleSheet(f"color: {C_ACCENT}; font-size: 11px; font-weight: bold; font-family: {FONT_FAMILY};")
        lay.addWidget(title)

        # AI Model Selector Dropdown
        self._model_combo = QComboBox()
        self._model_combo.setStyleSheet(COMBO_STYLE)
        self._model_combo.currentIndexChanged.connect(self._on_model_selected)
        lay.addWidget(self._model_combo)

        lay.addStretch()

        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(f"color: {C_GREEN}; font-size: 13px;")
        lay.addWidget(self._status_dot)

        self._status_label = QLabel("ONLINE")
        self._status_label.setStyleSheet(f"color: {C_CYAN}; font-size: 9px; font-family: {FONT_FAMILY};")
        lay.addWidget(self._status_label)

        # Stop button
        self._stop_btn = QPushButton("■ STOP")
        self._stop_btn.setFixedHeight(18)
        self._stop_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C_PINK};
                border: 1px solid {C_PINK}; font-size: 9px;
                font-family: {FONT_FAMILY}; padding: 0 4px; border-radius: 2px;
            }}
            QPushButton:hover {{ background: {C_PINK}; color: #000; }}
        """)
        self._stop_btn.setVisible(False)
        self._stop_btn.clicked.connect(self._stop_generation)
        lay.addWidget(self._stop_btn)

        # Clear button
        clear_btn = QPushButton("CLR")
        clear_btn.setFixedSize(26, 18)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C_TEXT};
                border: 1px solid {C_DIM}; font-size: 8px;
                font-family: {FONT_FAMILY}; border-radius: 2px;
            }}
            QPushButton:hover {{ border-color: {C_CYAN}; color: {C_CYAN}; }}
        """)
        clear_btn.clicked.connect(self._clear_chat)
        lay.addWidget(clear_btn)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C_TEXT};
                border: none; font-size: 12px; font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{ color: {C_PINK}; }}
        """)
        close_btn.clicked.connect(self.hide)
        lay.addWidget(close_btn)

        return header

    def _make_log(self) -> QTextEdit:
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(LOG_STYLE)
        self._log.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._log.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        hint = " | hold LEFT-CTRL to speak" if self._ptt else ""
        self._append_system(f"PROJECT CYN v1.2 SESSION READY — select model above and enter directive{hint}.")
        return self._log

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {C_DIM}; background: {C_DIM}; max-height: 1px;")
        return line

    def _make_input_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(42)
        bar.setStyleSheet(f"background: {C_BG};")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(6)

        prompt = QLabel(">_")
        prompt.setStyleSheet(f"color: {C_CYAN}; font-family: {FONT_FAMILY}; font-size: 14px; font-weight: bold;")
        self._input = QLineEdit()
        self._input.setStyleSheet(INPUT_STYLE)
        self._input.setPlaceholderText("Enter instructions for CYN (e.g., inspect code, analyze memory, chat)...")
        self._input.returnPressed.connect(self._on_send)

        send_btn = QPushButton("ENTER")
        send_btn.setFixedHeight(24)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: #111a28; color: {C_CYAN};
                border: 1px solid {C_CYAN}; font-size: 9px;
                font-family: {FONT_FAMILY}; font-weight: bold;
                padding: 0 8px; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {C_CYAN}; color: #000; }}
        """)
        send_btn.clicked.connect(self._on_send)

        lay.addWidget(prompt)
        lay.addWidget(self._input)
        lay.addWidget(send_btn)
        return bar

    def _connect_signals(self):
        self._bridge.append_token.connect(self._on_token)
        self._bridge.append_error.connect(self._on_error)
        self._bridge.set_status.connect(self._set_status)
        self._bridge.generation_done.connect(self._on_generation_done)

    # -------------------------------------------------------------------------
    # Model Selection & Connection Logic
    # -------------------------------------------------------------------------

    def _populate_models(self):
        self._model_combo.blockSignals(True)
        self._model_combo.clear()

        available = self._ai.get_available_models()
        active = self._ai.get_current_model()

        selected_idx = 0
        for i, (m_id, label, provider) in enumerate(available):
            self._model_combo.addItem(label, userData=m_id)
            if m_id == active:
                selected_idx = i

        self._model_combo.setCurrentIndex(selected_idx)
        self._model_combo.blockSignals(False)

    def _on_model_selected(self, index: int):
        model_id = self._model_combo.currentData()
        if model_id:
            self._ai.set_model(model_id)
            self._append_system(f"Active Model switched to: [{model_id}]")
            self._check_connection()

    def _check_connection(self):
        online = self._ai.is_connected()
        color = C_GREEN if online else C_PINK
        text = "ONLINE" if online else "KEY REQUIRED"
        self._set_status(color, text)

    def _set_status(self, color: str, text: str):
        self._status_dot.setStyleSheet(f"color: {color}; font-size: 13px;")
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 9px; font-family: {FONT_FAMILY};")

    # -------------------------------------------------------------------------
    # Chat Transmission & Streaming
    # -------------------------------------------------------------------------

    def _on_send(self):
        text = self._input.text().strip()
        if not text or self._generating:
            return

        self._input.clear()
        self._append_user(text)

        self._generating = True
        self._stop_btn.setVisible(True)
        self._set_status(C_ACCENT, "THINKING...")
        self._ctrl.set_state_by_name("cyn_inspect.gif")

        # Start assistant line in log
        self._log.append(f"<span style='color: {C_CYAN}; font-weight: bold;'>CYN:</span> ")
        self._current_reply_buf = ""

        # Stream call
        self._ai.send(
            user_message=text,
            on_token=lambda tok: self._bridge.append_token.emit(tok),
            on_done=lambda full: self._bridge.generation_done.emit(full),
            on_error=lambda err: self._bridge.append_error.emit(err),
        )

    def _on_token(self, token: str):
        self._current_reply_buf += token
        cursor = self._log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self._log.setTextCursor(cursor)
        self._log.ensureCursorVisible()

        # Check for state tags in text
        if "[state:" in token or "[state:" in self._current_reply_buf:
            m = re.findall(r"\[state:([^\]]+)\]", self._current_reply_buf)
            if m:
                self._ctrl.set_state_by_name(m[-1])

    def _on_generation_done(self, full_text: str):
        self._generating = False
        self._stop_btn.setVisible(False)
        self._check_connection()

        # Check final GIF state tag or return to idle
        m = re.findall(r"\[state:([^\]]+)\]", full_text)
        if m:
            self._ctrl.set_state_by_name(m[-1])
        else:
            self._ctrl.set_state_by_name("cyn-md.gif")

        self._log.append("")

    def _on_error(self, err_msg: str):
        self._generating = False
        self._stop_btn.setVisible(False)
        self._set_status(C_PINK, "ERROR")
        self._log.append(f"<span style='color: {C_PINK};'>{err_msg}</span>")
        self._ctrl.set_state_by_name("cyn_glitch.gif")
        QTimer.singleShot(2500, lambda: self._ctrl.set_state_by_name("cyn-md.gif"))

    def _stop_generation(self):
        self._generating = False
        self._stop_btn.setVisible(False)
        self._append_system("Generation halted by user.")
        self._ctrl.set_state_by_name("cyn-md.gif")
        self._check_connection()

    def _clear_chat(self):
        self._ai.clear_history()
        self._log.clear()
        self._append_system("Session memory purged. Ready for directives.")

    # -------------------------------------------------------------------------
    # Formatting Helpers
    # -------------------------------------------------------------------------

    def _append_user(self, text: str):
        self._log.append(f"<span style='color: {C_USER}; font-weight: bold;'>&gt; Oliver:</span> {text}")

    def _append_system(self, text: str):
        self._log.append(f"<span style='color: #4da6ff;'>// {text}</span>")

    # -------------------------------------------------------------------------
    # Voice / PTT Handlers
    # -------------------------------------------------------------------------

    def _ptt_pressed(self):
        if self._stt:
            self._set_status(C_PINK, "LISTENING (MIC)")
            self._ctrl.set_state_by_name("cyn_inspect.gif")

    def _ptt_released(self):
        if self._stt:
            self._set_status(C_CYAN, "PROCESSING AUDIO...")
