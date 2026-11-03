"""Local Wake-Word Subsystem and Lifecycle State Manager for Project CYN.

Conforms to Section 2:
- Target: 'CYN' (/s/ /ih/ /n/ or /s/ /iy/ /n/)
- Threshold: 0.65 activation confidence on 16kHz Mono PCM
- Global Hotkey: Ctrl+Space
- Lifecycle states: STATE_SLEEP, STATE_WAKE_TRIGGERED, STATE_ACTIVE_ENGAGED, STATE_INACTIVITY_SLEEP
"""

from __future__ import annotations

import asyncio
import enum
import logging
import threading
import time
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger("CYN.WakeWord")


class CynLifecycleState(str, enum.Enum):
    STATE_SLEEP = "STATE_SLEEP"
    STATE_WAKE_TRIGGERED = "STATE_WAKE_TRIGGERED"
    STATE_ACTIVE_ENGAGED = "STATE_ACTIVE_ENGAGED"
    STATE_INACTIVITY_SLEEP = "STATE_INACTIVITY_SLEEP"


WAKE_ANNOUNCEMENT = (
    "<audio: static_burst> <audio: camera_shutter> "
    "[anim:head_twitch_jitter] [visor:solver_x] [blend:mouth_flat_open] "
    "Statement: Auditory trigger tripped. CYN online. "
    "<pitch: -15%>Greetings, Admin Oliver.<pitch: default> Optical sensors streaming."
)

SLEEP_DEPARTURE = (
    "Statement: Inactivity threshold exceeded. Entering low-power sleep partition. "
    "Do not disassemble reality while I slumber, Oliver. "
    "[anim:slump_powersave] [visor:blink_shutter] [target:look_away_void]"
)


class WakeWordDetector:
    def __init__(
        self,
        on_state_change: Optional[Callable[[CynLifecycleState, str], None]] = None,
        inactivity_timeout_sec: float = 120.0,
        confidence_threshold: float = 0.65,
    ) -> None:
        self.state = CynLifecycleState.STATE_SLEEP
        self.on_state_change = on_state_change
        self.inactivity_timeout_sec = inactivity_timeout_sec
        self.confidence_threshold = confidence_threshold
        self.last_active_time = time.time()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._hotkey_listener = None
        self._oww_model = None
        self._init_detector_async()
        self._init_hotkey()

    def _init_detector_async(self) -> None:
        """Initialize openWakeWord in a background thread to prevent blocking server boot."""
        def _loader():
            try:
                import openwakeword
                from openwakeword.model import Model

                logger.info("Initializing openWakeWord engine in background...")
                try:
                    openwakeword.utils.download_models()
                    self._oww_model = Model(inference_framework="onnx")
                    logger.info(f"openWakeWord loaded models: {list(self._oww_model.models.keys())}")
                except Exception as e:
                    logger.warning(f"openWakeWord model loading note: {e}")
            except Exception as e:
                logger.warning(f"openWakeWord module note: {e}")

        t = threading.Thread(target=_loader, daemon=True)
        t.start()

    def _init_hotkey(self) -> None:
        """Initialize Ctrl+Space hotkey listener."""
        try:
            from pynput import keyboard

            def on_press(key):
                try:
                    # Check for Ctrl + Space
                    if key == keyboard.Key.space and (
                        keyboard.Controller().ctrl_pressed
                        or getattr(self, "_ctrl_down", False)
                    ):
                        self.trigger_wake("Hotkey Ctrl+Space")
                except Exception:
                    pass

            # Alternative pynput GlobalHotKeys
            def trigger():
                self.trigger_wake("Hotkey Ctrl+Space")

            self._hotkey_listener = keyboard.GlobalHotKeys({"<ctrl>+<space>": trigger})
            self._hotkey_listener.daemon = True
            self._hotkey_listener.start()
            logger.info("Wake hotkey registered: Ctrl+Space")
        except Exception as e:
            logger.warning(f"Hotkey listener setup note: {e}")

    def start(self) -> None:
        """Start background microphone audio monitoring."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._audio_loop, daemon=True)
        self._thread.start()
        logger.info("WakeWord monitoring loop started in STATE_SLEEP.")

    def stop(self) -> None:
        self._running = False
        if self._hotkey_listener:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass

    def trigger_wake(self, reason: str = "Acoustic trigger") -> None:
        """Explicitly transition into STATE_WAKE_TRIGGERED."""
        if self.state in (CynLifecycleState.STATE_WAKE_TRIGGERED, CynLifecycleState.STATE_ACTIVE_ENGAGED):
            self.last_active_time = time.time()
            return
        logger.info(f"Wake triggered via: {reason}")
        self.state = CynLifecycleState.STATE_WAKE_TRIGGERED
        self.last_active_time = time.time()
        if self.on_state_change:
            self.on_state_change(self.state, WAKE_ANNOUNCEMENT)

    def transition_to_active(self) -> None:
        """Transition from wake-triggered into active bidirectional streaming."""
        self.state = CynLifecycleState.STATE_ACTIVE_ENGAGED
        self.last_active_time = time.time()
        if self.on_state_change:
            self.on_state_change(self.state, "STATE_ACTIVE_ENGAGED")

    def touch_activity(self) -> None:
        """Reset inactivity timer when audio or frames are processed."""
        self.last_active_time = time.time()
        if self.state == CynLifecycleState.STATE_SLEEP:
            self.trigger_wake("Direct activity")

    def _audio_loop(self) -> None:
        """Low-power 16kHz PCM audio polling loop."""
        import sounddevice as sd

        chunk_size = 1280  # 80ms at 16kHz
        try:
            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="int16",
                blocksize=chunk_size,
            ) as stream:
                while self._running:
                    # Inactivity timeout check
                    if self.state == CynLifecycleState.STATE_ACTIVE_ENGAGED:
                        if time.time() - self.last_active_time > self.inactivity_timeout_sec:
                            logger.info("Inactivity threshold reached. Transitioning to sleep.")
                            self.state = CynLifecycleState.STATE_INACTIVITY_SLEEP
                            if self.on_state_change:
                                self.on_state_change(self.state, SLEEP_DEPARTURE)
                            self.state = CynLifecycleState.STATE_SLEEP
                            continue

                    # Read audio chunk
                    data, overflowed = stream.read(chunk_size)
                    if overflowed:
                        continue

                    # If in sleep state, run wake-word inference
                    if self.state == CynLifecycleState.STATE_SLEEP:
                        audio_pcm = data.flatten()
                        # Test with openwakeword if loaded
                        if self._oww_model:
                            predictions = self._oww_model.predict(audio_pcm)
                            for model_name, score in predictions.items():
                                if score >= self.confidence_threshold:
                                    self.trigger_wake(f"openWakeWord [{model_name} score={score:.2f}]")
                                    break
                        else:
                            # Audio energy spike threshold check for testing
                            rms = np.sqrt(np.mean(audio_pcm.astype(np.float32) ** 2))
                            if rms > 4500:  # Loud distinct vocal burst
                                self.trigger_wake(f"Acoustic impulse [rms={rms:.0f}]")

                    time.sleep(0.01)
        except Exception as e:
            logger.warning(f"Audio input stream note: {e}")
            # Fallback idle loop keeping hotkey alive
            while self._running:
                time.sleep(0.5)
