"use client";

/**
 * Hook for text-to-speech functionality using Gradium API
 * speakWithSubtitles: play TTS and call onSubtitle(visibleText) in sync with speech for subtitle effect
 */

import { useState, useCallback, useRef } from "react";

export interface SubtitleTimestamps {
  text: string;
  start_s: number;
  stop_s: number;
}

interface UseTextToSpeechReturn {
  speak: (text: string) => Promise<void>;
  speakWithSubtitles: (
    text: string,
    callbacks: {
      onSubtitle: (visibleText: string) => void;
      onEnd?: () => void;
    },
  ) => Promise<void>;
  stop: () => void;
  pause: () => void;
  resume: () => void;
  isSpeaking: boolean;
  isPaused: boolean;
  isSupported: boolean;
  error: string | null;
}

export function useTextToSpeech(): UseTextToSpeechReturn {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isSupported = true; // Backend TTS always supported

  const audioRef = useRef<HTMLAudioElement | null>(null);

  const speak = useCallback(async (text: string) => {
    try {
      setError(null);

      // Stop any ongoing speech
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }

      // Call backend TTS endpoint
      const response = await fetch("http://localhost:8000/api/voice/tts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          voice_id: "m86j6D7UZpGzHsNu", // Jack - male British voice (matches backend default)
          output_format: "wav",
        }),
      });

      if (!response.ok) {
        throw new Error(`TTS request failed: ${response.statusText}`);
      }

      // Get audio blob
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      // Create and play audio element
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onplay = () => setIsSpeaking(true);
      audio.onended = () => {
        setIsSpeaking(false);
        setIsPaused(false);
        URL.revokeObjectURL(audioUrl);
      };
      audio.onerror = () => {
        setIsSpeaking(false);
        setIsPaused(false);
        setError("Failed to play audio");
        URL.revokeObjectURL(audioUrl);
      };
      audio.onpause = () => {
        if (audio.currentTime < audio.duration) {
          setIsPaused(true);
        }
      };

      await audio.play();
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to generate speech";
      setError(errorMessage);
      console.error("TTS error:", err);
      setIsSpeaking(false);
    }
  }, []);

  const speakWithSubtitles = useCallback(
    async (
      text: string,
      {
        onSubtitle,
        onEnd,
      }: { onSubtitle: (visibleText: string) => void; onEnd?: () => void },
    ) => {
      try {
        setError(null);
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current = null;
        }

        const response = await fetch(
          "http://localhost:8000/api/voice/tts/with-timestamps",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              text,
              voice_id: "m86j6D7UZpGzHsNu",
              output_format: "wav",
            }),
          },
        );
        if (!response.ok) throw new Error(`TTS failed: ${response.statusText}`);

        const data = (await response.json()) as {
          audio_base64: string;
          timestamps: SubtitleTimestamps[];
        };
        const audioBytes = Uint8Array.from(atob(data.audio_base64), (c) =>
          c.charCodeAt(0),
        );
        const blob = new Blob([audioBytes], { type: "audio/wav" });
        const audioUrl = URL.createObjectURL(blob);
        const audio = new Audio(audioUrl);
        audioRef.current = audio;

        const timestamps = data.timestamps ?? [];
        let rafId: number;

        const updateSubtitle = () => {
          const t = audio.currentTime;
          if (timestamps.length === 0) {
            onSubtitle(text);
            return;
          }
          const visible: string[] = [];
          for (const item of timestamps) {
            if (item.start_s <= t) visible.push(item.text);
            else break;
          }
          onSubtitle(visible.join(" ").trim());
        };

        audio.onplay = () => {
          setIsSpeaking(true);
          updateSubtitle();
        };
        audio.ontimeupdate = updateSubtitle;
        audio.onended = () => {
          setIsSpeaking(false);
          setIsPaused(false);
          onSubtitle(text);
          onEnd?.();
          URL.revokeObjectURL(audioUrl);
        };
        audio.onerror = () => {
          setIsSpeaking(false);
          onSubtitle(text);
          onEnd?.();
          setError("Failed to play audio");
          URL.revokeObjectURL(audioUrl);
        };

        await audio.play();
      } catch (err) {
        const msg = err instanceof Error ? err.message : "TTS error";
        setError(msg);
        setIsSpeaking(false);
        onSubtitle(text);
        onEnd?.();
      }
    },
    [],
  );

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    setIsSpeaking(false);
    setIsPaused(false);
  }, []);

  const pause = useCallback(() => {
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
      setIsPaused(true);
    }
  }, []);

  const resume = useCallback(() => {
    if (audioRef.current && audioRef.current.paused) {
      audioRef.current.play();
      setIsPaused(false);
      setIsSpeaking(true);
    }
  }, []);

  return {
    speak,
    speakWithSubtitles,
    stop,
    pause,
    resume,
    isSpeaking,
    isPaused,
    isSupported,
    error,
  };
}
