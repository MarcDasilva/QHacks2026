"use client";

import { useEffect } from "react";
import {
  useRive,
  useStateMachineInput,
  Layout,
  Fit,
  Alignment,
} from "@rive-app/react-webgl2";

const STATE_MACHINE_NAME = "State Machine 1";

export function BoohooRive() {
  const { rive, RiveComponent } = useRive({
    src: "/boohoobody.riv",
    stateMachines: STATE_MACHINE_NAME,
    layout: new Layout({
      fit: Fit.Contain,
      alignment: Alignment.Center,
    }),
    autoplay: true,
  });

  const talkingInput = useStateMachineInput(rive, STATE_MACHINE_NAME, "talking", false);
  const thinkingInput = useStateMachineInput(rive, STATE_MACHINE_NAME, "thinking", false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!e.shiftKey) return;
      if (e.key === "T") {
        e.preventDefault();
        if (talkingInput) talkingInput.value = !talkingInput.value;
      }
      if (e.key === "Y") {
        e.preventDefault();
        if (thinkingInput) thinkingInput.value = !thinkingInput.value;
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [talkingInput, thinkingInput]);

  return (
    <div
      className="h-full min-h-[200px] w-full relative"
      style={{
        backgroundImage: "radial-gradient(circle, rgba(156, 163, 175, 0.45) 1px, transparent 1px)",
        backgroundSize: "12px 12px",
      }}
    >
      <RiveComponent />
    </div>
  );
}
