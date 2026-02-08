"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { API_URL } from "@/lib/api-config";

const BACKEND_URL = API_URL;

/** Delay (ms) after records dialogue completes before triggering analytics visit (README flow). */
export const ANALYTICS_VISIT_DELAY_MS = 3000;

/** Delay (ms) after analytics TTS is DONE before "I'm going to generate the report now" and report API. */
export const REPORT_DELAY_AFTER_TTS_MS = 3000;

export interface ChatMessage {
  id: string;
  type:
    | "user"
    | "thought"
    | "plan"
    | "navigation"
    | "answer"
    | "error"
    | "chat"
    | "confirmation";
  content: string;
  data?: unknown;
  timestamp: Date;
}

function createMessage(
  message: Omit<ChatMessage, "id" | "timestamp">,
): ChatMessage {
  return {
    ...message,
    id: Math.random().toString(36).slice(2, 11),
    timestamp: new Date(),
  };
}

export interface UseBackendChatReturn {
  messages: ChatMessage[];
  input: string;
  setInput: (value: string) => void;
  isLoading: boolean;
  pendingMessage: string | null;
  addMessage: (message: Omit<ChatMessage, "id" | "timestamp">) => void;
  handleSubmit: (e: React.FormEvent) => Promise<void>;
  handleConfirmation: (confirmed: boolean) => Promise<void>;
  backendHealthy: boolean | null;
  checkHealth: () => Promise<void>;
  /** True when we added the analytics discussion and are waiting for TTS to finish before starting report countdown. */
  reportPendingTts: boolean;
  /** Call when analytics discussion TTS is done; starts 3s delay then "I'm generating the report" and report API. */
  startReportCountdownAfterTts: () => void;
}

/** Delay (ms) after turning glow on before navigating — glow must show first, then change page. */
export const GLOW_BEFORE_NAV_MS = 1000;

export interface UseBackendChatOptions {
  /** Called when the stream emits a cluster_prediction (parent + child cluster for user's follow-up). */
  onClusterPrediction?: (
    parentClusterId: number,
    childClusterId: number,
  ) => void;
  /** Called when the stream emits glow_on (turn glow mode on after follow-up). */
  onGlowOn?: () => void;
  /** Called when navigation is requested. Layout must turn glow on, wait GLOW_BEFORE_NAV_MS, then navigate to url. If provided, the hook never calls router.push — layout owns the order. */
  onBeforeNavigate?: (url: string) => void;
  /** Called when report generation starts (e.g. set Rive thinking true). */
  onStartReportGeneration?: () => void;
  /** Called when report PDF is ready with blob URL for viewing. Caller should set thinking false and open/show PDF. */
  onReportComplete?: (pdfBlobUrl: string | null) => void;
}

