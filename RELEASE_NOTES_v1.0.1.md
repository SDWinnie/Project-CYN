# Project CYN v1.0.1 (Hotfix & Full-Spectrum Connectivity Edition)

## Overview
This patch release resolves local connectivity issues (`ERR_CONNECTION_REFUSED`), fixes static file serving, enhances Cloudflare public tunnel relay handling, and introduces full client-side Standalone Simulation capabilities on [GitHub Pages](https://sdwinnie.github.io/Project-CYN/).

---

## 🛠️ Key Fixes & Enhancements

### 1. Instant Startup & Elimination of `ERR_CONNECTION_REFUSED`
- **Root Cause Fixed:** Synchronous openWakeWord ONNX model downloads inside `WakeWordDetector.__init__` previously blocked `aiohttp` from binding to port 8080.
- **Resolution:** Model loading was moved to a non-blocking background daemon thread. The web server now binds and starts serving `http://localhost:8080/` in under **50ms**.

### 2. Static Root Route Direct Serving
- **Root Cause Fixed:** `add_static("/", path=STATIC_DIR, show_index=True)` defaulted to an HTML directory listing (`Index of /.`).
- **Resolution:** Explicit route added for `/` returning `web_avatar/index.html` directly.

### 3. Cloudflare Tunnel Relay Parameter Normalization
- **Resolution:** Normalized `port` vs `local_port` constructor arguments in `CloudflareTunnelRelay` and moved binary verification into a dedicated thread to prevent startup stalls.

### 4. Standalone Simulation Mode (GitHub Pages & Offline Web)
- **Live URL:** [https://sdwinnie.github.io/Project-CYN/](https://sdwinnie.github.io/Project-CYN/)
- Works out-of-the-box in standalone browsers without requiring an active local Python server.
- Built-in client-side parser, procedural Web Audio DSP engine (servo whirr, camera shutter, static burst, joint click), Web Speech synthesis, and procedural Visor shader atlas (Indices 0–6).
- Added interactive **"Connect Relay"** button on the HUD to hook into public Cloudflare tunnels dynamically.

### 5. Android Companion App (APK v1.0.1) Updates
- Updated `MainActivity.kt` with automatic protocol detection: converts `https://*.trycloudflare.com` tunnels to secure `wss://` endpoints seamlessly for the background Foreground Service daemon.
- Background sensor streaming (accelerometer/gyro, battery levels, thermal warnings, touch gestures) fully synchronized with both local LAN and public tunnel relays.

---

## 📦 Attached Release Assets
- **`CYN-Companion-v1.0.1.apk`**: Android Companion application with background Foreground Service daemon.
- **`CYN-Desktop-Service-Windows-v1.0.1.zip`**: Windows Standalone Service with System Tray manager.
