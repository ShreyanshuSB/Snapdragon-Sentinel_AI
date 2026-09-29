"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  Brain,
  CheckCircle2,
  Clock,
  Compass,
  Edit3,
  Eye,
  FileText,
  Filter,
  FolderPlus,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  X,
  MessageSquare,
} from "lucide-react";
import Link from "next/link";
import { ConfirmationModal } from "@/components/ConfirmationModal";
import { Navbar } from "@/components/Navbar";
import { api } from "@/lib/api";
import { Memory, MemoryStats, Project, RetrievalResult } from "@/lib/types";

const CATEGORIES = ["All", "Projects", "Notes", "Documents", "Objects", "Conversations"];
const SEARCH_MODES = [
  { id: "HYBRID", label: "Hybrid Search (Recommended)", desc: "Semantic + Keyword + Project context" },
  { id: "SEMANTIC", label: "Semantic Search", desc: "Dense vector cosine similarity" },
  { id: "KEYWORD", label: "Keyword Match", desc: "Lexical token overlap" },
];

export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [searchTerm, setSearchTerm] = useState("");
  const [searchMode, setSearchMode] = useState<"HYBRID" | "SEMANTIC" | "KEYWORD">("HYBRID");
  const [searchResults, setSearchResults] = useState<RetrievalResult[] | null>(null);
  const [searchMeta, setSearchMeta] = useState<{ query: string; took_ms: number; query_embed_ms: number } | null>(null);

  const [loading, setLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modals state
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isViewOpen, setIsViewOpen] = useState(false);
  const [activeMemory, setActiveMemory] = useState<Memory | null>(null);

  // Duplicate Check Modal State
  const [duplicateWarning, setDuplicateWarning] = useState<{
    title: string;
    similarity: number;
    existingId?: number | null;
  } | null>(null);

  // Delete confirmations
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [isDeleteAllOpen, setIsDeleteAllOpen] = useState(false);

  // Form states
  const [formTitle, setFormTitle] = useState("");
  const [formContent, setFormContent] = useState("");
  const [formCategory, setFormCategory] = useState("note");
  const [formSource, setFormSource] = useState("USER_NOTE");
  const [formProjectId, setFormProjectId] = useState<number | "">("");

  // New Project modal state
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const [mems, projs, st] = await Promise.all([
        api.getMemories({
          category: selectedCategory === "All" ? undefined : selectedCategory.toLowerCase(),
          search: undefined, // Standard list fetches all; search is executed via hybrid search
        }),
        api.getProjects(),
        api.getMemoryStats(),
      ]);
      setMemories(mems);
      setProjects(projs);
      setStats(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load local memories.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = searchTerm.trim();
    if (!q) {
      setSearchResults(null);
      setSearchMeta(null);
      return;
    }

    setIsSearching(true);
    setError(null);
    try {
      const res = await api.searchMemories({
        query: q,
        search_mode: searchMode,
        top_k: 12,
        category: selectedCategory === "All" ? undefined : selectedCategory.toLowerCase(),
        include_documents: true,
      });

      setSearchResults(res.results);
      setSearchMeta({
        query: res.query,
        took_ms: res.total_ms || res.took_ms || 0,
        query_embed_ms: res.query_embed_ms || res.embedding_ms || 0,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Search failed.";
      setError(msg);
    } finally {
      setIsSearching(false);
    }
  };

  const handleClearSearch = () => {
    setSearchTerm("");
    setSearchResults(null);
    setSearchMeta(null);
    fetchData();
  };

  const resetForm = () => {
    setFormTitle("");
    setFormContent("");
    setFormCategory("note");
    setFormSource("USER_NOTE");
    setFormProjectId("");
    setActiveMemory(null);
    setDuplicateWarning(null);
  };

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim() || !formContent.trim()) return;

    try {
      // 1. Run Duplicate check first
      const dupCheck = await api.checkDuplicateMemory({
        title: formTitle.trim(),
        content: formContent.trim(),
        project_id: formProjectId === "" ? null : Number(formProjectId),
        threshold: 0.85,
      });

      if (dupCheck.is_duplicate) {
        setDuplicateWarning({
          title: dupCheck.existing_title || "Existing Memory",
          similarity: dupCheck.similarity,
          existingId: dupCheck.existing_memory_id,
        });
        return;
      }

      await saveMemoryConfirmed();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save memory.";
      setError(msg);
    }
  };

  const saveMemoryConfirmed = async () => {
    try {
      await api.createMemory({
        title: formTitle.trim(),
        content: formContent.trim(),
        category: formCategory.toLowerCase(),
        source_type: formSource,
        project_id: formProjectId === "" ? null : Number(formProjectId),
      });

      setIsAddOpen(false);
      resetForm();
      setSuccessMsg("Memory saved and semantically indexed into private SQLite store.");
      fetchData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save memory.";
      setError(msg);
    }
  };

  const handleUpdateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeMemory) return;

    try {
      await api.updateMemory(activeMemory.id, {
        title: formTitle.trim(),
        content: formContent.trim(),
        category: formCategory.toLowerCase(),
        source_type: formSource,
        project_id: formProjectId === "" ? null : Number(formProjectId),
      });

      setIsEditOpen(false);
      resetForm();
      setSuccessMsg("Memory updated and vector refreshed.");
      fetchData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update memory.";
      setError(msg);
    }
  };

  const handleReindex = async () => {
    setIsReindexing(true);
    setError(null);
    try {
      const res = await api.reindexMemories(true, true);
      setSuccessMsg(`Index rebuilt: ${res.memories_indexed ?? res.memories_reindexed ?? 0} memories & ${res.chunks_indexed ?? res.document_chunks_reindexed ?? 0} chunks reindexed in ${res.duration_ms.toFixed(1)} ms.`);
      fetchData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reindex semantic store.";
      setError(msg);
    } finally {
      setIsReindexing(false);
    }
  };

  const handleDeleteSingle = async () => {
    if (!deleteTargetId) return;
    try {
      await api.deleteMemory(deleteTargetId);
      setDeleteTargetId(null);
      setSuccessMsg("Memory deleted from local disk.");
      fetchData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete memory.";
      setError(msg);
    }
  };

  const handleDeleteAll = async () => {
    try {
      const res = await api.deleteAllMemories();
      setIsDeleteAllOpen(false);
      setSuccessMsg(`All ${res.deleted_count} local memories have been purged.`);
      fetchData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to purge local memories.";
      setError(msg);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      await api.createProject({
        name: newProjectName.trim(),
        description: newProjectDesc.trim() || undefined,
      });
      setIsNewProjectOpen(false);
      setNewProjectName("");
      setNewProjectDesc("");
      setSuccessMsg("New project workspace created.");
      const projs = await api.getProjects();
      setProjects(projs);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create project.";
      setError(msg);
    }
  };

  const openEdit = (mem: Memory) => {
    setActiveMemory(mem);
    setFormTitle(mem.title);
    setFormContent(mem.content);
    setFormCategory(mem.category);
    setFormSource(mem.source_type);
    setFormProjectId(mem.project_id || "");
    setIsEditOpen(true);
  };

  const openView = (mem: Memory) => {
    setActiveMemory(mem);
    setIsViewOpen(true);
  };

  const renderEmbeddingStatusBadge = (status?: string) => {
    const s = (status || "PENDING").toUpperCase();
    if (s === "READY") {
      return (
        <span className="rounded-md border border-emerald-500/30 bg-emerald-950/40 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 font-mono flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          READY
        </span>
      );
    }
    if (s === "STALE") {
      return (
        <span className="rounded-md border border-cyan-500/30 bg-cyan-950/40 px-2 py-0.5 text-[10px] font-semibold text-cyan-400 font-mono flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
          STALE
        </span>
      );
    }
    if (s === "FAILED") {
      return (
        <span className="rounded-md border border-rose-500/30 bg-rose-950/40 px-2 py-0.5 text-[10px] font-semibold text-rose-400 font-mono flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
          FAILED
        </span>
      );
    }
    return (
      <span className="rounded-md border border-amber-500/30 bg-amber-950/40 px-2 py-0.5 text-[10px] font-semibold text-amber-400 font-mono flex items-center gap-1">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
        PENDING
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
        {/* Top Header */}
        <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-md border border-cyan-500/30 bg-cyan-950/40 px-2 py-0.5 text-xs font-semibold text-cyan-300">
                MEMORA Local Semantic Memory
              </span>
              <span className="text-xs text-slate-500 font-mono">384-d Dense Cosine Retrieval</span>
            </div>
            <h1 className="mt-1 text-2xl sm:text-3xl font-bold text-white tracking-tight">
              User-Controlled Memory & Semantic Retrieval
            </h1>
            <p className="mt-1 text-xs text-slate-400">
              Information only enters permanent memory by your explicit intent. Search operates across personal memories and source documents without blurring the two.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleReindex}
              disabled={isReindexing}
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5 text-xs font-semibold text-slate-300 hover:bg-white/10 transition disabled:opacity-50"
              title="Rebuild all memory and document chunk embeddings"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isReindexing ? "animate-spin text-cyan-400" : ""}`} />
              <span>{isReindexing ? "Reindexing..." : "Rebuild Index"}</span>
            </button>

            <button
              onClick={() => setIsNewProjectOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3.5 py-2.5 text-xs font-semibold text-slate-300 hover:bg-white/10 transition"
            >
              <FolderPlus className="h-4 w-4" />
              <span>New Project</span>
            </button>

            <button
              onClick={() => {
                resetForm();
                setIsAddOpen(true);
              }}
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2.5 text-xs font-semibold text-slate-950 shadow-[0_0_15px_rgba(6,182,212,0.3)] hover:bg-cyan-300 transition"
            >
              <Plus className="h-4 w-4" />
              <span>Add Memory</span>
            </button>
          </div>
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

        {/* Search Bar & Retrieval Mode Selector */}
        <div className="mb-6 rounded-2xl border border-white/10 bg-slate-900/60 p-4 space-y-4">
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Ask a question or search: 'What sensor did I use?', 'circuit regulator', 'badminton tension'..."
                className="w-full rounded-xl border border-white/10 bg-slate-950 pl-10 pr-10 py-2.5 text-xs text-slate-200 placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            <button
              type="submit"
              disabled={isSearching}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 px-5 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition disabled:opacity-50"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>{isSearching ? "Searching..." : "Retrieve"}</span>
            </button>
          </form>

          {/* Search Mode Toggles & Category Filter */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-white/5 text-xs">
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
              <span className="text-slate-500 font-medium mr-1 flex items-center gap-1">
                <Compass className="h-3 w-3" /> Mode:
              </span>
              {SEARCH_MODES.map((mode) => {
                const active = searchMode === mode.id;
                return (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => setSearchMode(mode.id as "HYBRID" | "SEMANTIC" | "KEYWORD")}
                    className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition whitespace-nowrap ${
                      active
                        ? "border border-cyan-400/40 bg-cyan-500/15 text-cyan-300 shadow-[0_0_8px_rgba(6,182,212,0.15)]"
                        : "border border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/5"
                    }`}
                    title={mode.desc}
                  >
                    {mode.id === "HYBRID" ? "Hybrid" : mode.id === "SEMANTIC" ? "Semantic" : "Keyword"}
                  </button>
                );
              })}
            </div>

            {/* Category Tabs */}
            <div className="flex items-center gap-1 overflow-x-auto">
              <span className="text-slate-500 font-medium mr-1 flex items-center gap-1">
                <Filter className="h-3 w-3" /> Category:
              </span>
              {CATEGORIES.map((cat) => {
                const active = selectedCategory === cat;
                return (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition whitespace-nowrap ${
                      active
                        ? "bg-slate-800 text-white font-semibold"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {cat}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Stats Row */}
        {stats && (
          <div className="mb-8 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3 flex items-center justify-between">
              <span className="text-slate-400">Total Memories:</span>
              <span className="font-semibold text-white font-mono">{stats.total_memories}</span>
            </div>
            <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3 flex items-center justify-between">
              <span className="text-slate-400">Active Projects:</span>
              <span className="font-semibold text-cyan-300 font-mono">{stats.project_count}</span>
            </div>
            <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3 flex items-center justify-between">
              <span className="text-slate-400">Storage Engine:</span>
              <span className="font-semibold text-emerald-300">{stats.storage_type}</span>
            </div>
            <div className="rounded-xl border border-white/10 bg-slate-900/60 p-3 flex items-center justify-between">
              <span className="text-slate-400">Retention:</span>
              <span className="font-semibold text-slate-300">Local Only</span>
            </div>
          </div>
        )}

        {/* SEMANTIC RETRIEVAL RESULTS VIEW */}
        {searchResults !== null && (
          <div className="mb-10 rounded-3xl border border-cyan-500/30 bg-cyan-950/10 p-6 backdrop-blur-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-cyan-500/20">
              <div>
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-cyan-400" />
                  <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                    Ranked Retrieval Evidence ({searchResults.length} {searchResults.length === 1 ? "Hit" : "Hits"})
                  </h2>
                </div>
                {searchMeta && (
                  <p className="mt-1 text-[11px] text-slate-400 font-mono">
                    Query: &quot;{searchMeta.query}&quot; • Search latency: {searchMeta.took_ms.toFixed(1)} ms • Query embed: {searchMeta.query_embed_ms.toFixed(1)} ms
                  </p>
                )}
              </div>

              <button
                onClick={handleClearSearch}
                className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-white/10 transition"
              >
                <X className="h-3.5 w-3.5" />
                <span>Clear Results</span>
              </button>
            </div>

            {searchResults.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400">
                No matching memories or document excerpts found for this query. Try different terms or switch to Hybrid/Semantic mode.
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {searchResults.map((hit) => {
                  const isDoc = hit.result_type === "DOCUMENT" || hit.source_type === "DOCUMENT";
                  return (
                    <div
                      key={hit.id}
                      className="flex flex-col justify-between rounded-2xl border border-white/10 bg-slate-900/80 p-5 hover:border-cyan-400/40 transition shadow-lg"
                    >
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-3">
                          <span
                            className={`rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider border ${
                              isDoc
                                ? "border-purple-500/30 bg-purple-950/40 text-purple-300"
                                : "border-cyan-500/30 bg-cyan-950/40 text-cyan-300"
                            }`}
                          >
                            {isDoc ? "SOURCE DOCUMENT" : "PERSISTENT MEMORY"}
                          </span>

                          <span className="rounded-full bg-cyan-500/20 border border-cyan-400/30 px-2 py-0.5 text-[10px] font-bold text-cyan-300 font-mono">
                            {(hit.score * 100).toFixed(0)}% Match
                          </span>
                        </div>

                        <h3 className="font-bold text-white text-base line-clamp-1">
                          {hit.title}
                        </h3>

                        <p className="mt-2 text-xs text-slate-300 leading-relaxed line-clamp-3">
                          {hit.content}
                        </p>
                      </div>

                      <div className="mt-4 pt-3 border-t border-white/5 space-y-2">
                        {/* Why this matched tag */}
                        <div className="rounded-lg bg-slate-950/60 p-2 text-[10px] text-slate-400 flex items-start gap-1.5 border border-white/5">
                          <Sparkles className="h-3 w-3 text-cyan-400 shrink-0 mt-0.5" />
                          <span className="leading-tight">{hit.why_matched}</span>
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                          {isDoc && hit.page_number !== null ? (
                            <span className="text-purple-300 text-[10px] font-mono">Page {hit.page_number}</span>
                          ) : hit.project_name ? (
                            <span className="text-cyan-300 text-[10px] font-mono">{hit.project_name}</span>
                          ) : (
                            <span className="text-slate-500 text-[10px]">No Project</span>
                          )}

                          <div className="flex items-center gap-2">
                            {hit.created_at && (
                              <span className="text-[10px] text-slate-500 font-mono">
                                {new Date(hit.created_at).toLocaleDateString()}
                              </span>
                            )}
                            <Link
                              href={isDoc ? `/chat?document_id=${encodeURIComponent(String(hit.source_id || hit.id))}&page=${hit.page_number || 1}` : `/chat?memory_id=${hit.id}`}
                              className="inline-flex items-center gap-1 rounded border border-cyan-500/30 bg-cyan-950/40 px-2 py-0.5 text-[10px] text-cyan-300 hover:text-white hover:bg-cyan-900/40 transition"
                              title="Ask SENTINEL about this"
                            >
                              <MessageSquare className="h-2.5 w-2.5" />
                              <span>Ask</span>
                            </Link>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* DEFAULT MEMORIES GRID */}
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Brain className="h-4 w-4 text-cyan-400" />
              <span>All Stored Memories ({memories.length})</span>
            </h2>
          </div>

          {loading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  className="h-44 rounded-2xl border border-white/10 bg-slate-900/40 p-5 animate-pulse"
                />
              ))}
            </div>
          ) : memories.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-white/10 bg-slate-900/40 p-12 text-center">
              <Brain className="mx-auto h-12 w-12 text-slate-600 mb-3" />
              <h3 className="text-base font-semibold text-white">No memories found</h3>
              <p className="mt-1 text-xs text-slate-400 max-w-md mx-auto">
                Your local knowledge store is empty. Add a hardware project, schematic note, or workspace reference.
              </p>
              <button
                onClick={() => {
                  resetForm();
                  setIsAddOpen(true);
                }}
                className="mt-5 inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition"
              >
                <Plus className="h-4 w-4" />
                <span>Add Memory</span>
              </button>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {memories.map((mem) => (
                <div
                  key={mem.id}
                  className="group flex flex-col justify-between rounded-2xl border border-white/10 bg-slate-900/60 p-5 hover:border-cyan-500/30 hover:bg-slate-900/80 transition shadow-lg"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-1.5">
                        <span className="rounded-md border border-slate-700 bg-slate-800/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-cyan-300">
                          {mem.category}
                        </span>
                        {renderEmbeddingStatusBadge(mem.embedding_status)}
                      </div>

                      <span className="text-[11px] text-slate-500 flex items-center gap-1 font-mono">
                        <Clock className="h-3 w-3" />
                        {new Date(mem.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    <h3 className="font-bold text-white text-base group-hover:text-cyan-200 transition line-clamp-1">
                      {mem.title}
                    </h3>

                    <p className="mt-2 text-xs text-slate-300 leading-relaxed line-clamp-3">
                      {mem.content}
                    </p>
                  </div>

                  <div className="mt-5 pt-3 border-t border-white/5">
                    <div className="flex items-center justify-between text-[11px] text-slate-400 mb-3">
                      <span className="capitalize">Source: {mem.source_type}</span>
                      {mem.project_name ? (
                        <span className="rounded bg-cyan-950/60 border border-cyan-800/50 px-1.5 py-0.5 text-cyan-300 text-[10px]">
                          {mem.project_name}
                        </span>
                      ) : (
                        <span className="text-slate-600">No Project</span>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-end gap-2 pt-1 border-t border-white/5">
                      <Link
                        href={`/chat?memory_id=${mem.id}`}
                        className="inline-flex items-center gap-1 rounded-lg border border-purple-500/30 bg-purple-950/40 px-2.5 py-1 text-[11px] text-purple-300 hover:text-white hover:bg-purple-900/40 transition"
                        title="Ask SENTINEL about this memory"
                      >
                        <MessageSquare className="h-3 w-3" />
                        <span>Ask</span>
                      </Link>

                      <button
                        onClick={() => openView(mem)}
                        className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-slate-300 hover:text-white hover:bg-white/10 transition"
                        title="Open full view"
                      >
                        <Eye className="h-3 w-3" />
                        <span>Open</span>
                      </button>

                      <button
                        onClick={() => openEdit(mem)}
                        className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-slate-300 hover:text-white hover:bg-white/10 transition"
                        title="Edit memory"
                      >
                        <Edit3 className="h-3 w-3" />
                        <span>Edit</span>
                      </button>

                      <button
                        onClick={() => setDeleteTargetId(mem.id)}
                        className="inline-flex items-center gap-1 rounded-lg border border-rose-500/20 bg-rose-500/10 px-2.5 py-1 text-[11px] text-rose-300 hover:bg-rose-500/20 transition"
                        title="Delete memory"
                      >
                        <Trash2 className="h-3 w-3" />
                        <span>Delete</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Purge Everything Danger Zone */}
        {memories.length > 0 && (
          <div className="mt-12 rounded-2xl border border-rose-500/20 bg-rose-950/10 p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-300">
                Data Management & Retention
              </h4>
              <p className="mt-1 text-xs text-slate-400">
                Purge all stored personal memories and embeddings from the local SQLite database. Source documents are preserved.
              </p>
            </div>
            <button
              onClick={() => setIsDeleteAllOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition whitespace-nowrap"
            >
              <Trash2 className="h-4 w-4" />
              <span>Purge All Memories</span>
            </button>
          </div>
        )}

        {/* ADD / EDIT MEMORY MODAL */}
        {(isAddOpen || isEditOpen) && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
            <div className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl">
              <button
                onClick={() => {
                  setIsAddOpen(false);
                  setIsEditOpen(false);
                  resetForm();
                }}
                className="absolute right-4 top-4 text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>

              <div className="flex items-center gap-2 mb-4">
                <Brain className="h-5 w-5 text-cyan-400" />
                <h3 className="text-lg font-bold text-white">
                  {isAddOpen ? "Add to Private Memory" : "Edit Local Memory"}
                </h3>
              </div>

              <form onSubmit={isAddOpen ? handleAddSubmit : handleUpdateMemory} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Title *</label>
                  <input
                    type="text"
                    required
                    value={formTitle}
                    onChange={(e) => setFormTitle(e.target.value)}
                    placeholder="e.g. Temperature Monitoring Project"
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2.5 text-xs text-white placeholder:text-slate-600 focus:border-cyan-400 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Content / Details *</label>
                  <textarea
                    required
                    rows={4}
                    value={formContent}
                    onChange={(e) => setFormContent(e.target.value)}
                    placeholder="Components used: ESP32 microcontroller, DHT11 temperature sensor, breadboard, jumper cables..."
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2.5 text-xs text-white placeholder:text-slate-600 focus:border-cyan-400 focus:outline-none leading-relaxed"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Category</label>
                    <select
                      value={formCategory}
                      onChange={(e) => setFormCategory(e.target.value)}
                      className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-400 focus:outline-none"
                    >
                      <option value="project">Project</option>
                      <option value="note">Note</option>
                      <option value="document">Document</option>
                      <option value="object">Object</option>
                      <option value="conversation">Conversation</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Source Type</label>
                    <select
                      value={formSource}
                      onChange={(e) => setFormSource(e.target.value)}
                      className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-400 focus:outline-none"
                    >
                      <option value="USER_NOTE">Manual Note</option>
                      <option value="VISION">Camera Vision</option>
                      <option value="CONVERSATION">Conversation Excerpt</option>
                      <option value="DOCUMENT">Document Note</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Associate with Project (Optional)
                  </label>
                  <select
                    value={formProjectId}
                    onChange={(e) => setFormProjectId(e.target.value === "" ? "" : Number(e.target.value))}
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white focus:border-cyan-400 focus:outline-none"
                  >
                    <option value="">None (Standalone)</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mt-6 flex items-center justify-end gap-3 pt-3 border-t border-white/10">
                  <button
                    type="button"
                    onClick={() => {
                      setIsAddOpen(false);
                      setIsEditOpen(false);
                      resetForm();
                    }}
                    className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs text-slate-300 hover:bg-white/10"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="rounded-xl bg-cyan-400 px-5 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition"
                  >
                    {isAddOpen ? "Save to Memory" : "Save Changes"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* DUPLICATE WARNING MODAL (Section 28) */}
        {duplicateWarning && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
            <div className="relative w-full max-w-md rounded-2xl border border-amber-500/30 bg-slate-900 p-6 shadow-2xl">
              <div className="flex items-center gap-2 mb-3 text-amber-400">
                <AlertCircle className="h-5 w-5" />
                <h3 className="text-base font-bold text-white">Similar Memory Already Exists</h3>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed mb-4">
                A similar memory was detected: <span className="font-semibold text-white">&quot;{duplicateWarning.title}&quot;</span> with <span className="font-semibold text-amber-300 font-mono">{(duplicateWarning.similarity * 100).toFixed(1)}%</span> semantic similarity.
              </p>

              <div className="rounded-xl border border-white/5 bg-slate-950 p-3 text-[11px] text-slate-400 mb-6">
                SENTINEL never silently deletes or overwrites existing records. You may save this as an additional memory or cancel.
              </div>

              <div className="flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setDuplicateWarning(null)}
                  className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs text-slate-300 hover:bg-white/10"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    setDuplicateWarning(null);
                    await saveMemoryConfirmed();
                  }}
                  className="rounded-xl bg-amber-400 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-amber-300 transition"
                >
                  Keep Both (Save Anyway)
                </button>
              </div>
            </div>
          </div>
        )}

        {/* VIEW DETAIL MODAL */}
        {isViewOpen && activeMemory && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
            <div className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl">
              <button onClick={() => setIsViewOpen(false)} className="absolute right-4 top-4 text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>

              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="rounded-md border border-cyan-500/30 bg-cyan-950/40 px-2 py-0.5 text-[10px] font-semibold uppercase text-cyan-300">
                    {activeMemory.category}
                  </span>
                  {activeMemory.project_name && (
                    <span className="text-xs text-slate-400">• Project: {activeMemory.project_name}</span>
                  )}
                </div>
                {renderEmbeddingStatusBadge(activeMemory.embedding_status)}
              </div>

              <h3 className="text-lg font-bold text-white mb-4">{activeMemory.title}</h3>

              <div className="rounded-xl border border-white/10 bg-slate-950 p-4 text-xs text-slate-200 leading-relaxed max-h-60 overflow-y-auto whitespace-pre-wrap">
                {activeMemory.content}
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] text-slate-400 bg-slate-950/40 p-3 rounded-xl border border-white/5 font-mono">
                <div>Source: <span className="text-white capitalize">{activeMemory.source_type}</span></div>
                <div>Storage: <span className="text-emerald-400">SQLite LargeBinary</span></div>
                <div>Vector: <span className="text-cyan-300">{activeMemory.embedding_dimension || 384}-d Float32</span></div>
                <div>Model: <span className="text-slate-300 truncate">{activeMemory.embedding_model || "SentenceTransformer"}</span></div>
              </div>

              <div className="mt-6 flex items-center justify-between">
                <button
                  onClick={() => {
                    setIsViewOpen(false);
                    setDeleteTargetId(activeMemory.id);
                  }}
                  className="inline-flex items-center gap-1.5 text-xs text-rose-400 hover:text-rose-300"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Delete Memory</span>
                </button>

                <button
                  onClick={() => {
                    setIsViewOpen(false);
                    openEdit(activeMemory);
                  }}
                  className="rounded-xl bg-cyan-400 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300"
                >
                  Edit Memory
                </button>
              </div>
            </div>
          </div>
        )}

        {/* CREATE PROJECT MODAL */}
        {isNewProjectOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
            <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl">
              <button onClick={() => setIsNewProjectOpen(false)} className="absolute right-4 top-4 text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>

              <div className="flex items-center gap-2 mb-4">
                <FolderPlus className="h-5 w-5 text-cyan-400" />
                <h3 className="text-lg font-bold text-white">Create Project Workspace</h3>
              </div>

              <form onSubmit={handleCreateProject} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Project Name *</label>
                  <input
                    type="text"
                    required
                    value={newProjectName}
                    onChange={(e) => setNewProjectName(e.target.value)}
                    placeholder="e.g. IoT Temperature Monitor"
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2.5 text-xs text-white placeholder:text-slate-600 focus:border-cyan-400 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                  <textarea
                    rows={3}
                    value={newProjectDesc}
                    onChange={(e) => setNewProjectDesc(e.target.value)}
                    placeholder="Workspace details, hardware components, and goals..."
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2.5 text-xs text-white placeholder:text-slate-600 focus:border-cyan-400 focus:outline-none"
                  />
                </div>

                <div className="mt-6 flex items-center justify-end gap-3 pt-3 border-t border-white/10">
                  <button
                    type="button"
                    onClick={() => setIsNewProjectOpen(false)}
                    className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs text-slate-300 hover:bg-white/10"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="rounded-xl bg-cyan-400 px-5 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition"
                  >
                    Create Project
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Single Memory Confirmation */}
        <ConfirmationModal
          isOpen={deleteTargetId !== null}
          title="Delete this memory?"
          message="Are you sure you want to remove this memory from your private local database? This action cannot be undone."
          confirmLabel="Delete Memory"
          cancelLabel="Keep Memory"
          isDestructive={true}
          onConfirm={handleDeleteSingle}
          onClose={() => setDeleteTargetId(null)}
        />

        {/* Delete All Memories Confirmation */}
        <ConfirmationModal
          isOpen={isDeleteAllOpen}
          title="Delete all local memories?"
          message="WARNING: This will permanently delete all stored memories, project attachments, and knowledge cards from your private local SQLite database. This action is irreversible."
          confirmLabel="Purge All Memories"
          cancelLabel="Cancel"
          isDestructive={true}
          onConfirm={handleDeleteAll}
          onClose={() => setIsDeleteAllOpen(false)}
        />
      </main>
    </div>
  );
}
