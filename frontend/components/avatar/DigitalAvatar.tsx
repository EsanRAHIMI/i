'use client';

import { useRef, useEffect, useState, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Sphere, Text, Html } from '@react-three/drei';
import * as THREE from 'three';
import { useAppStore } from '@/store/useAppStore';
import { useLipSync, getMouthAnimationParams } from '@/hooks/useLipSync';

interface AvatarProps {
  isActive?: boolean;
  isSpeaking?: boolean;
  audioUrl?: string;
  className?: string;
}

// Simple 3D Avatar Mesh Component
function AvatarMesh({ isActive, isSpeaking, audioUrl }: { isActive: boolean; isSpeaking: boolean; audioUrl?: string }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const mouthRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  
  // Use lip sync hook
  const { lipSyncData, mouthShape } = useLipSync(audioUrl, isSpeaking);

  useFrame((state) => {
    if (meshRef.current) {
      // Gentle floating animation
      meshRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.1;
      
      // Rotation when active
      if (isActive) {
        meshRef.current.rotation.y += 0.01;
      }
      
      // Pulsing effect when speaking
      if (isSpeaking) {
        const scale = 1 + Math.sin(state.clock.elapsedTime * 8) * 0.05;
        meshRef.current.scale.setScalar(scale);
      } else {
        meshRef.current.scale.setScalar(1);
      }
    }

    // Animate mouth based on lip sync data
    if (mouthRef.current && isSpeaking) {
      const mouthParams = getMouthAnimationParams(mouthShape, lipSyncData.amplitude);
      mouthRef.current.scale.set(mouthParams.scaleX, mouthParams.scaleY, 1);
      mouthRef.current.position.y = -0.2 + mouthParams.positionY;
      mouthRef.current.rotation.z = mouthParams.rotation;
    }
  });

  return (
    <group>
      {/* Main Avatar Sphere */}
      <Sphere
        ref={meshRef}
        args={[1, 32, 32]}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <meshStandardMaterial
          color={hovered ? '#8b5cf6' : '#6366f1'}
          emissive={isActive ? '#4338ca' : '#1e1b4b'}
          emissiveIntensity={isActive ? 0.3 : 0.1}
          roughness={0.2}
          metalness={0.8}
        />
      </Sphere>

      {/* Glow Effect */}
      <Sphere args={[1.2, 16, 16]}>
        <meshBasicMaterial
          color="#6366f1"
          transparent
          opacity={isActive ? 0.2 : 0.1}
          side={THREE.BackSide}
        />
      </Sphere>

      {/* Eyes */}
      <group position={[0, 0.2, 0.8]}>
        <Sphere args={[0.1, 8, 8]} position={[-0.2, 0, 0]}>
          <meshBasicMaterial color="#ffffff" />
        </Sphere>
        <Sphere args={[0.1, 8, 8]} position={[0.2, 0, 0]}>
          <meshBasicMaterial color="#ffffff" />
        </Sphere>
        
        {/* Pupils */}
        <Sphere args={[0.05, 8, 8]} position={[-0.2, 0, 0.05]}>
          <meshBasicMaterial color="#000000" />
        </Sphere>
        <Sphere args={[0.05, 8, 8]} position={[0.2, 0, 0.05]}>
          <meshBasicMaterial color="#000000" />
        </Sphere>
      </group>

      {/* Mouth - animated based on lip sync */}
      <group position={[0, -0.2, 0.8]}>
        <Sphere 
          ref={mouthRef}
          args={[isSpeaking ? 0.15 : 0.1, 8, 8]}
        >
          <meshBasicMaterial 
            color={isSpeaking ? "#ff6b6b" : "#4ecdc4"}
            transparent
            opacity={isSpeaking ? 0.9 : 0.7}
          />
        </Sphere>
      </group>

      {/* Status indicator */}
      {isActive && (
        <Text
          position={[0, -2, 0]}
          fontSize={0.3}
          color="#6366f1"
          anchorX="center"
          anchorY="middle"
        >
          {isSpeaking ? 'Speaking...' : 'Listening...'}
        </Text>
      )}
    </group>
  );
}

// Camera Controller
function CameraController() {
  const { camera } = useThree();
  
  useEffect(() => {
    camera.position.set(0, 0, 5);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  return null;
}

// Loading fallback
function AvatarFallback() {
  return (
    <Html center>
      <div className="flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    </Html>
  );
}

export function DigitalAvatar({ isActive = false, isSpeaking = false, audioUrl, className }: AvatarProps) {
  const { voiceSession } = useAppStore();
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);

  // Determine avatar state from voice session
  const avatarActive = isActive || voiceSession?.status === 'listening' || voiceSession?.status === 'processing';
  const avatarSpeaking = isSpeaking || voiceSession?.status === 'speaking';

  // Initialize audio analysis for lip sync
  useEffect(() => {
    if (audioUrl && typeof window !== 'undefined') {
      const initAudio = async () => {
        try {
          const context = new (window.AudioContext || (window as any).webkitAudioContext)();
          const analyserNode = context.createAnalyser();
          analyserNode.fftSize = 256;
          
          setAudioContext(context);
          setAnalyser(analyserNode);

          // Load and play audio
          const response = await fetch(audioUrl);
          const arrayBuffer = await response.arrayBuffer();
          const audioBuffer = await context.decodeAudioData(arrayBuffer);
          
          const source = context.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(analyserNode);
          analyserNode.connect(context.destination);
          source.start();
        } catch (error) {
          console.error('Audio initialization failed:', error);
        }
      };

      initAudio();
    }

    return () => {
      if (audioContext) {
        audioContext.close();
      }
    };
  }, [audioUrl]);

  return (
    <div className={`w-full h-full ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        style={{ background: 'transparent' }}
      >
        <CameraController />
        
        {/* Lighting */}
        <ambientLight intensity={0.4} />
        <pointLight position={[10, 10, 10]} intensity={0.8} />
        <pointLight position={[-10, -10, -10]} intensity={0.3} color="#6366f1" />
        
        {/* Avatar */}
        <Suspense fallback={<AvatarFallback />}>
          <AvatarMesh isActive={avatarActive} isSpeaking={avatarSpeaking} audioUrl={audioUrl} />
        </Suspense>
        
        {/* Controls for interaction */}
        <OrbitControls
          enableZoom={false}
          enablePan={false}
          maxPolarAngle={Math.PI / 2}
          minPolarAngle={Math.PI / 2}
          autoRotate={avatarActive}
          autoRotateSpeed={0.5}
        />
      </Canvas>
    </div>
  );
}