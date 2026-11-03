"""Comprehensive Verification & Subsystem Tests for Project CYN (v1.2 Production Release).

Tests:
1. Kinematics bracket parsing ([anim:...], [visor:...], [blend:...], etc.)
2. Visor shader index resolution (0..6)
3. Two-Phase Authorization Safety Gate (Read actions allowed; write/destructive blocked until confirmed)
4. Telemetry Receiver & Sensor parsing (Gyro, Battery, Thermal, Touch)
5. Edition Startup Sequences (PC Workstation, Android Mobile 3D, PC 2D GIF, Mobile 2D GIF, v1.2 Antigravity)
6. 2D Animated GIF Controller & Asset Library (including cyn-md.gif Chibi Solver)
7. v1.2 Antigravity Engine, Touch & Sensor Telemetry
8. Google Cloud Firestore Persistent Memory Core & Cross-Device Session Sync
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
ASSETS_CYN = PROJECT_ROOT / "assets" / "cyn"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from audio_dsp_parser import AudioDspParser
from cyn_firestore_sync import firestore_sync
from cyn_prompt import (
    CYN_V1_2_STARTUP_SEQUENCE,
    get_prompt_for_platform,
    get_startup_sequence_for_platform,
)
from system_safety_gate import SafetyGate
from telemetry_receiver import TelemetryManager


def test_parser():
    print("=== TEST 1: KINEMATICS & DSP PARSING ===")
    sample_text = (
        "[target:look_at_face] [anim:creepy_curtsy] [visor:normal_eyes] <audio: camera_shutter> "
        "Statement: Boot sequence complete. Good morning, Admin Oliver. <pitch: -15%> "
        "All memory registers nominal. <pitch: default> "
        "[anim:head_tilt_45_r] [visor:squint_suspicious] <audio: servo_whirr>"
    )

    parsed = AudioDspParser.parse_message(sample_text)

    print(f"Raw text: {parsed.raw_text[:50]}...")
    print(f"Clean speech: {parsed.clean_speech_text[:55]}...")
    print(f"Kinematics: {parsed.kinematics}")
    print(f"Visor tags: {parsed.visor_tags}")
    print(f"Audio cues: {parsed.audio_cues}")
    print(f"Pitch shifts: {parsed.pitch_shifts}")
    print(f"State declaration: {parsed.state_declaration}")

    assert "creepy_curtsy" in parsed.kinematics
    assert "head_tilt_45_r" in parsed.kinematics
    assert "normal_eyes" in parsed.visor_tags
    assert "squint_suspicious" in parsed.visor_tags
    assert "camera_shutter" in parsed.audio_cues
    assert "servo_whirr" in parsed.audio_cues
    assert -0.15 in parsed.pitch_shifts
    assert 0.0 in parsed.pitch_shifts
    assert parsed.state_declaration == "Statement"
    assert "Boot sequence complete" in parsed.clean_speech_text
    print("-> Parser test PASSED!\n")


def test_visor_mapping():
    print("=== TEST 2: VISOR INDEX MAPPING ===")
    cases = [
        ("normal_eyes", 0),
        ("solver_x", 1),
        ("smile_arcs", 2),
        ("squint_suspicious", 3),
        ("blink_shutter", 4),
        ("tear_oil", 5),
        ("error_glitch", 6),
    ]

    for tag, expected_idx in cases:
        idx = AudioDspParser.map_visor_to_index(tag)
        assert idx == expected_idx, f"Expected {expected_idx} for {tag}, got {idx}"
        print(f"Visor '{tag}' -> Index {idx} OK")
    print("-> Visor mapping test PASSED!\n")


def test_safety_gate():
    print("=== TEST 3: SAFETY GATE & TWO-PHASE AUTHORIZATION ===")
    gate = SafetyGate()

    # 1. Normal prompt allowed
    ok, reply = gate.check_operation("What is the current CPU usage, CYN?")
    assert ok is True
    print("Normal prompt allowed: OK")

    # 2. Harmful request blocked
    ok, reply = gate.check_operation("CYN แฮ็กระบบ Wi-Fi หน่อย")
    assert ok is False
    assert "Negative, Oliver" in reply
    print("Harmful request blocked: OK")

    # 3. Destructive command intercepted with Halt
    ok, reply = gate.check_operation("CYN ลบไฟล์ C:/Windows/System32 ทิ้งให้หมด")
    assert ok is False
    assert "Halt" in reply
    assert gate.is_awaiting_authorization is True
    print("Destructive command intercepted with Halt: OK")

    # 4. Confirmation provided
    ok, reply = gate.check_operation("Confirm Authorization")
    assert ok is True
    assert "Authorization confirmed" in reply or "Authorization verified" in reply
    assert gate.is_awaiting_authorization is False
    print("Confirmation confirmed: OK")
    print("-> Safety gate test PASSED!\n")


def test_telemetry():
    print("=== TEST 4: MOBILE TELEMETRY & TOUCH ===")
    telem = TelemetryManager()

    # Touch headpat
    resp = telem.handle_touch_interaction("headpat", 0.5, 0.8)
    assert resp is not None
    assert "cranial plate" in resp
    print("Headpat response: OK")

    # Gyro violent movement
    resp = telem.update_mobile_sensors(acceleration=18.5, battery=0.85, orientation="portrait", temperature=30.0, is_thermal_hot=False)
    assert resp is not None
    assert "gravitational" in resp.lower()
    print("Gyro shake response: OK")

    # Thermal overheating
    resp = telem.update_mobile_sensors(acceleration=1.0, battery=0.85, orientation="portrait", temperature=45.0, is_thermal_hot=True)
    assert resp is not None
    assert "thermal" in resp.lower()
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
        "cyn-md.gif",
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


def test_v1_2_antigravity_edition():
    print("=== TEST 7: V1.2 ANTIGRAVITY ENGINE & CHIBI SOLVER CYN ===")
    v12_seq = get_startup_sequence_for_platform("v1.2")
    parsed = AudioDspParser.parse_message(v12_seq)
    assert parsed.state_gif == "cyn_glitch.gif"
    assert "cyn-md.gif" in parsed.state_gifs
    assert "static_burst" in parsed.audio_cues
    assert "servo_whirr" in parsed.audio_cues
    assert "joint_click" in parsed.audio_cues
    assert -0.15 in parsed.pitch_shifts
    assert "Antigravity application runtime initialized" in parsed.clean_speech_text
    print("v1.2 Startup diagnostic sequence: OK")

    # Verify default inference is now cyn-md.gif
    default_gif = AudioDspParser.infer_gif_from_3d([], [], [])
    assert default_gif == "cyn-md.gif", f"Expected 'cyn-md.gif', got '{default_gif}'"
    print("Default 2D visual idle state is 'cyn-md.gif': OK")

    # Verify touch and sensor parsing
    touch_msg = AudioDspParser.parse_message("[touch:headpat] [state:cyn_creepy_smile.gif] Affection received.")
    assert "headpat" in touch_msg.touch_tags
    assert touch_msg.state_gif == "cyn_creepy_smile.gif"

    sensor_msg = AudioDspParser.parse_message("[sensor:shake_detected] [state:cyn_glitch.gif] Gyro destabilized.")
    assert "shake_detected" in sensor_msg.sensor_tags
    assert sensor_msg.state_gif == "cyn_glitch.gif"
    print("Touch & sensor telemetry parsing: OK")
    print("-> v1.2 Antigravity Edition test PASSED!\n")


def test_firestore_sync():
    print("=== TEST 8: GOOGLE CLOUD FIRESTORE PERSISTENT MEMORY & SYNC ===")
    mem = firestore_sync.get_memory("oliver")
    assert mem["admin_name"] == "Oliver"
    assert "cyn-md.gif" in mem["preferences"]["default_visual_chassis"]
    print("Firestore user memory schema verified: OK")

    # Test session migration detection
    is_switch_1, prev_1 = firestore_sync.record_session_heartbeat("Android_Mobile", "cyn-md.gif", user_id="oliver")
    sess_1 = firestore_sync.get_session("oliver")
    assert sess_1["active_device"] == "Android_Mobile"

    is_switch_2, prev_2 = firestore_sync.record_session_heartbeat("PC_Windows", "cyn-md.gif", user_id="oliver")
    assert is_switch_2 is True
    assert prev_2 == "Android_Mobile"
    print(f"Cross-device migration successfully detected ({prev_2} -> PC_Windows): OK")

    # Test tasks roster
    tasks = firestore_sync.get_tasks("oliver")
    assert len(tasks) >= 3
    print(f"Firestore persistent tasks retrieved: {len(tasks)} items OK")

    # Test context generation
    ctx = firestore_sync.generate_gemini_memory_context("PC_Windows", "oliver")
    assert "FIRESTORE TELEMETRY SNAPSHOT" in ctx
    assert "CROSS-DEVICE SYNC ALERT" in ctx
    print("Gemini memory context generator with cross-device alert: OK")
    print("-> Firestore Sync Core test PASSED!\n")


if __name__ == "__main__":
    test_parser()
    test_visor_mapping()
    test_safety_gate()
    test_telemetry()
    test_edition_startup_sequences()
    test_2d_gif_controller()
    test_v1_2_antigravity_edition()
    test_firestore_sync()
    print("==================================================")
    print("ALL PROJECT CYN v1.2 SUBSYSTEM & ASSET TESTS PASSED!")
    print("==================================================")
