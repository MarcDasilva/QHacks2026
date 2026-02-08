"use client";

import { IconLoader2, IconSparkles } from "@tabler/icons-react";
import { Button } from "@/components/ui/button";
import type { ChatMessage } from "@/hooks/use-backend-chat";

interface ChatMessageViewProps {
  message: ChatMessage;
  onConfirmation: (confirmed: boolean) => void;
  isLoading: boolean;
}

export function ChatMessageView({
  message,
  onConfirmation,
  isLoading,
}: ChatMessageViewProps) {
  const data = message.data as
    | {
        plan?: Array<{ product: string; why: string }>;
        rationale?: string[];
        key_metrics?: string[];
      }
    | undefined;

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
          <IconLoader2 className="h-4 w-4 animate-spin text-blue-500 mt-1 shrink-0" />
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
              <IconSparkles className="h-4 w-4 shrink-0" />
              {message.content}
            </div>
            {data?.plan && (
              <ul className="space-y-1 text-sm">
                {data.plan.map((item, idx) => (
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
            {data?.rationale && data.rationale.length > 0 && (
              <div className="mt-3 pt-3 border-t border-green-200 dark:border-green-800">
                <div className="font-medium text-xs text-green-700 dark:text-green-300 mb-2">
                  Detailed Insights:
                </div>
                <ul className="space-y-1 text-xs">
                  {data.rationale.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-green-600 dark:text-green-400">
                        ✓
                      </span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {data?.key_metrics && data.key_metrics.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {data.key_metrics.map((metric, idx) => (
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
                onClick={() => onConfirmation(true)}
                disabled={isLoading}
                className="bg-purple-600 hover:bg-purple-700"
              >
                Yes, Deep Analysis
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onConfirmation(false)}
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
}
