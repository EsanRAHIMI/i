'use client';

import { useRef, useEffect, useState, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Sphere, Text, Html, Billboard } from '@react-three/drei';
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
function AvatarMesh({ isActive, isSpeaking, audioUrl, avatarUrl }: { isActive: boolean; isSpeaking: boolean; audioUrl?: string; avatarUrl?: string }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const mouthRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const [textureError, setTextureError] = useState(false);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  
  // Use lip sync hook
  const { lipSyncData, mouthShape } = useLipSync(audioUrl, isSpeaking);
  
  // Load avatar texture if available
  useEffect(() => {
    if (!avatarUrl) {
      console.log('No avatar URL provided');
      setTexture((prevTexture) => {
        if (prevTexture) {
          prevTexture.dispose();
        }
        return null;
      });
      setTextureError(false);
      return;
    }

    // Build full URL for texture
    let textureUrl: string;
    if (avatarUrl.startsWith('http://') || avatarUrl.startsWith('https://')) {
      textureUrl = avatarUrl;
    } else {
      // Handle relative URLs from backend
      let apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // Remove trailing /api/v1 from apiUrl if present (to avoid duplication)
      // since avatar_url from backend already includes /api/v1
      if (apiUrl.endsWith('/api/v1')) {
        apiUrl = apiUrl.replace(/\/api\/v1$/, '');
      }
      
      // Remove leading slash if present to avoid double slashes
      const cleanUrl = avatarUrl.startsWith('/') ? avatarUrl : `/${avatarUrl}`;
      textureUrl = `${apiUrl}${cleanUrl}`;
    }

    console.log('Loading avatar texture from:', textureUrl);
    setTextureError(false);

    let currentTexture: THREE.Texture | null = null;
    let isCancelled = false;

    const loader = new THREE.TextureLoader();
    // Set crossOrigin for CORS
    loader.setCrossOrigin('anonymous');
    
    loader.load(
      textureUrl,
      (loadedTexture) => {
        if (isCancelled) {
          loadedTexture.dispose();
          return;
        }
        console.log('Avatar texture loaded successfully', {
          width: loadedTexture.image?.width,
          height: loadedTexture.image?.height,
          format: loadedTexture.format,
        });
        loadedTexture.colorSpace = THREE.SRGBColorSpace;
        // Configure texture settings for flat plane display
        // For a flat plane, we want the texture to display without distortion
        loadedTexture.wrapS = THREE.ClampToEdgeWrapping;
        loadedTexture.wrapT = THREE.ClampToEdgeWrapping;
        // Set repeat to 1 to show full texture without tiling
        loadedTexture.repeat.set(1, 1);
        // Set offset to center the texture
        loadedTexture.offset.set(0, 0);
        // Use better filtering for smoother texture
        loadedTexture.minFilter = THREE.LinearMipmapLinearFilter;
        loadedTexture.magFilter = THREE.LinearFilter;
        // Generate mipmaps for better quality at different distances
        loadedTexture.generateMipmaps = true;
        // For plane geometry, we need to flip Y to display correctly
        loadedTexture.flipY = true; // Flip Y for correct orientation
        loadedTexture.needsUpdate = true;
        currentTexture = loadedTexture;
        setTexture((prevTexture) => {
          if (prevTexture) {
            prevTexture.dispose();
          }
          return loadedTexture;
        });
        setTextureError(false);
      },
      (progress) => {
        // Progress callback (optional)
        if (progress.total > 0) {
          const percent = (progress.loaded / progress.total) * 100;
          console.log(`Avatar texture loading: ${percent.toFixed(0)}%`);
        }
      },
      (error) => {
        if (isCancelled) return;
        console.error('Failed to load avatar texture:', error);
        console.error('Texture URL was:', textureUrl);
        setTextureError(true);
        setTexture((prevTexture) => {
          if (prevTexture) {
            prevTexture.dispose();
          }
          return null;
        });
      }
    );

    return () => {
      isCancelled = true;
      if (currentTexture) {
        currentTexture.dispose();
      }
    };
  }, [avatarUrl]);

  // Force material update when texture changes
  useEffect(() => {
    if (meshRef.current && texture) {
      const material = meshRef.current.material as THREE.MeshStandardMaterial;
      
      if (material && texture.image) {
        material.map = texture;
        material.needsUpdate = true;
        
        // Circle geometry is already circular, no need to adjust
        // Just ensure the texture is properly applied
        console.log('Material updated with texture for circular display:', {
          hasMap: !!material.map,
          mapWidth: material.map?.image?.width,
          mapHeight: material.map?.image?.height,
          aspectRatio: texture.image ? (texture.image.width / texture.image.height) : null,
        });
      }
    }
  }, [texture]);

  useFrame((state) => {
    if (meshRef.current) {
      // Gentle floating animation (only for sphere background, not for plane)
      if (!texture) {
        meshRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.1;
        
        // Rotation when active (only for sphere)
        if (isActive) {
          meshRef.current.rotation.y += 0.01;
        }
      }
      
      // Pulsing effect when speaking (works for both sphere and plane)
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
      {/* Background Sphere - Only shown when no texture */}
      {!texture && (
        <>
          <Sphere
            ref={meshRef}
            args={[1.5, 64, 64]}
            onPointerOver={() => setHovered(true)}
            onPointerOut={() => setHovered(false)}
          >
            <meshStandardMaterial
              color={hovered ? '#8b5cf6' : '#6366f1'}
              emissive={isActive ? '#4338ca' : '#1e1b4b'}
              emissiveIntensity={isActive ? 0.3 : 0.1}
              roughness={0.2}
              metalness={0.8}
              side={THREE.FrontSide}
            />
          </Sphere>
          {/* Glow Effect */}
          <Sphere args={[1.8, 16, 16]}>
            <meshBasicMaterial
              color="#6366f1"
              transparent
              opacity={isActive ? 0.2 : 0.1}
              side={THREE.BackSide}
            />
          </Sphere>
        </>
      )}

      {/* Flat Image Display - Shows user image as flat circle in center */}
      {texture && (
        <Billboard
          follow={true}
          lockX={false}
          lockY={false}
          lockZ={false}
        >
          <group>
            {/* Circular frame/border */}
            <mesh>
              <ringGeometry args={[1.05, 1.1, 64]} />
              <meshBasicMaterial
                color="#6366f1"
                transparent
                opacity={0.9}
                side={THREE.DoubleSide}
              />
            </mesh>
            
            {/* User image - using circle geometry for proper circular shape */}
            <mesh
              ref={meshRef}
              onPointerOver={() => setHovered(true)}
              onPointerOut={() => setHovered(false)}
            >
              <circleGeometry args={[1.0, 64]} />
              <meshStandardMaterial
                map={texture}
                color="#ffffff"
                emissive="#000000"
                emissiveIntensity={0}
                roughness={0.8}
                metalness={0.0}
                side={THREE.DoubleSide}
                transparent={false}
                opacity={1.0}
              />
            </mesh>
          </group>
        </Billboard>
      )}

      {/* Eyes - Show on top of user image when texture exists */}
      {texture && (
        <Billboard
          follow={true}
          lockX={false}
          lockY={false}
          lockZ={false}
        >
          <group position={[0, 0.25, 0.01]}>
            <Sphere args={[0.06, 8, 8]} position={[-0.12, 0, 0]}>
              <meshBasicMaterial color="#ffffff" />
            </Sphere>
            <Sphere args={[0.06, 8, 8]} position={[0.12, 0, 0]}>
              <meshBasicMaterial color="#ffffff" />
            </Sphere>
            
            {/* Pupils */}
            <Sphere args={[0.03, 8, 8]} position={[-0.12, 0, 0.01]}>
              <meshBasicMaterial color="#000000" />
            </Sphere>
            <Sphere args={[0.03, 8, 8]} position={[0.12, 0, 0.01]}>
              <meshBasicMaterial color="#000000" />
            </Sphere>
          </group>
        </Billboard>
      )}

      {/* Eyes - Only show when no texture (sphere mode) */}
      {!texture && (
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
      )}

      {/* Mouth - Show on top of user image when texture exists */}
      {texture && (
        <Billboard
          follow={true}
          lockX={false}
          lockY={false}
          lockZ={false}
        >
          <group position={[0, -0.25, 0.01]}>
            <Sphere 
              ref={mouthRef}
              args={[isSpeaking ? 0.1 : 0.06, 8, 8]}
            >
              <meshBasicMaterial 
                color={isSpeaking ? "#ff6b6b" : "#4ecdc4"}
                transparent
                opacity={isSpeaking ? 0.9 : 0.7}
              />
            </Sphere>
          </group>
        </Billboard>
      )}

      {/* Mouth - Only show when no texture (sphere mode) */}
      {!texture && (
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
      )}

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
    camera.position.set(0, 0, 3.5);
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
  const { voiceSession, user } = useAppStore();
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);

  // Debug: Log avatar URL changes
  useEffect(() => {
    console.log('DigitalAvatar - user avatar_url:', user?.avatar_url);
  }, [user?.avatar_url]);

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
        camera={{ position: [0, 0, 3.5], fov: 75 }}
        style={{ background: 'transparent' }}
      >
        <CameraController />
        
        {/* Lighting - Increased intensity for better texture visibility */}
        <ambientLight intensity={0.8} />
        <pointLight position={[10, 10, 10]} intensity={1.2} />
        <pointLight position={[-10, -10, -10]} intensity={0.6} color="#6366f1" />
        <directionalLight position={[5, 5, 5]} intensity={0.5} />
        
        {/* Avatar */}
        <Suspense fallback={<AvatarFallback />}>
          <AvatarMesh 
            isActive={avatarActive} 
            isSpeaking={avatarSpeaking} 
            audioUrl={audioUrl}
            avatarUrl={user?.avatar_url}
          />
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