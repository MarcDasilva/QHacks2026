"use client";

import { useEffect, useRef } from "react";
import {
  useRive,
  useStateMachineInput,
  Layout,
  Fit,
  Alignment,
} from "@rive-app/react-webgl2";

const STATE_MACHINE_NAME = "State Machine 1";

const EYE_CENTER = 50;
const EYE_AMPLITUDE = 22;
const EYE_PERIOD_MS = 1200;

type BoohooRiveProps = {
  /** When true, eyes move up/down instead of following cursor (glow highlight mode). */
  glowActive?: boolean;
};

export function BoohooRive({ glowActive = false }: BoohooRiveProps) {
  const { rive, RiveComponent } = useRive({
    src: "/boohooplusglow.riv",
    stateMachines: STATE_MACHINE_NAME,
    layout: new Layout({
      fit: Fit.Contain,
      alignment: Alignment.Center,
    }),
    autoplay: true,
  });

  const talkingInput = useStateMachineInput(
    rive,
    STATE_MACHINE_NAME,
    "talking",
    false,
  );
  const thinkingInput = useStateMachineInput(
    rive,
    STATE_MACHINE_NAME,
    "thinking",
    false,
  );
  const characterXInput = useStateMachineInput(
    rive,
    STATE_MACHINE_NAME,
    "characterX",
    EYE_CENTER,
  );
  const characterYInput = useStateMachineInput(
    rive,
    STATE_MACHINE_NAME,
    "characterY",
    EYE_CENTER,
  );
  const rafRef = useRef<number>(0);

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

  useEffect(() => {
    if (!characterXInput || !characterYInput) return;

    if (glowActive) {
      const start = performance.now();
      const tick = () => {
        const t = performance.now() - start;
        characterXInput.value = EYE_CENTER;
        characterYInput.value =
          EYE_CENTER +
          EYE_AMPLITUDE * Math.sin((t * Math.PI * 2) / EYE_PERIOD_MS);
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);
      return () => cancelAnimationFrame(rafRef.current);
    }

    const handleMove = (e: MouseEvent) => {
      characterXInput.value = (e.clientX / window.innerWidth) * 100;
      characterYInput.value = 100 - (e.clientY / window.innerHeight) * 100;
    };
    window.addEventListener("mousemove", handleMove);
    return () => window.removeEventListener("mousemove", handleMove);
  }, [glowActive, characterXInput, characterYInput]);

  return (
    <div
      className="h-full min-h-[200px] w-full relative"
      style={{
        backgroundImage:
          "radial-gradient(circle, rgba(156, 163, 175, 0.45) 1px, transparent 1px)",
        backgroundSize: "12px 12px",
      }}
    >
      <RiveComponent />
    </div>
  );
}
