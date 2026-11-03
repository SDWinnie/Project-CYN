/**
 * Visor Display Emissive Shader Protocol for Project CYN.
 * Conforms to Section 3:
 * Index 0: [visor:normal_eyes] (Rounded yellow-amber digital pill capsules)
 * Index 1: [visor:solver_x] (Radiant yellow Absolute Solver cross sigil)
 * Index 2: [visor:smile_arcs] (Inverted curved crescent eye arcs)
 * Index 3: [visor:squint_suspicious] (Narrow horizontal scanning slits)
 * Index 4: [visor:blink_shutter] (Black unlit matrix, LEDs extinguished)
 * Index 5: [visor:tear_oil] (Black dripping viscous fluid particles)
 * Index 6: [visor:error_glitch] (Chaotic noise artifact scanlines)
 */

class CynVisorShader {
  constructor(previewCanvas = null) {
    this.canvas = document.createElement('canvas');
    this.canvas.width = 512;
    this.canvas.height = 256;
    this.ctx = this.canvas.getContext('2d');

    this.previewCanvas = previewCanvas;
    this.previewCtx = previewCanvas ? previewCanvas.getContext('2d') : null;

    this.currentIndex = 0;
    this.targetIndex = 0;
    this.oilDrops = [];
    this.time = 0;
    this.isBlinking = false;

    // Three.js texture reference
    this.texture = null;

    this._initOilParticles();
  }

  _initOilParticles() {
    this.oilDrops = [];
    for (let i = 0; i < 18; i++) {
      this.oilDrops.push({
        x: 100 + Math.random() * 312,
        y: Math.random() * 256,
        speed: 1.5 + Math.random() * 3.0,
        radius: 2 + Math.random() * 4,
        length: 8 + Math.random() * 15
      });
    }
  }

  getThreeTexture() {
    if (!this.texture && typeof THREE !== 'undefined') {
      this.texture = new THREE.CanvasTexture(this.canvas);
      this.texture.minFilter = THREE.LinearFilter;
      this.texture.magFilter = THREE.LinearFilter;
    }
    return this.texture;
  }

  setVisorIndex(index) {
    this.targetIndex = Math.max(0, Math.min(6, parseInt(index, 10)));
    this.currentIndex = this.targetIndex;
  }

  setVisorTag(tag) {
    const clean = tag.toLowerCase().replace('visor:', '').trim();
    const map = {
      'normal_eyes': 0,
      'solver_x': 1,
      'smile_arcs': 2,
      'squint_suspicious': 3,
      'blink_shutter': 4,
      'tear_oil': 5,
      'error_glitch': 6
    };
    if (map[clean] !== undefined) {
      this.setVisorIndex(map[clean]);
    }
  }

  update(delta) {
    this.time += delta;
    this.render();

    if (this.texture) {
      this.texture.needsUpdate = true;
    }

    if (this.previewCtx && this.previewCanvas) {
      this.previewCtx.clearRect(0, 0, this.previewCanvas.width, this.previewCanvas.height);
      this.previewCtx.drawImage(
        this.canvas, 
        0, 0, 
        this.previewCanvas.width, 
        this.previewCanvas.height
      );
    }
  }

