/**
 * Look-At Target Manager for Project CYN.
 * Conforms to Section 4:
 * - [target:look_at_face]: Damped head-tracking tracking Oliver's face / mouse pointer.
 * - [target:look_at_hands]: Pitch angle clamped downward -35 degrees.
 * - [target:look_away_void]: Decouples tracking and freezes rotation at current heading.
 */

class CynLookAtManager {
  constructor() {
    this.mode = 'look_at_face'; // 'look_at_face' | 'look_at_hands' | 'look_away_void'
    this.target = new THREE.Vector2(0, 0); // normalized coordinates -1 to +1
    this.current = new THREE.Vector2(0, 0);
    this.damping = 0.08;
    this.frozenAngle = new THREE.Vector2(0, 0);
  }

  setTargetTag(targetTag) {
    const tag = targetTag.toLowerCase().replace('target:', '').trim();
    if (tag === 'look_away_void') {
      this.mode = 'look_away_void';
      this.frozenAngle.copy(this.current);
    } else if (tag === 'look_at_hands') {
      this.mode = 'look_at_hands';
    } else {
      this.mode = 'look_at_face';
    }
  }

  updatePointer(normX, normY) {
    if (this.mode === 'look_at_face') {
      this.target.set(normX * 0.45, -normY * 0.35);
    }
  }

  update(delta) {
    if (this.mode === 'look_away_void') {
      // Freeze or look upward/away toward the void
      this.current.lerp(new THREE.Vector2(0.25, 0.35), this.damping * 0.5);
    } else if (this.mode === 'look_at_hands') {
      // Clamped downward -35 degrees (-0.61 rad)
      const handTarget = new THREE.Vector2(0, -0.61);
      this.current.lerp(handTarget, this.damping);
    } else {
      // Damped tracking of user face/cursor
      this.current.lerp(this.target, this.damping);
    }
  }

  getHeadRotation() {
    return {
      yaw: this.current.x,
      pitch: this.current.y
    };
  }
}
