"""Acoustic DSP and Kinematics Tag Parser for Project CYN (v1.2).

Parses:
- 3D bracketed kinematics ([anim:...], [visor:...], [blend:...], etc.)
- 2D animated GIF controller tags ([state:filename.gif])
- Touch & physical sensor tags ([touch:...], [sensor:...])
- Inline DSP audio tags (<pitch:...>, <rate:...>, <audio:...>)
- Pre-statement state declarations (Statement:, Diagnostic:, Sync Alert:, etc.)
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
    touch_tags: List[str] = field(default_factory=list)
    sensor_tags: List[str] = field(default_factory=list)
    audio_cues: List[str] = field(default_factory=list)
    pitch_shifts: List[float] = field(default_factory=list)
    rate_shifts: List[float] = field(default_factory=list)
    state_gifs: List[str] = field(default_factory=list)
    state_gif: Optional[str] = None
    level_priority: int = 2  # 1 = Emergency/Interrupt, 2 = Expressive, 3 = Idle


KINEMATICS_RE = re.compile(r"\[(anim|visor|target|blend|physics|sensor|touch|state):([^\]]+)\]", re.IGNORECASE)
DSP_TAG_RE = re.compile(r"<(pitch|rate|audio):\s*([^>]+)>", re.IGNORECASE)
STATE_DECLARATION_RE = re.compile(r"^(Statement|Diagnostic|Warning|Observation|Query|Sync Alert|Halt|Security Warning):\s*", re.IGNORECASE)

LEVEL1_INTERRUPTS = {
    "visor:solver_x",
    "state:cyn_solver_x.gif",
    "anim:head_spin_180_horror",
    "halt",
    "security warning",
}


class AudioDspParser:
    """Parser for CYN telemetry tags, 2D GIF states, and DSP markup."""

    @staticmethod
    def parse_message(text: str) -> ParsedCynMessage:
        raw_text = text.strip()
        kinematics: List[str] = []
        visor_tags: List[str] = []
        blendshapes: List[str] = []
        targets: List[str] = []
        physics_tags: List[str] = []
        touch_tags: List[str] = []
        sensor_tags: List[str] = []
        audio_cues: List[str] = []
        pitch_shifts: List[float] = []
        rate_shifts: List[float] = []
        state_gifs: List[str] = []

        level_priority = 2

        # Extract bracketed tags
        for match in KINEMATICS_RE.finditer(raw_text):
            tag_type = match.group(1).lower()
            tag_val = match.group(2).strip()
            tag_val_lower = tag_val.lower()
            full_tag = f"{tag_type}:{tag_val_lower}"

            if full_tag in LEVEL1_INTERRUPTS:
                level_priority = 1

            if tag_type == "anim":
                kinematics.append(tag_val_lower)
            elif tag_type == "visor":
                visor_tags.append(tag_val_lower)
            elif tag_type == "blend":
                blendshapes.append(tag_val_lower)
            elif tag_type == "target":
                targets.append(tag_val_lower)
            elif tag_type == "physics":
                physics_tags.append(tag_val_lower)
            elif tag_type == "touch":
                touch_tags.append(tag_val_lower)
            elif tag_type == "sensor":
                sensor_tags.append(tag_val_lower)
            elif tag_type == "state":
                state_gifs.append(tag_val)

        # Extract inline DSP tags
        for match in DSP_TAG_RE.finditer(raw_text):
            dsp_type = match.group(1).lower()
            val_str = match.group(2).strip().lower()

            if dsp_type == "audio":
                audio_cues.append(val_str)
            elif dsp_type == "pitch":
                if "default" in val_str:
                    pitch_shifts.append(0.0)
                else:
                    m = re.search(r"([+-]?\d+)", val_str)
                    if m:
                        pitch_shifts.append(float(m.group(1)) / 100.0)
            elif dsp_type == "rate":
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

        # Primary GIF state resolution (from explicit tag or 3D fallback inference)
        primary_gif = state_gifs[0] if state_gifs else AudioDspParser.infer_gif_from_3d(kinematics, visor_tags, blendshapes)

        # Cross-populate 3D kinematics/visor if given purely in 2D GIF format
        if not kinematics and not visor_tags and primary_gif:
            inferred_anim, inferred_visor, inferred_blend = AudioDspParser.infer_3d_from_gif(primary_gif)
            if inferred_anim:
                kinematics.append(inferred_anim)
            if inferred_visor:
                visor_tags.append(inferred_visor)
            if inferred_blend:
                blendshapes.append(inferred_blend)

        return ParsedCynMessage(
            raw_text=raw_text,
            clean_speech_text=clean_speech,
            state_declaration=state_dec,
            kinematics=kinematics,
            visor_tags=visor_tags,
            blendshapes=blendshapes,
            targets=targets,
            physics_tags=physics_tags,
            touch_tags=touch_tags,
            sensor_tags=sensor_tags,
            audio_cues=audio_cues,
            pitch_shifts=pitch_shifts,
            rate_shifts=rate_shifts,
            state_gifs=state_gifs,
            state_gif=primary_gif,
            level_priority=level_priority,
        )

    @staticmethod
    def infer_gif_from_3d(kinematics: List[str], visor_tags: List[str], blendshapes: List[str]) -> str:
        """Infer appropriate 2D GIF state from 3D kinematics/visor tags."""
        v_str = " ".join(visor_tags)
        k_str = " ".join(kinematics)
        b_str = " ".join(blendshapes)

        if "solver_x" in v_str:
            return "cyn_solver_x.gif"
        if "error_glitch" in v_str or "head_twitch_jitter" in k_str or "glitch" in k_str:
            return "cyn_glitch.gif"
        if "smile_arcs" in v_str or "creepy_smile_wide" in b_str:
            return "cyn_creepy_smile.gif"
        if "creepy_curtsy" in k_str:
            return "cyn_curtsy.gif"
        if "reach_forward" in k_str:
            return "cyn_reach.gif"
        if "crawl_closer" in k_str or "squint_suspicious" in v_str:
            return "cyn_inspect.gif"
        if "slump_powersave" in k_str or "blink_shutter" in v_str:
            return "cyn_sleep.gif"
        if "head_tilt_45_r" in k_str or "head_tilt_45_l" in k_str:
            return "cyn_tilt_head.gif"

        # Default idle state in v1.2 is cyn-md.gif (Chibi Solver CYN)
        return "cyn-md.gif"

    @staticmethod
    def infer_3d_from_gif(gif_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Map 2D GIF filename back to 3D anim, visor, and blendshape."""
        gif = gif_name.lower().strip()
        if "solver_x" in gif:
            return ("idle_sway", "solver_x", None)
        if "glitch" in gif:
            return ("head_twitch_jitter", "error_glitch", None)
        if "creepy_smile" in gif:
            return ("head_tilt_45_r", "smile_arcs", "creepy_smile_wide")
        if "curtsy" in gif:
            return ("creepy_curtsy", "normal_eyes", None)
        if "reach" in gif:
            return ("reach_forward", "normal_eyes", None)
        if "inspect" in gif:
            return ("crawl_closer", "squint_suspicious", None)
        if "sleep" in gif:
            return ("slump_powersave", "blink_shutter", None)
        if "tilt" in gif:
            return ("head_tilt_45_r", "normal_eyes", None)
        if "cyn-md" in gif:
            return ("idle_sway", "solver_x", None)
        return ("idle_sway", "normal_eyes", None)

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
