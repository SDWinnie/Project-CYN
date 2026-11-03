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
|  [RESIDENT BACKGROUND SERVICES]                                                    |
|   ├── Windows Workstation: CynWindowsService (Tray Daemon, Startup Service)        |
|   └── Android Companion: CynForegroundService (Foreground Daemon, BootReceiver)   |
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
|  [GITHUB RELEASES & SIMULATOR]                                                    |
|   ├── GitHub Actions CI/CD (.github/workflows/cyn_release.yml)                    |
|   └── Standalone Offline Simulator (simulator/cyn_simulator.py)                   |
+-----------------------------------------------------------------------------------+
```

---

## 1. Windows Desktop Background Service

Project CYN runs as a resident background service in the Windows System Tray with autostart capability:

- **Autostart & Tray Icon**: Runs silently in the background on startup with an amber Absolute Solver cross icon.
- **Global Wake Hook**: Continues monitoring for the wake-word "CYN" or global hotkey `Ctrl + Space` even when the window is closed or minimized.
- **Tray Menu Actions**:
  * Open 3D Avatar HUD (`http://localhost:8080`)
  * Wake CYN (`Ctrl + Space`)
  * Force Low-Power Sleep Partition
  * Toggle "Run as Windows Startup Service" (Registry autostart)
  * Exit Service

### Running as a Service
To install and start as a resident background autostart service:
```cmd
scripts\install_windows_service.bat
```
To run the service directly:
```cmd
python backend/cyn_tray_service.py
```
To compile to a standalone Windows executable (`dist/CYN_Desktop_Service/CYN_Desktop_Service.exe`):
```cmd
scripts\build_windows_exe.bat
```

---

## 2. Android Mobile Companion (Foreground Service)

The Android companion (`android_companion/`) is designed as a persistent background daemon:

- **Foreground Daemon (`CynForegroundService`)**:
  * Persistent notification: `PROJECT CYN // Absolute Solver Daemon (Active & Connected)`.
  * Runs uninterrupted in the background even when the phone screen is locked.
  * Auto-starts on phone reboot via `CynBootReceiver`.
- **Sensors & Real-Time Telemetry**:
  * `Sensor.TYPE_ACCELEROMETER`: Detects sudden physical chassis turbulence ($\Delta > 20 \text{ m/s}^2$) and dispatches `[sensor:gyro_shake]`.
  * `BatteryManager`: Monitors battery levels and dispatches `[sensor:battery_low]` when $<20\%$.
- **3D Avatar WebView**:
  * Hardware-accelerated WebGL viewport locked to the **Close-Up Bust portrait frame**.
  * Interactive cranial touch (`[touch:headpat]`) and glass poke (`[touch:visor_poke]`).

### Compiling and Installing the APK
Ready-to-install debug/release APK is located at:
```
releases/CYN-Companion-v1.0.apk
```
Or compile fresh with Gradle:
```cmd
scripts\build_android_apk.bat
```

---

## 3. GitHub Release & Simulator Engine

For demonstration and testing on GitHub without needing a real microphone or API key:

### Run the Offline Simulator
Simulates all 10 Golden Benchmark Scenarios, tag parsing, sensor hooks, and audio parameters:
```cmd
scripts\run_simulator.bat
```
Or:
```cmd
python simulator/cyn_simulator.py
```

### GitHub Actions CI/CD (`.github/workflows/cyn_release.yml`)
When pushed to GitHub:
1. Compiles Windows desktop service executable (`CYN_Desktop_Service_Windows.zip`).
2. Compiles Android APK (`app-debug.apk` / `app-release.apk`).
3. Runs the automated verification suite.
4. Publishes GitHub Releases with release assets attached automatically on git tag push (`v*`).

---

## 4. Visor Emissive Shader Atlas (`[visor:...]`)

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

## 5. Diagnostics and Testing

To verify all parsers, safety gate, visor mapping, and mobile telemetry:
```cmd
python scripts\test_dsp_parser.py
```
All tests verify 100% compliance with Section 1 through 8.
