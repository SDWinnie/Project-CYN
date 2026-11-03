/**
 * Real-Time Animation Queue Manager for Project CYN.
 * Conforms to Section 4:
 * - Priority Hierarchy:
 *   Level 1 (Interrupt/Emergency): [visor:solver_x], [anim:head_spin_180_horror], Safety rejections.
 *   Level 2 (Expressive Gestures): [anim:head_tilt_...], [anim:reach_forward], [anim:creepy_curtsy], FIFO.
 *   Level 3 (Ambient Idle Loops): [anim:idle_sway], breathing dynamics.
 * - Interpolation:
 *   Slerp duration t = 250ms
 *   Glitch snap [anim:head_twitch_jitter] bypasses Slerp (t = 0ms) with Gaussian noise.
 */

class CynAnimationQueueManager {
  constructor(avatarRig) {
    this.rig = avatarRig;
    this.level1Current = null;
    this.level2Queue = [];
    this.currentLevel2 = null;
    this.currentGestureTime = 0;
    this.gestureDuration = 1.6; // seconds per expressive gesture

    this.slerpDuration = 0.25; // 250ms Slerp
    this.slerpTimer = 0;

    // Bone target rotations (Euler / Quaternions)
    this.currentPose = {
      neckRotation: new THREE.Euler(0, 0, 0),
      headRotation: new THREE.Euler(0, 0, 0),
      spineRotation: new THREE.Euler(0, 0, 0),
      leftArmRotation: new THREE.Euler(0, 0, 0),
      rightArmRotation: new THREE.Euler(0, 0, 0),
      tendrilDeploy: 0.0,
      ribbonFlutter: 0.0
    };

    this.targetPose = {
      neckRotation: new THREE.Euler(0, 0, 0),
      headRotation: new THREE.Euler(0, 0, 0),
      spineRotation: new THREE.Euler(0, 0, 0),
      leftArmRotation: new THREE.Euler(0, 0, 0),
      rightArmRotation: new THREE.Euler(0, 0, 0),
      tendrilDeploy: 0.0,
      ribbonFlutter: 0.0
    };

    this.baseIdlePose = { ...this.targetPose };
  }

  enqueueAnimation(animTag, priority = 2) {
    const tag = animTag.toLowerCase().replace('anim:', '').trim();

    if (priority === 1 || tag === 'head_spin_180_horror' || tag === 'solver_x') {
      // Level 1 Interrupt: clear queues, play immediately
      this.clearAll();
      this.level1Current = tag;
      this._applyPoseForTag(tag, true);
    } else if (priority === 2) {
      // Level 2 Expressive Gesture: append to FIFO queue
      this.level2Queue.push(tag);
    } else {
      // Level 3 Ambient Idle
      if (!this.level1Current && !this.currentLevel2 && this.level2Queue.length === 0) {
        this._applyPoseForTag(tag, false);
      }
    }
  }

  clearAll() {
    this.level1Current = null;
    this.currentLevel2 = null;
    this.level2Queue = [];
  }

  _applyPoseForTag(tag, isLevel1 = false) {
    this.slerpTimer = 0;

    // Glitch snap tag: bypass Slerp (t = 0ms) + Gaussian jitter
    if (tag === 'head_twitch_jitter') {
      const jitterZ = (Math.random() - 0.5) * 0.45;
      const jitterY = (Math.random() - 0.5) * 0.35;
      this.currentPose.headRotation.set(0, jitterY, jitterZ);
      this.targetPose.headRotation.set(0, jitterY, jitterZ);
      this.slerpTimer = this.slerpDuration; // instant
      return;
    }

    switch (tag) {
      case 'head_tilt_45_r':
        this.targetPose.neckRotation.set(0.08, 0.15, -0.42); // 45 degree mechanical tilt right
        this.targetPose.leftArmRotation.set(0, 0, 0);
        this.targetPose.rightArmRotation.set(0, 0, 0);
        break;

      case 'head_tilt_45_l':
        this.targetPose.neckRotation.set(0.08, -0.15, 0.42); // 45 degree mechanical tilt left
        this.targetPose.leftArmRotation.set(0, 0, 0);
        this.targetPose.rightArmRotation.set(0, 0, 0);
        break;

      case 'head_spin_180_horror':
        // Unhinged neck rotation around Y
        this.targetPose.neckRotation.set(0.1, Math.PI, 0.2);
        this.targetPose.tendrilDeploy = 1.0;
        break;

      case 'creepy_curtsy':
        this.targetPose.spineRotation.set(0.24, 0, 0);
        this.targetPose.neckRotation.set(-0.15, 0, 0);
        this.targetPose.leftArmRotation.set(0.4, 0.2, 0.5);
        this.targetPose.rightArmRotation.set(0.4, -0.2, -0.5);
        break;

      case 'crawl_closer':
        this.targetPose.spineRotation.set(0.35, 0, 0);
        this.targetPose.neckRotation.set(-0.25, 0, 0);
        this.targetPose.leftArmRotation.set(0.6, 0.1, 0.2);
        this.targetPose.rightArmRotation.set(0.6, -0.1, -0.2);
        break;

      case 'reach_forward':
        this.targetPose.spineRotation.set(0.1, 0, 0);
        this.targetPose.rightArmRotation.set(1.4, -0.2, -0.1);
        break;

      case 'finger_drum_monotone':
        this.targetPose.rightArmRotation.set(0.5, -0.2, -0.3);
        break;

      case 'slump_powersave':
        this.targetPose.spineRotation.set(0.42, 0, 0);
        this.targetPose.neckRotation.set(0.48, 0.1, 0.1);
        this.targetPose.leftArmRotation.set(0.1, 0, 0.1);
        this.targetPose.rightArmRotation.set(0.1, 0, -0.1);
        this.targetPose.tendrilDeploy = 0.0;
        break;

      case 'idle_sway':
      default:
        this.targetPose.neckRotation.set(0, 0, 0);
        this.targetPose.spineRotation.set(0, 0, 0);
        this.targetPose.leftArmRotation.set(0, 0, 0);
        this.targetPose.rightArmRotation.set(0, 0, 0);
        break;
    }
  }

