"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

const CRM_DATABASE_VALUE = "crm";

export type ExpansionPhase = "idle" | "expanding" | "holding" | "done";

const READY_DELAY_MS = 0;

type DashboardContextValue = {
  selectedDatabase: string | null;
  setSelectedDatabase: (db: string | null) => void;
  expansionPhase: ExpansionPhase;
  showClusterView: boolean;
  ready: boolean;
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

const EXPAND_MS = 900;
const HOLD_MS = 2200;

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [selectedDatabase, setSelectedDatabase] = useState<string | null>(null);
  const [expansionPhase, setExpansionPhase] = useState<ExpansionPhase>("idle");
  const [ready, setReady] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const readyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showClusterView =
    selectedDatabase === CRM_DATABASE_VALUE && expansionPhase === "done";

  useEffect(() => {
    if (selectedDatabase !== CRM_DATABASE_VALUE) {
      setExpansionPhase("idle");
      setReady(false);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      if (readyTimeoutRef.current) {
        clearTimeout(readyTimeoutRef.current);
        readyTimeoutRef.current = null;
      }
      return;
    }

    setExpansionPhase("expanding");
    const t1 = setTimeout(() => {
      setExpansionPhase("holding");
      timeoutRef.current = setTimeout(() => {
        setExpansionPhase("done");
        timeoutRef.current = null;
        readyTimeoutRef.current = setTimeout(() => {
          setReady(true);
          readyTimeoutRef.current = null;
        }, READY_DELAY_MS);
      }, HOLD_MS);
    }, EXPAND_MS);

    return () => {
      clearTimeout(t1);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      if (readyTimeoutRef.current) clearTimeout(readyTimeoutRef.current);
    };
    // Only run when selectedDatabase changes. Do NOT depend on expansionPhase,
    // or the effect re-runs when we set "expanding" and the cleanup clears our timeouts.
  }, [selectedDatabase]);

  useEffect(() => {
    if (selectedDatabase !== CRM_DATABASE_VALUE) {
      setReady(false);
      if (readyTimeoutRef.current) {
        clearTimeout(readyTimeoutRef.current);
        readyTimeoutRef.current = null;
      }
    }
  }, [selectedDatabase]);

  const value: DashboardContextValue = {
    selectedDatabase,
    setSelectedDatabase,
    expansionPhase,
    showClusterView,
    ready,
  };

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const ctx = useContext(DashboardContext);
  if (!ctx)
    throw new Error("useDashboard must be used within DashboardProvider");
  return ctx;
}

export { CRM_DATABASE_VALUE };
