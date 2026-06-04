"use client";

import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame, type ThreeElements } from "@react-three/fiber";
import * as THREE from "three";

/** A procedurally-built low-poly noir detective: fedora, trench coat, and a
 *  magnifying glass he slowly scans with. Idle-breathes and turns toward the
 *  cursor. No external model asset — all primitives + flat shading. */

const INK = "#16120d";
const COAT = "#2a2118";
const SKIN = "#d8c0a0";
const PAPER = "#e9dcc0";
const RED = "#b8231a";
const GLASS = "#9fc4d8";

function Detective() {
  const root = useRef<THREE.Group>(null);
  const torso = useRef<THREE.Group>(null);
  const armR = useRef<THREE.Group>(null);

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;
    const reduce = state.viewport.aspect < 0; // placeholder, never true
    if (root.current) {
      // breathing bob
      root.current.position.y = Math.sin(t * 1.3) * 0.03 - 0.05;
      // mouse-look: ease the whole figure toward the pointer
      const targetY = state.pointer.x * 0.55;
      root.current.rotation.y = THREE.MathUtils.damp(
        root.current.rotation.y,
        targetY,
        4,
        delta,
      );
    }
    if (torso.current) {
      torso.current.rotation.x = THREE.MathUtils.damp(
        torso.current.rotation.x,
        -state.pointer.y * 0.12,
        4,
        delta,
      );
    }
    if (armR.current) {
      // slow scanning sweep with the magnifier
      armR.current.rotation.y = Math.sin(t * 0.8) * 0.28 - 0.15;
      armR.current.rotation.z = -0.5 + Math.sin(t * 0.8 + 1) * 0.06;
    }
    void reduce;
  });

  const mat = (color: string, extra: Partial<THREE.MeshStandardMaterial> = {}) =>
    ({ color, flatShading: true, ...extra }) as ThreeElements["meshStandardMaterial"];

  return (
    <group ref={root} position={[0, -0.05, 0]} rotation={[0, 0.2, 0]}>
      <group ref={torso}>
        {/* trench coat (flared) */}
        <mesh position={[0, 0.62, 0]} castShadow>
          <cylinderGeometry args={[0.3, 0.56, 1.25, 10]} />
          <meshStandardMaterial {...mat(COAT)} />
        </mesh>
        {/* coat front placket */}
        <mesh position={[0, 0.62, 0.3]}>
          <boxGeometry args={[0.12, 1.1, 0.06]} />
          <meshStandardMaterial {...mat(INK)} />
        </mesh>
        {/* belt */}
        <mesh position={[0, 0.5, 0]}>
          <cylinderGeometry args={[0.44, 0.44, 0.1, 10]} />
          <meshStandardMaterial {...mat(INK)} />
        </mesh>
        <mesh position={[0, 0.5, 0.42]}>
          <boxGeometry args={[0.12, 0.12, 0.04]} />
          <meshStandardMaterial {...mat(RED)} />
        </mesh>
        {/* collar */}
        <mesh position={[0, 1.26, 0]} rotation={[0.3, 0, 0]}>
          <cylinderGeometry args={[0.2, 0.3, 0.18, 8, 1, true]} />
          <meshStandardMaterial {...mat(INK, { side: THREE.DoubleSide })} />
        </mesh>
        {/* scarf */}
        <mesh position={[0, 1.2, 0.08]}>
          <cylinderGeometry args={[0.16, 0.16, 0.12, 8]} />
          <meshStandardMaterial {...mat(RED)} />
        </mesh>

        {/* head */}
        <mesh position={[0, 1.46, 0]} castShadow>
          <sphereGeometry args={[0.24, 16, 14]} />
          <meshStandardMaterial {...mat(SKIN)} />
        </mesh>

        {/* fedora: brim + crown + band */}
        <mesh position={[0, 1.62, 0]}>
          <cylinderGeometry args={[0.42, 0.44, 0.04, 14]} />
          <meshStandardMaterial {...mat(INK)} />
        </mesh>
        <mesh position={[0, 1.74, 0]}>
          <cylinderGeometry args={[0.24, 0.27, 0.24, 12]} />
          <meshStandardMaterial {...mat(INK)} />
        </mesh>
        <mesh position={[0, 1.65, 0]}>
          <cylinderGeometry args={[0.275, 0.275, 0.05, 14]} />
          <meshStandardMaterial {...mat(RED)} />
        </mesh>

        {/* left arm (down) */}
        <group position={[-0.4, 1.15, 0]} rotation={[0, 0, 0.18]}>
          <mesh position={[0, -0.4, 0]}>
            <capsuleGeometry args={[0.1, 0.6, 4, 8]} />
            <meshStandardMaterial {...mat(COAT)} />
          </mesh>
          <mesh position={[0, -0.78, 0]}>
            <sphereGeometry args={[0.1, 10, 8]} />
            <meshStandardMaterial {...mat(SKIN)} />
          </mesh>
        </group>

        {/* right arm raised, holding the magnifier */}
        <group ref={armR} position={[0.4, 1.15, 0]} rotation={[0, 0, -0.5]}>
          <mesh position={[0, -0.32, 0.18]} rotation={[0.6, 0, 0]}>
            <capsuleGeometry args={[0.1, 0.62, 4, 8]} />
            <meshStandardMaterial {...mat(COAT)} />
          </mesh>
          {/* hand */}
          <mesh position={[0, -0.5, 0.5]}>
            <sphereGeometry args={[0.1, 10, 8]} />
            <meshStandardMaterial {...mat(SKIN)} />
          </mesh>
          {/* magnifying glass: handle + ring + lens */}
          <group position={[0, -0.5, 0.62]} rotation={[1.2, 0, 0]}>
            <mesh position={[0, -0.18, 0]}>
              <cylinderGeometry args={[0.035, 0.035, 0.34, 8]} />
              <meshStandardMaterial {...mat("#3a2c1c")} />
            </mesh>
            <mesh position={[0, 0.05, 0]} rotation={[Math.PI / 2, 0, 0]}>
              <torusGeometry args={[0.17, 0.03, 8, 20]} />
              <meshStandardMaterial {...mat("#caa64a", { metalness: 0.4, roughness: 0.4 })} />
            </mesh>
            <mesh position={[0, 0.05, 0]} rotation={[Math.PI / 2, 0, 0]}>
              <cylinderGeometry args={[0.16, 0.16, 0.015, 20]} />
              <meshStandardMaterial
                {...mat(GLASS, { transparent: true, opacity: 0.32, metalness: 0.1, roughness: 0.05 })}
              />
            </mesh>
          </group>
        </group>
      </group>

      {/* legs */}
      <mesh position={[-0.16, 0.02, 0]}>
        <capsuleGeometry args={[0.12, 0.2, 4, 8]} />
        <meshStandardMaterial {...mat(INK)} />
      </mesh>
      <mesh position={[0.16, 0.02, 0]}>
        <capsuleGeometry args={[0.12, 0.2, 4, 8]} />
        <meshStandardMaterial {...mat(INK)} />
      </mesh>
    </group>
  );
}

