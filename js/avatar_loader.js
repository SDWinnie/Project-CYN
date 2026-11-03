/**
 * Avatar Loader & Procedural 3D CYN Rig Generator for Project CYN.
 * Conforms to Section 3:
 * - Humanoid VRM 1.0 bone hierarchy
 * - Custom bones: Cyn_Neck_Glitch, Solver_Tendril_Root, Solver_Tendril_01..04_L/R, Ribbon_Dynamic_L/R
 * - Emissive visor plane with dynamic procedural shader texture
 * - Raycast hit zones for cranial headpat and visor poke
 */

class CynAvatarRig {
  constructor(scene, visorShader, lookAtManager) {
    this.scene = scene;
    this.visorShader = visorShader;
    this.lookAtManager = lookAtManager;

    this.root = new THREE.Group();
    this.root.name = 'CYN_Avatar_Root';
    this.scene.add(this.root);

    this.bones = {};
    this.tendrils = [];
    this.hitTargets = [];
    this.isVRM = false;
    this.vrmInstance = null;

    this._buildProceduralCynModel();
  }

  _buildProceduralCynModel() {
    const darkMetal = new THREE.MeshStandardMaterial({
      color: 0x181920,
      metalness: 0.85,
      roughness: 0.35,
    });
    const silverMetal = new THREE.MeshStandardMaterial({
      color: 0x8a8e9e,
      metalness: 0.9,
      roughness: 0.2,
    });
    const maidBlack = new THREE.MeshStandardMaterial({
      color: 0x0c0d12,
      roughness: 0.7,
    });
    const maidWhite = new THREE.MeshStandardMaterial({
      color: 0xe6e6ee,
      roughness: 0.6,
    });
    const amberEmissive = new THREE.MeshBasicMaterial({
      color: 0xffcc00,
    });

    // 1. HIPS & SPINE ROOT
    const hips = new THREE.Group();
    hips.position.y = -0.55;
    this.root.add(hips);
    this.bones.Hips = hips;

    const spine = new THREE.Group();
    spine.position.y = 0.28;
    hips.add(spine);
    this.bones.Spine = spine;

    // Torso / Maid Dress Mesh
    const dressGeo = new THREE.CylinderGeometry(0.24, 0.38, 0.45, 16);
    const dressMesh = new THREE.Mesh(dressGeo, maidBlack);
    dressMesh.position.y = 0.18;
    hips.add(dressMesh);

    // Maid apron
    const apronGeo = new THREE.PlaneGeometry(0.22, 0.38);
    const apronMesh = new THREE.Mesh(apronGeo, maidWhite);
    apronMesh.position.set(0, 0.18, 0.25);
    hips.add(apronMesh);

    // 2. CHEST & UPPER CHEST
    const chest = new THREE.Group();
    chest.position.y = 0.26;
    spine.add(chest);
    this.bones.Chest = chest;

    const chestMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.24, 0.26, 16), darkMetal);
    chest.add(chestMesh);

    // Drone yellow hazard core
    const coreMesh = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.05, 0.04), amberEmissive);
    coreMesh.position.set(0, 0.04, 0.13);
    chest.add(coreMesh);

    // 3. CYN_NECK_GLITCH (Auxiliary Kinetic Drone Bone)
    const neckGlitch = new THREE.Group();
    neckGlitch.name = 'Cyn_Neck_Glitch';
    neckGlitch.position.y = 0.22;
    chest.add(neckGlitch);
    this.bones.Cyn_Neck_Glitch = neckGlitch;

    // Metallic segmented neck ring assembly
    const neckGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.14, 12);
    const neckMesh = new THREE.Mesh(neckGeo, silverMetal);
    neckGlitch.add(neckMesh);

    // 4. HEAD ASSEMBLY
    const head = new THREE.Group();
    head.name = 'Head';
    head.position.y = 0.18;
    neckGlitch.add(head);
    this.bones.Head = head;

    // Spherical Drone Cranial chassis
    const headGeo = new THREE.SphereGeometry(0.32, 28, 24);
    const headMesh = new THREE.Mesh(headGeo, darkMetal);
    headMesh.userData.touchTarget = 'headpat';
    head.add(headMesh);
    this.hitTargets.push(headMesh);

    // 5. VISOR DISPLAY EMISSIVE PLANE (Curved cylinder / plane)
    const visorGeo = new THREE.PlaneGeometry(0.44, 0.24, 8, 4);
    const visorMat = new THREE.MeshBasicMaterial({
      map: this.visorShader.getThreeTexture(),
      transparent: true,
      depthWrite: false,
    });
    const visorMesh = new THREE.Mesh(visorGeo, visorMat);
    visorMesh.position.set(0, 0.02, 0.315);
    visorMesh.userData.touchTarget = 'visor_poke';
    head.add(visorMesh);
    this.hitTargets.push(visorMesh);

    // 6. MAID BOW & SECONDARY SPRING BONES (Ribbon_Dynamic_L/R)
    const bowRoot = new THREE.Group();
    bowRoot.position.set(0, 0.32, -0.05);
    head.add(bowRoot);

    const ribbonL = new THREE.Group();
    ribbonL.name = 'Ribbon_Dynamic_L';
    ribbonL.position.set(-0.16, 0.06, 0);
    bowRoot.add(ribbonL);
    this.bones.Ribbon_Dynamic_L = ribbonL;

    const ribbonR = new THREE.Group();
    ribbonR.name = 'Ribbon_Dynamic_R';
    ribbonR.position.set(0.16, 0.06, 0);
    bowRoot.add(ribbonR);
    this.bones.Ribbon_Dynamic_R = ribbonR;

    const bowGeo = new THREE.ConeGeometry(0.12, 0.24, 5);
    const bowMat = new THREE.MeshStandardMaterial({ color: 0x111116, roughness: 0.6 });
    const bowMeshL = new THREE.Mesh(bowGeo, bowMat);
    bowMeshL.rotation.z = Math.PI * 0.4;
    ribbonL.add(bowMeshL);

    const bowMeshR = new THREE.Mesh(bowGeo, bowMat);
    bowMeshR.rotation.z = -Math.PI * 0.4;
    ribbonR.add(bowMeshR);

    // Maid white cap headband
    const capGeo = new THREE.TorusGeometry(0.33, 0.025, 8, 20, Math.PI);
    const capMesh = new THREE.Mesh(capGeo, maidWhite);
    capMesh.rotation.x = -Math.PI * 0.45;
    capMesh.position.set(0, 0.08, 0.02);
    head.add(capMesh);

    // 7. ARMS & SHOULDERS
    const armGeo = new THREE.CylinderGeometry(0.045, 0.045, 0.32, 12);
    armGeo.translate(0, -0.16, 0);

    const leftArm = new THREE.Group();
    leftArm.position.set(-0.32, 0.1, 0);
    chest.add(leftArm);
    leftArm.add(new THREE.Mesh(armGeo, silverMetal));
    this.bones.LeftUpperArm = leftArm;

    const rightArm = new THREE.Group();
    rightArm.position.set(0.32, 0.1, 0);
    chest.add(rightArm);
    rightArm.add(new THREE.Mesh(armGeo, silverMetal));
    this.bones.RightUpperArm = rightArm;

    // 8. ABSOLUTE SOLVER TENDRILS (Solver_Tendril_Root & Chains 01-04 L/R)
    const tendrilRoot = new THREE.Group();
    tendrilRoot.name = 'Solver_Tendril_Root';
    tendrilRoot.position.set(0, 0.08, -0.16);
    chest.add(tendrilRoot);
    this.bones.Solver_Tendril_Root = tendrilRoot;

    this.tendrils = [];
    const tendrilMat = new THREE.MeshStandardMaterial({
      color: 0x14141c,
      metalness: 0.8,
      roughness: 0.2,
      emissive: 0x332200,
    });

    // 4 Eldritch Tendrils
    for (let t = 0; t < 4; t++) {
      const angle = (t / 4) * Math.PI * 2 + Math.PI * 0.25;
      const tendrilChain = {
        baseAngle: angle,
        segments: [],
      };

      let parentNode = tendrilRoot;
      for (let s = 0; s < 4; s++) {
        const segGroup = new THREE.Group();
        segGroup.position.set(
          Math.cos(angle) * (s === 0 ? 0.08 : 0.18),
          Math.sin(angle) * (s === 0 ? 0.08 : 0.18),
          -0.12
        );

        const segGeo = new THREE.ConeGeometry(0.04 - s * 0.007, 0.22, 6);
        segGeo.translate(0, 0.11, 0);
        const segMesh = new THREE.Mesh(segGeo, tendrilMat);
        segMesh.rotation.x = Math.PI * 0.5;
        segGroup.add(segMesh);

        parentNode.add(segGroup);
        tendrilChain.segments.push(segGroup);
        parentNode = segGroup;
      }
      this.tendrils.push(tendrilChain);
    }
  }

  applyKinematics(pose, idleSwayX, idleSwayY, time) {
    // 1. Cyn_Neck_Glitch Rotations
    if (this.bones.Cyn_Neck_Glitch) {
      this.bones.Cyn_Neck_Glitch.rotation.set(
        pose.neckRotation.x,
        pose.neckRotation.y,
        pose.neckRotation.z
      );
    }

    // 2. Head Look-At Tracking
    if (this.bones.Head && this.lookAtManager) {
      const look = this.lookAtManager.getHeadRotation();
      this.bones.Head.rotation.set(
        look.pitch + pose.headRotation.x,
        look.yaw + pose.headRotation.y,
        pose.headRotation.z
      );
    }

    // 3. Spine Breathing & Sway
    if (this.bones.Spine) {
      this.bones.Spine.rotation.set(
        pose.spineRotation.x + idleSwayX,
        pose.spineRotation.y + idleSwayY,
        pose.spineRotation.z
      );
    }

    // 4. Arms
    if (this.bones.LeftUpperArm) {
      this.bones.LeftUpperArm.rotation.set(
        pose.leftArmRotation.x,
        pose.leftArmRotation.y,
        pose.leftArmRotation.z
      );
    }
    if (this.bones.RightUpperArm) {
      this.bones.RightUpperArm.rotation.set(
        pose.rightArmRotation.x,
        pose.rightArmRotation.y,
        pose.rightArmRotation.z
      );
    }

    // 5. Ribbon Dynamic Spring Flutter
    const ribbonWiggle = Math.sin(time * 8.0) * (0.05 + pose.ribbonFlutter * 0.35);
    if (this.bones.Ribbon_Dynamic_L) {
      this.bones.Ribbon_Dynamic_L.rotation.z = ribbonWiggle;
    }
    if (this.bones.Ribbon_Dynamic_R) {
      this.bones.Ribbon_Dynamic_R.rotation.z = -ribbonWiggle;
    }

    // 6. Absolute Solver Tendrils Deploy & Undulation
    const deploy = pose.tendrilDeploy; // 0.0 (hidden/folded) to 1.0 (deployed)
    this.tendrils.forEach((chain, i) => {
      chain.segments.forEach((seg, sIdx) => {
        const wave = Math.sin(time * 3.5 + sIdx * 0.8 + i * 1.5) * 0.35 * deploy;
        seg.scale.setScalar(0.1 + deploy * 0.9);
        seg.rotation.x = wave;
        seg.rotation.y = Math.cos(time * 2.8 + sIdx) * 0.25 * deploy;
      });
    });
  }
}
