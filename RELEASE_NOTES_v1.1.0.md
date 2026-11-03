# Project CYN v1.1.0 (2D Animated GIF Desktop Overlay & Mobile Edition)

## 🌟 Overview
Project CYN (v7.0 Full-Spectrum Edition) now features a dual visual rig architecture:
1. **3D VRM / Three.js WebGL Runtime** (Original high-fidelity humanoid drone rig)
2. **2D Animated GIF Sprite Overlay** (Lightweight, frameless transparent desktop companion & mobile bubble widget)

---

## 🎨 2D Animated GIF Controller Library (`assets/cyn/`)
Nine procedural animated transparent background `.gif` files are included and mapped to `[state:filename.gif]`:

| GIF Asset | Emotional State & Kinematics | Trigger Conditions |
| :--- | :--- | :--- |
| `cyn_idle.gif` | Neutral uncanny standing loop, slight breathing sway | Default idle, listening, standard replies |
| `cyn_tilt_head.gif` | 45-degree robotic curious head snap | Questioning, scanning code, data queries |
| `cyn_glitch.gif` | Rapid shaking, frame-drop jitter, scanline distortion | System boot, gyro shake, sensor disturbances |
| `cyn_solver_x.gif` | Yellow Absolute Solver glowing cross/orbit across visor | Safety alerts, bug interception, operation halt |
| `cyn_creepy_smile.gif` | Unnaturally wide, rigid porcelain smile with curved arcs | Acknowledgment, headpat reaction, pleased drone |
| `cyn_curtsy.gif` | Stiff, robotic maid bow / curtsy | Greetings, diagnostic completion, status report |
| `cyn_reach.gif` | Hand/claw extends forward touching screen glass | Attentive listening, code touch, screen glass tap |
| `cyn_inspect.gif` | Leans down close to inspect code / screen details | Syntax debugging, hardware scan, fatigue check |
| `cyn_sleep.gif` | Slumped forward, eye display shut off (dormant mode) | Low-battery, late-night sleep mode, dormancy |

---

## 💻 Windows Native PyQt Desktop Overlay App (`desktop_overlay_2d/`)
- **Frameless & Translucent:** Seamlessly floats directly on top of Windows with zero window border (`Qt.FramelessWindowHint`, `Qt.WA_TranslucentBackground`).
- **Draggable Anywhere:** Click and drag CYN anywhere across multiple monitors.
- **Floating Cyberpunk Speech Balloon:** Displays operational status declarations (`Statement:`, `Diagnostic:`, `Warning:`) and clean speech text with auto-hiding timer.
- **Interactive Context Menu:** Right-click CYN for instant actions (Wake, Headpat, Poke Visor, Code Inspection, Absolute Solver X, Sleep, Snap to Bottom-Right).
- **Launcher:** Quick-launch via `scripts/run_cyn_desktop_2d.bat`.

---

## 🌐 Web Avatar Dual-Rig Mode (GitHub Pages)
- **Live URL:** [https://sdwinnie.github.io/Project-CYN/](https://sdwinnie.github.io/Project-CYN/)
- Includes a 1-click **"Mode: 3D VRM / 2D GIF"** toggle button in the HUD.
- Full client-side simulation, Web Audio DSP cues, and SpeechSynthesis support in both modes.

---

## 📱 Android Companion App Updates
- Included 2D GIF assets inside `app/src/main/assets/cyn/`.
- Foreground Service daemon handles gyroscopic shake, battery levels, thermal warnings, and touch events mapped to 2D GIF states.

---

## 📦 Attached Release Assets
- **`CYN-Desktop-Overlay-2D.zip`**: Windows Standalone 2D Transparent Desktop Overlay application bundle.
- **`CYN-Companion-v1.1.0-2DGIF.apk`**: Android Companion application with 2D GIF assets and Foreground Service daemon.
