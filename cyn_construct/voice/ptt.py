"""ptt.py - Push-to-Talk Hotkey Listener using pynput.
"""

from typing import Callable, Optional

try:
    from pynput import keyboard
except ImportError:
    keyboard = None


class PushToTalk:
    def __init__(self, on_press: Callable[[], None], on_release: Callable[[], None]):
        self._on_press = on_press
        self._on_release = on_release
        self._is_pressed = False
        self._listener = None

    def start(self):
        if not keyboard:
            return
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def _handle_press(self, key):
        if key == keyboard.Key.ctrl_l and not self._is_pressed:
            self._is_pressed = True
            if self._on_press:
                self._on_press()

    def _handle_release(self, key):
        if key == keyboard.Key.ctrl_l and self._is_pressed:
            self._is_pressed = False
            if self._on_release:
                self._on_release()

    def stop(self):
        if self._listener:
            self._listener.stop()
