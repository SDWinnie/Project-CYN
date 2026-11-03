"""Main Backend Server and WebSocket Gateway for Project CYN.

Coordinates:
- aiohttp Web server (serves Three.js Avatar client to PC and Android browsers)
- Real-time WebSocket bridge (/ws/cyn)
- Gemini Multimodal Live API client (gemini-3.8-live)
- Local openWakeWord & hotkey daemon (Ctrl+Space)
- Two-Phase Safety Authorization Gate
- Telemetry Manager (Windows & Android mobile sensors)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Set

from aiohttp import web, WSMsgType

from audio_dsp_parser import AudioDspParser, ParsedCynMessage
from cyn_prompt import CYN_SYSTEM_PROMPT, get_startup_sequence_for_platform, get_prompt_for_platform
from gemini_live_client import GeminiLiveBridge
from system_safety_gate import SafetyGate
from telemetry_receiver import TelemetryManager
from wake_word_detector import CynLifecycleState, WakeWordDetector

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
)
logger = logging.getLogger("CYN.App")

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "web_avatar"


class CynServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.app = web.Application()
        self.ws_clients: Set[web.WebSocketResponse] = set()

        self.safety_gate = SafetyGate()
        self.telemetry = TelemetryManager()
        self.gemini_bridge = GeminiLiveBridge(on_cyn_event=self._on_cyn_model_event)
        self.wake_detector = WakeWordDetector(on_state_change=self._on_wake_state_change)

        self._setup_routes()

    def _setup_routes(self) -> None:
        self.app.router.add_get("/ws/cyn", self.handle_websocket)
        self.app.router.add_get("/api/status", self.handle_status)
        self.app.router.add_post("/api/speak_test", self.handle_speak_test)

        # Serve static web avatar frontend
        if STATIC_DIR.exists():
            self.app.router.add_static("/", path=STATIC_DIR, show_index=True)

    def _on_wake_state_change(self, state: CynLifecycleState, message: str) -> None:
        """Called when wake-word or hotkey changes state."""
        logger.info(f"Wake state changed: {state.value}")
        parsed = AudioDspParser.parse_message(message)
        asyncio.run_coroutine_threadsafe(
            self.broadcast_cyn_event(parsed, None, {"lifecycle_state": state.value}),
            asyncio.get_event_loop(),
        )

    def _on_cyn_model_event(self, parsed: ParsedCynMessage, audio_bytes: bytes | None) -> None:
        """Called when Gemini Live emits response tokens/audio."""
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii") if audio_bytes else None
        asyncio.run_coroutine_threadsafe(
            self.broadcast_cyn_event(parsed, audio_b64),
            asyncio.get_event_loop(),
        )

    async def broadcast_cyn_event(
        self,
        parsed: ParsedCynMessage,
        audio_b64: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast formatted event payload to all connected WebGL avatar clients."""
        visor_index = 0
        if parsed.visor_tags:
            visor_index = AudioDspParser.map_visor_to_index(parsed.visor_tags[0])

        payload = {
            "type": "cyn_response",
            "priority": parsed.level_priority,
            "raw_text": parsed.raw_text,
            "clean_text": parsed.clean_speech_text,
            "state_declaration": parsed.state_declaration,
            "kinematics": parsed.kinematics,
            "visor_tags": parsed.visor_tags,
            "visor_index": visor_index,
            "blendshapes": parsed.blendshapes,
            "targets": parsed.targets,
            "physics_tags": parsed.physics_tags,
            "audio_cues": parsed.audio_cues,
            "pitch_shifts": parsed.pitch_shifts,
            "rate_shifts": parsed.rate_shifts,
            "audio_pcm_b64": audio_b64,
        }
        if extra:
            payload.update(extra)

        msg_str = json.dumps(payload)
        for ws in list(self.ws_clients):
            if not ws.closed:
                try:
                    await ws.send_str(msg_str)
                except Exception as e:
                    logger.warning(f"Error broadcasting to client: {e}")

    async def handle_status(self, request: web.Request) -> web.Response:
        return web.json_response({
            "status": "online",
            "entity": "CYN (Absolute Solver Drone)",
            "master": "Admin Oliver",
            "lifecycle_state": self.wake_detector.state.value,
            "connected_avatar_clients": len(self.ws_clients),
            "gemini_connected": self.gemini_bridge._is_connected,
        })

    async def handle_speak_test(self, request: web.Request) -> web.Response:
        """Endpoint to test arbitrary CYN dialogue strings."""
        data = await request.json()
        text = data.get("text", "")
        parsed = AudioDspParser.parse_message(text)
        await self.broadcast_cyn_event(parsed)
        return web.json_response({"status": "dispatched", "parsed": parsed.__dict__})

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws_clients.add(ws)

        client_type = request.query.get("client", "pc").lower()
        logger.info(f"WebGL Avatar client connected [{client_type}]: {request.remote}")

        # Send mandatory Edition startup diagnostic sequence
        startup_text = get_startup_sequence_for_platform(client_type)
        initial_parsed = AudioDspParser.parse_message(startup_text)
        initial_visor_idx = AudioDspParser.map_visor_to_index(initial_parsed.visor_tags[0]) if initial_parsed.visor_tags else 0

        await ws.send_str(json.dumps({
            "type": "handshake",
            "edition": "mobile" if client_type in ("android", "mobile") else "pc",
            "lifecycle_state": self.wake_detector.state.value,
            "initial_event": {
                "priority": initial_parsed.level_priority,
                "raw_text": initial_parsed.raw_text,
                "clean_text": initial_parsed.clean_speech_text,
                "kinematics": initial_parsed.kinematics,
                "visor_tags": initial_parsed.visor_tags,
                "visor_index": initial_visor_idx,
                "audio_cues": initial_parsed.audio_cues,
                "pitch_shifts": initial_parsed.pitch_shifts,
                "blendshapes": initial_parsed.blendshapes,
                "targets": initial_parsed.targets,
            }
        }))

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_type = data.get("type")

                    # Handle audio chunk from client microphone
                    if msg_type == "audio_chunk":
                        raw_b64 = data.get("pcm_b64", "")
                        if raw_b64:
                            pcm_data = base64.b64decode(raw_b64)
                            self.wake_detector.touch_activity()
                            await self.gemini_bridge.send_audio_chunk(pcm_data)

                    # Handle optical video frame (JPEG base64)
                    elif msg_type == "video_frame":
                        jpg_b64 = data.get("jpg_b64", "")
                        if jpg_b64:
                            jpg_bytes = base64.b64decode(jpg_b64)
                            self.wake_detector.touch_activity()
                            await self.gemini_bridge.send_video_frame(jpg_bytes)

                    # Handle text user input
                    elif msg_type == "user_chat":
                        text = data.get("text", "")
                        self.wake_detector.touch_activity()
                        # Pass through safety gate
                        allowed, response_str = self.safety_gate.check_operation(text)
                        if not allowed:
                            parsed = AudioDspParser.parse_message(response_str)
                            await self.broadcast_cyn_event(parsed)
                        else:
                            await self.gemini_bridge.send_text_prompt(text)

                    # Handle mobile sensor telemetry (gyro, battery, thermal, touch)
                    elif msg_type == "mobile_telemetry":
                        acc = float(data.get("acceleration", 0.0))
                        bat = float(data.get("battery", 1.0))
                        orient = data.get("orientation", "portrait")
                        temp = float(data.get("temperature", 32.0))
                        is_hot = bool(data.get("thermal_hot", False))
                        reply = self.telemetry.update_mobile_sensors(acc, bat, orient, temp, is_hot)
                        if reply:
                            parsed = AudioDspParser.parse_message(reply)
                            await self.broadcast_cyn_event(parsed)

                    # Handle screen touch gestures ([touch:headpat], [touch:visor_poke])
                    elif msg_type == "touch_event":
                        t_type = data.get("touch_type", "")
                        x = float(data.get("x", 0))
                        y = float(data.get("y", 0))
                        reply = self.telemetry.handle_touch_interaction(t_type, x, y)
                        if reply:
                            parsed = AudioDspParser.parse_message(reply)
                            await self.broadcast_cyn_event(parsed)

                    # Wake trigger from UI button
                    elif msg_type == "trigger_wake":
                        self.wake_detector.trigger_wake("UI Button Click")

                elif msg.type == WSMsgType.ERROR:
                    logger.warning(f"WebSocket connection closed with error: {ws.exception()}")
        finally:
            self.ws_clients.discard(ws)
            logger.info("WebGL Avatar client disconnected.")

        return ws

    async def start(self) -> None:
        """Start servers and background threads."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"============================================================")
        logger.info(f"CYN v7.0 Full-Spectrum Server active at: http://localhost:{self.port}")
        logger.info(f"LAN Access for Android Client: http://<YOUR_IP>:{self.port}")
        logger.info(f"============================================================")

        # Start wake word listener
        self.wake_detector.start()

        # Connect to Gemini Live API
        await self.gemini_bridge.connect()

        # Keep server running
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            await self.gemini_bridge.disconnect()
            self.wake_detector.stop()
            await runner.cleanup()


def main():
    server = CynServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Shutdown sequence initiated by user.")


if __name__ == "__main__":
    main()
