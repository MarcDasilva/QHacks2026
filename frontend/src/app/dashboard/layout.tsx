"use client";

import {
  CRM_DATABASE_VALUE,
  DashboardProvider,
  useDashboard,
} from "@/app/dashboard/dashboard-context";
import { AppSidebar } from "@/components/app-sidebar";
import { BoohooRive } from "@/components/boohoo-rive";
import { GlowEffect } from "@/components/glow-effect";
import { SiteHeader } from "@/components/site-header";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { useAudioRecorder } from "@/hooks/use-audio-recorder";
import { useBackendChat } from "@/hooks/use-backend-chat";
import { useTextToSpeech } from "@/hooks/use-text-to-speech";
import { createClient } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";
import { ArrowRight, Loader2, Mic, Volume, VolumeX } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import TextType from "@/components/TextType.jsx";
import { useVoice } from "@/contexts/voice-context";

function mapSupabaseUser(user: User): {
  name: string;
  email: string;
  avatar: string;
} {
  const name =
    user.user_metadata?.full_name ??
    user.user_metadata?.name ??
    user.email?.split("@")[0] ??
    "User";
  const email = user.email ?? "";
  const avatar =
    user.user_metadata?.avatar_url ?? user.user_metadata?.picture ?? "";
  return { name, email, avatar };
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [showGlow, setShowGlow] = useState(false);
  const router = useRouter();

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.shiftKey && (e.key === "U" || e.key === "u")) {
      e.preventDefault();
      setShowGlow((prev) => !prev);
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
      if (!session?.user) {
        router.replace("/");
      }
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (!session?.user) {
        router.replace("/");
      }
    });
    return () => subscription.unsubscribe();
  }, [router]);

  const handleLogout = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.replace("/");
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const sidebarUser = mapSupabaseUser(user);

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <DashboardProvider showGlow={showGlow} setShowGlow={setShowGlow}>
        <DashboardLayoutContent user={sidebarUser} onLogout={handleLogout}>
          {children}
        </DashboardLayoutContent>
      </DashboardProvider>
    </SidebarProvider>
  );
}

function DashboardLayoutContent({
  user,
  onLogout,
  children,
}: {
  user: { name: string; email: string; avatar: string };
  onLogout: () => void;
  children: React.ReactNode;
}) {
  const {
    expansionPhase,
    selectedDatabase,
    ready,
    showClusterDashboardAfterAnalysis,
    wow,
    showGlow,
  } = useDashboard();
  const { isSpeaking } = useVoice();
  const isExpandingOrHolding =
    expansionPhase === "expanding" || expansionPhase === "holding";
  const isCrmSelected = selectedDatabase === CRM_DATABASE_VALUE;
  const boohooFullWidth = isCrmSelected && !showClusterDashboardAfterAnalysis;

  return (
    <>
      <AppSidebar variant="inset" user={user} onLogout={onLogout} />
      <SidebarInset className="min-h-0">
        <SiteHeader />
        <div className="relative flex min-h-0 flex-1 flex-col">
          <div className="@container/main flex min-h-0 flex-1 flex-col gap-2">
            <div
              className={`flex min-h-0 flex-1 gap-4 overflow-hidden px-4 py-4 md:px-6 md:py-6 ${boohooFullWidth ? "justify-end" : ""}`}
            >
              <div
                className={`relative flex flex-col overflow-hidden rounded-xl transition-[flex-basis,min-width] duration-[1.8s] ease-out ${
                  boohooFullWidth
                    ? "w-0 min-w-0 shrink-0 basis-0 overflow-hidden"
                    : "min-h-0 min-w-0 flex-1 shrink"
                }`}
              >
                <div className="min-h-0 min-w-0 flex-1 overflow-auto">
                  {children}
                </div>
                <GlowEffect active={showGlow} />
              </div>
              <div
                className={`relative flex h-full max-h-full shrink-0 flex-col overflow-hidden rounded-xl border border-border bg-zinc-200 dark:bg-zinc-800 transition-[flex-basis] duration-[1.8s] ease-out ${
                  boohooFullWidth
                    ? "basis-full"
                    : isExpandingOrHolding
                      ? "basis-3/4"
                      : "basis-80 md:basis-96"
                }`}
              >
                <BoohooRive
                  glowActive={showGlow}
                  talking={isSpeaking}
                  wow={wow}
                />
                {isCrmSelected && ready && <CrmReadyOverlay />}
              </div>
            </div>
          </div>
        </div>
      </SidebarInset>
    </>
  );
}

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

