/**
 * Hook for recording audio and sending to backend STT (Gradium)
 * Streams audio chunks in real-time for live transcription
 */

import { useState, useCallback, useRef } from 'react';

interface UseAudioRecorderReturn {
  isRecording: boolean;
  startRecording: (onTranscript: (text: string) => void) => Promise<void>;
  stopRecording: () => Promise<void>;
  error: string | null;
}

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const onTranscriptRef = useRef<((text: string) => void) | null>(null);
  const accumulatedTranscriptRef = useRef<string>('');
  const audioChunksRef = useRef<Blob[]>([]);
  const processingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const mimeTypeRef = useRef<string>('');

  const startRecording = useCallback(async (onTranscript: (text: string) => void) => {
    try {
      setError(null);
      onTranscriptRef.current = onTranscript;
      accumulatedTranscriptRef.current = '';
      audioChunksRef.current = [];

      // Request microphone access with optimal settings for Gradium
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1, // Mono
          sampleRate: 24000, // 24kHz for Gradium STT
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        } 
      });

      // Try to use WAV format if supported, otherwise use webm
      let mimeType = 'audio/webm;codecs=opus';
      if (MediaRecorder.isTypeSupported('audio/wav')) {
        mimeType = 'audio/wav';
      } else if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      }
      
      mimeTypeRef.current = mimeType;
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000,
      });

      // Accumulate audio chunks
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // Start recording with 500ms intervals
      mediaRecorder.start(500);
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);

      // Process accumulated chunks every 2 seconds for streaming transcription
      processingIntervalRef.current = setInterval(async () => {
        if (audioChunksRef.current.length > 0) {
          const chunks = [...audioChunksRef.current];
          await processAccumulatedChunks(chunks, mimeType);
        }
      }, 2000);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start recording';
      setError(errorMessage);
      console.error('Recording error:', err);
    }
  }, []);

  const processAccumulatedChunks = async (chunks: Blob[], mimeType: string) => {
    try {
      console.log(`Processing ${chunks.length} chunks, total size: ${chunks.reduce((sum, c) => sum + c.size, 0)} bytes`);
      
      // Combine all chunks into one blob
      const audioBlob = new Blob(chunks, { type: mimeType });
      console.log(`Combined audio blob: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
      
      // Check if we need to convert WebM to WAV
      const needsConversion = mimeType.includes('webm');
      
      let base64Audio: string;
      let format = 'wav';
      
      if (needsConversion) {
        console.log('Converting WebM to WAV...');
        // Convert WebM to WAV using Web Audio API
        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        
        try {
          const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
          console.log(`Decoded audio: ${audioBuffer.duration}s, ${audioBuffer.sampleRate}Hz`);
          
          // Convert to WAV format
          const wavBlob = await audioBufferToWav(audioBuffer);
          base64Audio = await blobToBase64(wavBlob);
          console.log(`WAV conversion complete, base64 length: ${base64Audio.length}`);
          
          audioContext.close();
        } catch (decodeError) {
          console.log('Skipping incomplete audio chunk:', decodeError);
          audioContext.close();
          return;
        }
      } else {
        // Already in WAV format
        base64Audio = await blobToBase64(audioBlob);
      }

      console.log('Sending to backend STT endpoint...');
      // Send to backend streaming endpoint
      const response = await fetch('http://localhost:8000/api/voice/stt/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          audio_chunk: base64Audio,
          is_final: false,
          input_format: format,
        }),
      });

      console.log(`Backend response: ${response.status} ${response.statusText}`);
      if (!response.ok) {
        console.error(`STT stream failed: ${response.statusText}`);
        return;
      }

      // Read SSE stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        console.log('Reading SSE stream...');
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            console.log('Stream ended');
            break;
          }

          const chunk = decoder.decode(value);
          console.log('Received chunk:', chunk);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                console.log('Parsed SSE data:', data);
                
                if (data.type === 'transcript' && data.text) {
                  // Update accumulated transcript
                  const newText = data.text.trim();
                  console.log('New transcript text:', newText);
                  if (newText && !accumulatedTranscriptRef.current.includes(newText)) {
                    accumulatedTranscriptRef.current += (accumulatedTranscriptRef.current ? ' ' : '') + newText;
                    console.log('Accumulated transcript:', accumulatedTranscriptRef.current);
                    if (onTranscriptRef.current) {
                      onTranscriptRef.current(accumulatedTranscriptRef.current.trim());
                    }
                  }
                }
              } catch (parseError) {
                console.error('Parse error:', parseError);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Chunk processing error:', err);
    }
  };

  const stopRecording = useCallback(async (): Promise<void> => {
    return new Promise((resolve) => {
      // Clear processing interval
      if (processingIntervalRef.current) {
        clearInterval(processingIntervalRef.current);
        processingIntervalRef.current = null;
      }

      if (!mediaRecorderRef.current || !isRecording) {
        resolve();
        return;
      }

      mediaRecorderRef.current.onstop = async () => {
        try {
          // Process any remaining chunks
          if (audioChunksRef.current.length > 0) {
            await processAccumulatedChunks(audioChunksRef.current, mimeTypeRef.current);
          }

          // Stop all tracks
          if (mediaRecorderRef.current?.stream) {
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
          }

          setIsRecording(false);
          resolve();
        } catch (err) {
          const errorMessage = err instanceof Error ? err.message : 'Failed to stop recording';
          setError(errorMessage);
          console.error('Stop error:', err);
          setIsRecording(false);
          resolve();
        }
      };

      mediaRecorderRef.current.stop();
    });
  }, [isRecording]);

  return {
    isRecording,
    startRecording,
    stopRecording,
    error,
  };
}

// Helper function to convert Blob to base64
function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = (reader.result as string).split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// Helper function to convert AudioBuffer to WAV format
function audioBufferToWav(audioBuffer: AudioBuffer): Promise<Blob> {
  return new Promise((resolve) => {
    const numberOfChannels = 1; // Mono
    const sampleRate = audioBuffer.sampleRate;
    const format = 1; // PCM
    const bitDepth = 16;
    
    const bytesPerSample = bitDepth / 8;
    const blockAlign = numberOfChannels * bytesPerSample;
    
    const data = audioBuffer.getChannelData(0);
    const dataLength = data.length * bytesPerSample;
    const buffer = new ArrayBuffer(44 + dataLength);
    const view = new DataView(buffer);
    
    // Write WAV header
    let pos = 0;
    
    // "RIFF" chunk descriptor
    writeString(view, pos, 'RIFF'); pos += 4;
    view.setUint32(pos, 36 + dataLength, true); pos += 4;
    writeString(view, pos, 'WAVE'); pos += 4;
    
    // "fmt " sub-chunk
    writeString(view, pos, 'fmt '); pos += 4;
    view.setUint32(pos, 16, true); pos += 4; // fmt chunk size
    view.setUint16(pos, format, true); pos += 2; // audio format (1 = PCM)
    view.setUint16(pos, numberOfChannels, true); pos += 2;
    view.setUint32(pos, sampleRate, true); pos += 4;
    view.setUint32(pos, sampleRate * blockAlign, true); pos += 4; // byte rate
    view.setUint16(pos, blockAlign, true); pos += 2;
    view.setUint16(pos, bitDepth, true); pos += 2;
    
    // "data" sub-chunk
    writeString(view, pos, 'data'); pos += 4;
    view.setUint32(pos, dataLength, true); pos += 4;
    
    // Write PCM samples
    const volume = 0.8; // Prevent clipping
    for (let i = 0; i < data.length; i++) {
      const sample = Math.max(-1, Math.min(1, data[i])) * volume;
      const int16 = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
      view.setInt16(pos, int16, true);
      pos += 2;
    }
    
    resolve(new Blob([buffer], { type: 'audio/wav' }));
  });
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}
