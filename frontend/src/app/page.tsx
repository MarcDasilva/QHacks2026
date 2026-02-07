"use client";

import type { ComponentType } from "react";
import Image from "next/image";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import LogoLoop from "@/components/LogoLoop";
import { createClient } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";

const LOGO_IMAGES = [
  { src: "/Hover and Click me (1).png", alt: "Logo 1" },
  { src: "/Hover and Click me (2).png", alt: "Logo 2" },
  { src: "/Hover and Click me (3).png", alt: "Logo 3" },
  { src: "/Hover and Click me (4).png", alt: "Logo 4" },
];

type LogoLoopProps = {
  logos: typeof LOGO_IMAGES;
  speed?: number;
  direction?: string;
  width?: string | number;
  logoHeight?: number;
  gap?: number;
  ariaLabel?: string;
};
const LogoLoopTyped = LogoLoop as ComponentType<LogoLoopProps>;

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        fill="#000"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#000"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#000"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#000"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

// Invisible content box (video area) – used to position Compass beside it
const CONTENT_BOX = {
  topLeft: { x: 110, y: 89.5 },
  topRight: { x: 800, y: 89.5 },
  bottomLeft: { x: 110, y: 743.5 },
  bottomRight: { x: 800, y: 743.5 },
};
const CONTENT_TOP = CONTENT_BOX.topLeft.y;
const CONTENT_HEIGHT = CONTENT_BOX.bottomLeft.y - CONTENT_BOX.topLeft.y;
const CONTENT_RIGHT = CONTENT_BOX.topRight.x;
const SIDE_PADDING = 28; // padding from content box and from screen edge

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [faded, setFaded] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const t = setTimeout(() => setFaded(true), 100);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
      if (session?.user) {
        router.replace("/dashboard");
      }
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        router.replace("/dashboard");
      }
    });
    return () => subscription.unsubscribe();
  }, [router]);

  const handleSignIn = async () => {
    const supabase = createClient();
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo:
          typeof window !== "undefined"
            ? `${window.location.origin}/auth/callback`
            : undefined,
      },
    });
  };

  return (
    <div className="fixed inset-0 h-screen w-screen bg-black">
      <div
        className="pointer-events-none fixed inset-0 z-50 bg-black transition-opacity duration-700 ease-out"
        style={{ opacity: faded ? 0 : 1 }}
        aria-hidden
      />
      <video
        src="/compass.mp4"
        autoPlay
        muted
        playsInline
        loop
        className="absolute inset-0 h-full w-full object-cover"
      />
      {/* Strip between content box and screen edge: flex grid, Compass centered horizontally and vertically */}
      <div
        className="pointer-events-none absolute flex items-center justify-center"
        style={{
          left: CONTENT_RIGHT,
          top: CONTENT_TOP,
          height: CONTENT_HEIGHT,
          right: SIDE_PADDING,
        }}
      >
        <header className="flex flex-col items-center text-center">
          <div className="relative inline-block">
            <div className="absolute bottom-full left-0 right-0 mb-1 flex w-full justify-center">
              <div className="mx-auto mt-6 w-3/4 min-w-0 overflow-hidden">
                <LogoLoopTyped
                  logos={LOGO_IMAGES}
                  speed={40}
                  direction="left"
                  width="100%"
                  logoHeight={55}
                  gap={24}
                  ariaLabel="Logo loop"
                />
              </div>
            </div>
            <h1
              className="text-center text-4xl font-normal tracking-tight text-white sm:text-5xl md:text-7xl lg:text-8xl xl:text-9xl 2xl:text-[10rem]"
              style={{ fontFamily: "Array, sans-serif" }}
            >
              compass
            </h1>
          </div>
          <div
            className="mt-2 w-full text-center text-2xl font-normal text-white md:text-3xl lg:text-4xl"
            style={{ fontFamily: "Zodiak, sans-serif" }}
          >
            <p>See Insights Clearer</p>
          </div>
          {loading ? (
            <div
              className="pointer-events-auto mt-6 inline-flex items-center gap-3 rounded-md border-0 bg-white/80 px-6 py-3 text-lg font-normal text-black"
              style={{ fontFamily: "Zodiak, sans-serif" }}
            >
              Loading…
            </div>
          ) : (
            <button
              type="button"
              onClick={handleSignIn}
              className="pointer-events-auto mt-6 inline-flex items-center gap-3 rounded-md border-0 bg-white px-6 py-3 text-lg font-normal text-black shadow-none transition-opacity hover:opacity-90"
              style={{ fontFamily: "Zodiak, sans-serif" }}
              aria-label="Sign in with Google"
            >
              <GoogleIcon className="h-6 w-6 shrink-0" />
              Sign in with Google
            </button>
          )}
          <Image
            src="/qhacks.png"
            alt="QHacks"
            width={120}
            height={48}
            className="mt-6 h-auto w-28 object-contain"
          />
        </header>
      </div>
    </div>
  );
}
