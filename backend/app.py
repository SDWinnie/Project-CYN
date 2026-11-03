"""Project CYN: Local WebSocket Gateway, Static Assets Server & Cloudflare Intermediary.
Serves:
- WebSocket endpoint: /ws/cyn
- Status API: /api/status
- Tunnel Info API: /api/tunnel
- Test Speak API: /api/speak_test
- Firestore Sync APIs: /api/firestore/memory, /api/firestore/sessions, /api/firestore/tasks
- Static 2D Assets: /assets/cyn/*
- Static WebGL Avatar: /*
"""

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional, Set

from aiohttp import WSMsgType, web

# Ensure backend root is on Python sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

STATIC_DIR = PROJECT_ROOT / "web_avatar"
ASSETS_DIR = PROJECT_ROOT / "assets"

from audio_dsp_parser import AudioDspParser, ParsedCynMessage
from cyn_construct.ai.model_client import MultiModelClient
from cyn_firestore_sync import firestore_sync
from cyn_prompt import (
    CYN_V1_2_STARTUP_SEQUENCE,
    get_prompt_for_platform,
    get_startup_sequence_for_platform,
)
from gemini_live_client import GeminiLiveBridge
from system_safety_gate import SafetyGate
from telemetry_receiver import TelemetryManager
from tunnel_relay import CloudflareTunnelRelay
from wake_word_detector import CynLifecycleState, WakeWordDetector

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
)
logger = logging.getLogger("CYN.App")


class CynServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.app = web.Application()
        self.ws_clients: Set[web.WebSocketResponse] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        self.safety_gate = SafetyGate()
        self.telemetry = TelemetryManager()
        self.gemini_bridge = GeminiLiveBridge(on_cyn_event=self._on_cyn_model_event)
        self.wake_detector = WakeWordDetector(on_state_change=self._on_wake_state_change)
        self.tunnel_relay = CloudflareTunnelRelay(port=self.port, on_url_ready=self._on_tunnel_url_ready)
        self.multi_model = MultiModelClient()

        self._setup_routes()

    def _setup_routes(self) -> None:
        self.app.router.add_get("/ws/cyn", self.handle_websocket)
        self.app.router.add_get("/api/status", self.handle_status)
        self.app.router.add_get("/api/tunnel", self.handle_tunnel_info)
        self.app.router.add_post("/api/speak_test", self.handle_speak_test)
        self.app.router.add_get("/api/models", self.handle_get_models)
        self.app.router.add_post("/api/models", self.handle_post_models)

        # Firestore Persistent Memory Core APIs (v1.2)
        self.app.router.add_get("/api/firestore/memory", self.handle_get_memory)
        self.app.router.add_post("/api/firestore/memory", self.handle_post_memory)
        self.app.router.add_get("/api/firestore/sessions", self.handle_get_sessions)
        self.app.router.add_post("/api/firestore/sessions", self.handle_post_sessions)
        self.app.router.add_get("/api/firestore/tasks", self.handle_get_tasks)
        self.app.router.add_post("/api/firestore/tasks", self.handle_post_tasks)

        # Serve static assets (2D animated GIFs)
        if ASSETS_DIR.exists():
            self.app.router.add_static("/assets", path=ASSETS_DIR, show_index=False)

        # Serve static web avatar frontend
        if STATIC_DIR.exists():
            self.app.router.add_get("/", self.handle_index)
            self.app.router.add_static("/", path=STATIC_DIR, show_index=False)

    async def handle_index(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(STATIC_DIR / "index.html")

    def _on_tunnel_url_ready(self, public_url: str) -> None:
        logger.info(f"Relay Conduit Active for Clients: {public_url}")
        msg_payload = {
            "type": "tunnel_ready",
            "public_url": public_url,
            "mobile_url": f"{public_url}?client=android",
            "mobile_2d_url": f"{public_url}?client=android&mode=2d",
        }
        if self.loop and self.loop.is_running():
            for ws in list(self.ws_clients):
                if not ws.closed:
                    try:
                        asyncio.run_coroutine_threadsafe(
                            ws.send_str(json.dumps(msg_payload)),
                            self.loop,
                        )
                    except Exception:
                        pass

    async def handle_tunnel_info(self, request: web.Request) -> web.Response:
        return web.json_response({
            "status": "active" if self.tunnel_relay.public_url else "initializing",
            "public_url": self.tunnel_relay.public_url,
            "mobile_url": f"{self.tunnel_relay.public_url}?client=android" if self.tunnel_relay.public_url else None,
            "mobile_2d_url": f"{self.tunnel_relay.public_url}?client=android&mode=2d" if self.tunnel_relay.public_url else None,
        })

    def _on_wake_state_change(self, state: CynLifecycleState, message: str) -> None:
        """Called when wake-word or hotkey changes state."""
        logger.info(f"Wake state changed: {state.value}")
        parsed = AudioDspParser.parse_message(message)
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.broadcast_cyn_event(parsed, None, {"lifecycle_state": state.value}),
                self.loop,
            )

    def _on_cyn_model_event(self, parsed: ParsedCynMessage, audio_bytes: Optional[bytes]) -> None:
        """Called when Gemini Live emits response tokens/audio."""
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii") if audio_bytes else None
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.broadcast_cyn_event(parsed, audio_b64),
                self.loop,
            )

    async def broadcast_cyn_event(
        self,
        parsed: ParsedCynMessage,
        audio_b64: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        """Broadcast formatted event payload to all connected WebGL and 2D overlay clients."""
        visor_index = 0
        if parsed.visor_tags:
            visor_index = AudioDspParser.map_visor_to_index(parsed.visor_tags[0])

        payload = {
            "type": "cyn_response",
            "priority": parsed.level_priority,
            "raw_text": parsed.raw_text,
            "clean_text": parsed.clean_speech_text,
            "state_declaration": parsed.state_declaration,
            "state_gif": parsed.state_gif or "cyn-md.gif",
            "state_gifs": parsed.state_gifs,
            "kinematics": parsed.kinematics,
            "visor_tags": parsed.visor_tags,
            "visor_index": visor_index,
            "blendshapes": parsed.blendshapes,
            "targets": parsed.targets,
            "physics_tags": parsed.physics_tags,
            "touch_tags": parsed.touch_tags,
            "sensor_tags": parsed.sensor_tags,
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
        sess = firestore_sync.get_session("oliver")
        return web.json_response({
            "status": "online",
            "entity": "PROJECT CYN (Absolute Solver Drone Prototype)",
            "version": "1.2.0 (Production Release)",
            "master": "Admin Oliver",
            "runtime": "Antigravity Framework",
            "firestore_sync": "ONLINE" if firestore_sync.is_cloud_connected else "LOCAL_CACHE_SYNC",
            "active_device": sess.get("active_device", "PC_Windows"),
            "last_active_gif": sess.get("last_active_gif_state", "cyn-md.gif"),
            "lifecycle_state": self.wake_detector.state.value,
            "connected_avatar_clients": len(self.ws_clients),
            "gemini_connected": self.gemini_bridge._is_connected,
            "visual_modes": ["2D Chibi Solver GIF (cyn-md.gif)", "3D VRM Three.js Rig"],
        })

    # =========================================================================
    # FIRESTORE REST API HANDLERS
    # =========================================================================
    async def handle_get_memory(self, request: web.Request) -> web.Response:
        user_id = request.query.get("user", "oliver")
        return web.json_response(firestore_sync.get_memory(user_id))

    async def handle_post_memory(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid_json"}, status=400)
        user_id = data.get("user", "oliver")
        updated = firestore_sync.update_memory(data.get("updates", {}), user_id)
        return web.json_response({"status": "updated", "memory": updated})

    async def handle_get_sessions(self, request: web.Request) -> web.Response:
        user_id = request.query.get("user", "oliver")
        return web.json_response(firestore_sync.get_session(user_id))

    async def handle_post_sessions(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid_json"}, status=400)
        device = data.get("device", "PC_Windows")
        gif_state = data.get("gif_state", "cyn-md.gif")
        session_id = data.get("session_id")
        user_id = data.get("user", "oliver")
        is_switch, prev_device = firestore_sync.record_session_heartbeat(device, gif_state, session_id, user_id)
        return web.json_response({
            "status": "recorded",
            "is_device_switch": is_switch,
            "previous_device": prev_device,
            "active_device": device,
            "session": firestore_sync.get_session(user_id),
        })

    async def handle_get_tasks(self, request: web.Request) -> web.Response:
        user_id = request.query.get("user", "oliver")
        return web.json_response({"tasks": firestore_sync.get_tasks(user_id)})

    async def handle_post_tasks(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid_json"}, status=400)
        action = data.get("action", "add")
        user_id = data.get("user", "oliver")
        if action == "add":
            tasks = firestore_sync.add_task(data.get("task", {}), user_id)
            return web.json_response({"status": "added", "tasks": tasks})
        elif action == "update_status":
            task_id = data.get("task_id", "")
            new_status = data.get("status", "completed")
            ok = firestore_sync.update_task_status(task_id, new_status, user_id)
            return web.json_response({
                "status": "updated" if ok else "not_found",
                "tasks": firestore_sync.get_tasks(user_id),
            })
        return web.json_response({"error": "unknown_action"}, status=400)

    async def handle_speak_test(self, request: web.Request) -> web.Response:
        """Endpoint to test arbitrary CYN dialogue strings."""
        data = await request.json()
        text = data.get("text", "")
        parsed = AudioDspParser.parse_message(text)
        await self.broadcast_cyn_event(parsed)
        return web.json_response({"status": "dispatched", "parsed": parsed.__dict__})

    async def _send_delayed_sync_alert(self, ws: web.WebSocketResponse, sync_parsed: ParsedCynMessage) -> None:
        """Sends cross-device continuity acknowledgment after initial handshake."""
        await asyncio.sleep(0.8)
        if not ws.closed:
            try:
                visor_idx = AudioDspParser.map_visor_to_index(sync_parsed.visor_tags[0]) if sync_parsed.visor_tags else 0
                await ws.send_str(json.dumps({
                    "type": "cyn_response",
                    "priority": sync_parsed.level_priority,
                    "raw_text": sync_parsed.raw_text,
                    "clean_text": sync_parsed.clean_speech_text,
                    "state_declaration": sync_parsed.state_declaration,
                    "state_gif": sync_parsed.state_gif or "cyn-md.gif",
                    "state_gifs": sync_parsed.state_gifs,
                    "kinematics": sync_parsed.kinematics,
                    "visor_tags": sync_parsed.visor_tags,
                    "visor_index": visor_idx,
                    "audio_cues": sync_parsed.audio_cues,
                    "pitch_shifts": sync_parsed.pitch_shifts,
                }))
            except Exception as e:
                logger.warning(f"Could not send sync alert: {e}")

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws_clients.add(ws)

        client_type = request.query.get("client", "v1.2").lower()
        mode = request.query.get("mode", "").lower()
        if mode == "2d" and "2d" not in client_type:
            client_type = f"{client_type}_2d"

        device_name = "Android_Mobile" if ("android" in client_type or "mobile" in client_type) else "PC_Windows"

        # Record session in Firestore and check for cross-device migration
        is_switch, prev_device = firestore_sync.record_session_heartbeat(
            device=device_name,
            gif_state="cyn-md.gif",
            user_id="oliver",
        )

        logger.info(f"Client connected [{client_type} | {device_name}]: {request.remote} (Migration from {prev_device}: {is_switch})")

        # Send mandatory Edition startup diagnostic sequence
        startup_text = get_startup_sequence_for_platform(client_type)
        initial_parsed = AudioDspParser.parse_message(startup_text)
        initial_visor_idx = AudioDspParser.map_visor_to_index(initial_parsed.visor_tags[0]) if initial_parsed.visor_tags else 0

        await ws.send_str(json.dumps({
            "type": "handshake",
            "edition": client_type,
            "device": device_name,
            "firestore_sync": "ONLINE" if firestore_sync.is_cloud_connected else "LOCAL_CACHE_SYNC",
            "lifecycle_state": self.wake_detector.state.value,
            "initial_event": {
                "priority": initial_parsed.level_priority,
                "raw_text": initial_parsed.raw_text,
                "clean_text": initial_parsed.clean_speech_text,
                "state_declaration": initial_parsed.state_declaration,
                "state_gif": initial_parsed.state_gif or "cyn-md.gif",
                "state_gifs": initial_parsed.state_gifs,
                "kinematics": initial_parsed.kinematics,
                "visor_tags": initial_parsed.visor_tags,
                "visor_index": initial_visor_idx,
                "audio_cues": initial_parsed.audio_cues,
                "pitch_shifts": initial_parsed.pitch_shifts,
                "blendshapes": initial_parsed.blendshapes,
                "targets": initial_parsed.targets,
            }
        }))

        # If device switched, emit cross-device continuity acknowledgment
        if is_switch:
            sync_alert_text = (
                f"[state:cyn-md.gif] <audio: servo_whirr> Sync Alert: Telemetry retrieved from Firestore. "
                f"Resuming session previously active on {prev_device}. Welcome back to {device_name}, Oliver."
            )
            sync_parsed = AudioDspParser.parse_message(sync_alert_text)
            asyncio.create_task(self._send_delayed_sync_alert(ws, sync_parsed))

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

                    # Handle Firestore sync trigger from client
                    elif msg_type == "firestore_heartbeat":
                        device_flag = data.get("device", device_name)
                        gif = data.get("gif_state", "cyn-md.gif")
                        firestore_sync.record_session_heartbeat(device_flag, gif)

                    # Wake trigger from UI button
                    elif msg_type == "trigger_wake":
                        self.wake_detector.trigger_wake("UI Button Click")

                elif msg.type == WSMsgType.ERROR:
                    logger.warning(f"WebSocket connection closed with error: {ws.exception()}")
        finally:
            self.ws_clients.discard(ws)
            logger.info("Client disconnected.")

        return ws

    async def start(self) -> None:
        """Start servers immediately (<50ms) and initialize background tasks concurrently."""
        self.loop = asyncio.get_running_loop()
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"============================================================")
        logger.info(f"PROJECT CYN v1.2 Antigravity Engine running at: http://localhost:{self.port}")
        logger.info(f"Firestore Sync Status: {'CLOUD_ONLINE' if firestore_sync.is_cloud_connected else 'LOCAL_CACHE_SYNC (data/firestore_cache.json)'}")
        logger.info(f"LAN Access for Android Client: http://<YOUR_IP>:{self.port}")
        logger.info(f"============================================================")

        # Launch background tasks asynchronously without blocking HTTP/WebSocket listener
        bg_task = asyncio.create_task(self._init_background_services())

        # Keep server running
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            bg_task.cancel()
            self.tunnel_relay.stop()
            await self.gemini_bridge.disconnect()
            self.wake_detector.stop()
            await runner.cleanup()

    async def _init_background_services(self) -> None:
        """Non-blocking background subsystem initialization."""
        # 1. Start Cloudflare public intermediary relay tunnel
        try:
            self.tunnel_relay.start()
        except Exception as e:
            logger.warning(f"Tunnel relay startup note: {e}")

        # 2. Start wake word listener
        try:
            self.wake_detector.start()
        except Exception as e:
            logger.warning(f"Wake detector startup note: {e}")

        # 3. Connect to Gemini Live API
        try:
            await self.gemini_bridge.connect()
        except Exception as e:
            logger.warning(f"Gemini Live API connection note: {e}")


def main():
    server = CynServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Shutdown sequence initiated by user.")


if __name__ == "__main__":
    main()