export function useBackendChat(
  router: AppRouterInstance,
  options: UseBackendChatOptions = {},
): UseBackendChatReturn {
  const {
    onClusterPrediction,
    onGlowOn,
    onBeforeNavigate,
    onStartReportGeneration,
    onReportComplete,
  } = options;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  /** Cluster from the current stream run; after "complete", we wait 3s then call analytics-visit. */
  const lastClusterPredictionRef = useRef<{
    parent_cluster_id: number;
    child_cluster_id: number;
  } | null>(null);
  const analyticsVisitTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const reportGenerateTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const [reportPendingTts, setReportPendingTts] = useState(false);
  const pendingReportAfterTtsRef = useRef<{
    parentId: number;
    childId: number;
    discussion: string;
  } | null>(null);

  const addMessage = useCallback(
    (message: Omit<ChatMessage, "id" | "timestamp">) => {
      setMessages((prev) => [...prev, createMessage(message)]);
    },
    [],
  );

  const handleNavigate = useCallback(
    (url: string) => {
      router.push(url);
    },
    [router],
  );

  useEffect(() => {
    return () => {
      if (analyticsVisitTimeoutRef.current)
        clearTimeout(analyticsVisitTimeoutRef.current);
      if (reportGenerateTimeoutRef.current)
        clearTimeout(reportGenerateTimeoutRef.current);
    };
  }, []);

  const sendMessage = useCallback(
    async (userMessage: string, mode: "chat" | "deep_analysis") => {
      lastClusterPredictionRef.current = null;
      if (analyticsVisitTimeoutRef.current) {
        clearTimeout(analyticsVisitTimeoutRef.current);
        analyticsVisitTimeoutRef.current = null;
      }
      if (reportGenerateTimeoutRef.current) {
        clearTimeout(reportGenerateTimeoutRef.current);
        reportGenerateTimeoutRef.current = null;
      }
      pendingReportAfterTtsRef.current = null;
      setReportPendingTts(false);
      setIsLoading(true);

      if (!pendingMessage) {
        addMessage({ type: "user", content: userMessage });
      }

      try {
        const response = await fetch(`${BACKEND_URL}/api/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userMessage, mode }),
        });

        if (!response.ok) {
          let detail = `Server error (${response.status})`;
          try {
            const body = (await response.json()) as { detail?: string };
            if (body?.detail) detail = body.detail;
          } catch {
            try {
              const text = await response.text();
              if (text) detail = text.slice(0, 200);
            } catch {
              // keep default detail
            }
          }
          throw new Error(detail);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error("No response body");
        }

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const data = JSON.parse(line.slice(6)) as {
                type: string;
                content?: string;
                data?: {
                  url?: string;
                  plan?: unknown;
                  rationale?: string[];
                  key_metrics?: string[];
                  parent_cluster_id?: number;
                  child_cluster_id?: number;
                };
              };

              if (data.type === "cluster_prediction" && data.data != null) {
                const parent = data.data.parent_cluster_id;
                const child = data.data.child_cluster_id;
                if (
                  typeof parent === "number" &&
                  typeof child === "number"
                ) {
                  lastClusterPredictionRef.current = {
                    parent_cluster_id: parent,
                    child_cluster_id: child,
                  };
                  if (onClusterPrediction) onClusterPrediction(parent, child);
                }
              } else if (data.type === "glow_on" && onGlowOn) {
                onGlowOn();
              } else if (data.type === "navigation") {
                addMessage({
                  type: "navigation",
                  content: data.content ?? "",
                  data: data.data,
                });
                if (data.data?.url) {
                  const url = data.data.url;
                  if (onBeforeNavigate) {
                    // Layout owns glow-then-navigate: hook only notifies with url; layout turns glow on and navigates after delay
                    onBeforeNavigate(url);
                  } else {
                    setTimeout(() => handleNavigate(url), 500);
                  }
                }
              } else if (data.type === "plan") {
                addMessage({
                  type: "plan",
                  content: data.content ?? "",
                  data: data.data,
                });
              } else if (data.type === "thought") {
                addMessage({ type: "thought", content: data.content ?? "" });
              } else if (data.type === "answer") {
                addMessage({
                  type: "answer",
                  content: data.content ?? "",
                  data: data.data,
                });
              } else if (data.type === "chat") {
                addMessage({ type: "chat", content: data.content ?? "" });
              } else if (data.type === "complete") {
                const pending = lastClusterPredictionRef.current;
                lastClusterPredictionRef.current = null;
                if (
                  pending != null &&
                  onBeforeNavigate
                ) {
                  const parentId = pending.parent_cluster_id;
                  const childId = pending.child_cluster_id;
                  analyticsVisitTimeoutRef.current = setTimeout(() => {
                    analyticsVisitTimeoutRef.current = null;
                    fetch(`${BACKEND_URL}/api/chat/analytics-visit`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        parent_cluster_id: parentId,
                        child_cluster_id: childId,
                      }),
                    })
                      .then((res) => (res.ok ? res.json() : null))
                      .then((body: { url?: string; discussion?: string } | null) => {
                        if (!body) return;
                        if (body.url) onBeforeNavigate(body.url);
                        const discussion = body.discussion ?? "";
                        if (discussion)
                          addMessage({
                            type: "chat",
                            content: discussion,
                          });
                        // Wait for analytics TTS to finish; layout will call startReportCountdownAfterTts() in TTS onEnd
                        pendingReportAfterTtsRef.current = {
                          parentId,
                          childId,
                          discussion,
                        };
                        setReportPendingTts(true);
                      })
                      .catch((err) => console.error("Analytics visit failed:", err));
                  }, ANALYTICS_VISIT_DELAY_MS);
                }
                setIsLoading(false);
                return;
              } else if (data.type === "error") {
                addMessage({
                  type: "error",
                  content: data.content ?? "Unknown error",
                });
                setIsLoading(false);
                return;
              }
            } catch (err) {
              console.error("Error parsing SSE data:", err);
            }
          }
        }
      } catch (error) {
        console.error("Error:", error);
        const message = error instanceof Error ? error.message : String(error);
        addMessage({
          type: "error",
          content:
            message.includes("Failed to fetch") ||
            message.includes("NetworkError")
              ? "Failed to connect to the backend. Make sure the server is running on port 8000."
              : message,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [
      addMessage,
      handleNavigate,
      pendingMessage,
      onClusterPrediction,
      onGlowOn,
      onBeforeNavigate,
      onStartReportGeneration,
      onReportComplete,
    ],
  );

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const userMessage = input.trim();
      if (!userMessage || isLoading) return;

      setInput("");

      const mode = userMessage.toLowerCase().includes("analysis")
        ? "deep_analysis"
        : "chat";
      await sendMessage(userMessage, mode);
    },
    [input, isLoading, sendMessage],
  );

  const handleConfirmation = useCallback(
    async (confirmed: boolean) => {
      if (!pendingMessage) return;
      const mode = confirmed ? "deep_analysis" : "chat";
      await sendMessage(pendingMessage, mode);
      setPendingMessage(null);
    },
    [pendingMessage, sendMessage],
  );

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/health`);
      const data = await res.json().catch(() => ({}));
      setBackendHealthy(res.ok && data?.status === "healthy");
    } catch {
      setBackendHealthy(false);
    }
  }, []);

  const startReportCountdownAfterTts = useCallback(() => {
    const pending = pendingReportAfterTtsRef.current;
    pendingReportAfterTtsRef.current = null;
    setReportPendingTts(false);
    if (!pending || !onStartReportGeneration || !onReportComplete) return;
    reportGenerateTimeoutRef.current = setTimeout(() => {
      reportGenerateTimeoutRef.current = null;
      addMessage({
        type: "chat",
        content: "I'm going to generate the report now.",
      });
      onStartReportGeneration();
      fetch(`${BACKEND_URL}/api/report/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parent_cluster_id: pending.parentId,
          child_cluster_id: pending.childId,
          discussion: pending.discussion,
        }),
      })
        .then((res) => (res.ok ? res.arrayBuffer() : null))
        .then((buf: ArrayBuffer | null) => {
          if (buf == null) {
            onReportComplete(null);
            return;
          }
          const blob = new Blob([buf], { type: "application/pdf" });
          const url = URL.createObjectURL(blob);
          onReportComplete(url);
        })
        .catch((err) => {
          console.error("Report generate failed:", err);
          onReportComplete(null);
        });
    }, REPORT_DELAY_AFTER_TTS_MS);
  }, [
    addMessage,
    onStartReportGeneration,
    onReportComplete,
  ]);

  return {
    messages,
    input,
    setInput,
    isLoading,
    pendingMessage,
    addMessage,
    handleSubmit,
    handleConfirmation,
    backendHealthy,
    checkHealth,
    reportPendingTts,
    startReportCountdownAfterTts,
  };
}
