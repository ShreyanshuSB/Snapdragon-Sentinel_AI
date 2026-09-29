"use client";

import React, { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  Brain,
  Camera,
  ChevronDown,
  ChevronUp,
  Clock,
  Cpu,
  FileText,
  Folder,
  Layers,
  Mic,
  Paperclip,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  User,
  X,
} from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { VoiceAssistantModal } from "@/components/VoiceAssistantModal";
import { api } from "@/lib/api";
import {
  ChatMessage,
  Conversation,
  GroundingAction,
  Memory,
  Project,
  SourceAttribution,
} from "@/lib/types";

function ChatContent() {
  const searchParams = useSearchParams();
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConvId, setCurrentConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Multimodal Context State
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [selectedMemoryIds, setSelectedMemoryIds] = useState<number[]>([]);
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const [attachedFileName, setAttachedFileName] = useState<string | null>(null);
  const [attachedFileId, setAttachedFileId] = useState<string | null>(null);
  const [attachedDocId, setAttachedDocId] = useState<string | null>(null);
  const [attachedDocPage, setAttachedDocPage] = useState<number | null>(null);
  const [showMemoryPicker, setShowMemoryPicker] = useState(false);

  // Accordion state for message source inspection
  const [expandedSources, setExpandedSources] = useState<Record<number, boolean>>({});

  // Voice modal state
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);

  // Competition DEMO / SIMULATION mode state (Step 7)
  const [isDemoMode, setIsDemoMode] = useState(false);

  // 1. Initial Load & URL Parameter Ingestion (Sections 25, 26, 27)

  useEffect(() => {
    let isMounted = true;
    async function loadInitial() {
      try {
        const [convs, mems, projs] = await Promise.all([
          api.getConversations(),
          api.getMemories(),
          api.getProjects(),
        ]);
        if (!isMounted) return;
        setConversations(convs);
        setMemories(mems);
        setProjects(projs);

        // Check search params from Vision, Documents, or Memory navigation
        const pImageId = searchParams.get("image_id");
        const pDocId = searchParams.get("document_id");
        const pPage = searchParams.get("page");
        const pMemoryId = searchParams.get("memory_id");
        const pProjId = searchParams.get("project_id");

        if (pImageId) {
          setAttachedFileId(pImageId);
          setAttachedFileName(`Vision Image: ${pImageId.slice(0, 8)}...`);
        }
        if (pDocId) {
          setAttachedDocId(pDocId);
          const pageNum = pPage ? parseInt(pPage, 10) : 1;
          setAttachedDocPage(pageNum);
          setAttachedFileName(`Document ${pDocId} (p. ${pageNum})`);
        }
        if (pMemoryId) {
          const memIdNum = parseInt(pMemoryId, 10);
          if (!isNaN(memIdNum)) {
            setSelectedMemoryIds([memIdNum]);
          }
        }
        if (pProjId) {
          const projIdNum = parseInt(pProjId, 10);
          if (!isNaN(projIdNum)) {
            setSelectedProjectId(projIdNum);
          }
        }

        if (convs.length > 0) {
          const firstId = convs[0].id;
          setCurrentConvId(firstId);
          const msgs = await api.getConversationMessages(firstId);
          if (isMounted) setMessages(msgs);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load chat workspace.";
          setError(msg);
        }
      }
    }
    loadInitial();
    return () => {
      isMounted = false;
    };
  }, [searchParams]);

  const selectConversation = async (convId: number) => {
    setCurrentConvId(convId);
    setError(null);
    try {
      const msgs = await api.getConversationMessages(convId);
      setMessages(msgs);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load conversation messages.";
      setError(msg);
    }
  };

  const startNewChat = async () => {
    try {
      const newConv = await api.createConversation("New Workspace Session");
      setConversations([newConv, ...conversations]);
      setCurrentConvId(newConv.id);
      setMessages([]);
      setSelectedMemoryIds([]);
      setAttachedImage(null);
      setAttachedFileName(null);
      setAttachedFileId(null);
      setAttachedDocId(null);
      setAttachedDocPage(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create new conversation.";
      setError(msg);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const toggleSources = (msgId: number) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || loading) return;

    const userText = inputText.trim();
    setInputText("");
    setLoading(true);
    setError(null);

    // Build context
    const memoryContextStrings = memories
      .filter((m) => selectedMemoryIds.includes(m.id))
      .map((m) => `${m.title}: ${m.content}`);

    const contextStrings = [...memoryContextStrings];
    if (attachedFileName) {
      contextStrings.push(`Attached Reference: ${attachedFileName}`);
    }

    // Optimistically show user message
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      conversation_id: currentConvId || 0,
      role: "user",
      content: userText,
      metadata: {
        memory_context: memoryContextStrings,
        has_image: Boolean(attachedImage || attachedFileId),
        project_id: selectedProjectId,
      },
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await api.sendChatMessage({
        conversation_id: currentConvId || undefined,
        text: userText,
        project_id: selectedProjectId,
        image_id: attachedFileId || undefined,
        image_context: attachedImage || undefined,
        document_id: attachedDocId || undefined,
        page_number: attachedDocPage || undefined,
        memory_id: selectedMemoryIds.length === 1 ? selectedMemoryIds[0] : undefined,
        context: contextStrings,
        memory_context: memoryContextStrings,
        mode: isDemoMode ? "demo" : "live",
      });

      if (!currentConvId) {
        setCurrentConvId(response.conversation_id);
      }

      const asstMsg: ChatMessage = {
        id: response.assistant_message_id || Date.now() + 1,
        conversation_id: response.conversation_id,
        role: "assistant",
        content: response.answer || response.response,
        metadata: {
          ...response.metadata,
          sources: response.sources || response.metadata?.sources,
          context_used: response.context_used || response.metadata?.context_summary,
          timing: response.timing || response.metadata?.timing,
          action: response.action || response.metadata?.action,
          mode: response.mode || response.metadata?.mode,
          model: response.model,
          runtime: response.runtime,
          verification: response.verification,
          status: response.status,
        },
        created_at: response.created_at,
      };


      setMessages((prev) => [...prev, asstMsg]);

      // Clear one-time context attachments
      setAttachedImage(null);
      setAttachedFileName(null);
      setAttachedFileId(null);
      setAttachedDocId(null);
      setAttachedDocPage(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to generate grounded AI response.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const uploadRes = await api.uploadFile(file, {
        conversation_id: currentConvId || undefined,
      });
      setAttachedFileId(uploadRes.file_id);
      setAttachedFileName(uploadRes.file_name);

      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (event) => {
          setAttachedImage(event.target?.result as string);
        };
        reader.readAsDataURL(file);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload file.";
      setError(msg);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 flex flex-col">
        {/* Top Header */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-md border border-cyan-500/30 bg-cyan-950/40 px-2 py-0.5 text-xs font-semibold text-cyan-300">
                MULTIMODAL REASONING
              </span>
              <span className="text-xs text-slate-500">Step 4 — Vision • OCR • Memory • Grounded Retrieval</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Ask SENTINEL
            </h1>
          </div>

          <div className="flex items-center gap-2">
            {/* Mode Selector (Step 7 - Live vs Demo) */}
            <button
              type="button"
              onClick={() => setIsDemoMode(!isDemoMode)}
              className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
                isDemoMode
                  ? "border-amber-500/50 bg-amber-950/40 text-amber-300"
                  : "border-white/10 bg-slate-900/80 text-slate-400 hover:text-white"
              }`}
              title="Toggle reproducible competition DEMO / SIMULATION mode"
            >
              <Sparkles className="h-3.5 w-3.5 text-amber-400" />
              <span>{isDemoMode ? "DEMO / SIMULATION" : "LIVE MODE"}</span>
            </button>

            {/* Project Filter Selector (Section 22) */}
            <div className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-slate-900/80 px-2.5 py-1.5 text-xs">
              <Folder className="h-3.5 w-3.5 text-cyan-400" />
              <select
                aria-label="Project Scope Filter"
                value={selectedProjectId || ""}
                onChange={(e) => setSelectedProjectId(e.target.value ? parseInt(e.target.value, 10) : null)}
                className="bg-transparent text-xs text-slate-300 focus:outline-none"
              >
                <option value="" className="bg-slate-900 text-slate-300">All Projects</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id} className="bg-slate-900 text-slate-200">
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={startNewChat}
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-3.5 py-2 text-xs font-semibold text-slate-950 shadow-[0_0_12px_rgba(6,182,212,0.3)] hover:bg-cyan-300 transition"
            >
              <Plus className="h-4 w-4" />
              <span>New Session</span>
            </button>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mb-4 flex items-center justify-between rounded-xl border border-rose-500/30 bg-rose-950/20 p-3 text-xs text-rose-300">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-rose-400" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-white">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Chat Layout: Left Sessions Sidebar, Right Messages Area */}
        <div className="grid flex-1 gap-6 lg:grid-cols-[260px_1fr] min-h-[580px]">
          {/* SESSIONS SIDEBAR */}
          <div className="hidden lg:flex flex-col rounded-3xl border border-white/10 bg-slate-900/60 p-4 backdrop-blur-xl">
            <div className="mb-3 flex items-center justify-between px-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Workspace Sessions
              </span>
              <span className="text-[11px] text-slate-500 font-mono">{conversations.length}</span>
            </div>

            <div className="flex-1 space-y-1 overflow-y-auto">
              {conversations.map((conv) => {
                const isActive = currentConvId === conv.id;
                return (
                  <button
                    key={conv.id}
                    onClick={() => selectConversation(conv.id)}
                    className={`w-full text-left rounded-xl px-3 py-2.5 text-xs transition flex flex-col gap-1 ${
                      isActive
                        ? "border border-cyan-500/30 bg-cyan-950/40 text-cyan-200"
                        : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                    }`}
                  >
                    <span className="font-medium truncate text-white">{conv.title}</span>
                    <span className="text-[10px] text-slate-500">
                      {new Date(conv.updated_at).toLocaleDateString()}
                    </span>
                  </button>
                );
              })}

              {conversations.length === 0 && (
                <div className="py-6 text-center text-xs text-slate-500">
                  No sessions yet.
                </div>
              )}
            </div>
          </div>

          {/* MAIN CHAT CONSOLE */}
          <div className="flex flex-col rounded-3xl border border-white/10 bg-slate-900/60 backdrop-blur-xl overflow-hidden">
            {/* Context Attachment Bar */}
            <div className="border-b border-white/10 bg-slate-900/80 px-4 py-2.5 flex flex-wrap items-center gap-2 text-xs">
              <span className="text-slate-400 font-medium flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                Active Context:
              </span>

              {/* Memory references pill */}
              <button
                type="button"
                onClick={() => setShowMemoryPicker(!showMemoryPicker)}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition ${
                  selectedMemoryIds.length > 0
                    ? "border-purple-500/40 bg-purple-950/30 text-purple-300"
                    : "border-white/10 bg-white/5 text-slate-400 hover:text-white"
                }`}
              >
                <Brain className="h-3 w-3" />
                <span>
                  {selectedMemoryIds.length > 0
                    ? `${selectedMemoryIds.length} Memories Linked`
                    : "Attach Memory"}
                </span>
              </button>

              {/* Attached file/image indicator */}
              {attachedFileName && (
                <div className="inline-flex items-center gap-1 rounded-lg border border-cyan-500/30 bg-cyan-950/40 px-2.5 py-1 text-xs text-cyan-300">
                  <Camera className="h-3 w-3" />
                  <span className="truncate max-w-[150px]">{attachedFileName}</span>
                  <button
                    onClick={() => {
                      setAttachedImage(null);
                      setAttachedFileName(null);
                      setAttachedFileId(null);
                      setAttachedDocId(null);
                      setAttachedDocPage(null);
                    }}
                    className="ml-1 text-cyan-400 hover:text-white"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )}

              {/* Active Project Filter pill */}
              {selectedProjectId && (
                <div className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/30 bg-emerald-950/40 px-2.5 py-1 text-xs text-emerald-300">
                  <Folder className="h-3 w-3" />
                  <span>Project: {projects.find((p) => p.id === selectedProjectId)?.name || selectedProjectId}</span>
                  <button
                    onClick={() => setSelectedProjectId(null)}
                    className="ml-1 text-emerald-400 hover:text-white"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )}
            </div>

            {/* Memory Drawer Selection */}
            {showMemoryPicker && (
              <div className="border-b border-white/10 bg-slate-950/90 p-4 animate-in slide-in-from-top-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-300">
                    Select local memories to include in multimodal reasoning:
                  </span>
                  <button
                    onClick={() => setShowMemoryPicker(false)}
                    className="text-xs text-slate-500 hover:text-white"
                  >
                    Done
                  </button>
                </div>

                <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto pt-1">
                  {memories.map((m) => {
                    const isSelected = selectedMemoryIds.includes(m.id);
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => {
                          if (isSelected) {
                            setSelectedMemoryIds(selectedMemoryIds.filter((id) => id !== m.id));
                          } else {
                            setSelectedMemoryIds([...selectedMemoryIds, m.id]);
                          }
                        }}
                        className={`rounded-lg border px-2.5 py-1 text-xs transition ${
                          isSelected
                            ? "border-purple-400 bg-purple-900/40 text-purple-200"
                            : "border-white/10 bg-slate-900 text-slate-400 hover:text-white"
                        }`}
                      >
                        {m.title}
                      </button>
                    );
                  })}
                  {memories.length === 0 && (
                    <span className="text-xs text-slate-500">No memories saved yet.</span>
                  )}
                </div>
              </div>
            )}

            {/* MESSAGE STREAM */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full py-16 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-500/20 bg-cyan-500/10 text-cyan-400 mb-3">
                    <Sparkles className="h-6 w-6" />
                  </div>
                  <h3 className="text-base font-semibold text-white">Ask SENTINEL Anything</h3>
                  <p className="mt-1 text-xs text-slate-400 max-w-md">
                    Ask questions about your physical workspace, hardware components, circuit wiring, or saved project notes.
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {[
                      "What am I working on?",
                      "What sensor did I use for my temperature project?",
                      "What resistor does the sensor circuit require?",
                    ].map((example) => (
                      <button
                        key={example}
                        onClick={() => setInputText(example)}
                        className="rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 hover:border-cyan-400/40 hover:text-cyan-300 transition"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg) => {
                  const isUser = msg.role === "user";
                  const sources: SourceAttribution[] = Array.isArray(msg.metadata?.sources)
                    ? (msg.metadata?.sources as SourceAttribution[])
                    : [];
                  const contextSummary = msg.metadata?.context_used as Record<string, unknown> | undefined;
                  const timing = msg.metadata?.timing as Record<string, unknown> | undefined;
                  const isSourcesOpen = Boolean(expandedSources[msg.id]);

                  return (
                    <div
                      key={msg.id}
                      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
                    >
                      {!isUser && (
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                          <Cpu className="h-4 w-4" />
                        </div>
                      )}

                      <div
                        className={`max-w-[85%] sm:max-w-[80%] rounded-2xl p-4 text-xs leading-relaxed ${
                          isUser
                            ? "bg-cyan-500/15 border border-cyan-500/30 text-white"
                            : "bg-slate-900 border border-white/10 text-slate-200"
                        }`}
                      >
                        {/* Context Used Badges (Section 24) */}
                        {!isUser && contextSummary && (
                          <div className="mb-2 pb-2 border-b border-white/5 flex flex-wrap items-center gap-2 text-[10px] text-slate-400">
                            <span className="font-mono text-cyan-300">Context:</span>
                            {Number(contextSummary.vision_count || 0) > 0 && (
                              <span className="inline-flex items-center gap-1 rounded bg-cyan-950/60 px-1.5 py-0.5 text-cyan-300 border border-cyan-500/20">
                                <Camera className="h-2.5 w-2.5" />
                                {String(contextSummary.vision_count)} Objects
                              </span>
                            )}
                            {Number(contextSummary.ocr_count || 0) > 0 && (
                              <span className="inline-flex items-center gap-1 rounded bg-amber-950/60 px-1.5 py-0.5 text-amber-300 border border-amber-500/20">
                                <FileText className="h-2.5 w-2.5" />
                                {String(contextSummary.ocr_count)} OCR Regions
                              </span>
                            )}
                            {Number(contextSummary.memory_count || 0) > 0 && (
                              <span className="inline-flex items-center gap-1 rounded bg-purple-950/60 px-1.5 py-0.5 text-purple-300 border border-purple-500/20">
                                <Brain className="h-2.5 w-2.5" />
                                {String(contextSummary.memory_count)} Memories
                              </span>
                            )}
                            {Number(contextSummary.document_count || 0) > 0 && (
                              <span className="inline-flex items-center gap-1 rounded bg-blue-950/60 px-1.5 py-0.5 text-blue-300 border border-blue-500/20">
                                <Layers className="h-2.5 w-2.5" />
                                {String(contextSummary.document_count)} Docs
                              </span>
                            )}
                          </div>
                        )}

                        {/* Answer Text */}
                        <p className="whitespace-pre-wrap leading-relaxed text-sm text-slate-100">{msg.content}</p>

                        {/* Structured Grounding Action Card (Step 7) */}
                        {!isUser && Boolean(msg.metadata?.action) && (
                          (() => {
                            const act = msg.metadata?.action as GroundingAction;
                            if (!act || act.action === "NONE") return null;
                            return (
                              <div className="mt-3 rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <div className="flex items-center gap-2">
                                    <span className="relative flex h-2 w-2">
                                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                                      <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
                                    </span>
                                    <span className="font-semibold text-cyan-300">
                                      Grounding: {act.label || act.action}
                                    </span>
                                    {act.zone && (
                                      <span className="rounded bg-cyan-900/50 px-1.5 py-0.5 text-[10px] font-mono uppercase text-cyan-300 border border-cyan-500/20">
                                        {act.zone}
                                      </span>
                                    )}
                                  </div>
                                  {act.action === "HIGHLIGHT_OBJECT" && (
                                    <a
                                      href={`/vision?highlight=${act.target_id || ""}`}
                                      className="inline-flex items-center gap-1 rounded-lg bg-cyan-500/20 px-2.5 py-1 text-xs font-medium text-cyan-200 border border-cyan-500/40 hover:bg-cyan-500/30 transition"
                                    >
                                      Show on Workspace Vision &rarr;
                                    </a>
                                  )}
                                  {act.action === "OPEN_DOCUMENT" && (
                                    <a
                                      href={`/documents?id=${act.document_id || ""}&page=${act.page || 1}`}
                                      className="inline-flex items-center gap-1 rounded-lg bg-blue-500/20 px-2.5 py-1 text-xs font-medium text-blue-200 border border-blue-500/40 hover:bg-blue-500/30 transition"
                                    >
                                      Open Document &rarr;
                                    </a>
                                  )}
                                  {act.action === "OPEN_MEMORY" && (
                                    <a
                                      href={`/memory?id=${act.memory_id || ""}`}
                                      className="inline-flex items-center gap-1 rounded-lg bg-purple-500/20 px-2.5 py-1 text-xs font-medium text-purple-200 border border-purple-500/40 hover:bg-purple-500/30 transition"
                                    >
                                      View in Memory &rarr;
                                    </a>
                                  )}
                                  {act.action === "OPEN_VISION" && (
                                    <a
                                      href="/vision"
                                      className="inline-flex items-center gap-1 rounded-lg bg-cyan-500/20 px-2.5 py-1 text-xs font-medium text-cyan-200 border border-cyan-500/40 hover:bg-cyan-500/30 transition"
                                    >
                                      Open Vision Workspace &rarr;
                                    </a>
                                  )}
                                </div>
                                {act.description && (
                                  <p className="mt-1 text-[11px] text-slate-400">{act.description}</p>
                                )}
                              </div>
                            );
                          })()
                        )}


                        {/* Expandable Sources Section (Section 15, 24) */}
                        {!isUser && sources.length > 0 && (
                          <div className="mt-3 pt-2.5 border-t border-white/5">
                            <button
                              type="button"
                              onClick={() => toggleSources(msg.id)}
                              className="flex items-center justify-between w-full text-[11px] font-semibold text-cyan-300 hover:text-cyan-200 transition"
                            >
                              <div className="flex items-center gap-1.5">
                                <ShieldCheck className="h-3 w-3 text-cyan-400" />
                                <span>Grounded Sources ({sources.length})</span>
                              </div>
                              {isSourcesOpen ? (
                                <ChevronUp className="h-3.5 w-3.5" />
                              ) : (
                                <ChevronDown className="h-3.5 w-3.5" />
                              )}
                            </button>

                            {isSourcesOpen && (
                              <div className="mt-2 space-y-1.5 pt-1 animate-in fade-in-50">
                                {sources.map((s, idx) => {
                                  const badgeColor =
                                    s.type === "MEMORY"
                                      ? "border-purple-500/30 bg-purple-950/40 text-purple-300"
                                      : s.type === "DOCUMENT"
                                      ? "border-blue-500/30 bg-blue-950/40 text-blue-300"
                                      : s.type === "OCR"
                                      ? "border-amber-500/30 bg-amber-950/40 text-amber-300"
                                      : "border-cyan-500/30 bg-cyan-950/40 text-cyan-300";

                                  return (
                                    <div
                                      key={idx}
                                      className="rounded-lg border border-white/5 bg-slate-950/60 p-2 text-[11px]"
                                    >
                                      <div className="flex items-center justify-between gap-2">
                                        <div className="flex items-center gap-1.5 font-medium">
                                          <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono border ${badgeColor}`}>
                                            {s.type}
                                          </span>
                                          <span className="text-slate-200 font-semibold">{s.title}</span>
                                          {s.page && (
                                            <span className="text-[10px] text-slate-400">p.{s.page}</span>
                                          )}
                                        </div>
                                        {s.score !== undefined && s.score !== null && (
                                          <span className="text-[10px] font-mono text-cyan-400">
                                            rel: {s.score.toFixed(2)}
                                          </span>
                                        )}
                                      </div>
                                      {s.snippet && (
                                        <p className="mt-1 text-[11px] text-slate-400 italic line-clamp-2">
                                          &ldquo;{s.snippet}&rdquo;
                                        </p>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Latency and Model Metadata Footer */}
                        {!isUser && timing && (
                          <div className="mt-2.5 pt-2 border-t border-white/5 flex flex-wrap items-center justify-between text-[10px] text-slate-500 font-mono">
                            <span className="flex items-center gap-1">
                              <Clock className="h-2.5 w-2.5" />
                              Total: {Number(timing.total_ms || 0).toFixed(0)}ms (ret: {Number(timing.retrieval_ms || 0).toFixed(0)}ms, gen: {Number(timing.generation_ms || 0).toFixed(0)}ms)
                            </span>
                            <span className="text-slate-400">
                              Host CPU • Snapdragon Target
                            </span>
                          </div>
                        )}
                      </div>

                      {isUser && (
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-800 border border-slate-700 text-slate-300">
                          <User className="h-4 w-4" />
                        </div>
                      )}
                    </div>
                  );
                })
              )}

              {loading && (
                <div className="flex gap-3 justify-start">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                    <Cpu className="h-4 w-4 animate-spin" />
                  </div>
                  <div className="rounded-2xl bg-slate-900 border border-white/10 p-4 text-xs text-slate-400 flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
                    <span>Retrieving multimodal evidence & reasoning...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* INPUT CONTROLS */}
            <form onSubmit={handleSendMessage} className="p-4 border-t border-white/10 bg-slate-950/70">
              <div className="flex items-center gap-2">
                {/* File / Camera Snapshot attach */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp,application/pdf,text/plain"
                  className="hidden"
                  onChange={handleFileUpload}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition"
                  title="Attach workspace photo or document"
                >
                  <Paperclip className="h-4 w-4" />
                </button>

                {/* Voice Input via Local Whisper STT */}
                <button
                  type="button"
                  onClick={() => setIsVoiceModalOpen(true)}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-500/40 bg-cyan-950/40 text-cyan-300 hover:text-white hover:bg-cyan-900/50 transition shadow-[0_0_12px_rgba(6,182,212,0.15)]"
                  title="Ask by Voice (Local Whisper STT)"
                >
                  <Mic className="h-4 w-4" />
                </button>

                {/* Prompt Text input */}
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Ask SENTINEL about your workspace, components, or memory..."
                  className="flex-1 rounded-xl border border-white/10 bg-slate-900 px-4 py-2.5 text-xs text-white placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none"
                />

                {/* Send */}
                <button
                  type="submit"
                  disabled={!inputText.trim() || loading}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-400 text-slate-950 font-bold hover:bg-cyan-300 transition disabled:opacity-40"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </form>
          </div>
        </div>
      </main>

      {/* Voice Assistant Modal */}
      <VoiceAssistantModal
        isOpen={isVoiceModalOpen}
        onClose={() => setIsVoiceModalOpen(false)}
        onActionComplete={(act) => {
          if (act.raw_query) {
            setInputText(act.raw_query);
          }
        }}
      />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 text-xs">Loading Ask SENTINEL...</div>}>
      <ChatContent />
    </Suspense>
  );
}
