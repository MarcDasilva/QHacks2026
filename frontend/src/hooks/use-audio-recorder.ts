/**
 * Hook for recording audio and sending to backend STT (Gradium).
 * Records as PCM via Web Audio API and sends WAV only (no WebM).
 * API accepts wav, pcm, opus only — see BACKEND_API_INTEGRATION.md.
 */

import { useState, useCallback, useRef } from "react";

interface UseAudioRecorderReturn {
  isRecording: boolean;
  startRecording: (onTranscript: (text: string) => void) => Promise<void>;
  stopRecording: () => Promise<void>;
  error: string | null;
}

const MIN_RECORDING_SAMPLES = 16000; // ~0.33s at 48kHz
const RECORDER_WORKLET_URL = "/recorder-worklet.js";
/** Gradium STT expects 24kHz (see SDK: PCM 24000 Hz, Ready sample_rate 24000). */
const GRADIUM_STT_SAMPLE_RATE = 24000;

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const pcmChunksRef = useRef<Float32Array[]>([]);
  const sampleRateRef = useRef<number>(48000);
  const onTranscriptRef = useRef<((text: string) => void) | null>(null);
  const accumulatedTranscriptRef = useRef<string>("");

  const startRecording = useCallback(
    async (onTranscript: (text: string) => void) => {
      try {
        setError(null);
        onTranscriptRef.current = onTranscript;
        accumulatedTranscriptRef.current = "";
        pcmChunksRef.current = [];

        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: 24000,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
        streamRef.current = stream;

        const AudioContextClass =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext })
            .webkitAudioContext;
        const ctx = new AudioContextClass();
        audioContextRef.current = ctx;
        sampleRateRef.current = ctx.sampleRate;

        await ctx.audioWorklet.addModule(RECORDER_WORKLET_URL);
        const workletNode = new AudioWorkletNode(ctx, "recorder-processor");
        workletNodeRef.current = workletNode;

        workletNode.port.onmessage = (
          event: MessageEvent<{ samples: Float32Array }>,
        ) => {
          if (event.data?.samples) {
            pcmChunksRef.current.push(event.data.samples);
          }
        };

        const source = ctx.createMediaStreamSource(stream);
        sourceRef.current = source;

        source.connect(workletNode);
        workletNode.connect(ctx.destination);

        setIsRecording(true);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to start recording";
        setError(errorMessage);
        console.error("Recording error:", err);
      }
    },
    [],
  );

  const sendWavAndReadTranscript = useCallback(
    async (wavBlob: Blob, isFinal: boolean) => {
      const base64Audio = await blobToBase64(wavBlob);
      const response = await fetch(
        "http://localhost:8000/api/voice/stt/stream",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            audio_chunk: base64Audio,
            is_final: isFinal,
            input_format: "wav",
          }),
        },
      );

      if (!response.ok) {
        console.error(
          "[STT] stream failed:",
          response.status,
          response.statusText,
        );
        setError(`STT failed: ${response.statusText}`);
        return;
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      // Match sample integration: accumulate fullTranscript from every transcript event, setInput once at end
      let fullTranscript = "";
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          console.log("[STT] raw chunk:", chunk);
          buffer += chunk;
        }
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            console.log("[STT] parsed:", data);

            if (data.type === "transcript") {
              const text = data.text != null ? String(data.text).trim() : "";
              if (text) {
                fullTranscript += (fullTranscript ? " " : "") + text;
                console.log("[STT] accumulated:", fullTranscript);
              }
            }
            if (data.type === "complete") {
              console.log("[STT] complete, final transcript:", fullTranscript);
            }
            if (data.type === "error" && data.message) {
              console.error("[STT] error:", data.message);
              setError(String(data.message));
            }
          } catch (e) {
            console.warn("[STT] parse error:", e);
          }
        }
        if (done) break;
      }

      // Process remaining buffer (last event when stream ends)
      if (buffer.trim()) {
        for (const line of buffer.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            console.log("[STT] parsed (remaining):", data);
            if (data.type === "transcript") {
              const text = data.text != null ? String(data.text).trim() : "";
              if (text) {
                fullTranscript += (fullTranscript ? " " : "") + text;
                console.log("[STT] accumulated:", fullTranscript);
              }
            }
          } catch {
            // ignore
          }
        }
      }

      console.log("[STT] final transcript for input:", fullTranscript);
      if (onTranscriptRef.current) {
        onTranscriptRef.current(fullTranscript);
      }
    },
    [],
  );

  const stopRecording = useCallback(async (): Promise<void> => {
    const stream = streamRef.current;
    const ctx = audioContextRef.current;
    const source = sourceRef.current;
    const workletNode = workletNodeRef.current;

    if (!stream || !ctx || !source || !workletNode || !isRecording) {
      setIsRecording(false);
      return;
    }

    try {
      source.disconnect();
      workletNode.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      sourceRef.current = null;
      workletNodeRef.current = null;
      audioContextRef.current = null;

      const chunks = pcmChunksRef.current;
      pcmChunksRef.current = [];
      const totalSamples = chunks.reduce((n, c) => n + c.length, 0);

      if (totalSamples < MIN_RECORDING_SAMPLES) {
        setError(
          "Recording too short—please speak for at least half a second, then stop.",
        );
        setIsRecording(false);
        return;
      }

      const sampleRate = sampleRateRef.current;
      const merged = new Float32Array(totalSamples);
      let offset = 0;
      for (const c of chunks) {
        merged.set(c, offset);
        offset += c.length;
      }

      // Resample to 24kHz so Gradium STT receives expected sample rate
      const resampled = resampleTo24k(merged, sampleRate);
      const audioBuffer = ctx.createBuffer(
        1,
        resampled.length,
        GRADIUM_STT_SAMPLE_RATE,
      );
      audioBuffer.getChannelData(0).set(resampled);

      const wavBlob = await audioBufferToWav(audioBuffer);
      ctx.close();
      await sendWavAndReadTranscript(wavBlob, true);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to process recording";
      setError(errorMessage);
      console.error("Stop error:", err);
    } finally {
      setIsRecording(false);
    }
  }, [isRecording, sendWavAndReadTranscript]);

  return {
    isRecording,
    startRecording,
    stopRecording,
    error,
  };
}

