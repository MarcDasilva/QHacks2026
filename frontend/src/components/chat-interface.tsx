"use client";

import { useState, useRef, useEffect } from "react";
import { IconSend, IconLoader2, IconSparkles, IconMicrophone, IconVolume, IconVolumeOff } from "@tabler/icons-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useRouter } from "next/navigation";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";
import { useTextToSpeech } from "@/hooks/use-text-to-speech";
import { useVoice } from "@/contexts/voice-context";

interface Message {
  id: string;
  type: "user" | "thought" | "plan" | "navigation" | "answer" | "error" | "chat" | "confirmation";
  content: string;
  data?: any;
  timestamp: Date;
}

interface ChatInterfaceProps {
  className?: string;
}

export function ChatInterface({ className = "" }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const lastSpokenMessageRef = useRef<string>("");
  
  // Voice context to sync with Boohoo
  const voiceContext = useVoice();

  // Audio recording hook (Gradium STT)
  const { isRecording, startRecording, stopRecording, error: recordingError } = useAudioRecorder();

  // Text-to-speech hook (Gradium TTS)
  const { speak, stop: stopSpeaking, isSpeaking, isSupported: isTTSSupported, error: ttsError } = useTextToSpeech();

  // Sync voice states with context
  useEffect(() => {
    voiceContext.setIsSpeaking(isSpeaking);
  }, [isSpeaking, voiceContext]);

  useEffect(() => {
    voiceContext.setIsListening(isRecording);
  }, [isRecording, voiceContext]);

  useEffect(() => {
    voiceContext.setIsProcessing(isLoading);
  }, [isLoading, voiceContext]);

  // Display errors
  useEffect(() => {
    if (recordingError) {
      console.error("Recording error:", recordingError);
    }
    if (ttsError) {
      console.error("TTS error:", ttsError);
    }
  }, [recordingError, ttsError]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Auto-speak bot responses
  useEffect(() => {
    if (!isTTSEnabled || !isTTSSupported) return;

    const lastMessage = messages[messages.length - 1];
    if (!lastMessage) return;

    // Only speak bot responses (answer or chat types)
    if ((lastMessage.type === "answer" || lastMessage.type === "chat") && 
        lastMessage.content !== lastSpokenMessageRef.current) {
      lastSpokenMessageRef.current = lastMessage.content;
      speak(lastMessage.content);
    }
  }, [messages, isTTSEnabled, isTTSSupported, speak]);

  const toggleTTS = () => {
    if (isSpeaking) {
      stopSpeaking();
    }
    setIsTTSEnabled(!isTTSEnabled);
  };

  const handleMicClick = async () => {
    if (isRecording) {
      // Stop recording (transcript already streamed to input)
      voiceContext.setIsProcessing(true);
      await stopRecording();
      voiceContext.setIsProcessing(false);
    } else {
      // Start recording with real-time transcript callback
      await startRecording((transcript) => {
        setInput(transcript);
      });
    }
  };

  const addMessage = (message: Omit<Message, "id" | "timestamp">) => {
    setMessages((prev) => [
      ...prev,
      {
        ...message,
        id: Math.random().toString(36).substr(2, 9),
        timestamp: new Date(),
      },
    ]);
  };

  const handleNavigate = (url: string) => {
    // Navigate to the specified route
    router.push(url);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    // Stop recording if still active
    if (isRecording) {
      await stopRecording();
    }

    const userMessage = input.trim();
    setInput("");

    // Check if "analysis" keyword is present
    if (userMessage.toLowerCase().includes("analysis")) {
      // Add user message
      addMessage({
        type: "user",
        content: userMessage,
      });
      
      // Store pending message and show confirmation
      setPendingMessage(userMessage);
      
      // Add confirmation message
      addMessage({
        type: "confirmation",
        content: "Would you like to perform a deep analysis with data visualization?",
        data: { message: userMessage },
      });
      return;
    }

    // No "analysis" keyword - go straight to simple chat
    await sendMessage(userMessage, "chat");
  };

  const handleConfirmation = async (confirmed: boolean) => {
    if (!pendingMessage) return;
    
    const mode = confirmed ? "deep_analysis" : "chat";
    await sendMessage(pendingMessage, mode);
    setPendingMessage(null);
  };

  const sendMessage = async (userMessage: string, mode: "chat" | "deep_analysis") => {
    setIsLoading(true);

    // Add user message if not already added
    if (!pendingMessage) {
      addMessage({
        type: "user",
        content: userMessage,
      });
    }

    try {
      // Connect to SSE endpoint
      const response = await fetch("http://localhost:8000/api/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: userMessage, mode }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("No response body");
      }

      // Read the stream
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === "navigation") {
                // Handle navigation
                addMessage({
                  type: "navigation",
                  content: data.content,
                  data: data.data,
                });
                // Actually navigate
                if (data.data?.url) {
                  setTimeout(() => handleNavigate(data.data.url), 500);
                }
              } else if (data.type === "plan") {
                // Show plan
                addMessage({
                  type: "plan",
                  content: data.content,
                  data: data.data,
                });
              } else if (data.type === "thought") {
                // Show thought process
                addMessage({
                  type: "thought",
                  content: data.content,
                });
              } else if (data.type === "answer") {
                // Show final answer
                addMessage({
                  type: "answer",
                  content: data.content,
                  data: data.data,
                });
              } else if (data.type === "chat") {
                // Simple chat response
                addMessage({
                  type: "chat",
                  content: data.content,
                });
              } else if (data.type === "complete") {
                // Stream complete - stop loading immediately
                setIsLoading(false);
                return; // Exit the function to stop processing
              } else if (data.type === "error") {
                addMessage({
                  type: "error",
                  content: data.content,
                });
                setIsLoading(false);
                return; // Exit on error
              }
            } catch (err) {
              console.error("Error parsing SSE data:", err);
            }
          }
        }
      }
    } catch (error) {
      console.error("Error:", error);
      addMessage({
        type: "error",
        content: `Failed to connect to the backend. Make sure the server is running on port 8000.`,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderMessage = (message: Message) => {
    switch (message.type) {
      case "user":
        return (
          <div key={message.id} className="flex justify-end mb-4">
            <div className="max-w-[80%] rounded-lg bg-blue-600 px-4 py-2 text-white">
              {message.content}
            </div>
          </div>
        );

      case "thought":
        return (
          <div key={message.id} className="flex items-start gap-2 mb-3">
            <IconLoader2 className="h-4 w-4 animate-spin text-blue-500 mt-1" />
            <div className="text-sm text-muted-foreground italic">
              {message.content}
            </div>
          </div>
        );

      case "plan":
        return (
          <div key={message.id} className="mb-4">
            <div className="rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950 p-3">
              <div className="font-semibold text-sm mb-2 flex items-center gap-2">
                <IconSparkles className="h-4 w-4" />
                {message.content}
              </div>
              {message.data?.plan && (
                <ul className="space-y-1 text-sm">
                  {message.data.plan.map((item: any, idx: number) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-blue-600 dark:text-blue-400">•</span>
                      <span>
                        <strong>{item.product}:</strong> {item.why}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        );

      case "navigation":
        return (
          <div key={message.id} className="flex items-start gap-2 mb-3">
            <span className="text-lg">🧭</span>
            <div className="text-sm text-purple-600 dark:text-purple-400 font-medium">
              {message.content}
            </div>
          </div>
        );

      case "answer":
        return (
          <div key={message.id} className="mb-4">
            <div className="rounded-lg border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950 p-4">
              <div className="font-semibold text-sm mb-2 text-green-700 dark:text-green-300">
                📊 Analysis Complete
              </div>
              <div className="text-sm mb-3">{message.content}</div>
              
              {message.data?.rationale && message.data.rationale.length > 0 && (
                <div className="mt-3 pt-3 border-t border-green-200 dark:border-green-800">
                  <div className="font-medium text-xs text-green-700 dark:text-green-300 mb-2">
                    Detailed Insights:
                  </div>
                  <ul className="space-y-1 text-xs">
                    {message.data.rationale.map((item: string, idx: number) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-green-600 dark:text-green-400">✓</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {message.data?.key_metrics && message.data.key_metrics.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {message.data.key_metrics.map((metric: string, idx: number) => (
                    <span
                      key={idx}
                      className="inline-block rounded bg-green-100 dark:bg-green-900 px-2 py-0.5 text-xs font-mono"
                    >
                      {metric}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );

      case "error":
        return (
          <div key={message.id} className="mb-4">
            <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950 p-3">
              <div className="font-semibold text-sm text-red-700 dark:text-red-300">
                ⚠️ Error
              </div>
              <div className="text-sm mt-1">{message.content}</div>
            </div>
          </div>
        );

      case "chat":
        return (
          <div key={message.id} className="mb-4">
            <div className="max-w-[90%] rounded-lg border border-border bg-muted p-3">
              <div className="text-sm whitespace-pre-wrap">{message.content}</div>
            </div>
          </div>
        );

      case "confirmation":
        return (
          <div key={message.id} className="mb-4">
            <div className="rounded-lg border border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-950 p-4">
              <div className="font-semibold text-sm mb-3 text-purple-700 dark:text-purple-300">
                🔍 {message.content}
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => handleConfirmation(true)}
                  disabled={isLoading}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  Yes, Deep Analysis
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleConfirmation(false)}
                  disabled={isLoading}
                >
                  No, Simple Chat
                </Button>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`flex h-full flex-col ${className}`}>
      {/* Header */}
      <div className="border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <IconSparkles className="h-5 w-5 text-purple-500" />
          <h2 className="font-semibold text-sm">Analytics Assistant</h2>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Ask me about CRM service requests
        </p>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 px-4 py-4">
        <div ref={scrollRef}>
          {messages.length === 0 && (
            <div className="flex h-full items-center justify-center text-center">
              <div className="text-sm text-muted-foreground space-y-2">
                <p>👋 Hi! I'm your analytics assistant.</p>
                <p className="text-xs">
                  💬 Simple chat: "What are service requests?"<br />
                  📊 Deep analysis: "Show me an analysis of top categories"
                </p>
                <p className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                  💡 Use "analysis" keyword for data visualization
                </p>
              </div>
            </div>
          )}
          {messages.map(renderMessage)}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-border p-4">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isTTSSupported && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={toggleTTS}
                className="h-8 px-2"
                title={isTTSEnabled ? "Disable voice responses" : "Enable voice responses"}
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
              <span className="text-red-500 animate-pulse">● Recording... (text appears live)</span>
            ) : (
              <span>Click mic to speak</span>
            )}
          </div>
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isRecording ? "Speaking..." : "Ask a question or click mic..."}
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
          <Button type="submit" size="icon" disabled={isLoading || !input.trim()}>
            {isLoading ? (
              <IconLoader2 className="h-4 w-4 animate-spin" />
            ) : (
              <IconSend className="h-4 w-4" />
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
