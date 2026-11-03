"""Diagnostic and Verification Suite for Project CYN.

Tests:
1. Audio DSP tag extraction (<pitch: ...>, <audio: ...>, <rate: ...>)
2. Kinematics tag parsing ([anim:...], [visor:...], [blend:...], [physics:...])
3. Two-Phase Authorization Safety Gate (Halt / Confirm / Abort)
4. Visor sprite atlas mapping (0-6)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from audio_dsp_parser import AudioDspParser
from system_safety_gate import SafetyGate
from telemetry_receiver import TelemetryManager


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
    print("-> Telemetry test PASSED!\n")


if __name__ == "__main__":
    test_parser()
    test_visor_mapping()
    test_safety_gate()
    test_telemetry()
    print("========================================")
    print("ALL PROJECT CYN SUBSYSTEM TESTS PASSED!")
    print("========================================")
