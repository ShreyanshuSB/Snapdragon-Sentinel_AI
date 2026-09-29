"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Brain,
  Camera,
  Cpu,
  FileText,
  Layers,
  MessageSquare,
  Mic,
  Settings,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { VoiceAssistantModal } from "@/components/VoiceAssistantModal";

const navItems = [
  { href: "/", label: "Home", icon: Layers },
  { href: "/vision", label: "Vision", icon: Camera },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/memory", label: "Memory", icon: Brain },
  { href: "/chat", label: "Ask SENTINEL", icon: MessageSquare },
  { href: "/ai-lab", label: "AI Lab", icon: Cpu },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Navbar() {
  const pathname = usePathname();
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [isVoiceOpen, setIsVoiceOpen] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    api
      .getHealth()
      .then(() => {
        if (mounted) setBackendOnline(true);
      })
      .catch(() => {
        if (mounted) setBackendOnline(false);
      });
    return () => {
      mounted = false;
    };
  }, [pathname]);

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/80 backdrop-blur-xl transition-all">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        {/* Brand */}
        <Link href="/" className="group flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-cyan-400 text-slate-950 shadow-[0_0_20px_rgba(6,182,212,0.35)] transition group-hover:scale-105">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-wider text-white text-base">SENTINEL</span>
              <span className="rounded-md border border-cyan-500/30 bg-cyan-950/50 px-1.5 py-0.5 text-[10px] font-semibold text-cyan-300">
                Snapdragon AI
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">Private • Local-First • Multimodal</p>
          </div>
        </Link>

        {/* Navigation Items */}
        <nav className="flex items-center gap-1 overflow-x-auto py-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "border border-cyan-400/40 bg-cyan-500/10 text-cyan-300 shadow-[0_0_12px_rgba(6,182,212,0.15)]"
                    : "text-slate-300 hover:border-white/10 hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
                <span className="whitespace-nowrap">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Voice & Privacy & Health Badges */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Global Voice Assistant Button */}
          <button
            onClick={() => setIsVoiceOpen(true)}
            className="flex items-center gap-1.5 rounded-lg border border-cyan-400/40 bg-gradient-to-r from-cyan-600/20 to-blue-600/20 px-3 py-1.5 text-xs font-medium text-cyan-300 shadow-[0_0_15px_rgba(6,182,212,0.15)] hover:border-cyan-400/70 hover:scale-105 transition"
            title="Ask SENTINEL by Voice (Local Whisper STT)"
          >
            <Mic className="h-4 w-4 text-cyan-400 animate-pulse" />
            <span className="hidden sm:inline font-semibold">Voice</span>
          </button>

          <div className="hidden lg:flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-950/30 px-3 py-1 text-xs text-emerald-300">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Local-First</span>
          </div>

          <div
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
              backendOnline === true
                ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-300"
                : backendOnline === false
                ? "border-rose-500/30 bg-rose-950/20 text-rose-300"
                : "border-slate-700 bg-slate-800 text-slate-400"
            }`}
            title={
              backendOnline === true
                ? "FastAPI Backend Connected"
                : backendOnline === false
                ? "Backend Offline (Port 8000)"
                : "Checking backend..."
            }
          >
            <span
              className={`h-2 w-2 rounded-full ${
                backendOnline === true
                  ? "bg-emerald-400"
                  : backendOnline === false
                  ? "bg-rose-500"
                  : "bg-slate-400 animate-pulse"
              }`}
            />
            <span className="text-[11px] font-mono">
              {backendOnline === true ? "API Active" : backendOnline === false ? "API Disconnected" : "Connecting"}
            </span>
          </div>
        </div>
      </div>

      {/* Global Voice Assistant Modal */}
      <VoiceAssistantModal
        isOpen={isVoiceOpen}
        onClose={() => setIsVoiceOpen(false)}
      />
    </header>
  );
}
