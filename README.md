# PROJECT CYN (v7.0 FULL-SPECTRUM EDITION)

```
       .---.
      /     \    [ENTITY CODENAME: CYN]
     | () () |   [IDENTITY: ABSOLUTE SOLVER / WORKER DRONE]
      \  =  /    [MASTER: ADMIN OLIVER]
       '---'     [INTELLIGENCE: GEMINI MULTIMODAL LIVE API]
```

## System Architecture

Project CYN is a full-spectrum multimodal robotic companion embodying **CYN**, the Absolute Solver Worker Drone from *Murder Drones*. Built for pair-programming, technical surveillance, and physical desktop/mobile presence.

```
+-----------------------------------------------------------------------------------+
|                           PROJECT CYN CORE ARCHITECTURE                           |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [HOST PLATFORMS]                                                                 |
|   ├── Windows Workstation (Primary Desktop Full-Torso Frame)                     |
|   └── Android Mobile Client (Portable Companion Bust Frame + Gyro / Battery)      |
|                                                                                   |
|  [LOCAL POWER & WAKE-WORD]                                                        |
|   ├── openWakeWord / RMS Acoustic Trigger ('CYN' /s/ /ih/ /n/ threshold 0.65)    |
|   └── Global Hotkey (Ctrl + Space) & 120s Inactivity Dormant Sleep Loop           |
|                                                                                   |
|  [INTELLIGENCE BACKEND]                                                           |
|   ├── Gemini Multimodal Live API ('gemini-3.8-live' WebSocket bidirectional)      |
|   ├── 16kHz Mono PCM Audio Stream + 1 FPS Optical Camera Snapshots               |
|   └── Tag & DSP Interceptor (<pitch:...>, <audio:...>, [anim:...], [visor:...])   |
|                                                                                   |
|  [3D WEBGL AVATAR RUNTIME] (Three.js WebGL + VRM 1.0)                             |
|   ├── Custom Drone Rig: Cyn_Neck_Glitch, Solver_Tendril_01-04, Ribbon_Dynamic_L/R |
|   ├── Procedural Emissive Visor Shader Atlas (7 Distinct States, 0-6)             |
|   ├── Real-Time Animation Queue Manager (Priority Level 1, 2, 3 + 250ms Slerp)    |
|   └── Damped Look-At Manager ([target:look_at_face / hands / void])              |
|                                                                                   |
|  [TWO-PHASE SAFETY GATE]                                                          |
|   └── Intercepts Destructive Ops ('Confirm Authorization' / 'Abort')              |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Quick Start Guide

### 1. Requirements
- Python 3.10+
- Modern Web Browser (Chrome, Edge, Firefox, or Android Chrome)
- `GEMINI_API_KEY` set in your environment variables:
  ```cmd
  set GEMINI_API_KEY=your_gemini_api_key_here
  ```

### 2. Launching Desktop Workspace
Run the one-click batch launcher or start the server via command line:
```cmd
scripts\run_cyn_desktop.bat
```
Or manually:
```cmd
cd backend
python app.py
```
The console will start at:
```
http://localhost:8080
```

### 3. Connecting Android Mobile Companion
1. Connect your Android phone to the same local Wi-Fi / hotspot as your PC.
2. Find your PC's local IP address (`ipconfig` in cmd, e.g., `192.168.1.50`).
3. Open `http://<YOUR_PC_IP>:8080` in Chrome on your phone.
4. The viewport automatically clamps to the **Close-Up Bust portrait frame**, enabling touch interaction (headpat / visor poke) and gyroscope shake detection.

---

## Visor Emissive Shader Atlas (`[visor:...]`)

The visor plane renders an unlit emissive procedural shader atlas:
| Index | Tag | Visual Description |
|:---:|:---|:---|
| **0** | `[visor:normal_eyes]` | Rounded yellow-amber digital pill capsules |
| **1** | `[visor:solver_x]` | Radiant yellow Absolute Solver cross sigil |
| **2** | `[visor:smile_arcs]` | Inverted curved crescent eye arcs |
| **3** | `[visor:squint_suspicious]`| Narrow horizontal scanning slits |
| **4** | `[visor:blink_shutter]` | Black unlit matrix, LEDs extinguished |
| **5** | `[visor:tear_oil]` | Black dripping viscous fluid particles |
| **6** | `[visor:error_glitch]` | Chaotic noise artifact scanlines |

---

## Real-Time Animation Queue Manager Priority

- **Level 1 (Interrupt/Emergency)**: `[visor:solver_x]`, `[anim:head_spin_180_horror]`, Safety rejections. Clears all queues instantly, plays immediately.
- **Level 2 (Expressive Gestures)**: `[anim:head_tilt_45_l/r]`, `[anim:reach_forward]`, `[anim:creepy_curtsy]`, `[anim:crawl_closer]`. FIFO sequence with smooth cross-fade.
- **Level 3 (Ambient Idle Loops)**: `[anim:idle_sway]`, breathing dynamics. Suppressed while Level 1 or 2 is active.
- **Interpolation**: Bone transforms interpolate using Slerp at `t = 250ms`. Glitch snaps (`[anim:head_twitch_jitter]`) snap at `t = 0ms` with added Gaussian noise.

---

## Diagnostics and Testing

To verify all parsers, safety gate, visor mapping, and mobile telemetry:
```cmd
python scripts\test_dsp_parser.py
```
