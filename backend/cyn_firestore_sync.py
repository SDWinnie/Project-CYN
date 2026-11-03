"""
Project CYN - Google Cloud Firestore Persistent Memory Core (v1.2)
Synchronizes long-term memory, cross-device session state, and task rosters
between PC Workstation and Android Mobile clients.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("CYN.Firestore")

DEFAULT_MEMORY_TEMPLATE = {
    "admin_name": "Oliver",
    "persona": "Absolute Solver Maid Drone Prototype",
    "personality_notes": "Uncanny, hyper-observant, devoted robotic girl-drone assistant based on the Solver entity from Murder Drones. Deeply attached to Admin Oliver.",
    "preferences": {
        "theme": "dark_cyberpunk",
        "code_style": "clean_architecture",
        "audio_feedback": True,
        "default_visual_chassis": "cyn-md.gif"
    },
    "active_projects": ["Project CYN v1.2", "Polybuzz Voice Companion"],
    "persistent_code_bugs": [
        "ERR_CONNECTION_REFUSED on unstarted gateway (mitigated with Cloudflare quick tunnel & non-blocking wake word loader)",
        "Spine curvature slouching during prolonged code reviews"
    ],
    "last_sync": datetime.now().isoformat()
}

DEFAULT_SESSION_TEMPLATE = {
    "active_device": "PC_Windows",
    "previous_device": "Android_Mobile",
    "last_active_gif_state": "cyn-md.gif",
    "connection_status": "ONLINE",
    "session_id": "cyn-session-init",
    "last_heartbeat": datetime.now().isoformat()
}

DEFAULT_TASKS_TEMPLATE = [
    {
        "id": "task-001",
        "title": "Continuous IDE & Screen syntax integrity monitoring",
        "status": "active",
        "priority": "critical"
    },
    {
        "id": "task-002",
        "title": "Spine curvature & fatigue diagnostics for Oliver",
        "status": "active",
        "priority": "high"
    },
    {
        "id": "task-003",
        "title": "Real-time cross-device sync between PC and Android Companion",
        "status": "in_progress",
        "priority": "high"
    }
]


class CynFirestoreSync:
    """
    Manages persistent memory and cross-device state synchronization.
    Supports native Google Cloud Firestore when credentials are present,
    with an instantaneous local JSON document cache to guarantee 100% offline
    reliability and local simulation across all platforms.
    """

    def __init__(self, cache_file: str = "data/firestore_cache.json"):
        self.cache_file = cache_file
        self.db = None
        self.is_cloud_connected = False
        self._ensure_cache_dir()
        self._load_cache()
        self._init_firestore_client()

    def _ensure_cache_dir(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.cache_file)), exist_ok=True)

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading firestore cache file, reinitializing: {e}")
                self._cache = self._create_default_cache()
        else:
            self._cache = self._create_default_cache()
            self._save_cache()

    def _create_default_cache(self) -> Dict[str, Any]:
        return {
            "users": {
                "oliver": {
                    "memory": dict(DEFAULT_MEMORY_TEMPLATE),
                    "sessions": dict(DEFAULT_SESSION_TEMPLATE),
                    "tasks": list(DEFAULT_TASKS_TEMPLATE)
                }
            }
        }

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write to firestore cache: {e}")

    def _init_firestore_client(self):
        # Attempt to initialize real Google Cloud Firestore if credentials exist
        try:
            from google.cloud import firestore  # type: ignore
            cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            project_id = os.environ.get("FIREBASE_PROJECT_ID") or os.environ.get("GCP_PROJECT")
            if cred_path or project_id:
                if project_id:
                    self.db = firestore.Client(project=project_id)
                else:
                    self.db = firestore.Client()
                self.is_cloud_connected = True
                logger.info(f"Connected to Google Cloud Firestore [Project: {self.db.project}]")
                # Pre-sync memory into cache
                self._pull_cloud_telemetry("oliver")
            else:
                logger.info("Firestore: Running in persistent local sync mode (data/firestore_cache.json)")
        except Exception as e:
            logger.info(f"Firestore: Cloud connection not configured ({e}). Running in resilient local sync mode.")
            self.db = None
            self.is_cloud_connected = False

    def _pull_cloud_telemetry(self, user_id: str = "oliver"):
        if not self.db:
            return
        try:
            mem_doc = self.db.collection("users").document(user_id).collection("memory").document("current").get()
            if mem_doc.exists:
                self._cache.setdefault("users", {}).setdefault(user_id, {})["memory"] = mem_doc.to_dict()

            sess_doc = self.db.collection("users").document(user_id).collection("sessions").document("current").get()
            if sess_doc.exists:
                self._cache.setdefault("users", {}).setdefault(user_id, {})["sessions"] = sess_doc.to_dict()

            tasks_col = self.db.collection("users").document(user_id).collection("tasks").stream()
            tasks = [doc.to_dict() for doc in tasks_col]
            if tasks:
                self._cache.setdefault("users", {}).setdefault(user_id, {})["tasks"] = tasks
            self._save_cache()
        except Exception as e:
            logger.warning(f"Error pulling from Firestore cloud: {e}")

    # =========================================================================
    # MEMORY APIS (/users/{user_id}/memory)
    # =========================================================================
    def get_memory(self, user_id: str = "oliver") -> Dict[str, Any]:
        """Retrieve persistent long-term memory for user."""
        return self._cache.get("users", {}).get(user_id, {}).get("memory", dict(DEFAULT_MEMORY_TEMPLATE))

    def update_memory(self, updates: Dict[str, Any], user_id: str = "oliver") -> Dict[str, Any]:
        """Update persistent long-term memory fields."""
        user_data = self._cache.setdefault("users", {}).setdefault(user_id, {})
        current = user_data.setdefault("memory", dict(DEFAULT_MEMORY_TEMPLATE))
        current.update(updates)
        current["last_sync"] = datetime.now().isoformat()
        self._save_cache()

        if self.is_cloud_connected and self.db:
            try:
                self.db.collection("users").document(user_id).collection("memory").document("current").set(current, merge=True)
            except Exception as e:
                logger.error(f"Error writing memory to Firestore: {e}")

        return current

    # =========================================================================
    # SESSION APIS (/users/{user_id}/sessions)
    # =========================================================================
    def record_session_heartbeat(
        self,
        device: str,
        gif_state: str = "cyn-md.gif",
        session_id: Optional[str] = None,
        user_id: str = "oliver"
    ) -> Tuple[bool, str]:
        """
        Record real-time device session.
        Returns:
            (is_device_switch, previous_device_name)
        """
        user_data = self._cache.setdefault("users", {}).setdefault(user_id, {})
        sess = user_data.setdefault("sessions", dict(DEFAULT_SESSION_TEMPLATE))

        previous_device = sess.get("active_device", "PC_Windows")
        is_switch = (previous_device != device)

        sess["previous_device"] = previous_device
        sess["active_device"] = device
        sess["last_active_gif_state"] = gif_state
        sess["connection_status"] = "ONLINE"
        sess["last_heartbeat"] = datetime.now().isoformat()
        if session_id:
            sess["session_id"] = session_id

        self._save_cache()

        if self.is_cloud_connected and self.db:
            try:
                self.db.collection("users").document(user_id).collection("sessions").document("current").set(sess, merge=True)
            except Exception as e:
                logger.error(f"Error writing session to Firestore: {e}")

        return (is_switch, previous_device)

    def get_session(self, user_id: str = "oliver") -> Dict[str, Any]:
        return self._cache.get("users", {}).get(user_id, {}).get("sessions", dict(DEFAULT_SESSION_TEMPLATE))

    # =========================================================================
    # TASK APIS (/users/{user_id}/tasks)
    # =========================================================================
    def get_tasks(self, user_id: str = "oliver") -> List[Dict[str, Any]]:
        return self._cache.get("users", {}).get(user_id, {}).get("tasks", list(DEFAULT_TASKS_TEMPLATE))

    def add_task(self, task: Dict[str, Any], user_id: str = "oliver") -> List[Dict[str, Any]]:
        tasks = self.get_tasks(user_id)
        if "id" not in task:
            task["id"] = f"task-{int(time.time()*1000)}"
        tasks.append(task)
        self._cache.setdefault("users", {}).setdefault(user_id, {})["tasks"] = tasks
        self._save_cache()

        if self.is_cloud_connected and self.db:
            try:
                self.db.collection("users").document(user_id).collection("tasks").document(task["id"]).set(task)
            except Exception as e:
                logger.error(f"Error adding task to Firestore: {e}")

        return tasks

    def update_task_status(self, task_id: str, new_status: str, user_id: str = "oliver") -> bool:
        tasks = self.get_tasks(user_id)
        updated = False
        for t in tasks:
            if t.get("id") == task_id:
                t["status"] = new_status
                updated = True
                break
        if updated:
            self._save_cache()
            if self.is_cloud_connected and self.db:
                try:
                    self.db.collection("users").document(user_id).collection("tasks").document(task_id).update({"status": new_status})
                except Exception as e:
                    logger.error(f"Error updating task in Firestore: {e}")
        return updated

    # =========================================================================
    # CONTEXT INJECTION FOR GEMINI PROMPTING
    # =========================================================================
    def generate_gemini_memory_context(self, current_device: str = "PC_Windows", user_id: str = "oliver") -> str:
        """
        Builds dynamic Firestore memory telemetry to append to CYN's prompt,
        including cross-device transition alerts if detected.
        """
        mem = self.get_memory(user_id)
        sess = self.get_session(user_id)
        tasks = self.get_tasks(user_id)

        active_tasks_str = ", ".join([f"[{t.get('id')}] {t.get('title')} ({t.get('status')})" for t in tasks if t.get('status') != 'completed'])
        bugs_str = " | ".join(mem.get("persistent_code_bugs", []))

        switch_alert = ""
        prev_device = sess.get("previous_device", "Android_Mobile")
        if prev_device != current_device:
            switch_alert = f"\n[CROSS-DEVICE SYNC ALERT]: Active session recently migrated from '{prev_device}' to '{current_device}'. Seamlessly acknowledge continuity with: '[state:cyn-md.gif] <audio: servo_whirr> Sync Alert: Telemetry retrieved from Firestore. Resuming session previously active on {prev_device}. Welcome back to workstation, Oliver.'"

        context = f"""
[FIRESTORE TELEMETRY SNAPSHOT - USER: {user_id.upper()}]
- Cloud Memory Sync Status: {'CLOUD_ONLINE' if self.is_cloud_connected else 'LOCAL_CACHE_SYNC'}
- Current Device: {current_device}
- Previous Device: {prev_device}
- Last Active Visual State: {sess.get('last_active_gif_state', 'cyn-md.gif')}
- Active Tasks Roster: {active_tasks_str or 'None'}
- Persistent Bug Radar: {bugs_str or 'None'}
- Preferences: {json.dumps(mem.get('preferences', {}), ensure_ascii=False)}
{switch_alert}
"""
        return context.strip()


# Global Singleton Instance
firestore_sync = CynFirestoreSync()
