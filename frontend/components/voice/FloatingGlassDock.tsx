// frontend/components/voice/FloatingGlassDock.tsx
'use client';
import React, { useEffect, useRef, useState, useCallback } from "react";
import dynamic from 'next/dynamic';
import { Mic, MicOff, CalendarDays, Sparkles, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppStore } from '@/store/useAppStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { VoiceActivityIndicator } from './VoiceActivityIndicator';
import { logger } from '@/lib/logger';

/**
 * FloatingGlassDock v3 – "Genie 3D" Edition (Hardened)
 * - Safe against missing handlers (no runtime crash)
 * - Center button larger & breaks out of dock
 * - Genie popup with 3D model (GLB) that appears above dialog like a spirit
 * - Close returns the genie with a mist effect into the center button
 * - Keyboard: Space toggle, Esc close
 *
 * Dependencies (install once):
 *   yarn add framer-motion three @react-three/fiber @react-three/drei lucide-react
 *
 * NOTE: Put your GLB at public/models/iGebral.glb  (Next.js)  or serve it statically and
 * update MODEL_URL below. The user also uploaded /mnt/data/iGebral.glb; copy it to /public/models/.
 */

const MODEL_URL = "/models/iGebral.glb"; // change if needed

export default function FloatingGlassDock({
  agentOpen = false,
  onToggleAgent, // optional
  onLeftAction,
  onRightAction,
  leftIcon: LeftIcon = CalendarDays,
  rightIcon: RightIcon = Sparkles,
  leftLabel = "Schedule",
  rightLabel = "Suggest",
  className = "",
  onTranscript,
  onResponse,
}: {
  agentOpen?: boolean;
  onToggleAgent?: (next: boolean) => void; // <-- optional now
  onLeftAction?: () => void;
  onRightAction?: () => void;
  leftIcon?: React.ComponentType<{ className?: string }>;
  rightIcon?: React.ComponentType<{ className?: string }>;
  leftLabel?: string;
  rightLabel?: string;
  className?: string;
  onTranscript?: (text: string, isFinal: boolean) => void;
  onResponse?: (response: any) => void;
}) {
  const [open, setOpen] = useState(agentOpen);
  const centerBtnRef = useRef<HTMLButtonElement | null>(null);
  const { voiceSession, setVoiceSession, updateVoiceSession } = useAppStore();
  const [isStreaming, setIsStreaming] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [partialTranscript, setPartialTranscript] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  // WebSocket connection for real-time voice streaming
  const {
    isConnected,
    connectionState,
    sendVoiceData,
    sendVoiceStart,
    sendVoiceEnd,
  } = useWebSocket({
    onMessage: (message) => {
      switch (message.type) {
        case 'transcript_partial':
          setPartialTranscript(message.data.text);
          onTranscript?.(message.data.text, false);
          break;
          
        case 'transcript_final':
          setFinalTranscript(message.data.text);
          setPartialTranscript('');
          onTranscript?.(message.data.text, true);
          updateVoiceSession({ 
            transcript: message.data.text,
            confidence: message.data.confidence 
          });
          break;
          
        case 'agent_response':
          onResponse?.(message.data);
          if (message.data.audio_url) {
            updateVoiceSession({ status: 'speaking' });
            playAudioResponse(message.data.audio_url);
          } else {
            updateVoiceSession({ status: 'idle' });
          }
          break;
          
        case 'error':
          logger.error('Voice streaming error:', message.data);
          stopStreaming();
          break;
      }
    },
    onError: (error) => {
      // WebSocket errors are expected if server is not available - don't spam console
      logger.debug('WebSocket connection attempt (this is normal if WebSocket server is not configured)');
    }
  });

  useEffect(() => setOpen(agentOpen), [agentOpen]);

  // Initialize audio context and analyser
  const initAudioContext = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      streamRef.current = stream;

      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000
      });
      audioContextRef.current = audioContext;

      const analyser = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);
      
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      microphone.connect(analyser);
      analyserRef.current = analyser;

      return stream;
    } catch (error) {
      logger.error('Failed to initialize audio context:', error);
      throw error;
    }
  }, []);

  // Monitor audio levels
  const monitorAudioLevel = useCallback(() => {
    if (!analyserRef.current || !isStreaming) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);
    
    const sum = dataArray.reduce((acc, value) => acc + value, 0);
    const average = sum / dataArray.length;
    setAudioLevel(average / 255);

    animationFrameRef.current = requestAnimationFrame(monitorAudioLevel);
  }, [isStreaming]);

  // Start streaming
  const startStreaming = useCallback(async () => {
    if (!isConnected) {
      logger.warn('WebSocket not connected - voice streaming disabled');
      return;
    }

    try {
      setIsStreaming(true);
      setPartialTranscript('');
      setFinalTranscript('');
      
      setVoiceSession({
        id: Date.now().toString(),
        user_id: 'current-user',
        status: 'listening',
        created_at: new Date().toISOString()
      });

      const stream = await initAudioContext();
      
      // Start WebSocket voice session
      sendVoiceStart();

      // Create MediaRecorder for streaming
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0 && isConnected) {
          // Convert blob to ArrayBuffer and send via WebSocket
          const arrayBuffer = await event.data.arrayBuffer();
          sendVoiceData(arrayBuffer);
        }
      };

      // Start recording with small time slices for real-time streaming
      mediaRecorder.start(100); // 100ms chunks
      
      // Start audio level monitoring
      monitorAudioLevel();

    } catch (error) {
      logger.error('Failed to start streaming:', error);
      setIsStreaming(false);
      updateVoiceSession({ status: 'idle' });
    }
  }, [isConnected, initAudioContext, sendVoiceStart, sendVoiceData, monitorAudioLevel, setVoiceSession, updateVoiceSession]);

  // Stop streaming
  const stopStreaming = useCallback(() => {
    setIsStreaming(false);
    
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    sendVoiceEnd();
    updateVoiceSession({ status: 'processing' });
  }, [sendVoiceEnd, updateVoiceSession]);

  // Play audio response
  const playAudioResponse = useCallback(async (audioUrl: string) => {
    try {
      const audio = new Audio(audioUrl);
      audio.onended = () => {
        updateVoiceSession({ status: 'idle' });
      };
      await audio.play();
    } catch (error) {
      logger.error('Failed to play audio response:', error);
      updateVoiceSession({ status: 'idle' });
    }
  }, [updateVoiceSession]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  // Safe fallback for undefined handler (defined after stopStreaming)
  const safeToggleAgent = useCallback((next: boolean) => {
    setOpen(next); // local state always updates
    if (typeof onToggleAgent === "function") onToggleAgent(next);
    if (!next) {
      // Stop streaming when closing
      if (isStreaming) {
        stopStreaming();
      }
    }
  }, [onToggleAgent, isStreaming, stopStreaming]);

  // Button center for clip-path origin animation
  const [origin, setOrigin] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  useEffect(() => {
    const calc = () => {
      if (!centerBtnRef.current) return;
      const r = centerBtnRef.current.getBoundingClientRect();
      setOrigin({ x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) });
    };
    calc();
    window.addEventListener("resize", calc);
    window.addEventListener("scroll", calc, { passive: true } as any);
    return () => {
      window.removeEventListener("resize", calc);
      window.removeEventListener("scroll", calc as any);
    };
  }, []);

  const toggle = useCallback(() => safeToggleAgent(!open), [open, safeToggleAgent]);

  // Handle voice button click - toggle streaming when popup is open
  const handleVoiceButtonClick = useCallback(() => {
    if (open) {
      // If popup is open, toggle streaming
      if (isStreaming) {
        stopStreaming();
      } else if (isConnected && voiceSession?.status !== 'processing' && voiceSession?.status !== 'speaking') {
        startStreaming();
      }
    } else {
      // If popup is closed, open it
      safeToggleAgent(true);
    }
  }, [open, isStreaming, isConnected, voiceSession?.status, stopStreaming, startStreaming]);

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        if (open && isStreaming) {
          stopStreaming();
        } else if (open && !isStreaming && isConnected) {
          startStreaming();
        } else {
        toggle();
        }
      }
      if (e.key === "Escape" && open) {
        e.preventDefault();
        if (isStreaming) {
          stopStreaming();
        }
        safeToggleAgent(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, isStreaming, isConnected, stopStreaming, startStreaming, toggle]);

  return (
    <>
      <div
        aria-label="Voice control dock"
        className={`pointer-events-auto fixed inset-x-0 bottom-[max(env(safe-area-inset-bottom),1rem)] z-50 mx-auto w-full max-w-[560px] px-4 ${className}`}
      >
        <div
          className="relative mx-auto flex items-center justify-between rounded-2xl border border-white/15 bg-white/10 py-1 px-3 pb-2 shadow-[0_10px_40px_rgba(0,0,0,0.35)] backdrop-blur-xl dark:border-white/10 dark:bg-black/30"
          role="toolbar"
          aria-roledescription="dock"
        >
          {/* subtle top shine on container */}
          <span className="pointer-events-none absolute -top-px left-4 right-4 h-px bg-gradient-to-r from-transparent via-white/60 to-transparent"/>
          
          {/* Left action */}
          <GlassButton ariaLabel={leftLabel} onClick={onLeftAction} tooltip={leftLabel}>
            <LeftIcon className="h-5 w-5" aria-hidden="true" />
          </GlassButton>

          {/* Center: oversized & floating - Voice Control */}
          <motion.button
            ref={centerBtnRef}
            onClick={handleVoiceButtonClick}
            disabled={open && !isConnected && (voiceSession?.status === 'processing' || voiceSession?.status === 'speaking')}
            aria-label={
              isStreaming 
                ? "Stop recording" 
                : open 
                  ? "Start recording" 
                  : "Open voice agent"
            }
            className={`
              relative grid h-20 w-20 -translate-y-3 place-items-center rounded-full border shadow-2xl transition-all duration-200
              ${isStreaming 
                ? 'border-red-400/50 bg-red-500/30 hover:bg-red-500/40' 
                : open 
                  ? 'border-white/20 bg-white/15 hover:bg-white/25 dark:border-white/10 dark:bg-white/10'
                  : 'border-white/20 bg-white/15 hover:bg-white/25 dark:border-white/10 dark:bg-white/10'
              }
              ${open && !isConnected ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
            whileTap={{ scale: 0.97 }}
          >
            {/* halo / pulse when streaming */}
            <AnimatePresence>
              {isStreaming && (
                <motion.span
                  className="absolute inset-0 rounded-full"
                  initial={{ boxShadow: "0 0 0 0 rgba(239,68,68,0.45)" }}
                  animate={{ boxShadow: [
                    "0 0 0 0 rgba(239,68,68,0.35)",
                    "0 0 0 14px rgba(239,68,68,0.0)",
                  ]}}
                  transition={{ duration: 1.6, repeat: Infinity }}
                />
              )}
              {open && !isStreaming && voiceSession?.status === 'listening' && (
                <motion.span
                  className="absolute inset-0 rounded-full"
                  initial={{ boxShadow: "0 0 0 0 rgba(16,185,129,0.45)" }}
                  animate={{ boxShadow: [
                    "0 0 0 0 rgba(16,185,129,0.35)",
                    "0 0 0 14px rgba(16,185,129,0.0)",
                  ]}}
                  transition={{ duration: 1.6, repeat: Infinity }}
                />
              )}
            </AnimatePresence>
            
            {/* Audio level indicator when streaming */}
            {isStreaming && (
              <motion.div
                className="absolute inset-0 rounded-full border-4 border-white/30"
                animate={{
                  scale: 1 + audioLevel * 0.5,
                  opacity: Math.max(0.3, audioLevel)
                }}
                transition={{ duration: 0.1 }}
              />
            )}
            
            {isStreaming ? (
              <div className="relative h-7 w-7 bg-white rounded-sm" />
            ) : open ? (
              <Mic className="relative h-7 w-7" />
            ) : (
              <MicOff className="relative h-7 w-7" />
            )}
          </motion.button>

          {/* Right action */}
          <GlassButton ariaLabel={rightLabel} onClick={onRightAction} tooltip={rightLabel}>
            <RightIcon className="h-5 w-5" aria-hidden="true" />
          </GlassButton>
        </div>
      </div>

      {/* Genie Agent Popup (3D) */}
      <AgentGeniePopup 
        open={open} 
        onClose={() => safeToggleAgent(false)} 
        origin={origin}
        isStreaming={isStreaming}
        isConnected={isConnected}
        connectionState={connectionState}
        partialTranscript={partialTranscript}
        finalTranscript={finalTranscript}
        voiceSession={voiceSession}
        onStartStreaming={startStreaming}
        onStopStreaming={stopStreaming}
      />
    </>
  );
}

function GlassButton({
  ariaLabel,
  tooltip,
  onClick,
  children,
}: {
  ariaLabel: string;
  tooltip?: string;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      title={tooltip}
      onClick={onClick}
      className="grid h-12 w-12 place-items-center rounded-xl border border-white/20 bg-white/10 text-sm shadow-lg transition-all hover:translate-y-[-1px] hover:bg-white/20 active:translate-y-0 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
    >
      {children}
    </button>
  );
}

// ---------------- 3D POPUP ----------------
// We keep all 3D code client-only to avoid SSR crashes.
function AgentGeniePopup({
  open,
  onClose,
  origin,
  isStreaming,
  isConnected,
  connectionState,
  partialTranscript,
  finalTranscript,
  voiceSession,
  onStartStreaming,
  onStopStreaming,
}: {
  open: boolean;
  onClose: () => void;
  origin: { x: number; y: number };
  isStreaming: boolean;
  isConnected: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  partialTranscript: string;
  finalTranscript: string;
  voiceSession: any;
  onStartStreaming: () => void;
  onStopStreaming: () => void;
}) {
  // circle-reveal animation centered on the mic button
  const circleClosed = `circle(0px at ${origin.x}px ${origin.y}px)`;
  const circleOpen = `circle(150% at ${origin.x}px ${origin.y}px)`;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[60]"
          initial={{ clipPath: circleClosed }}
          animate={{ clipPath: circleOpen }}
          exit={{ clipPath: circleClosed }}
          transition={{ type: "spring", stiffness: 140, damping: 22 }}
        >
          {/* dim background */}
          <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px]" onClick={onClose} />

          {/* genie mist (CSS radial glow) rising from bottom center */}
          <motion.div
            className="pointer-events-none absolute inset-x-0 bottom-0 h-44"
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 22 }}
          >
            <div className="mx-auto h-full w-full max-w-[620px] bg-[radial-gradient(ellipse_at_bottom,rgba(16,185,129,0.35),rgba(0,0,0,0)_60%)]" />
          </motion.div>

          {/* 3D Avatar - positioned above the card, breaking out of frame */}
          <motion.div
            className="absolute inset-x-0 bottom-[calc(24rem+2rem)] mx-auto w-[min(600px,90vw)] h-[450px] z-[65]"
            initial={{ y: 60, scale: 0.9, opacity: 0 }}
            animate={{ y: 0, scale: 1, opacity: 1 }}
            exit={{ y: 30, scale: 0.95, opacity: 0 }}
            transition={{ type: "spring", stiffness: 200, damping: 24 }}
          >
            <div className="relative h-full w-full overflow-visible pointer-events-none bg-transparent">
              <CanvasIfClient>
                <ThreeScene modelUrl={MODEL_URL} />
              </CanvasIfClient>
            </div>
          </motion.div>

          {/* agent card with 3D */}
          <motion.div
            role="dialog"
            aria-modal="true"
            className="absolute inset-x-0 bottom-24 mx-auto w-[min(820px,95vw)]"
            initial={{ y: 40, scale: 0.95, opacity: 0 }}
            animate={{ y: 0, scale: 1, opacity: 1 }}
            exit={{ y: 20, scale: 0.98, opacity: 0 }}
            transition={{ type: "spring", stiffness: 220, damping: 26 }}
          >
            <div className="relative overflow-visible rounded-3xl border border-white/15 bg-gradient-to-b from-white/15 to-white/5 p-4 shadow-[0_30px_80px_rgba(0,0,0,0.45)] backdrop-blur-2xl dark:border-white/10 dark:from-white/10 dark:to-white/5">
              <button
                onClick={onClose}
                aria-label="Close agent"
                className="absolute right-3 top-3 z-10 rounded-full border border-white/20 bg-white/10 p-1 hover:bg-white/20"
              >
                <X className="h-4 w-4" />
              </button>

              <div className="grid grid-cols-1 gap-4 pt-4">
                {/* Voice Activity Indicator */}
                <div className="flex flex-col items-center justify-center py-4">
                  <VoiceActivityIndicator size="lg" showStatus={true} />
                </div>

                {/* Connection Status */}
                {!isConnected && (
                  <div className="flex items-center justify-center space-x-2 text-xs text-yellow-400">
                    <div className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
                    <span>
                      {connectionState === 'connecting' 
                        ? 'Connecting...' 
                        : connectionState === 'error'
                          ? 'Connection Error'
                          : 'Waiting for connection'}
                    </span>
                  </div>
                )}

                {/* Transcript Display */}
                {(partialTranscript || finalTranscript || voiceSession?.transcript) && (
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm leading-relaxed">
                    {partialTranscript && (
                      <p className="opacity-70 italic mb-2">{partialTranscript}</p>
                    )}
                    {(finalTranscript || voiceSession?.transcript) && (
                      <p className="opacity-90 font-medium">
                        "{finalTranscript || voiceSession?.transcript}"
                      </p>
                    )}
                    {voiceSession?.confidence && (
                      <p className="text-xs opacity-60 mt-2">
                        Confidence: {Math.round(voiceSession.confidence * 100)}%
                      </p>
                    )}
                  </div>
                )}

                {/* Default Message */}
                {!partialTranscript && !finalTranscript && !voiceSession?.transcript && (
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-3 text-sm leading-relaxed">
                    <p className="opacity-90">
                      {isStreaming 
                        ? 'Listening...' 
                        : voiceSession?.status === 'processing'
                          ? 'Processing...'
                          : voiceSession?.status === 'speaking'
                            ? 'Speaking...'
                            : 'Hi! I\'m here. Tell me what you need—schedule, focus, or a quick plan.'}
                    </p>
                  </div>
                )}

                {/* Quick Actions */}
                {!isStreaming && voiceSession?.status !== 'processing' && voiceSession?.status !== 'speaking' && (
                  <div className="flex flex-wrap gap-2 justify-center">
                    {[
                      "Plan my morning",
                      "Add 20-min focus block",
                      "Reschedule tonight walk",
                      "Summarize tomorrow",
                    ].map((t) => (
                      <button 
                        key={t} 
                        className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs hover:bg-white/20 transition-colors"
                        onClick={() => {
                          // Handle quick action click
                          logger.debug('Quick action triggered:', t);
                        }}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// -------- three.js helpers (client-only wrapper) --------
// -------- three.js helpers (client-only wrapper) --------
const Canvas = dynamic(() => import('@react-three/fiber').then(m => m.Canvas), { ssr: false });
function CanvasIfClient({ children }: { children: React.ReactNode }) {
  return (
    <Canvas 
      shadows 
      camera={{ position: [0, 0.3, 1.8], fov: 55 }}
      gl={{ alpha: true, antialias: true, preserveDrawingBuffer: true }}
      style={{ background: 'transparent' }}
    >
      {children}
    </Canvas>
  );
}

function ThreeScene({ modelUrl }: { modelUrl: string }) {
  const { useGLTF, PresentationControls, Environment, ContactShadows } = require("@react-three/drei");
  const gltf = useGLTF(modelUrl);

  return (
    <>
      {/* Transparent background - no color or fog */}
      <hemisphereLight intensity={0.6} groundColor={"#222"} />
      <directionalLight position={[2, 4, 2]} intensity={1.1} castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} />
      {/* Additional light for better face visibility */}
      <pointLight position={[-2, 2, 3]} intensity={0.8} color="#ffffff" />
      <spotLight position={[0, 3, 2]} angle={0.5} penumbra={0.5} intensity={1.2} castShadow />

      <PresentationControls 
        global 
        zoom={1.2} 
        rotation={[0, 0, 0]} 
        polar={[-Math.PI / 3, Math.PI / 3]} 
        azimuth={[-Math.PI / 2, Math.PI / 2]}
        enablePan={false}
        enableZoom={true}
        enableRotate={true}
      >
        <group position={[0, 0, 0]} dispose={null}>
          {/* Offset model down so face/head is centered (model origin is at feet, need to move down significantly for face to be at center) */}
          <group position={[0, -4.5, 0]}>
            <primitive object={gltf.scene} scale={2.8} />
          </group>
        </group>
      </PresentationControls>

      <Environment preset="city" />
      <ContactShadows position={[0, -4.5, 0]} opacity={0.45} scale={6} blur={2.6} far={2.2} />
    </>
  );
}

// ---------------- DEV TEST CASES ----------------
/**
 * 1) Minimal usage – NO onToggleAgent provided (should NOT throw):
 *    function Demo1() { return <FloatingGlassDock /> }
 *
 * 2) Controlled usage – Proper state handler provided:
 *    function Demo2() {
 *      const [open, setOpen] = useState(false);
 *      return (
 *        <FloatingGlassDock
 *          agentOpen={open}
 *          onToggleAgent={setOpen}
 *          onLeftAction={() => console.log('left')}
 *          onRightAction={() => console.log('right')}
 *        />
 *      );
 *    }
 *
 * 3) Three model path check – ensure GLB served from /public/models/iGebral.glb
 *    // Put iGebral.glb in your Next.js public/models folder. If path differs, update MODEL_URL.
 *
 * EXPECTED BEHAVIOR
 * - Tap center button => 3D genie pops above dock with mist and clip-path reveal from the button center.
 * - Tap again/Esc/background click => fades and returns into button (clip-path shrinks).
 * - No crashes if onToggleAgent is omitted.
 */
