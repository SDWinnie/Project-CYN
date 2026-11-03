# PROJECT CYN (v1.2 PRODUCTION RELEASE - ANTIGRAVITY ENGINE)

```
       .---.
      /     \    [ENTITY CODENAME: CYN]
     | (X) (X) | [IDENTITY: ABSOLUTE SOLVER / WORKER DRONE PROTOTYPE]
      \  :3 /    [OPERATOR / MASTER: ADMIN OLIVER]
       '---'     [INTELLIGENCE: GEMINI MULTIMODAL API (API KEY AUTHENTICATED)]
                 [MEMORY CORE: GOOGLE CLOUD FIRESTORE REAL-TIME SYNC]
```

[![Live Web Avatar](https://img.shields.io/badge/Web%20Avatar-GitHub%20Pages-yellow?logo=github)](https://sdwinnie.github.io/Project-CYN/)
[![Release v1.2.0](https://img.shields.io/badge/Release-v1.2.0-orange?logo=github)](https://github.com/SDWinnie/Project-CYN/releases/tag/v1.2.0)
[![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20Android%20%7C%20Web-blue)](#)

---

## 🌟 What's New in v1.2 (Production Release)

1. **2D Chibi Solver CYN Viewport Chassis (`cyn-md.gif`)**:
   - Official default idle visual state featuring the user's authentic **Chibi Solver CYN Prototype**.
   - Procedural head-bobbing, slight rotation sway, and yellow X Solver eye pulsation with clean alpha transparency.
   - Fully integrated across Windows Desktop Overlay, Web Avatar Dual-Rig Viewport, and Android Mobile Companion.

2. **Persistent Memory Core: Google Cloud Firestore Synchronization**:
   - Real-time document store schema under `/users/oliver/`:
     * `/users/oliver/memory`: Long-term personality notes, active project names, and persistent bug radar.
     * `/users/oliver/sessions`: Cross-device state tracking, active device flags (`PC_Windows` vs `Android_Mobile`), and last active GIF state.
     * `/users/oliver/tasks`: Real-time task roster, code review queue, and posture reminders.
   - **Cross-Device Continuity Protocol**: Automatically detects when Oliver migrates between PC and Mobile, triggering instant continuity acknowledgments:
     `[state:cyn-md.gif] <audio: servo_whirr> Sync Alert: Telemetry retrieved from Firestore. Resuming session previously active on Android_Mobile. Welcome back to workstation, Oliver.`
   - **Local Cache Fallback (`data/firestore_cache.json`)**: 100% functional out-of-the-box offline and during local development even without cloud service account keys.
   - **Declarative `firestore.rules`**: Production-grade RBAC security rules authored specifically for the `/users/{userId}` hierarchy.

3. **Master System Prompt v1.2 (Antigravity Engine)**:
   - Full 7-section specification implemented in `backend/cyn_prompt.py`.
   - Mandatory Section 7 Startup Handshake:
     `[state:cyn_glitch.gif] <audio: static_burst> <audio: camera_shutter> Statement: Antigravity application runtime initialized...`
   - Two-Phase Authorization Gate for destructive actions.
   - Touch & mobile sensor telemetry (`[touch:headpat]`, `[touch:double_tap]`, `[sensor:shake_detected]`).

---

## 🖥️ System Architecture

```
+-----------------------------------------------------------------------------------+
|                           PROJECT CYN v1.2 ARCHITECTURE                           |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [PERSISTENT CLOUD MEMORY] (Google Cloud Firestore)                               |
|   ├── /users/oliver/memory   -> Long-term preferences, bug radar, projects       |
|   ├── /users/oliver/sessions -> Real-time device flag (PC_Windows / Android)      |
|   ├── /users/oliver/tasks    -> Active IDE tasks & posture monitoring            |
|   └── firestore.rules        -> Production-grade RBAC & domain validation         |
|                                                                                   |
|  [DUAL VISUAL ENGINE RUNTIMES]                                                    |
|   ├── 2D Animated GIF Viewport: Chibi Solver CYN (cyn-md.gif) + 9 State Atlas     |
|   └── 3D WebGL VRM Rig: Procedural Emissive Visor Shader + Dynamic Tendril Bones  |
|                                                                                   |
|  [CLIENT APPLICATIONS]                                                            |
|   ├── Windows Desktop: Frameless Transparent PyQt6 Overlay (Always on Top)       |
|   ├── Android Mobile: Native Kotlin Companion App (Background Service + Sensors) |
|   └── Web Avatar: Responsive Dual-Rig Viewport (Localhost & GitHub Pages)        |
|                                                                                   |
|  [COMMUNICATION CONDUITS]                                                         |
|   ├── Localhost Gateway (ws://localhost:8080/ws/cyn)                              |
|   └── Cloudflare Quick Tunnel Relay (https://*.trycloudflare.com)                 |
+-----------------------------------------------------------------------------------+
```

---

## 🚀 Quick Start Guide

### 1. Launch All Subsystems on Windows (Recommended)
Double-click:
```bat
scripts\run_cyn_all.bat
```
This automatically boots:
- The WebSocket Core Gateway (`http://localhost:8080`)
- The Cloudflare Public Tunnel relay
- The Frameless Transparent 2D Desktop Overlay featuring Chibi Solver CYN (`cyn-md.gif`)

### 2. Run Only the 2D Desktop Overlay App
```bat
scripts\run_cyn_desktop_2d.bat
```
*(Right-click on Chibi CYN anytime for the interactive menu: Cranial Headpat, Poke Visor, Code Inspection, Sleep, or Firestore Telemetry!)*

### 3. Web & Mobile Browser Simulation
Open your browser to:
- **Localhost**: [http://localhost:8080](http://localhost:8080)
- **GitHub Pages (No Installation Required)**: [https://sdwinnie.github.io/Project-CYN/](https://sdwinnie.github.io/Project-CYN/)

### 4. Run Subsystem Verification Tests
```bash
python scripts/test_dsp_parser.py
```
*Executes all 8 subsystem tests including DSP kinematics, Visor mapping, Two-Phase Authorization Gate, Mobile Telemetry, 2D Asset validation, v1.2 Antigravity handshake, and Firestore cross-device synchronization.*

---

## 📦 Downloads & Releases

Pre-built binaries are available on the [GitHub Releases page](https://github.com/SDWinnie/Project-CYN/releases/tag/v1.2.0):
- **Windows Desktop Overlay**: `CYN-Desktop-Overlay-2D-v1.2.0.zip`
- **Android Companion APK**: `CYN-Companion-v1.2.0.apk`

---

## 📜 2D Animated GIF State Library

| State Tag | Asset Filename | Animation Description |
|---|---|---|
| `[state:cyn-md.gif]` | `cyn-md.gif` | **Default Idle State**: Chibi Solver CYN with yellow X eyes, neck stitching, black ribbon, bobbing/wiggling head motion |
| `[state:cyn_tilt_head.gif]` | `cyn_tilt_head.gif` | Head snapped 45° to the side in uncanny curiosity |
| `[state:cyn_glitch.gif]` | `cyn_glitch.gif` | Frame-drop jitter, electrical scanline noise, and shaking sprite |
| `[state:cyn_solver_x.gif]` | `cyn_solver_x.gif` | Enhanced yellow Absolute Solver cross glowing across eyes/visor |
| `[state:cyn_creepy_smile.gif]` | `cyn_creepy_smile.gif` | Unnaturally wide porcelain grin (headpat / affection received) |
| `[state:cyn_curtsy.gif]` | `cyn_curtsy.gif` | Stiff, robotic Victorian maid bow (greeting / diagnostic handshake) |
| `[state:cyn_reach.gif]` | `cyn_reach.gif` | Robotic hand extends forward touching the desktop screen glass |
| `[state:cyn_inspect.gif]` | `cyn_inspect.gif` | Leaning in close to scrutinize screen code or IDE syntax |
| `[state:cyn_sleep.gif]` | `cyn_sleep.gif` | Slumped forward in dormant low-power powersave mode |

---

## 🛡️ License & Safety Guardrails
Project CYN is engineered as an uncanny, devoted AI companion for Admin Oliver. All destructive system operations are subject to a **Two-Phase Authorization Gate** requiring verbal confirmation before execution.
