/**
 * Main WebGL Runtime Coordinator for Project CYN (v7.0 Full-Spectrum Edition).
 * Orchestrates Three.js rendering loop, WebSocket telemetry, audio/vision capture,
 * and HUD console interactions.
 */

window.addEventListener('DOMContentLoaded', () => {
  // 1. Scene, Camera, Renderer Setup
  const container = document.getElementById('viewport-container');
  const canvas = document.getElementById('cyn-canvas');
  const previewCanvas = document.getElementById('visor-preview-canvas');

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
      // Mobile Portrait: Viewport clamps to Close-Up Bust portrait frame
      camera.position.set(0, 0.18, 1.48);
    } else {
      // Desktop / Landscape: Viewport widens to Full-Torso frame with Solver tendrils visible
      camera.position.set(0, -0.06, 2.05);
    }
    camera.lookAt(0, 0.12, 0);
  }
  window.addEventListener('resize', adjustCameraViewport);
  adjustCameraViewport();

  // Mouse / Pointer Move Tracking for Look-At
  window.addEventListener('mousemove', (e) => {
    const normX = (e.clientX / window.innerWidth) * 2 - 1;
    const normY = (e.clientY / window.innerHeight) * 2 - 1;
    lookAtManager.updatePointer(normX, normY);
  });

  // 4. WebSocket Client Connection
  let ws = null;
  let wsConnected = false;

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const isMobileClient = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || (window.innerWidth < 860 && window.innerHeight > window.innerWidth);
    const clientType = isMobileClient ? 'android' : 'pc';
    const wsUrl = `${protocol}//${window.location.host}/ws/cyn?client=${clientType}`;

    updateStatusBadge('CONNECTING...', 'sleep');
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      wsConnected = true;
      updateStatusBadge(`ONLINE (${clientType.toUpperCase()} EDITION)`, 'normal');
    };

    ws.onclose = () => {
      wsConnected = false;
      updateStatusBadge('DISCONNECTED', 'sleep');
      setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
      console.warn('WebSocket error:', err);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'handshake' && data.initial_event) {
          handleServerPayload(data.initial_event);
        } else {
          handleServerPayload(data);
        }
      } catch (e) {
        console.error('Error parsing incoming WS message:', e);
      }
    };
  }

  // Touch Sensor Handler
  const touchSensor = new CynTouchSensor(canvas, camera, avatarRig, (touchPayload) => {
    audioDsp.ensureContext();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(touchPayload));
    }
  });

  // 5. Server Payload Dispatcher
  function handleServerPayload(data) {
    if (data.type === 'tunnel_ready' && data.public_url) {
      updatePublicRelayUrl(data.public_url);
      return;
    }

    if (data.type === 'cyn_response' || data.type === 'handshake') {
      const p = data.priority || 2;

      // Update Visor
      if (data.visor_index !== undefined) {
        visorShader.setVisorIndex(data.visor_index);
        updateVisorInfo(data.visor_index);
      }

      // Enqueue Kinematics Animations
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
      }

      // Update Status Badge if Solver or Special
      if (data.visor_index === 1) {
        updateStatusBadge('SOLVER X ENGAGED', 'solver');
      } else if (data.lifecycle_state === 'STATE_SLEEP') {
        updateStatusBadge('LOW POWER SLEEP', 'sleep');
      } else {
        updateStatusBadge('ACTIVE ENGAGED', 'normal');
      }

      // Render Dialogue in Transcript Box
      if (data.raw_text) {
        appendTranscript('CYN', data.clean_text || data.raw_text, data.kinematics || []);
      }
    }
  }

  // 6. UI Helpers
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
        b.textContent = `[${t}]`;
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

  // Send Chat message
  function sendChatMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    audioDsp.ensureContext();
    appendTranscript('OLIVER', text, []);
    chatInput.value = '';

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'user_chat',
        text: text
      }));
    }
  }

  if (sendBtn) sendBtn.addEventListener('click', sendChatMessage);
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendChatMessage();
    });
  }

  // 7. Interactive Action Buttons
  const wakeBtn = document.getElementById('btn-wake');
  const headpatBtn = document.getElementById('btn-headpat');
  const visorPokeBtn = document.getElementById('btn-visorpoke');
  const scenarioSelect = document.getElementById('scenario-select');

  if (wakeBtn) {
    wakeBtn.addEventListener('click', () => {
      audioDsp.ensureContext();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'trigger_wake' }));
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
        }
      }
      e.target.value = '';
    });
  }

  // 8. Main Render Animation Loop
  let lastTime = performance.now();
  function animate(now) {
    requestAnimationFrame(animate);
    const delta = Math.min((now - lastTime) / 1000, 0.1);
    lastTime = now;
    const time = now * 0.001;

    // Update Subsystems
    lookAtManager.update(delta);
    animQueue.update(delta, time);
    visorShader.update(delta);

    // Render WebGL
    renderer.render(scene, camera);
  }

  // Start connection and animation loop
  connectWebSocket();
  requestAnimationFrame(animate);
});
