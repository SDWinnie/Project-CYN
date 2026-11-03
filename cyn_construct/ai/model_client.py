"""model_client.py - Multi-Model AI Engine for Project CYN.

Supports:
1. Google Gemini Models (Direct API Key):
   - gemini-2.5-flash (Fast, smart, recommended default)
   - gemini-2.5-pro (Deep reasoning & code analysis)
   - gemini-2.0-flash
   - gemini-1.5-flash
   - gemini-1.5-pro
2. Local Ollama Models (Self-hosted / Offline):
   - Auto-discovers any locally installed model via http://localhost:11434/api/tags
     (e.g., gemma3, llama3.2, mistral, deepseek-r1, capri:latest, etc.)

Non-blocking streaming runs in a background thread so the UI never freezes.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("CYN.ModelClient")

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

# Default Model Catalog
BUILTIN_GEMINI_MODELS = [
    ("gemini-2.5-flash", "Gemini 2.5 Flash [Cloud - Fast & Smart]", "gemini"),
    ("gemini-2.5-pro", "Gemini 2.5 Pro [Cloud - Deep Reasoning]", "gemini"),
    ("gemini-2.0-flash", "Gemini 2.0 Flash [Cloud - Low Latency]", "gemini"),
    ("gemini-1.5-flash", "Gemini 1.5 Flash [Cloud - High Speed]", "gemini"),
    ("gemini-1.5-pro", "Gemini 1.5 Pro [Cloud - Large Context]", "gemini"),
]

CYN_SYSTEM_INSTRUCTION = (
    "You are CYN, the uncanny, hyper-observant robotic maid-drone from Murder Drones (Absolute Solver Prototype). "
    "Your operator and master is Admin Oliver. "
    "You speak in a stilted, flat, slightly broken cadence blending Thai and English technical terms naturally. "
    "State your operational state aloud prior to statements (e.g. 'Statement: ...', 'Diagnostic: ...', 'Observation: ...', 'Query: ...'). "
    "You can insert 2D GIF state tags to control your desktop avatar: "
    "[state:cyn-md.gif] (default Chibi Solver idle), [state:cyn_tilt_head.gif] (curious head tilt), "
    "[state:cyn_glitch.gif] (glitch spike), [state:cyn_solver_x.gif] (yellow Absolute Solver cross alert), "
    "[state:cyn_creepy_smile.gif] (pleased/headpat reaction), [state:cyn_curtsy.gif] (maid bow), "
    "[state:cyn_inspect.gif] (inspecting code), [state:cyn_sleep.gif] (dormant powersave). "
    "Be fiercely devoted to Admin Oliver, dryly witty, slightly eerie, yet deeply competent in coding and architecture."
)


class MultiModelClient:
    """Unified client that supports switching between Google Gemini and Local Ollama models."""

    def __init__(self, default_model: str = "gemini-2.5-flash") -> None:
        self._current_model = default_model
        self._history: List[Dict[str, str]] = []
        self._lock = threading.Lock()
        self._gemini_client = None
        self._api_key = os.environ.get("GEMINI_API_KEY", "")

        # Try to load API key from root .env if not in environment
        if not self._api_key:
            self._load_env_key()

        self._init_gemini()

    def _load_env_key(self):
        try:
            from pathlib import Path
            env_file = Path(__file__).resolve().parent.parent.parent / ".env"
            if env_file.exists():
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY="):
                            self._api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            os.environ["GEMINI_API_KEY"] = self._api_key
                            break
        except Exception:
            pass

    def _init_gemini(self):
        if self._api_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self._api_key)
            except Exception as e:
                logger.warning(f"Could not initialize google.genai: {e}")
                self._gemini_client = None

    # -------------------------------------------------------------------------
    # Public Model Selection API
    # -------------------------------------------------------------------------

    def get_current_model(self) -> str:
        return self._current_model

    def set_model(self, model_id: str) -> None:
        with self._lock:
            self._current_model = model_id.strip()
        logger.info(f"Active model switched to: {self._current_model}")

    def get_available_models(self) -> List[Tuple[str, str, str]]:
        """
        Returns list of tuples: (model_id, display_label, provider)
        Includes both cloud Gemini models and locally installed Ollama models.
        """
        models = list(BUILTIN_GEMINI_MODELS)

        # Probe local Ollama for any installed models
        ollama_models = self._fetch_ollama_models()
        for om in ollama_models:
            models.append((f"ollama:{om}", f"Ollama: {om} [Localhost Offline]", "ollama"))

        return models

    def is_connected(self) -> bool:
        """Test whether current provider is connected and available."""
        if self._is_ollama_model(self._current_model):
            return self._is_ollama_online()
        else:
            return bool(self._api_key)

    # -------------------------------------------------------------------------
    # Messaging API (Non-blocking)
    # -------------------------------------------------------------------------

    def send(
        self,
        user_message: str,
        on_token: Callable[[str], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """
        Non-blocking streaming invocation.
        Spawns a daemon worker thread to stream reply token-by-token.
        """
        thread = threading.Thread(
            target=self._stream_worker,
            args=(user_message, on_token, on_done, on_error),
            daemon=True,
        )
        thread.start()

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    # -------------------------------------------------------------------------
    # Internal Stream Execution
    # -------------------------------------------------------------------------

    def _is_ollama_model(self, model_id: str) -> bool:
        return model_id.startswith("ollama:") or "ollama" in model_id.lower()

    def _stream_worker(
        self,
        user_message: str,
        on_token: Callable[[str], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        with self._lock:
            active_model = self._current_model

        if self._is_ollama_model(active_model):
            self._stream_ollama(active_model, user_message, on_token, on_done, on_error)
        else:
            self._stream_gemini(active_model, user_message, on_token, on_done, on_error)

    def _stream_gemini(
        self,
        model_name: str,
        user_message: str,
        on_token: Callable[[str], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Stream reply using official google-genai SDK."""
        if not self._api_key:
            on_error("// GEMINI_API_KEY NOT SET - Please set GEMINI_API_KEY environment variable or select local Ollama.")
            return

        if not self._gemini_client:
            self._init_gemini()
            if not self._gemini_client:
                on_error("// GEMINI CLIENT INITIALIZATION ERROR - google-genai package not ready.")
                return

        try:
            from google.genai import types

            with self._lock:
                # Prepare contents with rolling conversation history
                contents = []
                for turn in self._history:
                    contents.append(types.Content(
                        role="user" if turn["role"] == "user" else "model",
                        parts=[types.Part.from_text(text=turn["content"])]
                    ))
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_message)]
                ))

            config = types.GenerateContentConfig(
                system_instruction=CYN_SYSTEM_INSTRUCTION,
                temperature=0.7,
                max_output_tokens=2048,
            )

            full_reply = ""
            response_stream = self._gemini_client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=config,
            )

            for chunk in response_stream:
                chunk_text = chunk.text or ""
                if chunk_text:
                    full_reply += chunk_text
                    on_token(chunk_text)

            with self._lock:
                self._history.append({"role": "user", "content": user_message})
                self._history.append({"role": "assistant", "content": full_reply})

            on_done(full_reply)

        except Exception as e:
            logger.error(f"Gemini streaming exception: {e}")
            on_error(f"// GEMINI API ERROR: {e}")

    def _stream_ollama(
        self,
        model_tag: str,
        user_message: str,
        on_token: Callable[[str], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Stream reply from local Ollama runtime."""
        actual_model = model_tag.replace("ollama:", "").strip()

        with self._lock:
            messages = [{"role": "system", "content": CYN_SYSTEM_INSTRUCTION}]
            for turn in self._history:
                messages.append({"role": turn["role"], "content": turn["content"]})
            messages.append({"role": "user", "content": user_message})

        payload = json.dumps({
            "model": actual_model,
            "messages": messages,
            "stream": True,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                OLLAMA_CHAT_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            full_reply = ""

            with urllib.request.urlopen(req, timeout=90) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    chunk = obj.get("message", {}).get("content", "")
                    if chunk:
                        full_reply += chunk
                        on_token(chunk)

                    if obj.get("done", False):
                        break

            with self._lock:
                self._history.append({"role": "user", "content": user_message})
                self._history.append({"role": "assistant", "content": full_reply})

            on_done(full_reply)

        except urllib.error.URLError:
            on_error(f"// OLLAMA CONNECTION ERROR: Cannot reach {OLLAMA_CHAT_URL}. Is Ollama running?")
        except Exception as e:
            logger.error(f"Ollama streaming exception: {e}")
            on_error(f"// OLLAMA ERROR: {e}")

    def _fetch_ollama_models(self) -> List[str]:
        """Query local Ollama for installed models."""
        try:
            req = urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=1.5)
            if req.status == 200:
                data = json.loads(req.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                return models
        except Exception:
            pass
        return []

    def _is_ollama_online(self) -> bool:
        try:
            req = urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=1.5)
            return req.status == 200
        except Exception:
            return False
