/**
 * Web Audio API Acoustic DSP Engine and Sound Bite Synthesizer for Project CYN.
 * Synthesizes all inline DSP sound effects autonomously:
 * - <audio: servo_whirr>
 * - <audio: camera_shutter>
 * - <audio: static_burst>
 * - <audio: joint_click>
 * And handles pitch/rate shifts on incoming speech streams.
 */

class CynAudioDspPlayer {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this._initialized = false;
  }

  init() {
    if (this._initialized) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioCtx();
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.value = 0.8;
      this.masterGain.connect(this.ctx.destination);
      this._initialized = true;
    } catch (e) {
      console.warn('AudioContext init note:', e);
    }
  }

  ensureContext() {
    if (!this._initialized) this.init();
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  playAudioCue(cueName) {
    this.ensureContext();
    if (!this.ctx) return;

    const cue = cueName.toLowerCase().trim();
    if (cue.includes('servo_whirr')) {
      this._playServoWhirr();
    } else if (cue.includes('camera_shutter')) {
      this._playCameraShutter();
    } else if (cue.includes('static_burst')) {
      this._playStaticBurst();
    } else if (cue.includes('joint_click')) {
      this._playJointClick();
    }
  }

  _playServoWhirr() {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    const filter = this.ctx.createBiquadFilter();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(320, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(740, this.ctx.currentTime + 0.12);
    osc.frequency.exponentialRampToValueAtTime(260, this.ctx.currentTime + 0.28);

    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(900, this.ctx.currentTime);
    filter.Q.value = 4.0;

    gain.gain.setValueAtTime(0.01, this.ctx.currentTime);
    gain.gain.linearRampToValueAtTime(0.22, this.ctx.currentTime + 0.05);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.3);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(this.masterGain);

    osc.start();
    osc.stop(this.ctx.currentTime + 0.32);
  }

  _playCameraShutter() {
    // Dual snappy click simulating physical drone camera iris
    const now = this.ctx.currentTime;
    [now, now + 0.055].forEach((t, i) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(i === 0 ? 1800 : 1200, t);
      osc.frequency.exponentialRampToValueAtTime(300, t + 0.03);

      gain.gain.setValueAtTime(0.3, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.035);

      osc.connect(gain);
      gain.connect(this.masterGain);

      osc.start(t);
      osc.stop(t + 0.04);
    });
  }

  _playStaticBurst() {
    // Filtered white noise burst with glitch distortion
    const bufferSize = this.ctx.sampleRate * 0.15;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const output = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      output[i] = (Math.random() * 2 - 1) * (Math.random() > 0.15 ? 1 : 0);
    }

    const whiteNoise = this.ctx.createBufferSource();
    whiteNoise.buffer = buffer;

    const filter = this.ctx.createBiquadFilter();
    filter.type = 'highpass';
    filter.frequency.setValueAtTime(1400, this.ctx.currentTime);

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.28, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.14);

    whiteNoise.connect(filter);
    filter.connect(gain);
    gain.connect(this.masterGain);

    whiteNoise.start();
    whiteNoise.stop(this.ctx.currentTime + 0.15);
  }

  _playJointClick() {
    // Robotic ratchet lock click
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(800, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(150, this.ctx.currentTime + 0.04);

    gain.gain.setValueAtTime(0.4, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.05);

    osc.connect(gain);
    gain.connect(this.masterGain);

    osc.start();
    osc.stop(this.ctx.currentTime + 0.05);
  }

  playRawPcm(pcmBytes, sampleRate = 24000, pitchRatio = 1.0) {
    this.ensureContext();
    if (!this.ctx || !pcmBytes || pcmBytes.length < 2) return;

    // Convert 16-bit PCM to Float32
    const int16 = new Int16Array(pcmBytes.buffer, pcmBytes.byteOffset, pcmBytes.byteLength / 2);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768.0;
    }

    const audioBuffer = this.ctx.createBuffer(1, float32.length, sampleRate);
    audioBuffer.copyToChannel(float32, 0);

    const source = this.ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.playbackRate.value = Math.max(0.4, Math.min(2.5, pitchRatio));

    source.connect(this.masterGain);
    source.start();
  }
}
