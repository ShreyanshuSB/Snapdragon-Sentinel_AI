"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Brain,
  Camera,
  Compass,
  Cpu,
  Eye,
  Lock,
  MessageSquare,
  PlusCircle,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
} from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { StatusIndicator } from "@/components/StatusIndicator";
import { api } from "@/lib/api";
import { Memory, SystemStatus } from "@/lib/types";

export default function HomePage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [recentMemories, setRecentMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setError(null);
    try {
      const [statusRes, memoriesRes] = await Promise.all([
        api.getStatus(),
        api.getMemories(),
      ]);
      setStatus(statusRes);
      setRecentMemories(memoriesRes.slice(0, 3));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to SENTINEL local backend.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    async function init() {
      try {
        const [statusRes, memoriesRes] = await Promise.all([
          api.getStatus(),
          api.getMemories(),
        ]);
        if (isMounted) {
          setStatus(statusRes);
          setRecentMemories(memoriesRes.slice(0, 3));
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to connect to SENTINEL local backend.";
          setError(msg);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }
    init();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
        {/* Error banner if backend down */}
        {error && (
          <div className="mb-8 flex items-center justify-between rounded-2xl border border-rose-500/30 bg-rose-950/20 p-4 text-sm text-rose-300">
            <div className="flex items-center gap-3">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-500 animate-pulse" />
              <span>{error}</span>
            </div>
            <button
              onClick={loadData}
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 px-3 py-1.5 text-xs text-rose-200 hover:bg-rose-900/40 transition"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry Connection
            </button>
          </div>
        )}

        {/* Hero Section - Focused on SENTINEL's core question */}
        <section className="relative overflow-hidden rounded-3xl border border-cyan-500/20 bg-gradient-to-b from-slate-900/90 via-slate-900/60 to-slate-950 p-8 sm:p-12 shadow-[0_20px_70px_rgba(6,182,212,0.1)]">
          <div className="absolute right-0 top-0 -mt-16 -mr-16 h-80 w-80 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />

          <div className="max-w-3xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3.5 py-1 text-xs font-semibold text-cyan-300">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Snapdragon PC Multimodal Companion • Foundation Hardened</span>
            </div>

            <h1 className="text-3xl font-extrabold tracking-tight sm:text-5xl text-white">
              SENTINEL
            </h1>
            <p className="mt-2 text-xl font-medium text-cyan-400">
              What do you want to understand?
            </p>

            <p className="mt-4 text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl">
              A private local AI architecture designed for Snapdragon Windows PCs. See workspace components, analyze physical context, and preserve private memories without cloud dependencies.
            </p>

            {/* Core Action Trio */}
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                href="/chat"
                className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:bg-cyan-300 transition"
              >
                <MessageSquare className="h-4 w-4" />
                <span>Ask</span>
              </Link>

              <Link
                href="/vision"
                className="inline-flex items-center gap-2 rounded-xl border border-cyan-500/30 bg-cyan-950/20 px-6 py-3 text-sm font-semibold text-cyan-200 hover:border-cyan-400 hover:bg-cyan-500/10 hover:text-white transition"
              >
                <Camera className="h-4 w-4" />
                <span>See</span>
              </Link>

              <Link
                href="/memory"
                className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-6 py-3 text-sm font-semibold text-slate-200 hover:border-cyan-400/50 hover:bg-cyan-500/10 hover:text-white transition"
              >
                <PlusCircle className="h-4 w-4" />
                <span>Remember</span>
              </Link>

              <button
                type="button"
                disabled
                className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-3 text-sm font-medium text-slate-500 cursor-not-allowed"
                title="Targeted physical search arriving in Phase 7"
              >
                <Search className="h-4 w-4" />
                <span>Find It</span>
                <span className="ml-1 text-[10px] rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
                  Phase 7
                </span>
              </button>
            </div>
          </div>
        </section>

        {/* System State Grid - Truthful Indicators */}
        <section className="mt-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold uppercase tracking-wider text-slate-400 text-xs">
              Live System State & Policy Verification
            </h2>
            <button
              onClick={loadData}
              disabled={loading}
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-400 transition"
            >
              <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {/* AI Policy & Status */}
            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">LOCAL AI POLICY</span>
                <StatusIndicator
                  tone="ready"
                  label="Enabled"
                  size="sm"
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">
                Model execution: <span className="text-amber-400 font-medium">Not Connected</span> (Weights pending Phase 2).
              </p>
            </div>

            {/* Vision */}
            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">VISION</span>
                <StatusIndicator
                  tone="not_connected"
                  label="Not Connected"
                  size="sm"
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">
                Local camera capture ready. Inference runtime disconnected.
              </p>
            </div>

            {/* NPU Acceleration */}
            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">NPU ACCELERATION</span>
                <StatusIndicator
                  tone="not_connected"
                  label="Not Verified"
                  size="sm"
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">
                Hardware detection is truthful. QNN/NPU execution will be verified via real benchmark.
              </p>
            </div>

            {/* Memory */}
            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">MEMORY (MEMORA)</span>
                <StatusIndicator
                  tone={status?.indicators?.memory?.tone || (loading ? "loading" : "ready")}
                  label={status?.indicators?.memory?.status || "Local Storage Ready"}
                  size="sm"
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">
                SQLite local store active ({status?.memory_stats?.total_memories ?? recentMemories.length} saved). User-controlled.
              </p>
            </div>

            {/* Privacy */}
            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">PRIVACY PREFERENCE</span>
                <StatusIndicator
                  tone="ready"
                  label="Local Preference Enforced"
                  size="sm"
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">
                Persistent database preference. Zero telemetry, user permission required.
              </p>
            </div>

            {/* Network */}
            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">NETWORK</span>
                <StatusIndicator
                  tone="ready"
                  label="Not Required"
                  size="sm"
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">
                Local-first architecture operates air-gapped without cloud dependencies.
              </p>
            </div>
          </div>
        </section>

        {/* Product Workflow Pillars */}
        <section className="mt-10 rounded-3xl border border-white/10 bg-slate-900/40 p-8 backdrop-blur-sm">
          <h2 className="text-lg font-bold text-white mb-2">Multimodal Core Workflow</h2>
          <p className="text-sm text-slate-400 mb-6">
            The unified pipeline combining vision, reasoning, and private long-term memory:
          </p>

          <div className="grid gap-6 md:grid-cols-4">
            <div className="relative rounded-2xl border border-white/10 bg-slate-900/80 p-5">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <Eye className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-white text-base">1. SEE</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                DESKAI watches your physical workspace through local camera video or snapshot frames.
              </p>
            </div>

            <div className="relative rounded-2xl border border-white/10 bg-slate-900/80 p-5">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
                <Cpu className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-white text-base">2. UNDERSTAND</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Local object detection and OCR extract spatial parts, sensors, breadboards, notes, and text.
              </p>
            </div>

            <div className="relative rounded-2xl border border-white/10 bg-slate-900/80 p-5">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
                <Brain className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-white text-base">3. REMEMBER</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                MEMORA preserves explicit project records, components, and notes into private local SQLite.
              </p>
            </div>

            <div className="relative rounded-2xl border border-white/10 bg-slate-900/80 p-5">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Compass className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-white text-base">4. RETRIEVE</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Ask SENTINEL combines current camera scene with past memories to answer contextual queries.
              </p>
            </div>
          </div>
        </section>

        {/* Quick Recent Memory Section */}
        <section className="mt-10">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">Recent Saved Knowledge</h2>
            <Link
              href="/memory"
              className="inline-flex items-center gap-1 text-xs font-medium text-cyan-400 hover:text-cyan-300"
            >
              <span>View all memories</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {recentMemories.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 bg-slate-900/30 p-8 text-center">
              <Brain className="mx-auto h-8 w-8 text-slate-600 mb-2" />
              <p className="text-sm text-slate-300 font-medium">No saved memories yet</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Explicitly save hardware projects, workspace setups, or notes to build your private local knowledge base.
              </p>
              <Link
                href="/memory"
                className="mt-4 inline-flex items-center gap-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 px-4 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 transition"
              >
                <PlusCircle className="h-3.5 w-3.5" />
                <span>Create First Memory</span>
              </Link>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-3">
              {recentMemories.map((mem) => (
                <div
                  key={mem.id}
                  className="rounded-2xl border border-white/10 bg-slate-900/60 p-5 hover:border-cyan-500/30 transition flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-slate-300">
                        {mem.category}
                      </span>
                      <span className="text-[11px] text-slate-500">
                        {new Date(mem.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <h3 className="font-semibold text-white text-sm line-clamp-1">{mem.title}</h3>
                    <p className="mt-2 text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {mem.content}
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Source: {mem.source_type}</span>
                    {mem.project_name && <span className="text-cyan-400/80">{mem.project_name}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-white/10 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="mx-auto max-w-7xl px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>SENTINEL • Privacy-First Multimodal AI for Snapdragon Windows PCs</p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <Shield className="h-3.5 w-3.5" /> Local Execution Preferred
            </span>
            <span className="flex items-center gap-1.5 text-slate-400">
              <Lock className="h-3.5 w-3.5" /> No Cloud Uploads
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
