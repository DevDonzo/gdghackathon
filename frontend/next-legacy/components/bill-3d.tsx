"use client";

import React, { useRef } from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { TextureLoader, Mesh, DoubleSide, Group } from "three";
import { Center, Float } from "@react-three/drei";

type BillProps = {
  scrollProgress: number;
};

const BillMesh = ({ scrollProgress }: BillProps) => {
  const groupRef = useRef<Group>(null);
  const texture = useLoader(TextureLoader, "/dollarbill.jpg");

  useFrame((state) => {
    if (!groupRef.current) return;

    let targetOpacity = 1;
    if (scrollProgress < 0.12) targetOpacity = scrollProgress / 0.12;
    if (scrollProgress > 0.88) targetOpacity = 1 - (scrollProgress - 0.88) / 0.12;

    const idleTilt = Math.sin(state.clock.elapsedTime * 0.45) * 0.025;
    const targetRotY = -0.34 + scrollProgress * Math.PI * 1.16;
    const targetRotX = -0.08 + idleTilt + scrollProgress * 0.16;
    const targetRotZ = -0.035 + scrollProgress * 0.07;
    const targetY = Math.sin(scrollProgress * Math.PI) * 0.16;
    const targetScale = 1.08 + Math.sin(scrollProgress * Math.PI) * 0.58;

    groupRef.current.rotation.y += (targetRotY - groupRef.current.rotation.y) * 0.07;
    groupRef.current.rotation.x += (targetRotX - groupRef.current.rotation.x) * 0.07;
    groupRef.current.rotation.z += (targetRotZ - groupRef.current.rotation.z) * 0.07;
    groupRef.current.position.y += (targetY - groupRef.current.position.y) * 0.06;
    groupRef.current.scale.setScalar(groupRef.current.scale.x + (targetScale - groupRef.current.scale.x) * 0.06);

    groupRef.current.children.forEach((child) => {
      const mesh = child as Mesh;
      if (mesh.material) {
        if (Array.isArray(mesh.material)) {
          mesh.material.forEach(m => { m.opacity = targetOpacity; m.transparent = true; });
        } else {
          mesh.material.opacity = targetOpacity;
          mesh.material.transparent = true;
        }
      }
    });
  });

  return (
    <group ref={groupRef}>
      {/* Front Face */}
      <mesh position={[0, 0, 0.01]}>
        <planeGeometry args={[4, 1.7]} />
        <meshStandardMaterial map={texture} transparent opacity={0} metalness={0.22} roughness={0.58} />
      </mesh>
      {/* Back face */}
      <mesh position={[0, 0, -0.01]} rotation={[0, Math.PI, 0]}>
        <planeGeometry args={[4, 1.7]} />
        <meshStandardMaterial map={texture} transparent opacity={0} metalness={0.22} roughness={0.58} />
      </mesh>
    </group>
  );
};

export const Bill3D = ({ scrollProgress }: BillProps) => {
  return (
    <div className="canvas-container">
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        <ambientLight intensity={0.85} />
        <pointLight position={[8, 8, 8]} intensity={1.1} />
        <spotLight position={[-8, 8, 8]} angle={0.28} penumbra={1} intensity={0.9} />
        <Center>
          <Float speed={0.85} rotationIntensity={0.08} floatIntensity={0.18}>
            <BillMesh scrollProgress={scrollProgress} />
          </Float>
        </Center>
      </Canvas>
    </div>
  );
};
