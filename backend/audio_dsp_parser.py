"""Acoustic DSP and Kinematics Tag Parser for Project CYN.

Parses bracketed kinematics ([anim:...], [visor:...], etc.),
inline DSP audio tags (<pitch:...>, <rate:...>, <audio:...>),
and pre-statement state declarations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


@dataclass
class ParsedCynMessage:
    raw_text: str
    clean_speech_text: str
    state_declaration: Optional[str] = None
    kinematics: List[str] = field(default_factory=list)
    visor_tags: List[str] = field(default_factory=list)
    blendshapes: List[str] = field(default_factory=list)
    targets: List[str] = field(default_factory=list)
    physics_tags: List[str] = field(default_factory=list)
    audio_cues: List[str] = field(default_factory=list)
    pitch_shifts: List[float] = field(default_factory=list)
    rate_shifts: List[float] = field(default_factory=list)
    level_priority: int = 2  # 1 = Emergency/Interrupt, 2 = Expressive, 3 = Idle


KINEMATICS_RE = re.compile(r"\[(anim|visor|target|blend|physics|sensor|touch):([^\]]+)\]", re.IGNORECASE)
DSP_TAG_RE = re.compile(r"<(pitch|rate|audio):\s*([^>]+)>", re.IGNORECASE)
STATE_DECLARATION_RE = re.compile(r"^(Statement|Diagnostic|Warning|Observation|Query|Halt):\s*", re.IGNORECASE)

LEVEL1_INTERRUPTS = {
    "visor:solver_x",
    "anim:head_spin_180_horror",
    "halt",
}


class AudioDspParser:
    """Parser for CYN telemetry tags and DSP markup."""

    @staticmethod
    def parse_message(text: str) -> ParsedCynMessage:
        raw_text = text.strip()
        kinematics: List[str] = []
        visor_tags: List[str] = []
        blendshapes: List[str] = []
        targets: List[str] = []
        physics_tags: List[str] = []
        audio_cues: List[str] = []
        pitch_shifts: List[float] = []
        rate_shifts: List[float] = []

        level_priority = 2

        # Extract bracketed tags
        for match in KINEMATICS_RE.finditer(raw_text):
            tag_type = match.group(1).lower()
            tag_val = match.group(2).lower()
            full_tag = f"{tag_type}:{tag_val}"

            if full_tag in LEVEL1_INTERRUPTS:
                level_priority = 1

            if tag_type == "anim":
                kinematics.append(tag_val)
            elif tag_type == "visor":
                visor_tags.append(tag_val)
            elif tag_type == "blend":
                blendshapes.append(tag_val)
            elif tag_type == "target":
                targets.append(tag_val)
            elif tag_type == "physics":
                physics_tags.append(tag_val)

        # Extract inline DSP tags
        for match in DSP_TAG_RE.finditer(raw_text):
            dsp_type = match.group(1).lower()
            val_str = match.group(2).strip().lower()

            if dsp_type == "audio":
                audio_cues.append(val_str)
            elif dsp_type == "pitch":
                # e.g., "-20%", "+35%", "default"
                if "default" in val_str:
                    pitch_shifts.append(0.0)
                else:
                    m = re.search(r"([+-]?\d+)", val_str)
                    if m:
                        pitch_shifts.append(float(m.group(1)) / 100.0)
            elif dsp_type == "rate":
                # e.g., "70%", "100%"
                m = re.search(r"(\d+)", val_str)
                if m:
                    rate_shifts.append(float(m.group(1)) / 100.0)

        # Remove tags for clean spoken audio synthesis
        clean_speech = KINEMATICS_RE.sub("", raw_text)
        clean_speech = DSP_TAG_RE.sub("", clean_speech).strip()

        # Check for state declaration at start of lines
        state_dec = None
        for line in clean_speech.splitlines():
            line_s = line.strip()
            m = STATE_DECLARATION_RE.match(line_s)
            if m:
                state_dec = m.group(1)
                break

        return ParsedCynMessage(
            raw_text=raw_text,
            clean_speech_text=clean_speech,
            state_declaration=state_dec,
            kinematics=kinematics,
            visor_tags=visor_tags,
            blendshapes=blendshapes,
            targets=targets,
            physics_tags=physics_tags,
            audio_cues=audio_cues,
            pitch_shifts=pitch_shifts,
            rate_shifts=rate_shifts,
            level_priority=level_priority,
        )

    @staticmethod
    def map_visor_to_index(visor_tag: str) -> int:
        """Map [visor:...] tag to 0-6 sprite atlas index."""
        tag = visor_tag.lower().replace("visor:", "").strip()
        mapping = {
            "normal_eyes": 0,
            "solver_x": 1,
            "smile_arcs": 2,
            "squint_suspicious": 3,
            "blink_shutter": 4,
            "tear_oil": 5,
            "error_glitch": 6,
        }
        return mapping.get(tag, 0)
