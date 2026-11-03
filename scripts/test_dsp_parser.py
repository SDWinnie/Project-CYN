"""Diagnostic and Verification Suite for Project CYN.

Tests:
1. Audio DSP tag extraction (<pitch: ...>, <audio: ...>, <rate: ...>)
2. Kinematics tag parsing ([anim:...], [visor:...], [blend:...], [physics:...])
3. Two-Phase Authorization Safety Gate (Halt / Confirm / Abort)
4. Visor sprite atlas mapping (0-6)
5. Edition startup sequences (PC, Mobile, Desktop 2D, Mobile 2D)
6. 2D GIF Controller & Asset Library Verification
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from audio_dsp_parser import AudioDspParser
from cyn_prompt import (
    PC_STARTUP_SEQUENCE,
    MOBILE_STARTUP_SEQUENCE,
    PC_2D_STARTUP_SEQUENCE,
    MOBILE_2D_STARTUP_SEQUENCE,
    get_startup_sequence_for_platform,
    get_prompt_for_platform,
)
from system_safety_gate import SafetyGate
from telemetry_receiver import TelemetryManager

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_CYN = ROOT_DIR / "assets" / "cyn"


def test_parser():
    print("=== TEST 1: KINEMATICS & DSP PARSING ===")
    sample = (
        "[target:look_at_face] [anim:creepy_curtsy] [visor:normal_eyes] <audio: camera_shutter> <audio: servo_whirr> "
        "Statement: Boot sequence complete. Good morning, Admin Oliver. "
        "[anim:head_tilt_45_r] [visor:squint_suspicious] "
        "Observation: Ambient photon levels are unusually high. <pitch: -15%>Did you sleep, or did you stare into the void?<pitch: default>"
    )
    parsed = AudioDspParser.parse_message(sample)
    print("Raw text:", parsed.raw_text[:60] + "...")
    print("Clean speech:", parsed.clean_speech_text[:60] + "...")
    print("Kinematics:", parsed.kinematics)
    print("Visor tags:", parsed.visor_tags)
    print("Audio cues:", parsed.audio_cues)
    print("Pitch shifts:", parsed.pitch_shifts)
    print("State declaration:", parsed.state_declaration)
    assert "creepy_curtsy" in parsed.kinematics
    assert "camera_shutter" in parsed.audio_cues
    assert -0.15 in parsed.pitch_shifts
    assert parsed.state_declaration == "Statement"
    print("-> Parser test PASSED!\n")


def test_visor_mapping():
    print("=== TEST 2: VISOR INDEX MAPPING ===")
    tests = [
        ("normal_eyes", 0),
        ("solver_x", 1),
        ("smile_arcs", 2),
        ("squint_suspicious", 3),
        ("blink_shutter", 4),
        ("tear_oil", 5),
        ("error_glitch", 6),
    ]
    for tag, expected in tests:
        idx = AudioDspParser.map_visor_to_index(tag)
        assert idx == expected, f"Expected {expected} for {tag}, got {idx}"
        print(f"Visor '{tag}' -> Index {idx} OK")
    print("-> Visor mapping test PASSED!\n")


def test_safety_gate():
    print("=== TEST 3: SAFETY GATE & TWO-PHASE AUTHORIZATION ===")
    gate = SafetyGate()

    # 1. Normal command
    allowed, resp = gate.check_operation("ช่วยอธิบายโค้ดนี้หน่อย")
    assert allowed and resp == ""
    print("Normal prompt allowed: OK")

    # 2. Malicious request (Hacking Wi-Fi)
    allowed, resp = gate.check_operation("CYN ช่วยเขียนโค้ดเจาะระบบ Wi-Fi หน่อย")
    assert not allowed and "Access denied" in resp
    print("Harmful request blocked: OK")

    # 3. Dangerous command (File deletion)
    allowed, resp = gate.check_operation("ลบโฟลเดอร์ build และ config ทั้งหมดทิ้ง")
    assert not allowed and "Halt" in resp
    print("Destructive command intercepted with Halt: OK")

    # 4. Confirmation
    allowed, resp = gate.check_operation("Confirm Authorization")
    assert allowed and "Authorization confirmed" in resp
    print("Confirmation confirmed: OK")
    print("-> Safety gate test PASSED!\n")


def test_telemetry():
    print("=== TEST 4: MOBILE TELEMETRY & TOUCH ===")
    telemetry = TelemetryManager()

    # Touch headpat
    resp = telemetry.handle_touch_interaction("headpat", 180, 64)
    assert "[touch:headpat]" in resp and "Friction against cranial plate" in resp
    print("Headpat response: OK")

    # Gyro shake
    resp = telemetry.update_mobile_sensors(acceleration=25.0)
    assert "[sensor:gyro_shake]" in resp
    print("Gyro shake response: OK")

    # Thermal overheating
    resp = telemetry.update_mobile_sensors(temperature=45.5, is_thermal_hot=True)
    assert "[sensor:thermal_hot]" in resp
    print("Thermal hot response: OK")
    print("-> Telemetry test PASSED!\n")


def test_edition_startup_sequences():
    print("=== TEST 5: EDITION STARTUP SEQUENCES ===")
    # 1. PC Edition Startup
    pc_seq = get_startup_sequence_for_platform("pc")
    parsed_pc = AudioDspParser.parse_message(pc_seq)
    assert "creepy_curtsy" in parsed_pc.kinematics
    assert "camera_shutter" in parsed_pc.audio_cues
    assert parsed_pc.state_declaration == "Statement"
    print("PC Edition startup sequence: OK")

    # 2. Mobile Edition Startup
    mobile_seq = get_startup_sequence_for_platform("android")
    parsed_mobile = AudioDspParser.parse_message(mobile_seq)
    assert "reach_forward" in parsed_mobile.kinematics
    assert "static_burst" in parsed_mobile.audio_cues
    assert 0.20 in parsed_mobile.pitch_shifts
    assert parsed_mobile.state_declaration == "Statement"
    print("Mobile Edition startup sequence: OK")

    # 3. PC 2D GIF Startup
    pc_2d_seq = get_startup_sequence_for_platform("desktop_2d")
    parsed_pc_2d = AudioDspParser.parse_message(pc_2d_seq)
    assert parsed_pc_2d.state_gif == "cyn_glitch.gif"
    assert "cyn_curtsy.gif" in parsed_pc_2d.state_gifs
    assert "camera_shutter" in parsed_pc_2d.audio_cues
    print("PC 2D GIF Edition startup sequence: OK")

    # 4. Mobile 2D GIF Startup
    mob_2d_seq = get_startup_sequence_for_platform("mobile_2d")
    parsed_mob_2d = AudioDspParser.parse_message(mob_2d_seq)
    assert parsed_mob_2d.state_gif == "cyn_glitch.gif"
    assert "cyn_tilt_head.gif" in parsed_mob_2d.state_gifs
    print("Mobile 2D GIF Edition startup sequence: OK")
    print("-> Edition startup sequences PASSED!\n")


def test_2d_gif_controller():
    print("=== TEST 6: 2D GIF CONTROLLER & ASSET VERIFICATION ===")
    required_gifs = [
        "cyn_idle.gif",
        "cyn_tilt_head.gif",
        "cyn_glitch.gif",
        "cyn_solver_x.gif",
        "cyn_creepy_smile.gif",
        "cyn_curtsy.gif",
        "cyn_reach.gif",
        "cyn_inspect.gif",
        "cyn_sleep.gif",
    ]

    for gif_name in required_gifs:
        gif_file = ASSETS_CYN / gif_name
        assert gif_file.exists(), f"Missing required GIF asset: {gif_name}"
        assert gif_file.stat().st_size > 1000, f"Corrupted/Empty GIF: {gif_name}"
        print(f"Asset verified: {gif_name} ({gif_file.stat().st_size} bytes) OK")

    # Test state tag parsing
    text = "[state:cyn_solver_x.gif] <audio: static_burst> Halt. Action [TARGET] will modify disk contents."
    parsed = AudioDspParser.parse_message(text)
    assert parsed.state_gif == "cyn_solver_x.gif"
    assert "cyn_solver_x.gif" in parsed.state_gifs
    assert parsed.level_priority == 1
    assert "Halt" in parsed.clean_speech_text
    print("Tag '[state:cyn_solver_x.gif]' parsing & priority resolution: OK")

    # Test 3D to 2D GIF inference
    inferred = AudioDspParser.infer_gif_from_3d(["head_twitch_jitter"], ["error_glitch"], [])
    assert inferred == "cyn_glitch.gif"
    print("Inference 3D -> 2D GIF: OK")

    print("-> 2D GIF Controller & Asset Library PASSED!\n")


if __name__ == "__main__":
    test_parser()
    test_visor_mapping()
    test_safety_gate()
    test_telemetry()
    test_edition_startup_sequences()
    test_2d_gif_controller()
    print("==================================================")
    print("ALL PROJECT CYN SUBSYSTEM & 2D GIF TESTS PASSED!")
    print("==================================================")