  render() {
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    // Deep black visor matrix background
    ctx.fillStyle = '#050508';
    ctx.fillRect(0, 0, w, h);

    // Subtle dark matrix grid lines
    ctx.strokeStyle = 'rgba(20, 20, 30, 0.4)';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 16) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }

    if (this.currentIndex === 4) {
      // Index 4: [visor:blink_shutter] - completely unlit LEDs
      return;
    }

    const amber = '#ffcc00';
    const amberGlow = 'rgba(255, 204, 0, 0.7)';

    ctx.save();
    ctx.shadowColor = amberGlow;
    ctx.shadowBlur = 18;

    switch (this.currentIndex) {
      case 0:
        this._renderNormalEyes(ctx, w, h, amber);
        break;
      case 1:
        this._renderAbsoluteSolverX(ctx, w, h, amber);
        break;
      case 2:
        this._renderSmileArcs(ctx, w, h, amber);
        break;
      case 3:
        this._renderSquintSuspicious(ctx, w, h, amber);
        break;
      case 5:
        this._renderTearOil(ctx, w, h, amber);
        break;
      case 6:
        this._renderErrorGlitch(ctx, w, h);
        break;
      default:
        this._renderNormalEyes(ctx, w, h, amber);
    }

    ctx.restore();

    // Subtle horizontal digital scanlines overlay
    ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
    for (let y = 0; y < h; y += 4) {
      ctx.fillRect(0, y, w, 2);
    }
  }

  _renderNormalEyes(ctx, w, h, color) {
    ctx.fillStyle = color;
    const eyeWidth = 44;
    const eyeHeight = 72;
    const radius = 22;

    // Left eye capsule
    this._roundRect(ctx, w * 0.35 - eyeWidth / 2, h * 0.5 - eyeHeight / 2, eyeWidth, eyeHeight, radius);
    ctx.fill();

    // Right eye capsule
    this._roundRect(ctx, w * 0.65 - eyeWidth / 2, h * 0.5 - eyeHeight / 2, eyeWidth, eyeHeight, radius);
    ctx.fill();
  }

  _renderAbsoluteSolverX(ctx, w, h, color) {
    const cx = w * 0.5;
    const cy = h * 0.5;
    const size = 78;

    ctx.strokeStyle = color;
    ctx.lineWidth = 10;
    ctx.lineCap = 'round';

    // Solver central cross sigil with arrows
    ctx.beginPath();
    ctx.moveTo(cx - size, cy - size);
    ctx.lineTo(cx + size, cy + size);
    ctx.moveTo(cx + size, cy - size);
    ctx.lineTo(cx - size, cy + size);
    ctx.stroke();

    // Outer sigil brackets
    ctx.lineWidth = 4;
    const offset = size * 0.85;
    [-1, 1].forEach(sx => {
      [-1, 1].forEach(sy => {
        ctx.beginPath();
        ctx.moveTo(cx + sx * offset, cy + sy * (offset - 20));
        ctx.lineTo(cx + sx * offset, cy + sy * offset);
        ctx.lineTo(cx + sx * (offset - 20), cy + sy * offset);
        ctx.stroke();
      });
    });

    // Central pulsing ring
    const pulse = 18 + Math.sin(this.time * 6) * 4;
    ctx.beginPath();
    ctx.arc(cx, cy, pulse, 0, Math.PI * 2);
    ctx.stroke();
  }

  _renderSmileArcs(ctx, w, h, color) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 9;
    ctx.lineCap = 'round';

    // Left crescent
    ctx.beginPath();
    ctx.arc(w * 0.35, h * 0.52, 34, Math.PI * 1.15, Math.PI * 1.85);
    ctx.stroke();

    // Right crescent
    ctx.beginPath();
    ctx.arc(w * 0.65, h * 0.52, 34, Math.PI * 1.15, Math.PI * 1.85);
    ctx.stroke();
  }

  _renderSquintSuspicious(ctx, w, h, color) {
    ctx.fillStyle = color;
    const slitW = 60;
    const slitH = 14;

    // Left scanning slit (tilted inward)
    ctx.save();
    ctx.translate(w * 0.35, h * 0.5);
    ctx.rotate(0.12);
    this._roundRect(ctx, -slitW / 2, -slitH / 2, slitW, slitH, 6);
    ctx.fill();
    ctx.restore();

    // Right scanning slit (tilted inward)
    ctx.save();
    ctx.translate(w * 0.65, h * 0.5);
    ctx.rotate(-0.12);
    this._roundRect(ctx, -slitW / 2, -slitH / 2, slitW, slitH, 6);
    ctx.fill();
    ctx.restore();
  }

  _renderTearOil(ctx, w, h, color) {
    // Normal eyes with dripping black oil particles
    this._renderNormalEyes(ctx, w, h, color);

    ctx.fillStyle = '#0a0a0d';
    ctx.strokeStyle = '#121216';

    this.oilDrops.forEach(drop => {
      drop.y += drop.speed;
      if (drop.y > h + drop.length) {
        drop.y = h * 0.45;
        drop.x = (Math.random() > 0.5 ? w * 0.35 : w * 0.65) + (Math.random() - 0.5) * 50;
      }
      ctx.beginPath();
      ctx.ellipse(drop.x, drop.y, drop.radius, drop.length, 0, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  _renderErrorGlitch(ctx, w, h) {
    // Chaotic RGB split scanlines
    const steps = 14;
    for (let i = 0; i < steps; i++) {
      const y = Math.random() * h;
      const height = 4 + Math.random() * 16;
      const xOffset = (Math.random() - 0.5) * 60;

      ctx.fillStyle = i % 2 === 0 ? 'rgba(255, 204, 0, 0.7)' : 'rgba(255, 50, 80, 0.6)';
      ctx.fillRect(w * 0.2 + xOffset, y, w * 0.6, height);
    }
  }

  _roundRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
  }
}
