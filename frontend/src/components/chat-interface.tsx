"use client";

import { useState, useRef, useEffect } from "react";
import {
  IconSend,
  IconLoader2,
  IconSparkles,
  IconMicrophone,
  IconVolume,
  IconVolumeOff,
} from "@tabler/icons-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRouter } from "next/navigation";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";
import { useBackendChat } from "@/hooks/use-backend-chat";
import { useTextToSpeech } from "@/hooks/use-text-to-speech";
import { useVoice } from "@/contexts/voice-context";
import { ChatMessageView } from "@/components/chat-message-view";

const ML_MODELS = [
  { value: "gpt-4o", label: "GPT-4o", icon: "/openai.png" },
  {
    value: "claude-3-5-sonnet",
    label: "Claude 3.5 Sonnet",
    icon: "/claude.svg",
  },
  { value: "gemini-1-5-pro", label: "Gemini 1.5 Pro", icon: "/gemini.png" },
  { value: "deepseek-r1", label: "DeepSeek R1", icon: "/deepseek.png" },
] as const;

interface ChatInterfaceProps {
  className?: string;
}

export function ChatInterface({ className = "" }: ChatInterfaceProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const lastSpokenMessageRef = useRef<string>("");
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);
  const [model, setModel] = useState<string>(ML_MODELS[0].value);

  const {
    messages,
    input,
    setInput,
    isLoading,
    handleSubmit,
    handleConfirmation,
    backendHealthy,
    checkHealth,
  } = useBackendChat(router);

  const voiceContext = useVoice();
  const {
    isRecording,
    startRecording,
    stopRecording,
    error: recordingError,
  } = useAudioRecorder();
  const {
    speak,
    stop: stopSpeaking,
    isSpeaking,
    isSupported: isTTSSupported,
    error: ttsError,
  } = useTextToSpeech();

  useEffect(() => {
    voiceContext.setIsSpeaking(isSpeaking);
  }, [isSpeaking, voiceContext]);
  useEffect(() => {
    voiceContext.setIsListening(isRecording);
  }, [isRecording, voiceContext]);
  useEffect(() => {
    voiceContext.setIsProcessing(isLoading);
  }, [isLoading, voiceContext]);

  useEffect(() => {
    if (recordingError) console.error("Recording error:", recordingError);
    if (ttsError) console.error("TTS error:", ttsError);
  }, [recordingError, ttsError]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  useEffect(() => {
    if (!isTTSEnabled || !isTTSSupported) return;
    const last = messages[messages.length - 1];
    if (!last || (last.type !== "answer" && last.type !== "chat")) return;
    if (last.content === lastSpokenMessageRef.current) return;
    lastSpokenMessageRef.current = last.content;
    speak(last.content);
  }, [messages, isTTSEnabled, isTTSSupported, speak]);

  const handleMicClick = async () => {
    if (isRecording) {
      voiceContext.setIsProcessing(true);
      await stopRecording();
      voiceContext.setIsProcessing(false);
    } else {
      await startRecording((transcript) => setInput(transcript));
    }
  };

  const toggleTTS = () => {
    if (isSpeaking) stopSpeaking();
    setIsTTSEnabled(!isTTSEnabled);
  };

  return (
    <div className={`flex h-full flex-col ${className}`}>
      <div className="border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <IconSparkles className="h-5 w-5 text-purple-500" />
          <h2 className="font-semibold text-sm">Analytics Assistant</h2>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Ask me about CRM service requests
        </p>
      </div>

      <ScrollArea className="flex-1 px-4 py-4">
        <div ref={scrollRef}>
          {messages.length === 0 && (
            <div className="flex h-full items-center justify-center text-center">
              <div className="text-sm text-muted-foreground space-y-2">
                <p>👋 Hi! I&apos;m your analytics assistant.</p>
                <p className="text-xs">
                  💬 Simple chat: &quot;What are service requests?&quot;
                  <br />
                  📊 Deep analysis: &quot;Show me an analysis of top
                  categories&quot;
                </p>
                <p className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                  💡 Use &quot;analysis&quot; keyword for data visualization
                </p>
              </div>
            </div>
          )}
          {messages.map((msg) => (
            <ChatMessageView
              key={msg.id}
              message={msg}
              onConfirmation={handleConfirmation}
              isLoading={isLoading}
            />
          ))}
        </div>
      </ScrollArea>

      <div className="border-t border-border p-4">
        {backendHealthy === false && (
          <p className="text-xs text-amber-600 dark:text-amber-400 mb-2">
            Backend unavailable. Start the server on port 8000.
          </p>
        )}
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isTTSSupported && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={toggleTTS}
                className="h-8 px-2"
                title={
                  isTTSEnabled
                    ? "Disable voice responses"
                    : "Enable voice responses"
                }
              >
                {isTTSEnabled ? (
                  <>
                    <IconVolume className="h-4 w-4 mr-1" />
                    <span className="text-xs">Voice On</span>
                  </>
                ) : (
                  <>
                    <IconVolumeOff className="h-4 w-4 mr-1" />
                    <span className="text-xs">Voice Off</span>
                  </>
                )}
              </Button>
            )}
          </div>
          <div className="text-xs text-muted-foreground">
            {isRecording ? (
              <span className="text-red-500 animate-pulse">
                ● Recording... (text appears live)
              </span>
            ) : (
              <span>Click mic to speak</span>
            )}
          </div>
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              isRecording ? "Speaking..." : "Ask a question or click mic..."
            }
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            type="button"
            size="icon"
            variant={isRecording ? "destructive" : "outline"}
            onClick={handleMicClick}
            disabled={isLoading}
            className={isRecording ? "animate-pulse" : ""}
            title={isRecording ? "Stop recording" : "Start recording"}
          >
            <IconMicrophone className="h-4 w-4" />
          </Button>
          <Button
            type="submit"
            size="icon"
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? (
              <IconLoader2 className="h-4 w-4 animate-spin" />
            ) : (
              <IconSend className="h-4 w-4" />
            )}
          </Button>
        </form>
        <div className="mt-2">
          <Select value={model} onValueChange={(v) => setModel(v)}>
            <SelectTrigger size="sm" className="h-7 w-fit max-w-[10rem]">
              <SelectValue placeholder="Model" />
            </SelectTrigger>
            <SelectContent>
              {ML_MODELS.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  <span className="flex items-center gap-2">
                    <img
                      src={m.icon}
                      alt=""
                      className="size-3.5 shrink-0 object-contain"
                    />
                    {m.label}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}