function CrmReadyOverlay() {
  const router = useRouter();
  const scrollRef = useRef<HTMLDivElement>(null);
  const scrollBottomRef = useRef<HTMLDivElement>(null);
  const lastSpokenMessageRef = useRef<string>("");
  const [model, setModel] = useState<string>(ML_MODELS[0].value);
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);

  const {
    messages,
    input,
    setInput,
    isLoading,
    pendingMessage,
    handleSubmit,
    handleConfirmation,
    addMessage,
    backendHealthy,
    checkHealth,
  } = useBackendChat(router, {
    onClusterPrediction: (parentClusterId) => {
      setSelectedCluster({ level: 1, cluster_id: parentClusterId });
    },
    onGlowOn: () => {
      glowOnAfterTTSRef.current = true;
    },
  });

  const {
    setShowClusterDashboardAfterAnalysis,
    setWow,
    setSelectedCluster,
    setShowGlow,
  } = useDashboard();
  const voiceContext = useVoice();
  const pendingAnalysisShiftRef = useRef(false);
  const prevLoadingRef = useRef(isLoading);
  const waitingForSttRef = useRef(false);
  const pendingSubmitAfterSttRef = useRef(false);
  const pendingSubmitTranscriptRef = useRef<string | null>(null);
  const followUpMessageTimeoutRef = useRef<ReturnType<
    typeof setTimeout
  > | null>(null);
  const glowOnAfterTTSRef = useRef(false);

  const CLUSTER_FOLLOW_UP_MESSAGE =
    "I searched the CRM and generated a vector database from its results, what are you interested in?";

  const handleSubmitWithAnalysis = (e: React.FormEvent) => {
    if (input.trim().toLowerCase().includes("analysis")) {
      pendingAnalysisShiftRef.current = true;
    }
    handleSubmit(e);
  };

  useEffect(() => {
    if (
      pendingSubmitTranscriptRef.current !== null &&
      input === pendingSubmitTranscriptRef.current
    ) {
      const transcript = pendingSubmitTranscriptRef.current;
      pendingSubmitTranscriptRef.current = null;
      handleSubmit({ preventDefault: () => {} } as React.FormEvent);
    }
  }, [input, handleSubmit]);

  const { isRecording, startRecording, stopRecording } = useAudioRecorder();
  const {
    speak,
    speakWithSubtitles,
    stop: stopSpeaking,
    isSpeaking,
    isSupported: isTTSSupported,
  } = useTextToSpeech();

  useEffect(() => {
    const wasLoading = prevLoadingRef.current;
    prevLoadingRef.current = isLoading;
    if (wasLoading && !isLoading && pendingAnalysisShiftRef.current) {
      const last = messages[messages.length - 1];
      const willSpeak =
        isTTSEnabled &&
        isTTSSupported &&
        last &&
        (last.type === "answer" || last.type === "chat");
      if (willSpeak) {
        return;
      }
      pendingAnalysisShiftRef.current = false;
      const t = setTimeout(() => {
        setShowClusterDashboardAfterAnalysis(true);
        setTimeout(() => {
          setWow(true);
          setTimeout(() => setWow(false), 1000);
          if (followUpMessageTimeoutRef.current)
            clearTimeout(followUpMessageTimeoutRef.current);
          followUpMessageTimeoutRef.current = setTimeout(() => {
            addMessage({
              type: "chat",
              content: CLUSTER_FOLLOW_UP_MESSAGE,
            });
            followUpMessageTimeoutRef.current = null;
          }, 2000);
        }, 1000);
      }, 1000);
      return () => clearTimeout(t);
    }
  }, [
    isLoading,
    messages,
    isTTSEnabled,
    isTTSSupported,
    setShowClusterDashboardAfterAnalysis,
    setWow,
    addMessage,
  ]);

  const [subtitleMessageId, setSubtitleMessageId] = useState<string | null>(
    null,
  );
  const [subtitleVisibleText, setSubtitleVisibleText] = useState("");

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
    checkHealth();
  }, [checkHealth]);

  useEffect(() => {
    return () => {
      if (followUpMessageTimeoutRef.current)
        clearTimeout(followUpMessageTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    scrollBottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, subtitleVisibleText, isLoading]);

  useEffect(() => {
    if (!isTTSEnabled || !isTTSSupported) return;
    const last = messages[messages.length - 1];
    if (!last || (last.type !== "answer" && last.type !== "chat")) return;
    if (last.content === lastSpokenMessageRef.current) return;
    lastSpokenMessageRef.current = last.content;
    setSubtitleMessageId(last.id);
    setSubtitleVisibleText("");
    speakWithSubtitles(last.content, {
      onSubtitle: setSubtitleVisibleText,
      onEnd: () => {
        setSubtitleMessageId(null);
        setSubtitleVisibleText("");
        if (glowOnAfterTTSRef.current) {
          glowOnAfterTTSRef.current = false;
          setShowGlow(true);
        }
        if (pendingAnalysisShiftRef.current) {
          pendingAnalysisShiftRef.current = false;
          setTimeout(() => {
            setShowClusterDashboardAfterAnalysis(true);
            setTimeout(() => {
              setWow(true);
              setTimeout(() => setWow(false), 1000);
              if (followUpMessageTimeoutRef.current)
                clearTimeout(followUpMessageTimeoutRef.current);
              followUpMessageTimeoutRef.current = setTimeout(() => {
                addMessage({
                  type: "chat",
                  content: CLUSTER_FOLLOW_UP_MESSAGE,
                });
                followUpMessageTimeoutRef.current = null;
              }, 2000);
            }, 1000);
          }, 1000);
        }
      },
    });
  }, [
    messages,
    isTTSEnabled,
    isTTSSupported,
    speakWithSubtitles,
    setShowClusterDashboardAfterAnalysis,
    setWow,
    setShowGlow,
    addMessage,
  ]);

  const handleMicClick = async () => {
    if (isRecording) {
      voiceContext.setIsProcessing(true);
      waitingForSttRef.current = true;
      await stopRecording();
      voiceContext.setIsProcessing(false);
    } else {
      await startRecording((transcript) => {
        setInput(transcript);
        waitingForSttRef.current = false;
        if (pendingSubmitAfterSttRef.current) {
          pendingSubmitAfterSttRef.current = false;
          if (transcript.trim().toLowerCase().includes("analysis")) {
            pendingAnalysisShiftRef.current = true;
          }
          pendingSubmitTranscriptRef.current = transcript;
        }
      });
    }
  };

  const toggleTTS = () => {
    if (isSpeaking) stopSpeaking();
    setIsTTSEnabled((v) => !v);
  };

  const lastUserMessage =
    [...messages].reverse().find((m) => m.type === "user")?.content ?? "";
  const responseMessages = messages.filter((m) =>
    [
      "answer",
      "chat",
      "thought",
      "plan",
      "navigation",
      "confirmation",
      "error",
    ].includes(m.type),
  );
  const lastResponse = responseMessages[responseMessages.length - 1];
  const showConfirmation = lastResponse?.type === "confirmation";
  const showThinkingSpinner =
    (isLoading && pendingMessage === null) ||
    (subtitleMessageId !== null && subtitleVisibleText === "");
  const previousMessagesText =
    responseMessages.length <= 1
      ? ""
      : responseMessages
          .slice(0, -1)
          .map((m) => m.content)
          .filter(Boolean)
          .join("\n\n");
  const useTextTypeForLast =
    lastResponse &&
    (lastResponse.type === "answer" || lastResponse.type === "chat") &&
    subtitleMessageId === lastResponse.id;
  const lastPartPlain = !useTextTypeForLast
    ? (lastResponse?.content ?? "")
    : "";

  return (
    <div
      className="absolute inset-0 z-10 flex flex-col px-6 pb-6 pt-4 md:px-8 md:pb-8 md:pt-4 animate-in fade-in-0 duration-700"
      style={{ fontFamily: "Zodiak, sans-serif" }}
    >
      <div className="flex flex-col items-center max-w-md w-full mx-auto mt-auto gap-0">
        {/* Single grey box: fixed height, scrollable text (same kind of dimensions as input) */}
        <ScrollArea className="h-24 w-full rounded-t-lg border border-b-0 border-border bg-zinc-200/80 dark:bg-zinc-700/50">
          <div
            ref={scrollRef}
            className="p-3 text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap"
          >
            {responseMessages.length === 0 && !isLoading && (
              <span className="text-zinc-500 dark:text-zinc-400">
                Ask a question or click the mic
              </span>
            )}
            {previousMessagesText ? previousMessagesText : null}
            {previousMessagesText && (lastPartPlain || useTextTypeForLast)
              ? "\n\n"
              : null}
            {showThinkingSpinner && (
              <div className="mt-2 flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400">
                <Loader2 className="size-4 animate-spin shrink-0" />
                <span>Thinking…</span>
              </div>
            )}
            {!showThinkingSpinner && useTextTypeForLast && lastResponse && (
              <TextType
                key={lastResponse.id}
                text={lastResponse.content}
                loop={false}
                typingSpeed={40}
                showCursor={true}
                className="text-zinc-700 dark:text-zinc-300"
                variableSpeed={undefined}
                onSentenceComplete={undefined}
              />
            )}
            {!showThinkingSpinner && lastPartPlain ? lastPartPlain : null}
            <div
              ref={scrollBottomRef}
              aria-hidden
              className="h-0 w-full shrink-0"
            />
            {showConfirmation && (
              <div className="flex flex-wrap gap-2 mt-2">
                <button
                  type="button"
                  onClick={() => handleConfirmation(true)}
                  disabled={isLoading}
                  className="text-xs px-2 py-1 rounded bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
                >
                  Yes, Deep Analysis
                </button>
                <button
                  type="button"
                  onClick={() => handleConfirmation(false)}
                  disabled={isLoading}
                  className="text-xs px-2 py-1 rounded border border-border hover:bg-zinc-200 dark:hover:bg-zinc-600 disabled:opacity-50"
                >
                  No, Simple Chat
                </button>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* One-line strip: last message sent (truncated) */}
        {lastUserMessage ? (
          <div
            className="w-full px-3 py-1.5 bg-zinc-100 dark:bg-zinc-800/80 border-x border-border text-sm text-zinc-600 dark:text-zinc-300 truncate"
            title={lastUserMessage}
          >
            {lastUserMessage}
          </div>
        ) : null}

        {/* Input + mic + send + model + voice */}
        <div className="flex shrink-0 w-full flex-col gap-3 rounded-b-lg border border-border bg-white dark:bg-zinc-100 px-4 py-3 text-sm text-zinc-800 dark:text-zinc-900 shadow-sm">
          {backendHealthy === false && (
            <p className="text-xs text-amber-600 dark:text-amber-400">
              Backend unavailable. Start the server on port 8000.
            </p>
          )}
          <div className="flex items-center gap-2">
            {isTTSSupported && (
              <button
                type="button"
                onClick={toggleTTS}
                className="flex items-center gap-1 rounded px-2 py-1 text-xs hover:bg-zinc-200 dark:hover:bg-zinc-600"
                title={isTTSEnabled ? "Click to mute" : "Voice off"}
              >
                {isTTSEnabled ? (
                  <Volume className="size-3.5" />
                ) : (
                  <VolumeX className="size-3.5" />
                )}
              </button>
            )}
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              {isRecording ? (
                <span className="text-red-500 animate-pulse">Recording...</span>
              ) : (
                "Click mic to speak"
              )}
            </span>
          </div>
          <form
            onSubmit={handleSubmitWithAnalysis}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isRecording ? "Speaking..." : "How Can I Help You?"}
              disabled={isLoading}
              className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-zinc-500 dark:placeholder:text-zinc-400 text-base disabled:opacity-60"
              aria-label="How Can I Help You?"
            />
            <button
              type="button"
              onClick={handleMicClick}
              disabled={isLoading}
              className={`flex size-8 shrink-0 items-center justify-center rounded-md transition-colors ${
                isRecording
                  ? "bg-red-600 text-white"
                  : "bg-zinc-200 text-zinc-700 hover:bg-zinc-300 dark:bg-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-500"
              } ${isRecording ? "animate-pulse" : ""}`}
              aria-label={
                isRecording ? "Stop recording" : "Activate microphone"
              }
            >
              <Mic className="size-4" />
            </button>
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="flex size-8 shrink-0 items-center justify-center rounded-md bg-foreground text-background hover:opacity-90 transition-opacity disabled:opacity-50"
              aria-label="Send"
            >
              {isLoading ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <ArrowRight className="size-4" />
              )}
            </button>
          </form>
          <Select value={model} onValueChange={setModel}>
            <SelectTrigger
              size="sm"
              className="h-7 w-fit max-w-[10rem] border-zinc-300 dark:border-zinc-600 bg-transparent text-zinc-700 dark:text-zinc-300 text-xs px-2"
            >
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