  setTendrilDeploy(active) {
    this.targetPose.tendrilDeploy = active ? 1.0 : 0.0;
  }

  setRibbonFlutter(intensity) {
    this.targetPose.ribbonFlutter = intensity;
  }

  update(delta, time) {
    // Manage Level 2 Queue playback
    if (!this.level1Current) {
      if (this.currentLevel2) {
        this.currentGestureTime += delta;
        if (this.currentGestureTime >= this.gestureDuration) {
          this.currentLevel2 = null;
          this.currentGestureTime = 0;
          this._applyPoseForTag('idle_sway');
        }
      } else if (this.level2Queue.length > 0) {
        this.currentLevel2 = this.level2Queue.shift();
        this.currentGestureTime = 0;
        this._applyPoseForTag(this.currentLevel2);
      }
    }

    // Slerp / Lerp interpolation (250ms transition)
    const factor = Math.min(1.0, delta / this.slerpDuration * 2.8);

    this.currentPose.neckRotation.x += (this.targetPose.neckRotation.x - this.currentPose.neckRotation.x) * factor;
    this.currentPose.neckRotation.y += (this.targetPose.neckRotation.y - this.currentPose.neckRotation.y) * factor;
    this.currentPose.neckRotation.z += (this.targetPose.neckRotation.z - this.currentPose.neckRotation.z) * factor;

    this.currentPose.spineRotation.x += (this.targetPose.spineRotation.x - this.currentPose.spineRotation.x) * factor;
    this.currentPose.spineRotation.y += (this.targetPose.spineRotation.y - this.currentPose.spineRotation.y) * factor;
    this.currentPose.spineRotation.z += (this.targetPose.spineRotation.z - this.currentPose.spineRotation.z) * factor;

    this.currentPose.leftArmRotation.x += (this.targetPose.leftArmRotation.x - this.currentPose.leftArmRotation.x) * factor;
    this.currentPose.leftArmRotation.y += (this.targetPose.leftArmRotation.y - this.currentPose.leftArmRotation.y) * factor;
    this.currentPose.leftArmRotation.z += (this.targetPose.leftArmRotation.z - this.currentPose.leftArmRotation.z) * factor;

    this.currentPose.rightArmRotation.x += (this.targetPose.rightArmRotation.x - this.currentPose.rightArmRotation.x) * factor;
    this.currentPose.rightArmRotation.y += (this.targetPose.rightArmRotation.y - this.currentPose.rightArmRotation.y) * factor;
    this.currentPose.rightArmRotation.z += (this.targetPose.rightArmRotation.z - this.currentPose.rightArmRotation.z) * factor;

    this.currentPose.tendrilDeploy += (this.targetPose.tendrilDeploy - this.currentPose.tendrilDeploy) * factor;

    // Apply ambient idle breathing sway when Level 1/2 inactive
    let idleSwayX = 0;
    let idleSwayY = 0;
    if (!this.level1Current && !this.currentLevel2) {
      idleSwayX = Math.sin(time * 1.8) * 0.025;
      idleSwayY = Math.cos(time * 0.9) * 0.02;
    }

    // Dispatch transforms to avatar rig bones
    if (this.rig) {
      this.rig.applyKinematics(this.currentPose, idleSwayX, idleSwayY, time);
    }
  }
}
