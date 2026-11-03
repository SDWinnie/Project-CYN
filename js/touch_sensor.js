/**
 * Mobile Companion Sensor Hooks & Touch Callback System for Project CYN.
 * Conforms to Section 5:
 * - [sensor:gyro_shake]: Sudden acceleration trigger
 * - [touch:headpat]: Cranial touch interaction
 * - [touch:visor_poke]: Visor glass touch interaction
 */

class CynTouchSensor {
  constructor(canvas, camera, cynModel, onEventCallback) {
    this.canvas = canvas;
    this.camera = camera;
    this.cynModel = cynModel;
    this.onEventCallback = onEventCallback;

    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();

    this.lastShakeTime = 0;
    this.lastAcceleration = 0;

    this._initListeners();
  }

  _initListeners() {
    // Pointer / touch click raycast
    const handlePointer = (clientX, clientY) => {
      const rect = this.canvas.getBoundingClientRect();
      this.mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;

      this.raycaster.setFromCamera(this.mouse, this.camera);

      // Check intersections with Cyn model parts
      if (this.cynModel && this.cynModel.hitTargets) {
        const hits = this.raycaster.intersectObjects(this.cynModel.hitTargets, true);
        if (hits.length > 0) {
          const hitObj = hits[0].object;
          const targetType = hitObj.userData.touchTarget || 'headpat';
          if (this.onEventCallback) {
            this.onEventCallback({
              type: 'touch_event',
              touch_type: targetType,
              x: clientX,
              y: clientY
            });
          }
          return;
        }
      }

      // Fallback: If clicked upper 40% of viewport, consider cranial headpat
      const relY = (clientY - rect.top) / rect.height;
      if (relY < 0.45) {
        if (this.onEventCallback) {
          this.onEventCallback({
            type: 'touch_event',
            touch_type: 'headpat',
            x: clientX,
            y: clientY
          });
        }
      }
    };

    this.canvas.addEventListener('click', (e) => {
      handlePointer(e.clientX, e.clientY);
    });

    this.canvas.addEventListener('touchstart', (e) => {
      if (e.touches.length > 0) {
        const t = e.touches[0];
        handlePointer(t.clientX, t.clientY);
      }
    }, { passive: true });

    // Gyroscope / Device Motion for shake detection
    if (window.DeviceMotionEvent) {
      window.addEventListener('devicemotion', (e) => {
        const acc = e.accelerationIncludingGravity;
        if (!acc) return;
        const totalAcc = Math.sqrt((acc.x || 0)**2 + (acc.y || 0)**2 + (acc.z || 0)**2);

        const deltaAcc = Math.abs(totalAcc - this.lastAcceleration);
        this.lastAcceleration = totalAcc;

        if (deltaAcc > 18.0 && Date.now() - this.lastShakeTime > 4000) {
          this.lastShakeTime = Date.now();
          if (this.onEventCallback) {
            this.onEventCallback({
              type: 'mobile_telemetry',
              acceleration: deltaAcc,
              orientation: window.innerWidth > window.innerHeight ? 'landscape' : 'portrait'
            });
          }
        }
      });
    }

    // Battery API check
    if (navigator.getBattery) {
      navigator.getBattery().then(battery => {
        battery.addEventListener('levelchange', () => {
          if (battery.level < 0.20 && !battery.charging) {
            if (this.onEventCallback) {
              this.onEventCallback({
                type: 'mobile_telemetry',
                battery: battery.level,
                acceleration: 0
              });
            }
          }
        });
      }).catch(() => {});
    }
  }
}
