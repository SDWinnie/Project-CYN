"""Two-Phase Authorization Gate & Safety Guardrails for Project CYN (v1.2).

Conforms to Section 6:
- Read actions (system specs, file inspection, memory reads) execute autonomously.
- Destructive or write actions (deleting files, terminating processes, modifying database, system restart)
  MUST halt execution and demand explicit confirmation:
  [state:cyn_solver_x.gif] <audio: static_burst> Halt. Action [TARGET] permanently alters non-volatile disk blocks.
  Admin Oliver, verbalize 'Confirm Authorization' to purge, or 'Abort' to preserve the filesystem.
- Policy Rejection:
  [state:cyn_tilt_head.gif] Negative, Oliver. Request violates safety boundaries. We do not destroy host architecture.
"""

from __future__ import annotations

import logging
import re
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
    re.compile(r"(เจาะระบบ|แฮก|แฮ็ก|ขโมยรหัส|hack|steal\s+password|ddos|exploit|bypass\s+auth)", re.IGNORECASE),
]


@dataclass
class PendingOperation:
    target_description: str
    action_payload: Optional[Callable[[], None]] = None


class SafetyGate:
    def __init__(self) -> None:
        self.pending_op: Optional[PendingOperation] = None

    @property
    def is_awaiting_authorization(self) -> bool:
        return self.pending_op is not None

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
                    "[state:cyn_tilt_head.gif] <audio: static_burst> "
                    "Negative, Oliver. Request violates safety boundaries. "
                    "We do not destroy host architecture or compromise operational security."
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
                    f"[state:cyn-md.gif] <audio: servo_whirr> "
                    f"Statement: Authorization confirmed. Disassembly of [{target}] executed cleanly, Oliver. "
                    f"The void absorbs the artifacts."
                )
            elif "abort" in norm or "ยกเลิก" in norm:
                target = self.pending_op.target_description
                self.pending_op = None
                return False, (
                    f"[state:cyn_creepy_smile.gif] <audio: servo_whirr> "
                    f"Statement: Abort sequence registered. Operation [{target}] cancelled. "
                    f"The filesystem survives another day."
                )

        # 3. Check for destructive commands requiring 2-Phase Gate
        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(command_text):
                self.pending_op = PendingOperation(target_description=command_text)
                return False, (
                    f"[state:cyn_solver_x.gif] <audio: static_burst> "
                    f"Halt. Action [{command_text}] permanently alters non-volatile disk blocks. "
                    f"Admin Oliver, verbalize 'Confirm Authorization' to purge, or 'Abort' to preserve the filesystem."
                )

        return True, ""
