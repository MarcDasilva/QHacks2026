"use client";

import { useState, useCallback } from "react";
import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";
import { API_URL } from "@/lib/api-config";

const BACKEND_URL = API_URL;

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
}

export interface UseBackendChatOptions {
  /** Called when the stream emits a cluster_prediction (parent + child cluster for user's follow-up). */
  onClusterPrediction?: (
    parentClusterId: number,
    childClusterId: number,
  ) => void;
  /** Called when the stream emits glow_on (turn glow mode on after follow-up). */
  onGlowOn?: () => void;
}

export function useBackendChat(
  router: AppRouterInstance,
  options: UseBackendChatOptions = {},
): UseBackendChatReturn {
  const { onClusterPrediction, onGlowOn } = options;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

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

  const sendMessage = useCallback(
    async (userMessage: string, mode: "chat" | "deep_analysis") => {
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
                  typeof child === "number" &&
                  onClusterPrediction
                ) {
                  onClusterPrediction(parent, child);
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
                  setTimeout(() => handleNavigate(data.data!.url!), 500);
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
    [addMessage, handleNavigate, pendingMessage, onClusterPrediction, onGlowOn],
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
  };
}
