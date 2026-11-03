"""main.py - Desktop Construct Launcher for Project CYN.

Architecture inspired by Capri Desktop Construct:
- Clean 2D Animated GIF Desktop Pet (cyn-md.gif)
- Selectable Multi-Model AI Engine (Gemini 2.5 Flash / Pro, Ollama local models)
- Cyberpunk Terminal Chat Interface anchored to CYN
- Click CYN to open terminal, Left-Ctrl to speak
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    from PyQt6.QtWidgets import QApplication

from cyn_construct.ai.model_client import MultiModelClient
from cyn_construct.character.controller import CharacterController
from cyn_construct.desktop.chat_window import ChatWindow
from cyn_construct.desktop.window import CynWindow
from cyn_construct.voice.ptt import PushToTalk


def get_assets_dir() -> str:
    return str(PROJECT_ROOT / "assets" / "cyn")


def load_voice_components():
    """Optional PTT listener."""
    try:
        ptt = PushToTalk(on_press=lambda: None, on_release=lambda: None)
        return ptt
    except Exception:
        return None


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ProjectCYN_Construct")
    app.setQuitOnLastWindowClosed(False)

    assets_dir = get_assets_dir()
    controller = CharacterController(assets_dir)
    ai_client = MultiModelClient(default_model="gemini-2.5-flash")
    ptt = load_voice_components()

    cyn_win = CynWindow(controller)
    chat_win = ChatWindow(
        ai_client=ai_client,
        character_controller=controller,
        parent_window=cyn_win,
        ptt=ptt,
    )

    cyn_win.set_chat_window(chat_win)
    cyn_win.show()

    print("==========================================================")
    print("PROJECT CYN // DESKTOP CONSTRUCT RUNNING")
    print("Operator: Admin Oliver")
    print(f"Active Model: {ai_client.get_current_model()}")
    print("Click CYN to open terminal chat. Right-click for options.")
    print("Double-click CYN for cranial headpat reaction.")
    print("==========================================================")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
