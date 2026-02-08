"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { SelectedCluster } from "@/types/clusters";

const CRM_DATABASE_VALUE = "crm";

export type ExpansionPhase = "idle" | "expanding" | "holding" | "done";

const READY_DELAY_MS = 0;

type DashboardContextValue = {
  selectedDatabase: string | null;
  setSelectedDatabase: (db: string | null) => void;
  expansionPhase: ExpansionPhase;
  showClusterView: boolean;
  ready: boolean;
  /** When true, layout shifts Boohoo to the right and shows cluster dashboard (e.g. after user says "analysis"). */
  showClusterDashboardAfterAnalysis: boolean;
  setShowClusterDashboardAfterAnalysis: (v: boolean) => void;
  /** When true, Rive shows "wow" (set true when cluster charts open, false after 1s). */
  wow: boolean;
  setWow: (v: boolean) => void;
  /** When true, Rive shows "thinking" (e.g. report generation in progress). */
  thinking: boolean;
  setThinking: (v: boolean) => void;
  /** Selected level-1 cluster for the 3D view (e.g. from cluster predictor follow-up). */
  selectedCluster: SelectedCluster;
  setSelectedCluster: (c: SelectedCluster) => void;
  /** Glow mode (e.g. turned on after user follow-up "deep research"). */
  showGlow: boolean;
  setShowGlow: (v: boolean) => void;
  /** Blob URL of the generated report PDF to show on Reports page (null when none). */
  reportPdfUrl: string | null;
  setReportPdfUrl: (url: string | null) => void;
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

const EXPAND_MS = 900;
const HOLD_MS = 2200;

type DashboardProviderProps = {
  children: ReactNode;
  /** Glow state (from layout) so overlay can turn glow on when backend sends glow_on */
  showGlow?: boolean;
  setShowGlow?: (v: boolean) => void;
};

export function DashboardProvider({
  children,
  showGlow: showGlowProp = false,
  setShowGlow: setShowGlowProp,
}: DashboardProviderProps) {
  const [selectedDatabase, setSelectedDatabase] = useState<string | null>(null);
  const [expansionPhase, setExpansionPhase] = useState<ExpansionPhase>("idle");
  const [ready, setReady] = useState(false);
  const [
    showClusterDashboardAfterAnalysis,
    setShowClusterDashboardAfterAnalysis,
  ] = useState(false);
  const [wow, setWow] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [selectedCluster, setSelectedCluster] = useState<SelectedCluster>(null);
  const [internalGlow, setInternalGlow] = useState(false);
  const [reportPdfUrl, setReportPdfUrl] = useState<string | null>(null);
  const showGlow = setShowGlowProp != null ? showGlowProp : internalGlow;
  const setShowGlow =
    setShowGlowProp != null ? setShowGlowProp : setInternalGlow;
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
    showClusterDashboardAfterAnalysis,
    setShowClusterDashboardAfterAnalysis,
    wow,
    setWow,
    thinking,
    setThinking,
    selectedCluster,
    setSelectedCluster,
    showGlow,
    setShowGlow,
    reportPdfUrl,
    setReportPdfUrl,
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
