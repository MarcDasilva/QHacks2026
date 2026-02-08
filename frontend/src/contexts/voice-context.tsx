"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface VoiceContextType {
  isSpeaking: boolean;
  setIsSpeaking: (value: boolean) => void;
  isListening: boolean;
  setIsListening: (value: boolean) => void;
  isProcessing: boolean;
  setIsProcessing: (value: boolean) => void;
}

const VoiceContext = createContext<VoiceContextType | undefined>(undefined);

export function VoiceProvider({ children }: { children: ReactNode }) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  return (
    <VoiceContext.Provider
      value={{
        isSpeaking,
        setIsSpeaking,
        isListening,
        setIsListening,
        isProcessing,
        setIsProcessing,
      }}
    >
      {children}
    </VoiceContext.Provider>
  );
}

export function useVoice() {
  const context = useContext(VoiceContext);
  if (context === undefined) {
    throw new Error("useVoice must be used within a VoiceProvider");
  }
  return context;
}
