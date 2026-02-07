"use client";

import { cn } from "@/lib/utils";
import { useEffect, useId, useState } from "react";

const FADE_MS = 300;

type GlowEffectProps = {
  /** When true, the glow highlight is shown on top as a border (no layout shift). */
  active: boolean;
  className?: string;
};

/**
 * Overlay that draws a rotating gradient border on top of a box.
 * Uses an SVG mask so only the edge band is visible with a rounded inner
 * cutout—center is transparent so content shows through and no elements move.
 */
export function GlowEffect({ active, className }: GlowEffectProps) {
  const [visible, setVisible] = useState(false);
  const [mounted, setMounted] = useState(false);
  const maskId = `glow-mask-${useId().replace(/:/g, "")}`;

  useEffect(() => {
    if (active) {
      setMounted(true);
      const t = requestAnimationFrame(() => {
        requestAnimationFrame(() => setVisible(true));
      });
      return () => cancelAnimationFrame(t);
    } else {
      setVisible(false);
      const id = setTimeout(() => setMounted(false), FADE_MS);
      return () => clearTimeout(id);
    }
  }, [active]);

  if (!mounted) return null;

  return (
    <div className={cn("absolute inset-0 z-10", className)} aria-hidden>
      {/* SVG mask: objectBoundingBox so 0–1 = 0–100% of the element. Outer rect = show gradient (white), inner rounded rect = hide (black). */}
      <svg
        aria-hidden
        className="absolute size-0 overflow-hidden"
        focusable={false}
      >
        <defs>
          <mask
            id={maskId}
            maskUnits="objectBoundingBox"
            maskContentUnits="objectBoundingBox"
          >
            <rect width="1" height="1" fill="white" />
            <rect
              x="0.005"
              y="0.005"
              width="0.99"
              height="0.99"
              rx="0.025"
              ry="0.025"
              fill="black"
            >
              {/* Reveal from outward to inward: inner cutout shrinks so the border band grows from the edge */}
              <animate
                attributeName="x"
                from="0.005"
                to="0.015"
                dur="0.35s"
                fill="freeze"
                begin="0s"
              />
              <animate
                attributeName="y"
                from="0.005"
                to="0.015"
                dur="0.35s"
                fill="freeze"
                begin="0s"
              />
              <animate
                attributeName="width"
                from="0.99"
                to="0.97"
                dur="0.35s"
                fill="freeze"
                begin="0s"
              />
              <animate
                attributeName="height"
                from="0.99"
                to="0.97"
                dur="0.35s"
                fill="freeze"
                begin="0s"
              />
            </rect>
          </mask>
        </defs>
      </svg>
      <div
        className="pointer-events-none absolute inset-0 overflow-hidden rounded-xl transition-opacity duration-300 ease-out"
        style={{
          opacity: visible ? 1 : 0,
          background:
            "linear-gradient(var(--gradient-angle), blue, purple, red, orange)",
          animation: "glow-rotation 5s linear infinite",
          filter: "blur(10px)",
          WebkitMaskImage: `url(#${maskId})`,
          maskImage: `url(#${maskId})`,
          WebkitMaskSize: "100% 100%",
          maskSize: "100% 100%",
          WebkitMaskPosition: "center",
          maskPosition: "center",
          WebkitMaskRepeat: "no-repeat",
          maskRepeat: "no-repeat",
        }}
      />
    </div>
  );
}
