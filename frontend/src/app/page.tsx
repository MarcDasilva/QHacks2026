"use client";

export default function Home() {
  return (
    <div className="fixed inset-0 h-screen w-screen bg-black">
      <video
        src="/0207.mp4"
        autoPlay
        muted
        playsInline
        className="absolute inset-0 h-full w-full object-cover"
      />
    </div>
  );
}
