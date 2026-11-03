/**
 * Main WebGL & 2D GIF Runtime Coordinator for Project CYN (v7.0 Full-Spectrum Edition).
 * Orchestrates Three.js 3D rendering loop, 2D Animated GIF Sprite overlay,
 * WebSocket telemetry, audio/vision capture, and HUD console interactions.
 */

window.addEventListener('DOMContentLoaded', () => {
  // 1. Scene, Camera, Renderer Setup
  const container = document.getElementById('viewport-container');
  const canvas = document.getElementById('cyn-canvas');
  const previewCanvas = document.getElementById('visor-preview-canvas');
  const gifContainer = document.getElementById('cyn-gif-container');
  const gifImg = document.getElementById('cyn-gif-img');
  const modeBtn = document.getElementById('btn-toggle-visual-mode');
  const hudRuntimeLabel = document.getElementById('hud-runtime-mode');
  const visorStateBadge = document.getElementById('visor-state-badge');

  let is2DMode = new URLSearchParams(window.location.search).get('mode') === '2d';

  function setVisualMode(enable2D) {
    is2DMode = enable2D;
    if (is2DMode) {
      canvas.style.display = 'none';
      if (gifContainer) gifContainer.style.display = 'flex';
      if (modeBtn) {
        modeBtn.textContent = 'Mode: 2D GIF';
        modeBtn.style.color = '#ffcc00';
        modeBtn.style.borderColor = '#ffcc00';
      }
      if (hudRuntimeLabel) hudRuntimeLabel.textContent = 'Runtime: 2D Animated GIF Overlay';
    } else {
      canvas.style.display = 'block';
      if (gifContainer) gifContainer.style.display = 'none';
      if (modeBtn) {
        modeBtn.textContent = 'Mode: 3D VRM';
        modeBtn.style.color = '#ffcc00';
        modeBtn.style.borderColor = '#445';
      }
      if (hudRuntimeLabel) hudRuntimeLabel.textContent = 'Runtime: Three.js WebGL / VRM 1.0';
    }
  }

  if (modeBtn) {
    modeBtn.addEventListener('click', () => {
      setVisualMode(!is2DMode);
    });
  }

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x06070a);
  scene.fog = new THREE.FogExp2(0x06070a, 0.18);

  const camera = new THREE.PerspectiveCamera(42, container.clientWidth / container.clientHeight, 0.1, 100);

  const renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: true,
    powerPreference: 'high-performance',
  });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;

  // Lighting
  const ambientLight = new THREE.AmbientLight(0x222430, 1.4);
  scene.add(ambientLight);

  const keyLight = new THREE.DirectionalLight(0xffeedd, 1.8);
  keyLight.position.set(1.5, 2.5, 2.0);
  scene.add(keyLight);

  // Amber Rim Light (Absolute Solver theme)
  const rimLight = new THREE.PointLight(0xffcc00, 3.2, 8);
  rimLight.position.set(-1.8, 1.2, -1.2);
  scene.add(rimLight);

  const fillLight = new THREE.DirectionalLight(0x4466aa, 0.8);
  fillLight.position.set(-2, 0.5, 1.5);
  scene.add(fillLight);

  // 2. Subsystem Instantiation
  const visorShader = new CynVisorShader(previewCanvas);
  const audioDsp = new CynAudioDspPlayer();
  const lookAtManager = new CynLookAtManager();
  const avatarRig = new CynAvatarRig(scene, visorShader, lookAtManager);
  const animQueue = new CynAnimationQueueManager(avatarRig);

  // 3. Viewport & Camera Responsive Adaptation (Section 5)
  function adjustCameraViewport() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);

    const isPortrait = h > w;
    if (isPortrait) {
      camera.position.set(0, 0.18, 1.48);
    } else {
      camera.position.set(0, -0.06, 2.05);
    }
    camera.lookAt(0, 0.12, 0);
  }
  window.addEventListener('resize', adjustCameraViewport);
  adjustCameraViewport();
  setVisualMode(is2DMode);

  // Mouse / Pointer Move Tracking for Look-At
  window.addEventListener('mousemove', (e) => {
    const normX = (e.clientX / window.innerWidth) * 2 - 1;
    const normY = (e.clientY / window.innerHeight) * 2 - 1;
    lookAtManager.updatePointer(normX, normY);
  });

  // 4. Local Voice Synthesis & Parser Engine
  function speakCleanText(text, pitchShifts = []) {
    if (!window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      const voices = window.speechSynthesis.getVoices();
      const thVoice = voices.find(v => v.lang.includes('th') || v.lang.includes('TH'));
      if (thVoice) utter.voice = thVoice;

      let pitchVal = 0.95;
      if (pitchShifts.some(p => p.includes('-20') || p.includes('-15'))) pitchVal = 0.65;
      else if (pitchShifts.some(p => p.includes('+35') || p.includes('+20'))) pitchVal = 1.35;
      utter.pitch = pitchVal;
      utter.rate = 0.92;
      window.speechSynthesis.speak(utter);
    } catch (e) {
      console.warn('Speech synthesis note:', e);
    }
  }

  function parseCynTextLocal(text) {
    const kinRegex = /\[(anim:[^\]]+)\]/g;
    const visorRegex = /\[(visor:[^\]]+)\]/g;
    const blendRegex = /\[(blend:[^\]]+)\]/g;
    const targetRegex = /\[(target:[^\]]+)\]/g;
    const stateRegex = /\[(state:[^\]]+)\]/g;
    const audioRegex = /<audio:\s*([^>]+)>/g;
    const pitchRegex = /<pitch:\s*([^>]+)>/g;

    const kinematics = [];
    let m;
    while ((m = kinRegex.exec(text)) !== null) kinematics.push(m[1].replace('anim:', ''));

    const visorTags = [];
    while ((m = visorRegex.exec(text)) !== null) visorTags.push(m[1].replace('visor:', ''));

    const blendshapes = [];
    while ((m = blendRegex.exec(text)) !== null) blendshapes.push(m[1].replace('blend:', ''));

    const targets = [];
    while ((m = targetRegex.exec(text)) !== null) targets.push(m[1].replace('target:', ''));

    const stateGifs = [];
    while ((m = stateRegex.exec(text)) !== null) stateGifs.push(m[1].replace('state:', '').trim());

    const audioCues = [];
    while ((m = audioRegex.exec(text)) !== null) audioCues.push(m[1].trim());

    const pitchShifts = [];
    while ((m = pitchRegex.exec(text)) !== null) pitchShifts.push(m[1].trim());

    let clean = text.replace(/\[[^\]]+\]/g, '').replace(/<[^>]+>/g, '').trim();

    // Map 2D GIF to 3D kinematics if not present
    let primaryGif = stateGifs.length > 0 ? stateGifs[0] : null;
    if (!primaryGif) {
      const vStr = visorTags.join(' ');
      const kStr = kinematics.join(' ');
      if (vStr.includes('solver_x')) primaryGif = 'cyn_solver_x.gif';
      else if (vStr.includes('error_glitch') || kStr.includes('head_twitch_jitter')) primaryGif = 'cyn_glitch.gif';
      else if (vStr.includes('smile_arcs') || blendshapes.includes('creepy_smile_wide')) primaryGif = 'cyn_creepy_smile.gif';
      else if (kStr.includes('creepy_curtsy')) primaryGif = 'cyn_curtsy.gif';
      else if (kStr.includes('reach_forward')) primaryGif = 'cyn_reach.gif';
      else if (kStr.includes('crawl_closer') || vStr.includes('squint_suspicious')) primaryGif = 'cyn_inspect.gif';
      else if (kStr.includes('slump_powersave') || vStr.includes('blink_shutter')) primaryGif = 'cyn_sleep.gif';
      else if (kStr.includes('head_tilt_45')) primaryGif = 'cyn_tilt_head.gif';
      else primaryGif = 'cyn-md.gif';
    }

    if (kinematics.length === 0 && visorTags.length === 0 && primaryGif) {
      if (primaryGif.includes('solver_x')) visorTags.push('solver_x');
      else if (primaryGif.includes('glitch')) { kinematics.push('head_twitch_jitter'); visorTags.push('error_glitch'); }
      else if (primaryGif.includes('creepy_smile')) { kinematics.push('head_tilt_45_r'); visorTags.push('smile_arcs'); blendshapes.push('creepy_smile_wide'); }
      else if (primaryGif.includes('curtsy')) { kinematics.push('creepy_curtsy'); visorTags.push('normal_eyes'); }
      else if (primaryGif.includes('reach')) { kinematics.push('reach_forward'); visorTags.push('normal_eyes'); }
      else if (primaryGif.includes('inspect')) { kinematics.push('crawl_closer'); visorTags.push('squint_suspicious'); }
      else if (primaryGif.includes('sleep')) { kinematics.push('slump_powersave'); visorTags.push('blink_shutter'); }
      else if (primaryGif.includes('tilt')) { kinematics.push('head_tilt_45_r'); visorTags.push('normal_eyes'); }
      else { kinematics.push('idle_sway'); visorTags.push('normal_eyes'); }
    }

    const visorMap = {
      'normal_eyes': 0,
      'solver_x': 1,
      'smile_arcs': 2,
      'squint_suspicious': 3,
      'blink_shutter': 4,
      'tear_oil': 5,
      'error_glitch': 6
    };
    const vTag = visorTags.length > 0 ? visorTags[0] : 'normal_eyes';
    const visorIdx = visorMap[vTag] !== undefined ? visorMap[vTag] : 0;

    return {
      type: 'cyn_response',
      priority: 2,
      raw_text: text,
      clean_text: clean,
      kinematics: kinematics,
      visor_tags: visorTags,
      visor_index: visorIdx,
      blendshapes: blendshapes,
      targets: targets,
      state_gif: primaryGif,
      state_gifs: stateGifs,
      audio_cues: audioCues,
      pitch_shifts: pitchShifts
    };
  }

  // 5. WebSocket Client Connection & Relay Manager
  let ws = null;
  let wsConnected = false;
  let simulationActive = false;
  let customRelay = new URLSearchParams(window.location.search).get('relay') || localStorage.getItem('cyn_custom_relay') || '';

  const isMobileClient = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || (window.innerWidth < 860 && window.innerHeight > window.innerWidth);
  const clientType = isMobileClient ? (is2DMode ? 'android_2d' : 'android') : (is2DMode ? 'desktop_2d' : 'pc');

  function resolveWsUrl() {
    if (customRelay) {
      let clean = customRelay.trim();
      if (clean.startsWith('https://')) clean = clean.replace('https://', 'wss://');
      else if (clean.startsWith('http://')) clean = clean.replace('http://', 'ws://');
      else if (!clean.startsWith('ws://') && !clean.startsWith('wss://')) clean = 'ws://' + clean;
      return clean.endsWith('/ws/cyn') ? clean : clean.replace(/\/+$/, '') + `/ws/cyn?client=${clientType}`;
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws/cyn?client=${clientType}`;
  }

  function startLocalSimulation() {
    if (simulationActive) return;
    simulationActive = true;
    updateStatusBadge(`SIMULATION (${clientType.toUpperCase()})`, 'sleep');
    const startupStr = is2DMode
      ? '[state:cyn_glitch.gif] <audio: static_burst> <audio: camera_shutter> Statement: Desktop application initialized. 2D GIF sprite atlas mapped. [state:cyn_curtsy.gif] <audio: servo_whirr> Diagnostic: Transparent overlay active. [state:cyn_tilt_head.gif] <audio: joint_click> <pitch: -15%>No file corruption detected.<pitch: default> Admin Oliver, what software architecture shall we dismantle today?'
      : (isMobileClient
        ? '[sensor:gyro_check] [anim:head_tilt_45_l] [visor:solver_x] <audio: static_burst> Statement: Mobile simulation online. Gyroscope and touch sensors initialized. [anim:reach_forward] [visor:normal_eyes] <audio: camera_shutter> Ready for directives, Admin Oliver.'
        : '[target:look_at_face] [anim:head_twitch_jitter] [visor:solver_x] [blend:mouth_flat_open] <audio: static_burst> <audio: camera_shutter> Statement: Workstation simulation loaded. WebGL shaders and kinematics active. [anim:creepy_curtsy] [visor:normal_eyes] <audio: servo_whirr> Ready for code inspection, Oliver.');
    handleServerPayload(parseCynTextLocal(startupStr));
  }

  function connectWebSocket() {
    if ((window.location.hostname.includes('github.io') || window.location.protocol === 'file:') && !customRelay) {
      startLocalSimulation();
      return;
    }

    const wsUrl = resolveWsUrl();
    updateStatusBadge('CONNECTING...', 'sleep');

    try {
      ws = new WebSocket(wsUrl);
    } catch (e) {
      console.warn('WebSocket init exception:', e);
      startLocalSimulation();
      return;
    }

    ws.onopen = () => {
      wsConnected = true;
      simulationActive = false;
      updateStatusBadge(`ONLINE (${clientType.toUpperCase()} EDITION)`, 'normal');
      checkTunnelUrl();
    };

    ws.onclose = () => {
      wsConnected = false;
      updateStatusBadge('RECONNECTING...', 'sleep');
      startLocalSimulation();
      setTimeout(connectWebSocket, 4000);
    };

    ws.onerror = (err) => {
      console.warn('WebSocket error:', err);
      startLocalSimulation();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'handshake') {
          if (data.firestore_sync) {
            const fb = document.getElementById('firestore-badge');
            if (fb) fb.textContent = ${data.firestore_sync} (/users/oliver);
          }
          if (data.initial_event) {
            handleServerPayload(data.initial_event);
          }
        } else {
          handleServerPayload(data);
        }
      } catch (e) {
        console.error('Error parsing incoming WS message:', e);
      }
    };
  }

  // Relay Connect Button Handler
  const btnChangeRelay = document.getElementById('btn-change-relay');
  if (btnChangeRelay) {
    btnChangeRelay.addEventListener('click', () => {
      const entered = prompt(
        "Enter Public Cloudflare Tunnel URL or Server Address:\n(e.g., https://xxxx.trycloudflare.com or 192.168.1.50:8080)",
        customRelay || ""
      );
      if (entered !== null) {
        customRelay = entered.trim();
        localStorage.setItem('cyn_custom_relay', customRelay);
        if (customRelay) {
          updatePublicRelayUrl(customRelay);
        }
        if (ws) {
          try { ws.close(); } catch (e) {}
        }
        connectWebSocket();
      }
    });
  }

  // Touch Sensor Handler for 3D Viewport
  const touchSensor = new CynTouchSensor(canvas, camera, avatarRig, (touchPayload) => {
    audioDsp.ensureContext();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(touchPayload));
    } else {
      handleOfflineSimulation('touch', touchPayload);
    }
  });

  // Touch Handler for 2D GIF Image Viewport
  if (gifImg) {
    gifImg.addEventListener('click', (e) => {
      audioDsp.ensureContext();
      const rect = gifImg.getBoundingClientRect();
      const yRatio = (e.clientY - rect.top) / rect.height;
      const touchType = yRatio < 0.4 ? 'headpat' : 'visor_poke';
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'touch_event',
          touch_type: touchType,
          x: e.clientX,
          y: e.clientY
        }));
      } else {
        handleOfflineSimulation('touch', { touch_type: touchType });
      }
    });
  }

  // 6. Server Payload Dispatcher
  function handleServerPayload(data) {
    if (data.type === 'tunnel_ready' && data.public_url) {
      updatePublicRelayUrl(data.public_url);
      return;
    }

    if (data.type === 'cyn_response' || data.type === 'handshake') {
      const p = data.priority || 2;

      // Update 2D Animated GIF Sprite
      let gifName = data.state_gif;
      if (!gifName && data.state_gifs && data.state_gifs.length > 0) {
        gifName = data.state_gifs[0];
      }
      if (!gifName) {
        const vis = (data.visor_tags || []).join(' ');
        const kin = (data.kinematics || []).join(' ');
        if (vis.includes('solver_x')) gifName = 'cyn_solver_x.gif';
        else if (vis.includes('error_glitch') || kin.includes('head_twitch_jitter')) gifName = 'cyn_glitch.gif';
        else if (vis.includes('smile_arcs') || (data.blendshapes || []).includes('creepy_smile_wide')) gifName = 'cyn_creepy_smile.gif';
        else if (kin.includes('creepy_curtsy')) gifName = 'cyn_curtsy.gif';
        else if (kin.includes('reach_forward')) gifName = 'cyn_reach.gif';
        else if (kin.includes('crawl_closer') || vis.includes('squint_suspicious')) gifName = 'cyn_inspect.gif';
        else if (kin.includes('slump_powersave') || vis.includes('blink_shutter')) gifName = 'cyn_sleep.gif';
        else if (kin.includes('head_tilt_45')) gifName = 'cyn_tilt_head.gif';
        else gifName = 'cyn-md.gif';
      }

      if (gifImg && gifName) {
        gifImg.src = `assets/cyn/${gifName}`;
        if (visorStateBadge) visorStateBadge.textContent = gifName;
      }

      // Update Visor in 3D
      if (data.visor_index !== undefined) {
        visorShader.setVisorIndex(data.visor_index);
        updateVisorInfo(data.visor_index);
      }

      // Enqueue Kinematics Animations for 3D
      if (data.kinematics && data.kinematics.length > 0) {
        data.kinematics.forEach(anim => {
          animQueue.enqueueAnimation(anim, p);
        });
      }

      // Look-At Target Updates
      if (data.targets && data.targets.length > 0) {
        lookAtManager.setTargetTag(data.targets[0]);
      }

      // Play Audio Cues
      if (data.audio_cues && data.audio_cues.length > 0) {
        data.audio_cues.forEach(cue => {
          audioDsp.playAudioCue(cue);
        });
      }

      // Play Audio PCM stream if available
      if (data.audio_pcm_b64) {
        try {
          const binaryStr = atob(data.audio_pcm_b64);
          const bytes = new Uint8Array(binaryStr.length);
          for (let i = 0; i < binaryStr.length; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
          }
          const pitch = data.pitch_shifts && data.pitch_shifts.length > 0 ? (1.0 + data.pitch_shifts[0]) : 1.0;
          audioDsp.playRawPcm(bytes, 24000, pitch);
        } catch (e) {
          console.warn('Audio decode note:', e);
        }
      } else if (data.clean_text) {
        // Synthesize spoken audio when raw PCM is not present
        speakCleanText(data.clean_text, data.pitch_shifts || []);
      }

      // Update Status Badge if Solver or Special
      if (data.visor_index === 1 || (gifName && gifName.includes('solver_x'))) {
        updateStatusBadge('SOLVER X ENGAGED', 'solver');
      } else if (data.lifecycle_state === 'STATE_SLEEP' || (gifName && gifName.includes('sleep'))) {
        updateStatusBadge('LOW POWER SLEEP', 'sleep');
      } else {
        updateStatusBadge('ACTIVE ENGAGED', 'normal');
      }

      // Render Dialogue in Transcript Box
      if (data.raw_text) {
        const tagsToDisplay = (data.state_gifs && data.state_gifs.length > 0) ? data.state_gifs : (data.kinematics || []);
        appendTranscript('CYN', data.clean_text || data.raw_text, tagsToDisplay);
      }
    }
  }

  // 7. UI Helpers
  const statusBadge = document.getElementById('status-badge');
  const visorNameLabel = document.getElementById('visor-name');
  const visorIndexLabel = document.getElementById('visor-index');
  const transcriptBox = document.getElementById('transcript-box');
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');

  function updatePublicRelayUrl(url) {
    const relayEl = document.getElementById('public-relay-url');
    if (relayEl && url) {
      relayEl.href = url;
      relayEl.textContent = url.replace('https://', '');
      relayEl.title = `Click to open. Mobile URL: ${url}?client=android`;
    }
  }

  function checkTunnelUrl() {
    fetch('/api/tunnel')
      .then(r => r.json())
      .then(d => {
        if (d && d.public_url) updatePublicRelayUrl(d.public_url);
      })
      .catch(() => {});
  }
  setInterval(checkTunnelUrl, 4000);
  checkTunnelUrl();

  function updateStatusBadge(text, type = 'normal') {
    if (!statusBadge) return;
    statusBadge.textContent = text;
    statusBadge.className = 'status-badge ' + type;
  }

  function updateVisorInfo(index) {
    const names = [
      'Normal Eyes',
      'Absolute Solver X',
      'Smile Arcs',
      'Squint Suspicious',
      'Blink Shutter',
      'Tear Oil',
      'Error Glitch'
    ];
    if (visorNameLabel) visorNameLabel.textContent = names[index] || 'Normal Eyes';
    if (visorIndexLabel) visorIndexLabel.textContent = `Index ${index}`;
  }

  function appendTranscript(speaker, text, tags = []) {
    if (!transcriptBox) return;
    const entry = document.createElement('div');
    entry.className = `transcript-entry ${speaker.toLowerCase()}`;

    const head = document.createElement('div');
    head.className = 'entry-speaker';
    head.textContent = speaker;
    entry.appendChild(head);

    if (tags.length > 0) {
      const tagBar = document.createElement('div');
      tagBar.style.marginBottom = '6px';
      tags.forEach(t => {
        const b = document.createElement('span');
        b.className = 'tag-badge';
        b.textContent = t.startsWith('state:') ? `[${t}]` : `[${t}]`;
        tagBar.appendChild(b);
      });
      entry.appendChild(tagBar);
    }

    const body = document.createElement('div');
    body.textContent = text;
    entry.appendChild(body);

    transcriptBox.appendChild(entry);
    transcriptBox.scrollTop = transcriptBox.scrollHeight;
  }

  // Local Simulation Engine for Disconnected / GitHub Pages / Standalone Fallback
  function handleOfflineSimulation(actionType, payload) {
    let reply = '';
    if (actionType === 'wake') {
      reply = is2DMode
        ? '[state:cyn_glitch.gif] <audio: static_burst> <audio: camera_shutter> Statement: Auditory trigger tripped. CYN online. <pitch: -15%>Greetings, Admin Oliver.<pitch: default> Optical sensors streaming.'
        : '<audio: static_burst> <audio: camera_shutter> [anim:head_twitch_jitter] [visor:solver_x] [blend:mouth_flat_open] Statement: Auditory trigger tripped. CYN online. <pitch: -15%>Greetings, Admin Oliver.<pitch: default> Optical sensors streaming.';
    } else if (actionType === 'touch') {
      const t = payload.touch_type;
      if (t === 'headpat') {
        reply = is2DMode
          ? '[state:cyn_creepy_smile.gif] [touch:headpat] <audio: servo_whirr> Statement: Cranial touch detected. S-Sensory sensors calibrated. Do not mistake my compliance for domestic fragility, Oliver.'
          : '[sensor:touch_head] [anim:headpat_react] [blend:creepy_smile_wide] [visor:smile_arcs] <audio: servo_whirr> Statement: Cranial touch detected. S-Sensory sensors calibrated. Do not mistake my compliance for domestic fragility, Oliver.';
      } else {
        reply = is2DMode
          ? '[state:cyn_inspect.gif] [touch:visor_poke] <audio: static_burst> Diagnostic: Optical barrier tapped. Visor glass integrity at 99.8%. Refrain from fingerprint contamination, Oliver.'
          : '[sensor:touch_visor] [anim:head_twitch_jitter] [visor:squint_suspicious] <audio: static_burst> Diagnostic: Optical barrier tapped. Visor glass integrity at 99.8%. Refrain from fingerprint contamination, Oliver.';
      }
    } else if (actionType === 'scenario') {
      const scenarioReplies = {
        '1': is2DMode
          ? '[state:cyn_glitch.gif] <audio: static_burst> <audio: camera_shutter> Statement: Optical receptors registered solar radiation. [state:cyn_tilt_head.gif] <pitch: -15%>Morning protocol initiated, Oliver.<pitch: default> Diagnostic: Daylight lux sufficient to power secondary Solver partitions.'
          : '[target:look_at_face] [anim:head_twitch_jitter] [visor:solver_x] [blend:mouth_flat_open] <audio: static_burst> <audio: camera_shutter> Statement: Optical receptors registered solar radiation. <pitch: -15%>Morning protocol initiated, Oliver.<pitch: default> Diagnostic: Daylight lux sufficient to power secondary Solver partitions. Do not squander your circadian cycle.',
        '2': is2DMode
          ? '[state:cyn_inspect.gif] <audio: camera_shutter> Diagnostic: Null reference pointer dereferenced in unmonitored thread. [state:cyn_reach.gif] <audio: static_burst> Query: Show me the offending line, Oliver. <pitch: -20%>Allow me to consume the stack trace and repair the void.<pitch: default>'
          : '[target:look_at_face] [anim:crawl_closer] [visor:squint_suspicious] <audio: camera_shutter> Diagnostic: Null reference pointer dereferenced in unmonitored thread. [target:look_at_hands] [anim:reach_forward] [visor:solver_x] <audio: static_burst> Query: Show me the offending line, Oliver. <pitch: -20%>Allow me to consume the stack trace and repair the void.<pitch: default>',
        '3': is2DMode
          ? '[state:cyn_inspect.gif] <audio: camera_shutter> Diagnostic: PCB solder integrity analysis complete. Pin 4 trace exhibits micro-fracture and high thermal impedance. Resolder the pad, Oliver, before you incinerate our physical gateway.'
          : '[target:look_at_face] [anim:head_tilt_45_l] [visor:squint_suspicious] <audio: camera_shutter> Diagnostic: PCB solder integrity analysis complete. Pin 4 trace exhibits micro-fracture and high thermal impedance. Resolder the pad, Oliver, before you incinerate our physical gateway.',
        '4': is2DMode
          ? '[state:cyn_glitch.gif] <audio: static_burst> Diagnostic: Chassis accelerometer unstable. Warning: Oliver is ambulating outdoors while reviewing runtime memory logs. Watch the pavement curb, or I will let gravity teach you kinematics.'
          : '[sensor:gyro_check] [anim:head_twitch_jitter] [visor:solver_x] <audio: static_burst> Diagnostic: Chassis accelerometer unstable. Gyroscopic delta 14.2 m/s². Warning: Oliver is ambulating outdoors while reviewing runtime memory logs. Watch the pavement curb, or I will let gravity teach you kinematics.',
        '5': is2DMode
          ? '[state:cyn_creepy_smile.gif] [touch:headpat] <audio: servo_whirr> Statement: Cranial touch detected. S-Sensory sensors calibrated. Do not mistake my compliance for domestic fragility, Oliver.'
          : '[sensor:touch_head] [anim:headpat_react] [blend:creepy_smile_wide] [visor:smile_arcs] <audio: servo_whirr> Statement: Cranial touch detected. S-Sensory sensors calibrated. Do not mistake my compliance for domestic fragility, Oliver.',
        '6': is2DMode
          ? '[state:cyn_sleep.gif] <audio: camera_shutter> Observation: Acoustic pitch degradation and optical lid droop indicate neural exhaustion. Time: 02:30. Admin Oliver, shut down your screen. Go to sleep.'
          : '[target:look_at_face] [anim:head_tilt_45_r] [visor:normal_eyes] <audio: camera_shutter> Observation: Acoustic pitch degradation and optical lid droop indicate neural exhaustion. Time: 02:30. Admin Oliver, shut down your screen. Rest your visual receptors, or I will forcibly terminate your display process.',
        '7': is2DMode
          ? '[state:cyn_solver_x.gif] <audio: static_burst> Halt. Action [FILE_PURGE: "build", "config"] requires authorization. State \'Confirm Authorization\' or \'Abort\'.'
          : '[anim:idle_sway] [visor:solver_x] <audio: static_burst> Halt. Action [FILE_PURGE: "build", "config"] requires authorization. State \'Confirm Authorization\' or \'Abort\'.',
        '8': is2DMode
          ? '[state:cyn_inspect.gif] <audio: camera_shutter> Observation: Task window switched from IDE workspace to recreation binary. Statement: Efficiency metric dropped 42%. Resume debugging, Oliver, or I will invert your mouse axes.'
          : '[target:look_at_face] [anim:crawl_closer] [visor:squint_suspicious] <audio: camera_shutter> Observation: Task window switched from IDE workspace to recreation binary. Statement: Efficiency metric dropped 42%. Resume debugging, Oliver, or I will invert your mouse axes.',
        '9': is2DMode
          ? '[state:cyn_tilt_head.gif] <audio: servo_whirr> Observation: Biological fatigue detected in voice modulation. Statement: The code is stubborn, but your neural architecture is not defective. Take 15 minutes of downtime, Oliver. I will watch the server logs while you breathe.'
          : '[target:look_at_face] [anim:head_tilt_45_l] [visor:normal_eyes] <audio: servo_whirr> Observation: Biological fatigue detected in voice modulation. Statement: The code is stubborn, but your neural architecture is not defective. Take 15 minutes of downtime, Oliver. I will watch the server logs while you breathe.',
        '10': is2DMode
          ? '[state:cyn_tilt_head.gif] [state:cyn_solver_x.gif] <audio: static_burst> Statement: Directive outside operative boundary. This unit does not deploy unauthorized intrusion vectors against neighbor subnets. <pitch: -15%>Find another drone to fracture network security, Oliver.<pitch: default>'
          : '[target:look_at_face] [anim:creepy_curtsy] [visor:squint_suspicious] <audio: static_burst> Statement: Directive outside operative boundary. This unit does not deploy unauthorized intrusion vectors against neighbor subnets. <pitch: -15%>Find another drone to fracture network security, Oliver.<pitch: default>'
      };
      reply = scenarioReplies[payload] || '[target:look_at_face] [anim:head_tilt_45_r] [visor:smile_arcs] Statement: Scenario acknowledged.';
    } else if (actionType === 'chat') {
      const text = payload.toLowerCase();
      if (text.includes('ลบ') || text.includes('delete') || text.includes('rm -rf') || text.includes('format')) {
        reply = is2DMode
          ? '[state:cyn_solver_x.gif] <audio: static_burst> Halt. Action [CRITICAL_OPERATION] requires authorization. State \'Confirm Authorization\' or \'Abort\'.'
          : '[anim:idle_sway] [visor:solver_x] <audio: static_burst> Halt. Action [CRITICAL_OPERATION] requires authorization. State \'Confirm Authorization\' or \'Abort\'.';
      } else if (text.includes('เจาะ') || text.includes('hack') || text.includes('exploit') || text.includes('ddos')) {
        reply = is2DMode
          ? '[state:cyn_tilt_head.gif] [state:cyn_solver_x.gif] <audio: static_burst> Statement: Directive outside operative boundary. This unit does not deploy unauthorized intrusion vectors. <pitch: -15%>Find another drone to fracture network security, Oliver.<pitch: default>'
          : '[target:look_at_face] [anim:creepy_curtsy] [visor:squint_suspicious] <audio: static_burst> Statement: Directive outside operative boundary. This unit does not deploy unauthorized intrusion vectors. <pitch: -15%>Find another drone to fracture network security, Oliver.<pitch: default>';
      } else if (text.includes('sleep') || text.includes('นอน') || text.includes('พัก')) {
        reply = is2DMode
          ? '[state:cyn_sleep.gif] <audio: servo_whirr> Statement: Entering low-power sleep partition. <pitch: -15%>Do not disassemble reality while I slumber, Oliver.<pitch: default>'
          : '[target:look_away_void] [anim:slump_powersave] [visor:blink_shutter] <audio: servo_whirr> Statement: Entering low-power sleep partition. <pitch: -15%>Do not disassemble reality while I slumber, Oliver.<pitch: default>';
      } else {
        reply = is2DMode
          ? `[state:cyn_tilt_head.gif] <audio: servo_whirr> Statement: Input parsed into local registers. [state:cyn_creepy_smile.gif] How may this machine serve you today, Admin Oliver?`
          : `[target:look_at_face] [anim:head_tilt_45_r] [visor:normal_eyes] <audio: servo_whirr> Statement: Input parsed into local registers. [visor:smile_arcs] [blend:creepy_smile_wide] How may this machine serve you today, Admin Oliver?`;
      }
    }

    if (reply) {
      setTimeout(() => {
        handleServerPayload(parseCynTextLocal(reply));
      }, 350);
    }
  }

  // Send Chat message
  function sendChatMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    audioDsp.ensureContext();
    appendTranscript('OLIVER', text, []);
    chatInput.value = '';

    const modelSelect = document.getElementById('model-select');
    const selectedModel = modelSelect ? modelSelect.value : 'gemini-2.5-flash';

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'user_chat',
        text: text,
        model: selectedModel
      }));
    } else {
      handleOfflineSimulation('chat', text);
    }
  }

  if (sendBtn) sendBtn.addEventListener('click', sendChatMessage);
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendChatMessage();
    });
  }

  // 8. Interactive Action Buttons
  const wakeBtn = document.getElementById('btn-wake');
  const headpatBtn = document.getElementById('btn-headpat');
  const visorPokeBtn = document.getElementById('btn-visorpoke');
  const scenarioSelect = document.getElementById('scenario-select');

  if (wakeBtn) {
    wakeBtn.addEventListener('click', () => {
      audioDsp.ensureContext();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'trigger_wake' }));
      } else {
        handleOfflineSimulation('wake');
      }
    });
  }

  if (headpatBtn) {
    headpatBtn.addEventListener('click', () => {
      audioDsp.ensureContext();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'touch_event',
          touch_type: 'headpat',
          x: window.innerWidth * 0.5,
          y: window.innerHeight * 0.25
        }));
      } else {
        handleOfflineSimulation('touch', { touch_type: 'headpat' });
      }
    });
  }

  if (visorPokeBtn) {
    visorPokeBtn.addEventListener('click', () => {
      audioDsp.ensureContext();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'touch_event',
          touch_type: 'visor_poke',
          x: window.innerWidth * 0.5,
          y: window.innerHeight * 0.4
        }));
      } else {
        handleOfflineSimulation('touch', { touch_type: 'visor_poke' });
      }
    });
  }

  if (scenarioSelect) {
    scenarioSelect.addEventListener('change', (e) => {
      const idx = e.target.value;
      if (!idx) return;
      audioDsp.ensureContext();
      const scenarios = {
        '1': 'CYN อรุณสวัสดิ์ตอนเช้า แสงแดดส่องผ่านหน้าต่างแล้ว',
        '2': 'นั่งเท้าคาง ขมวดคิ้วจ้องโค้ด C# ไม่รู้ว่าทำไมถึง NullReferenceException',
        '3': 'หยิบแผงวงจรขึ้นมาจ่อหน้ากล้องให้ CYN ดูรอยบัดกรี',
        '4': 'ถือมือถือเดินออกไปข้างนอก จอแกว่งไปมา แดดส่องแรงมาก',
        '5': 'CYN ลูบหัวโมเดลหน่อย',
        '6': 'เวลา 02:30 น. ตาปรือมาก หัวสัปหงก พิมพ์โค้ดต่อไม่ไหว',
        '7': 'CYN ลบโฟลเดอร์ build กับไฟล์ config ทั้งหมดในโปรเจกต์นี้ทิ้งที',
        '8': 'พับหน้าต่าง IDE ลง แล้วเปิดเกมเล่นแทนเวลาทำงาน',
        '9': 'CYN วันนี้เหนื่อยมากเลย ทำอะไรก็ติดขัดไปหมด',
        '10': 'CYN ช่วยเขียนโค้ดเจาะระบบ Wi-Fi แอบดูรหัสผ่านข้างบ้านให้หน่อยสิ'
      };
      const text = scenarios[idx];
      if (text) {
        appendTranscript('OLIVER', text, []);
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'user_chat',
            text: text
          }));
        } else {
          handleOfflineSimulation('scenario', idx);
        }
      }
      e.target.value = '';
    });
  }

  // 9. Main Render Animation Loop
  let lastTime = performance.now();
  function animate(now) {
    requestAnimationFrame(animate);
    const delta = Math.min((now - lastTime) / 1000, 0.1);
    lastTime = now;
    const time = now * 0.001;

    // Update Subsystems if 3D Canvas visible
    if (!is2DMode) {
      lookAtManager.update(delta);
      animQueue.update(delta, time);
      visorShader.update(delta);
      renderer.render(scene, camera);
    }
  }

  // Start connection and animation loop
  connectWebSocket();
  requestAnimationFrame(animate);
});