/** Resample Float32 mono to 24kHz for Gradium STT (expects 24kHz). */
function resampleTo24k(
  samples: Float32Array,
  sourceSampleRate: number,
): Float32Array {
  if (sourceSampleRate === GRADIUM_STT_SAMPLE_RATE) return samples;
  const targetLength = Math.round(
    (samples.length * GRADIUM_STT_SAMPLE_RATE) / sourceSampleRate,
  );
  const out = new Float32Array(targetLength);
  const ratio = sourceSampleRate / GRADIUM_STT_SAMPLE_RATE;
  const last = samples.length - 1;
  for (let i = 0; i < targetLength; i++) {
    const srcIdx = i * ratio;
    const lo = Math.floor(srcIdx);
    const hi = Math.min(lo + 1, last);
    const frac = srcIdx - lo;
    out[i] = samples[lo] * (1 - frac) + samples[hi] * frac;
  }
  return out;
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = (reader.result as string).split(",")[1];
      resolve(base64 ?? "");
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function audioBufferToWav(audioBuffer: AudioBuffer): Promise<Blob> {
  return new Promise((resolve) => {
    const numberOfChannels = 1;
    const sampleRate = audioBuffer.sampleRate;
    const format = 1;
    const bitDepth = 16;
    const bytesPerSample = bitDepth / 8;
    const blockAlign = numberOfChannels * bytesPerSample;
    const data = audioBuffer.getChannelData(0);
    const dataLength = data.length * bytesPerSample;
    const buffer = new ArrayBuffer(44 + dataLength);
    const view = new DataView(buffer);
    let pos = 0;

    writeString(view, pos, "RIFF");
    pos += 4;
    view.setUint32(pos, 36 + dataLength, true);
    pos += 4;
    writeString(view, pos, "WAVE");
    pos += 4;
    writeString(view, pos, "fmt ");
    pos += 4;
    view.setUint32(pos, 16, true);
    pos += 4;
    view.setUint16(pos, format, true);
    pos += 2;
    view.setUint16(pos, numberOfChannels, true);
    pos += 2;
    view.setUint32(pos, sampleRate, true);
    pos += 4;
    view.setUint32(pos, sampleRate * blockAlign, true);
    pos += 4;
    view.setUint16(pos, blockAlign, true);
    pos += 2;
    view.setUint16(pos, bitDepth, true);
    pos += 2;
    writeString(view, pos, "data");
    pos += 4;
    view.setUint32(pos, dataLength, true);
    pos += 4;

    const volume = 0.8;
    for (let i = 0; i < data.length; i++) {
      const sample = Math.max(-1, Math.min(1, data[i])) * volume;
      const int16 = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      view.setInt16(pos, int16, true);
      pos += 2;
    }

    resolve(new Blob([buffer], { type: "audio/wav" }));
  });
}

function writeString(view: DataView, offset: number, s: string) {
  for (let i = 0; i < s.length; i++) {
    view.setUint8(offset + i, s.charCodeAt(i));
  }
}
