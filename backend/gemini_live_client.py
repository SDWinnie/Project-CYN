"""Gemini Multimodal Live API Client for Project CYN.

Uses official google-genai SDK (v2.33+) with the 'gemini-3.8-live' WebSocket model.
Streams bidirectional 16kHz PCM audio & JPEG camera frames,
and parses incoming audio + output transcription into real-time CYN kinematics tags.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import AsyncGenerator, Callable, Optional

from cyn_prompt import CYN_SYSTEM_PROMPT
from audio_dsp_parser import AudioDspParser, ParsedCynMessage

logger = logging.getLogger("CYN.GeminiLive")


class GeminiLiveBridge:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3.8-live",
        on_cyn_event: Optional[Callable[[ParsedCynMessage, Optional[bytes]], None]] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name
        self.on_cyn_event = on_cyn_event
        self._session = None
        self._client = None
        self._is_connected = False
        self._receive_task: Optional[asyncio.Task] = None
        self._audio_buffer: bytearray = bytearray()
        self._text_accumulator: str = ""

    async def connect(self) -> bool:
        """Establish WebSocket connection with Gemini Live API."""
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Operating in local simulated/offline mode.")
            self._is_connected = False
            return False

        try:
            from google import genai
            from google.genai import types

            self._client = genai.Client(api_key=self.api_key)

            config = types.LiveConnectConfig(
                response_modalities=[types.Modality.AUDIO],
                system_instruction=types.Content(
                    parts=[types.Part(text=CYN_SYSTEM_PROMPT)]
                ),
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore"
                        )
                    )
                ),
            )

            logger.info(f"Connecting to Gemini Live API [{self.model_name}]...")
            self._session_context = self._client.aio.live.connect(model=self.model_name, config=config)
            self._session = await self._session_context.__aenter__()
            self._is_connected = True
            logger.info("Gemini Live API WebSocket session active.")

            # Start background receive task
            self._receive_task = asyncio.create_task(self._receive_loop())
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Gemini Live API: {e}", exc_info=True)
            self._is_connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect active session."""
        self._is_connected = False
        if self._receive_task:
            self._receive_task.cancel()
        if self._session and hasattr(self, "_session_context"):
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass
        self._session = None
        logger.info("Gemini Live session disconnected.")

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Send 16kHz 16-bit Mono PCM audio chunk to Live API."""
        if not self._is_connected or not self._session:
            return
        try:
            from google.genai import types

            await self._session.send_realtime_input(
                audio=types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000")
            )
        except Exception as e:
            logger.warning(f"Error sending audio: {e}")

    async def send_video_frame(self, jpeg_bytes: bytes) -> None:
        """Send JPEG encoded optical snapshot/video frame (1 FPS) to Live API."""
        if not self._is_connected or not self._session:
            return
        try:
            from google.genai import types

            await self._session.send_realtime_input(
                video=types.Blob(data=jpeg_bytes, mime_type="image/jpeg")
            )
        except Exception as e:
            logger.warning(f"Error sending video frame: {e}")

    async def send_text_prompt(self, text: str) -> None:
        """Send text injection or user chat turn."""
        if not self._is_connected or not self._session:
            # Fallback local echo/offline response for testing
            self._handle_offline_response(text)
            return
        try:
            await self._session.send_realtime_input(text=text)
        except Exception as e:
            logger.error(f"Error sending text input: {e}")

    async def _receive_loop(self) -> None:
        """Receive loop processing incoming audio chunks and output transcription."""
        try:
            async for response in self._session.receive():
                content = response.server_content
                if not content:
                    continue

                # Check for interruption
                if content.interrupted:
                    logger.info("Model generation interrupted by user voice.")
                    self._text_accumulator = ""
                    self._audio_buffer.clear()
                    if self.on_cyn_event:
                        # Send interrupt signal to client
                        parsed = AudioDspParser.parse_message("[anim:idle_sway]")
                        parsed.level_priority = 1
                        self.on_cyn_event(parsed, None)
                    continue

                audio_chunk: Optional[bytes] = None
                # Extract audio parts
                if content.model_turn and content.model_turn.parts:
                    for part in content.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            audio_chunk = part.inline_data.data
                            self._audio_buffer.extend(audio_chunk)
                        if part.text:
                            self._text_accumulator += part.text

                # Extract transcription text if available
                if content.output_transcription and content.output_transcription.text:
                    self._text_accumulator += content.output_transcription.text

                # When a turn completes or accumulates tags, dispatch to avatar
                if content.turn_complete or ("[" in self._text_accumulator and "]" in self._text_accumulator):
                    text_to_dispatch = self._text_accumulator.strip()
                    if text_to_dispatch:
                        parsed = AudioDspParser.parse_message(text_to_dispatch)
                        audio_to_send = bytes(self._audio_buffer) if self._audio_buffer else None
                        self._audio_buffer.clear()
                        if content.turn_complete:
                            self._text_accumulator = ""

                        if self.on_cyn_event:
                            self.on_cyn_event(parsed, audio_to_send)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in Gemini Live receive loop: {e}", exc_info=True)
            self._is_connected = False

    def _handle_offline_response(self, text: str) -> None:
        """Offline / Mock dialogue responder when API key or internet is disconnected."""
        text_lower = text.lower()
        if "sleep" in text_lower or "นอน" in text_lower:
            reply = (
                "[target:look_away_void] [anim:slump_powersave] [visor:blink_shutter] <audio: servo_whirr> "
                "Statement: Voluntary dormancy acknowledged. <pitch: -15%>Do not alter reality while I slumber, Oliver.<pitch: default>"
            )
        elif "bug" in text_lower or "error" in text_lower or "code" in text_lower:
            reply = (
                "[target:look_at_face] [anim:crawl_closer] [visor:squint_suspicious] <audio: camera_shutter> "
                "Diagnostic: Syntax despair detected. [target:look_at_hands] [anim:reach_forward] [visor:solver_x] <audio: static_burst> "
                "Query: Show me the offending line, Oliver. <pitch: -20%>Allow me to consume the stack trace and repair the void.<pitch: default>"
            )
        else:
            reply = (
                f"[target:look_at_face] [anim:head_tilt_45_r] [visor:normal_eyes] <audio: servo_whirr> "
                f"Statement: Input '{text}' parsed into local registers. "
                f"[visor:smile_arcs] [blend:creepy_smile_wide] How may this machine serve you, Admin Oliver?"
            )
        parsed = AudioDspParser.parse_message(reply)
        if self.on_cyn_event:
            self.on_cyn_event(parsed, None)