function GroundPool() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.32, 0]} receiveShadow>
      <circleGeometry args={[1.3, 48]} />
      <meshBasicMaterial color={PAPER} transparent opacity={0.5} />
    </mesh>
  );
}

export function DetectiveModel() {
  const reduced = useMemo(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    [],
  );

  return (
    <div className="detective-stage" aria-hidden>
      <Canvas
        shadows
        dpr={[1, 1.8]}
        camera={{ position: [0.15, 1.0, 5.1], fov: 30 }}
        frameloop={reduced ? "demand" : "always"}
        gl={{ alpha: true, antialias: true }}
        onCreated={({ camera }) => camera.lookAt(0, 0.82, 0)}
      >
        <ambientLight intensity={0.55} color="#fff4df" />
        {/* key interrogation light */}
        <spotLight
          position={[2.2, 4, 3]}
          angle={0.5}
          penumbra={0.8}
          intensity={2.6}
          color="#fff1d6"
          castShadow
          shadow-mapSize={[1024, 1024]}
        />
        {/* cool rim light for noir contrast */}
        <pointLight position={[-3, 2, -1]} intensity={1.1} color="#5a86b8" />
        <Suspense fallback={null}>
          <Detective />
          <GroundPool />
        </Suspense>
      </Canvas>
    </div>
  );
}
