import { useEffect, useState, useRef } from 'react';

interface LipSyncData {
  amplitude: number;
  frequency: number;
  isActive: boolean;
}

export function useLipSync(audioUrl?: string, isActive: boolean = false) {
  const [lipSyncData, setLipSyncData] = useState<LipSyncData>({
    amplitude: 0,
    frequency: 0,
    isActive: false
  });
  
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (!audioUrl || !isActive) {
      setLipSyncData({ amplitude: 0, frequency: 0, isActive: false });
      return;
    }

    const initAudioAnalysis = async () => {
      try {
        // Create audio context
        const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
        const audioContext = new AudioContext();
        audioContextRef.current = audioContext;

        // Create analyser
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.8;
        analyserRef.current = analyser;

        // Create audio element
        const audio = new Audio(audioUrl);
        audio.crossOrigin = 'anonymous';
        audioElementRef.current = audio;

        // Connect audio to analyser
        const source = audioContext.createMediaElementSource(audio);
        source.connect(analyser);
        analyser.connect(audioContext.destination);

        // Start audio analysis
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        
        const updateLipSync = () => {
          if (!analyser || !isActive) return;

          analyser.getByteFrequencyData(dataArray);
          
          // Calculate amplitude (volume)
          const sum = dataArray.reduce((acc, value) => acc + value, 0);
          const amplitude = sum / dataArray.length / 255;
          
          // Calculate dominant frequency
          let maxIndex = 0;
          let maxValue = 0;
          for (let i = 0; i < dataArray.length; i++) {
            if (dataArray[i] > maxValue) {
              maxValue = dataArray[i];
              maxIndex = i;
            }
          }
          
          const frequency = (maxIndex * audioContext.sampleRate) / (analyser.fftSize * 2);
          
          setLipSyncData({
            amplitude,
            frequency,
            isActive: amplitude > 0.01 // Threshold for detecting speech
          });

          animationFrameRef.current = requestAnimationFrame(updateLipSync);
        };

        // Start playback and analysis
        await audio.play();
        updateLipSync();

        // Handle audio end
        audio.addEventListener('ended', () => {
          setLipSyncData({ amplitude: 0, frequency: 0, isActive: false });
        });

      } catch (error) {
        console.error('Failed to initialize audio analysis:', error);
        setLipSyncData({ amplitude: 0, frequency: 0, isActive: false });
      }
    };

    initAudioAnalysis();

    return () => {
      // Cleanup
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      
      if (audioElementRef.current) {
        audioElementRef.current.pause();
        audioElementRef.current = null;
      }
      
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
      
      analyserRef.current = null;
    };
  }, [audioUrl, isActive]);

  // Generate mouth shapes based on frequency ranges
  const getMouthShape = () => {
    if (!lipSyncData.isActive || lipSyncData.amplitude < 0.01) {
      return 'closed';
    }

    const { frequency, amplitude } = lipSyncData;
    
    // Map frequency ranges to mouth shapes
    if (frequency < 300) {
      return amplitude > 0.3 ? 'open-wide' : 'open-small';
    } else if (frequency < 800) {
      return amplitude > 0.4 ? 'smile' : 'open-medium';
    } else if (frequency < 2000) {
      return 'ee-shape';
    } else {
      return 'oh-shape';
    }
  };

  return {
    lipSyncData,
    mouthShape: getMouthShape(),
    isAnalyzing: isActive && !!audioUrl
  };
}

// Utility function to get mouth animation parameters
export function getMouthAnimationParams(mouthShape: string, amplitude: number) {
  const baseParams = {
    scaleY: 1,
    scaleX: 1,
    positionY: 0,
    rotation: 0
  };

  switch (mouthShape) {
    case 'open-wide':
      return {
        ...baseParams,
        scaleY: 1.5 + amplitude * 0.5,
        scaleX: 1.2 + amplitude * 0.3,
        positionY: -0.1
      };
    
    case 'open-medium':
      return {
        ...baseParams,
        scaleY: 1.2 + amplitude * 0.3,
        scaleX: 1.1 + amplitude * 0.2
      };
    
    case 'open-small':
      return {
        ...baseParams,
        scaleY: 1.1 + amplitude * 0.2,
        scaleX: 1.05 + amplitude * 0.1
      };
    
    case 'smile':
      return {
        ...baseParams,
        scaleX: 1.3 + amplitude * 0.2,
        scaleY: 0.8,
        rotation: Math.PI / 12
      };
    
    case 'ee-shape':
      return {
        ...baseParams,
        scaleX: 0.8,
        scaleY: 1.1 + amplitude * 0.2
      };
    
    case 'oh-shape':
      return {
        ...baseParams,
        scaleX: 0.9,
        scaleY: 1.3 + amplitude * 0.3
      };
    
    default: // closed
      return baseParams;
  }
}