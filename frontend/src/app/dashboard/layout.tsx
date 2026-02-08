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
import { ArrowRight, Mic } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

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
      <DashboardProvider>
        <DashboardLayoutContent
          user={sidebarUser}
          onLogout={handleLogout}
          showGlow={showGlow}
        >
          {children}
        </DashboardLayoutContent>
      </DashboardProvider>
    </SidebarProvider>
  );
}

function DashboardLayoutContent({
  user,
  onLogout,
  showGlow,
  children,
}: {
  user: { name: string; email: string; avatar: string };
  onLogout: () => void;
  showGlow: boolean;
  children: React.ReactNode;
}) {
  const { expansionPhase, selectedDatabase, ready } = useDashboard();
  const isExpandingOrHolding =
    expansionPhase === "expanding" || expansionPhase === "holding";
  const isCrmSelected = selectedDatabase === CRM_DATABASE_VALUE;
  const boohooFullWidth = isCrmSelected;

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
              {!boohooFullWidth && (
                <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl">
                  <div className="min-h-0 flex-1 overflow-auto">{children}</div>
                  <GlowEffect active={showGlow} />
                </div>
              )}
              <div
                className={`relative flex h-full max-h-full shrink-0 flex-col overflow-hidden rounded-xl border border-border bg-zinc-200 dark:bg-zinc-800 transition-[flex-basis] duration-[1.8s] ease-out ${
                  boohooFullWidth
                    ? "basis-full"
                    : isExpandingOrHolding
                      ? "basis-3/4"
                      : "basis-80 md:basis-96"
                }`}
              >
                <BoohooRive glowActive={showGlow} />
                {boohooFullWidth && ready && <CrmReadyOverlay />}
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
  const [inputValue, setInputValue] = useState("");
  const [micOn, setMicOn] = useState(false);
  const [model, setModel] = useState(ML_MODELS[0].value);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      className="absolute inset-0 z-10 flex flex-col gap-4 px-6 pb-6 pt-4 md:px-8 md:pb-8 md:pt-4 animate-in fade-in-0 duration-700"
      style={{ fontFamily: "Zodiak, sans-serif" }}
    >
      <div className="flex shrink-0 justify-center">
        <div className="flex w-full max-w-md min-h-24 flex-col justify-center rounded-lg bg-zinc-400/60 dark:bg-zinc-600/60 px-4 py-3 text-sm text-zinc-700 dark:text-zinc-300">
          <p className="text-balance">Notes or context appear here.</p>
        </div>
      </div>
      <div className="flex min-h-0 flex-1" />
      <div className="flex shrink-0 justify-center">
        <div className="flex w-full max-w-md flex-col gap-3 rounded-lg border border-border bg-white dark:bg-zinc-100 px-4 py-3 text-sm text-zinc-800 dark:text-zinc-900 shadow-sm min-h-24">
          <div className="flex min-h-0 flex-1 flex-col gap-2">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="How Can I Help You?"
                className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-zinc-500 dark:placeholder:text-zinc-400 text-base"
                aria-label="How Can I Help You?"
              />
              <button
                type="button"
                onClick={() => setMicOn((o) => !o)}
                className={`flex size-8 shrink-0 items-center justify-center rounded-md transition-colors ${
                  micOn
                    ? "bg-zinc-800 text-white dark:bg-zinc-200 dark:text-zinc-900"
                    : "bg-zinc-200 text-zinc-700 hover:bg-zinc-300 dark:bg-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-500"
                }`}
                aria-label={micOn ? "Microphone on" : "Activate microphone"}
              >
                <Mic className="size-4" />
              </button>
              <button
                type="button"
                className="flex size-8 shrink-0 items-center justify-center rounded-md bg-foreground text-background hover:opacity-90 transition-opacity"
                aria-label="Send"
              >
                <ArrowRight className="size-4" />
              </button>
            </div>
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
    </div>
  );
}
