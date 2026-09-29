"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  CloudOff,
  Cpu,
  Database,
  HardDrive,
  Mic,
  Shield,
  ShieldCheck,
  X,
} from "lucide-react";
import { ConfirmationModal } from "@/components/ConfirmationModal";
import { Navbar } from "@/components/Navbar";
import { api } from "@/lib/api";
import { MemoryStats, PrivacyPolicy } from "@/lib/types";

export default function SettingsPage() {
  const [policy, setPolicy] = useState<PrivacyPolicy | null>(null);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modals
  const [isViewDataOpen, setIsViewDataOpen] = useState(false);
  const [isDeleteAllOpen, setIsDeleteAllOpen] = useState(false);
  const [isClearCacheOpen, setIsClearCacheOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function fetchData() {
      try {
        const [pol, st, models] = await Promise.all([
          api.getPrivacy(),
          api.getMemoryStats(),
          api.getModelStatus().catch(() => null),
        ]);
        if (isMounted) {
          setPolicy(pol);
          setStats(st);
          if (models) setModelStatus(models);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load privacy policy.";
          setError(msg);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }
    fetchData();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleToggle = async <K extends keyof PrivacyPolicy>(key: K, value: PrivacyPolicy[K]) => {
    if (!policy) return;
    setSaving(true);
    setSuccessMsg(null);
    setError(null);
    try {
      const updated = await api.updatePrivacy({ [key]: value });
      setPolicy(updated);
      setSuccessMsg(`Setting '${key}' updated and saved to persistent database.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to update ${key}.`;
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAllMemories = async () => {
    try {
      const res = await api.deleteAllMemories();
      setIsDeleteAllOpen(false);
      setSuccessMsg(`All ${res.deleted_count} memories deleted from local storage.`);
      const st = await api.getMemoryStats();
      setStats(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete memories.";
      setError(msg);
    }
  };

  const handleClearCache = () => {
    localStorage.clear();
    setIsClearCacheOpen(false);
    setSuccessMsg("Local client cache and cached session state cleared.");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />

      <main className="flex-1 mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2">
            <span className="rounded-md border border-cyan-500/30 bg-cyan-950/40 px-2 py-0.5 text-xs font-semibold text-cyan-300">
              Privacy Architecture
            </span>
            <span className="text-xs text-slate-500">Security & Storage Governance</span>
          </div>
          <h1 className="mt-1 text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Privacy & System Settings
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            SENTINEL preferences are stored in the local SQLite database. Preferences operate in harmony with your browser and OS device permissions.
          </p>
        </div>

        {/* Notices */}
        {error && (
          <div className="mb-6 flex items-center justify-between rounded-xl border border-rose-500/30 bg-rose-950/20 p-4 text-xs text-rose-300">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-rose-400" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-white">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {successMsg && (
          <div className="mb-6 flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-xs text-emerald-300">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>{successMsg}</span>
            </div>
            <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* SECTION 1: PERMISSION & CAPABILITY TOGGLES */}
        <div className="space-y-6">
          <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-cyan-400" />
              <span>Hardware & Ingestion Controls</span>
            </h2>

            <div className="divide-y divide-white/5 space-y-4">
              {/* Camera Access */}
              <div className="flex items-center justify-between pt-4">
                <div className="flex items-start gap-3">
                  <Camera className="h-5 w-5 text-cyan-400 mt-0.5 shrink-0" />
                  <div>
                    <h3 className="font-semibold text-white text-sm">Physical Workspace Camera Preference</h3>
                    <p className="text-xs text-slate-400">
                      Allow SENTINEL to access physical camera stream when on Vision page. Browser permission is also required.
                    </p>
                  </div>
                </div>

                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={policy?.camera_enabled ?? false}
                    onChange={(e) => handleToggle("camera_enabled", e.target.checked)}
                    className="sr-only peer"
                    disabled={saving}
                  />
                  <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-500" />
                </label>
              </div>

              {/* Microphone Access */}
              <div className="flex items-center justify-between pt-4">
                <div className="flex items-start gap-3">
                  <Mic className="h-5 w-5 text-blue-400 mt-0.5 shrink-0" />
                  <div>
                    <h3 className="font-semibold text-white text-sm">Microphone Input Preference</h3>
                    <p className="text-xs text-slate-400">
                      Enable microphone capture for future on-device speech transcription. Browser permission is also required.
                    </p>
                  </div>
                </div>

                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={policy?.microphone_enabled ?? false}
                    onChange={(e) => handleToggle("microphone_enabled", e.target.checked)}
                    className="sr-only peer"
                    disabled={saving}
                  />
                  <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-500" />
                </label>
              </div>

              {/* Persistent Memory */}
              <div className="flex items-center justify-between pt-4">
                <div className="flex items-start gap-3">
                  <Database className="h-5 w-5 text-purple-400 mt-0.5 shrink-0" />
                  <div>
                    <h3 className="font-semibold text-white text-sm">Persistent Local Memory</h3>
                    <p className="text-xs text-slate-400">
                      When enabled, explicitly requested memories are committed to local SQLite. If disabled, new saves are blocked.
                    </p>
                  </div>
                </div>

                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={policy?.memory_enabled ?? true}
                    onChange={(e) => handleToggle("memory_enabled", e.target.checked)}
                    className="sr-only peer"
                    disabled={saving}
                  />
                  <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-500" />
                </label>
              </div>

              {/* Local AI Policy & Model Connection Truthful Status */}
              <div className="flex items-center justify-between pt-4">
                <div className="flex items-start gap-3">
                  <Cpu className="h-5 w-5 text-emerald-400 mt-0.5 shrink-0" />
                  <div>
                    <h3 className="font-semibold text-white text-sm">Local AI Inference Execution</h3>
                    <p className="text-xs text-slate-400">
                      Policy targets Snapdragon NPU / GPU / CPU local execution without third-party cloud streaming.
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs font-semibold text-emerald-400">Policy: Local Execution Only</div>
                  <div className="text-[11px] text-slate-300 font-mono mt-0.5">
                    Vision: {modelStatus?.models?.vision?.name ? `${modelStatus.models.vision.name} (${modelStatus.models.vision.current_device || "Host CPU"})` : "YOLO-X Available"}
                  </div>
                  <div className="text-[10px] text-amber-400 font-mono">
                    NPU: {modelStatus?.models?.vision?.npu_verification === "VERIFIED" ? "Verified" : "Not Verified (Host Only)"}
                  </div>
                </div>
              </div>

              {/* Cloud Services */}
              <div className="flex items-center justify-between pt-4">
                <div className="flex items-start gap-3">
                  <CloudOff className="h-5 w-5 text-slate-500 mt-0.5 shrink-0" />
                  <div>
                    <h3 className="font-semibold text-white text-sm">Cloud AI Services</h3>
                    <p className="text-xs text-slate-400">
                      External cloud inference APIs. Kept strictly disabled by default for privacy preservation.
                    </p>
                  </div>
                </div>

                <span className="rounded-full border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-400">
                  Disabled
                </span>
              </div>
            </div>
          </div>

          {/* SECTION 2: PRIVACY ASSURANCE DECLARATION */}
          <div className="rounded-3xl border border-cyan-500/20 bg-gradient-to-r from-slate-900/90 to-cyan-950/20 p-6 backdrop-blur-xl">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-cyan-300 mb-2 flex items-center gap-2">
              <Shield className="h-4 w-4" />
              <span>Core Privacy Principles</span>
            </h2>
            <ul className="space-y-2 text-xs text-slate-300 leading-relaxed">
              <li className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                <span><strong>No surveillance:</strong> SENTINEL does not perform facial recognition or emotional profiling.</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                <span><strong>Explicit memory:</strong> No automatic secret logging; memories are only created with explicit user intent.</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                <span><strong>Accurate transparency:</strong> The system is designed for local-first execution and never claims unverified acceleration.</span>
              </li>
            </ul>
          </div>

          {/* SECTION 3: DATA MANAGEMENT */}
          <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
              <HardDrive className="h-4 w-4 text-amber-400" />
              <span>Local Data Management</span>
            </h2>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => setIsViewDataOpen(true)}
                className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-xs font-semibold text-slate-200 hover:bg-white/10 transition"
              >
                View Stored Data Info
              </button>

              <button
                type="button"
                onClick={() => setIsClearCacheOpen(true)}
                className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-xs font-semibold text-slate-200 hover:bg-white/10 transition"
              >
                Clear Client Cache
              </button>

              <button
                type="button"
                onClick={() => setIsDeleteAllOpen(true)}
                className="rounded-xl border border-rose-500/30 bg-rose-600/20 px-4 py-2.5 text-xs font-semibold text-rose-300 hover:bg-rose-600/30 transition"
              >
                Delete All Memories
              </button>
            </div>
          </div>
        </div>

        {/* VIEW DATA INFO MODAL */}
        {isViewDataOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
            <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl">
              <button onClick={() => setIsViewDataOpen(false)} className="absolute right-4 top-4 text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>

              <div className="flex items-center gap-2 mb-4">
                <Database className="h-5 w-5 text-cyan-400" />
                <h3 className="text-lg font-bold text-white">Stored Local Knowledge Info</h3>
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 flex justify-between">
                  <span className="text-slate-400">Database Engine:</span>
                  <span className="font-mono text-white">SQLite 3 (Alembic Migrated)</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 flex justify-between">
                  <span className="text-slate-400">Database Location:</span>
                  <span className="font-mono text-cyan-300">backend/sentinel.db</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 flex justify-between">
                  <span className="text-slate-400">Total Memories:</span>
                  <span className="font-mono text-white font-bold">{stats?.total_memories || 0}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 flex justify-between">
                  <span className="text-slate-400">Projects Tracked:</span>
                  <span className="font-mono text-white font-bold">{stats?.project_count || 0}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 flex justify-between">
                  <span className="text-slate-400">Uploads Directory:</span>
                  <span className="font-mono text-slate-300">data/uploads</span>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  type="button"
                  onClick={() => setIsViewDataOpen(false)}
                  className="rounded-xl bg-cyan-400 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* CLEAR CACHE CONFIRMATION */}
        <ConfirmationModal
          isOpen={isClearCacheOpen}
          title="Clear Client Session Cache?"
          message="This will clear temporary client session storage and reset uncommitted visual drafts. Your persistent SQLite memories will NOT be affected."
          confirmLabel="Clear Cache"
          cancelLabel="Cancel"
          isDestructive={false}
          onConfirm={handleClearCache}
          onClose={() => setIsClearCacheOpen(false)}
        />

        {/* DELETE ALL MEMORIES CONFIRMATION */}
        <ConfirmationModal
          isOpen={isDeleteAllOpen}
          title="Delete all local memories?"
          message="WARNING: This will permanently wipe all stored memories, project associations, and attachments from the local SQLite database. This action is irreversible."
          confirmLabel="Permanently Delete All"
          cancelLabel="Cancel"
          isDestructive={true}
          onConfirm={handleDeleteAllMemories}
          onClose={() => setIsDeleteAllOpen(false)}
        />
      </main>
    </div>
  );
}
