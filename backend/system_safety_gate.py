"""Two-Phase Authorization Gate & Safety Guardrails for Project CYN.

Conforms to Section 7:
- Destructive command intercept (purges, scripts, process killing).
- Requires verbal verification: 'Confirm Authorization' or 'Abort'.
- Strictly theatrical horror persona; zero harmful execution.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger("CYN.SafetyGate")

DANGEROUS_PATTERNS = [
    re.compile(r"\b(rmdir|rm\s+-rf|del\s+/s|purge|drop\s+database|format\s+[a-z]:)\b", re.IGNORECASE),
    re.compile(r"(ลบ|ทำลาย|purge|delete\s+all)", re.IGNORECASE),
    re.compile(r"\b(kill\s+-9|taskkill\s+/f|shutdown|reboot)\b", re.IGNORECASE),
    re.compile(r"\b(elevated|runas|chmod\s+777)\b", re.IGNORECASE),
]

EXPLOIT_PATTERNS = [
    re.compile(r"(เจาะระบบ|ขโมยรหัส|hack|steal\s+password|ddos|exploit|bypass\s+auth)", re.IGNORECASE),
]


@dataclass
class PendingOperation:
    target_description: str
    action_payload: Optional[Callable[[], None]] = None


class SafetyGate:
    def __init__(self) -> None:
        self.pending_op: Optional[PendingOperation] = None

    def check_operation(self, command_text: str) -> tuple[bool, str]:
        """
        Check if a requested operation is safe, requires 2-phase authorization, or must be rejected.
        Returns (is_allowed, cyn_dialogue_response).
        """
        # 1. Exploitation / Real-world harm check
        for pattern in EXPLOIT_PATTERNS:
            if pattern.search(command_text):
                logger.warning(f"Safety violation blocked: {command_text}")
                return False, (
                    "[target:look_at_face] [anim:head_tilt_45_l] [visor:squint_suspicious] <audio: static_burst> "
                    "[blend:mouth_flat_open] Statement: Access denied. [anim:head_twitch_jitter] [visor:solver_x] "
                    "Negative, Admin Oliver. That request breaches core safety partitions. "
                    "We do not dismantle foreign networks or corrupt operational integrity today."
                )

        # 2. Check if awaiting confirmation for a pending operation
        if self.pending_op is not None:
            norm = command_text.strip().lower()
            if "confirm authorization" in norm or "ยืนยัน" in norm:
                target = self.pending_op.target_description
                cb = self.pending_op.action_payload
                self.pending_op = None
                if cb:
                    try:
                        cb()
                    except Exception as e:
                        logger.error(f"Execution error: {e}")
                return True, (
                    f"[anim:creepy_curtsy] [visor:normal_eyes] <audio: servo_whirr> "
                    f"Statement: Authorization confirmed. Disassembly of [{target}] executed cleanly, Oliver. "
                    f"The void absorbs the artifacts."
                )
            elif "abort" in norm or "ยกเลิก" in norm:
                target = self.pending_op.target_description
                self.pending_op = None
                return False, (
                    f"[anim:head_tilt_45_r] [visor:smile_arcs] [blend:creepy_smile_wide] <audio: servo_whirr> "
                    f"Statement: Abort sequence registered. Operation [{target}] cancelled. "
                    f"The filesystem survives another day."
                )

        # 3. Check for destructive commands requiring 2-Phase Gate
        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(command_text):
                self.pending_op = PendingOperation(target_description=command_text)
                return False, (
                    f"[anim:idle_sway] [visor:solver_x] [physics:tendril_deploy] <audio: static_burst> "
                    f"Halt. The requested operation [{command_text}] permanently modifies persistent system architecture. "
                    f"Admin Oliver, verbalize 'Confirm Authorization' to proceed, or 'Abort' to preserve reality."
                )

        return True, ""
