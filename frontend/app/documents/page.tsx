"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Copy,
  FileCode,
  FileSearch,
  FileText,
  HardDrive,
  Search,
  Upload,
  Trash2,
  Loader2,
  MessageSquare,
} from "lucide-react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { ConfirmationModal } from "@/components/ConfirmationModal";
import { TextOverlay } from "@/components/TextOverlay";
import { api } from "@/lib/api";
import {
  DocumentPageResponse,
  DocumentResponse,
  DocumentSearchHit,
} from "@/lib/types";

export default function DocumentsPage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Loading & status lifecycle: "LOADING" | "READY" | "EMPTY" | "ERROR"
  const [loadingState, setLoadingState] = useState<"LOADING" | "READY" | "EMPTY" | "ERROR">("LOADING");

  // Document list & selection
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentResponse | null>(null);
  const [selectedDocPages, setSelectedDocPages] = useState<DocumentPageResponse[]>([]);
  const [activePageIndex, setActivePageIndex] = useState<number>(0);
  const [selectedRegionIdx, setSelectedRegionIdx] = useState<number | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<DocumentSearchHit[] | null>(null);
  const [searching, setSearching] = useState(false);

  // Ingestion & status
  const [uploading, setUploading] = useState(false);
  const [copiedText, setCopiedText] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Deletion modal
  const [docToDelete, setDocToDelete] = useState<DocumentResponse | null>(null);

  const loadDocumentDetails = async (documentId: string) => {
    try {
      const [doc, pages] = await Promise.all([
        api.getDocument(documentId),
        api.getDocumentPages(documentId),
      ]);
      setSelectedDoc(doc);
      setSelectedDocPages(pages);
      setActivePageIndex(0);
      setSelectedRegionIdx(null);
    } catch {
      // Non-fatal if details fail to load for an individual doc
    }
  };

  const loadDocuments = async (autoSelectId?: string) => {
    try {
      const docs = await api.getDocuments();
      setDocuments(docs);
      setErrorMsg(null);

      if (docs.length === 0) {
        setLoadingState("EMPTY");
        setSelectedDoc(null);
        setSelectedDocPages([]);
      } else {
        setLoadingState("READY");
        const targetId = autoSelectId || selectedDoc?.document_id || docs[0].document_id;
        await loadDocumentDetails(targetId);
      }
    } catch {
      setErrorMsg("Failed to load documents from local storage.");
      setLoadingState("ERROR");
    }
  };

  useEffect(() => {
    let isMounted = true;
    async function init() {
      setLoadingState("LOADING");
      setErrorMsg(null);
      try {
        const docs = await api.getDocuments();
        if (!isMounted) return;
        setDocuments(docs);
        if (docs.length === 0) {
          setLoadingState("EMPTY");
        } else {
          setLoadingState("READY");
          try {
            const firstId = docs[0].document_id;
            const [firstDoc, pages] = await Promise.all([
              api.getDocument(firstId),
              api.getDocumentPages(firstId),
            ]);
            if (isMounted) {
              setSelectedDoc(firstDoc);
              setSelectedDocPages(pages);
              setActivePageIndex(0);
            }
          } catch {
            // Details load failed, list is still valid
          }
        }
      } catch {
        if (isMounted) {
          setErrorMsg("Failed to load documents from local storage.");
          setLoadingState("ERROR");
        }
      }
    }
    void init();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setErrorMsg(null);
    setFeedbackMsg(`Processing "${file.name}" locally...`);

    try {
      const newDoc = await api.uploadDocument(file);
      setFeedbackMsg(
        `Document processed locally: ${newDoc.page_count} page(s) via ${newDoc.extraction_method.toUpperCase()}.`
      );
      await loadDocuments(newDoc.document_id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to process document.";
      setErrorMsg(msg);
      setFeedbackMsg(null);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }

    setSearching(true);
    setErrorMsg(null);
    try {
      const res = await api.searchDocuments(searchQuery.trim());
      setSearchResults(res.results);
      const matchCount = res.total_hits ?? res.total_matches ?? res.results.length;
      setFeedbackMsg(`Found ${matchCount} match(es) across local documents.`);
    } catch {
      setErrorMsg("Keyword search failed.");
    } finally {
      setSearching(false);
    }
  };

  const handleDelete = async () => {
    if (!docToDelete) return;
    try {
      await api.deleteDocument(docToDelete.document_id);
      setFeedbackMsg(`Deleted document "${docToDelete.file_name}" and its associated pages.`);
      const deletedId = docToDelete.document_id;
      setDocToDelete(null);
      if (selectedDoc?.document_id === deletedId) {
        setSelectedDoc(null);
        setSelectedDocPages([]);
      }
      await loadDocuments();
    } catch {
      setErrorMsg("Failed to delete document.");
    }
  };

  const copyPageText = () => {
    const curPage = selectedDocPages[activePageIndex];
    const textToCopy = curPage?.text || curPage?.text_content;
    if (!textToCopy) return;
    navigator.clipboard.writeText(textToCopy);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  const activePage = selectedDocPages[activePageIndex];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
        {/* Top Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-md border border-amber-500/30 bg-amber-950/40 px-2 py-0.5 text-xs font-semibold text-amber-300">
                Phase 2 — Document Intelligence
              </span>
              <span className="text-xs text-slate-500">Local-Only Text & Scanned PDF Pipeline</span>
            </div>
            <h1 className="mt-1 text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Document Intelligence & Local Search
            </h1>
            <p className="mt-1 text-xs text-slate-400">
              Direct text extraction for native documents; local OCR for scanned pages. 100% private and on-device.
            </p>
          </div>

          {/* Upload Button */}
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md,.csv,image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={handleFileUpload}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 px-5 py-2.5 text-xs font-semibold text-slate-950 shadow-[0_0_15px_rgba(245,158,11,0.3)] hover:opacity-95 transition disabled:opacity-50"
            >
              <Upload className={`h-4 w-4 ${uploading ? "animate-spin" : ""}`} />
              <span>{uploading ? "Processing Locally..." : "Upload Document"}</span>
            </button>
          </div>
        </div>

        {/* Notices */}
        {errorMsg && loadingState === "ERROR" && (
          <div className="mb-6 flex items-start gap-3 rounded-2xl border border-rose-500/30 bg-rose-950/30 p-4 text-sm text-rose-300">
            <AlertCircle className="h-5 w-5 shrink-0 text-rose-400 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium text-rose-200">Notice</p>
              <p className="mt-1 text-xs text-rose-300">{errorMsg}</p>
            </div>
          </div>
        )}

        {feedbackMsg && (
          <div className="mb-6 flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-950/30 px-4 py-2.5 text-xs text-amber-300">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-amber-400" />
            <span>{feedbackMsg}</span>
          </div>
        )}

        {/* Search Bar */}
        <div className="mb-6">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search across all ingested documents (e.g. DHT11, ESP32, resistor, pinout)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-slate-900/80 pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-amber-400 focus:outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={searching}
              className="rounded-xl border border-amber-500/30 bg-amber-950/40 px-5 py-2.5 text-xs font-semibold text-amber-300 hover:bg-amber-900/40 transition"
            >
              {searching ? "Searching..." : "Search"}
            </button>
            {searchResults && (
              <button
                type="button"
                onClick={() => {
                  setSearchResults(null);
                  setSearchQuery("");
                }}
                className="rounded-xl border border-white/10 px-3 py-2.5 text-xs text-slate-400 hover:text-white"
              >
                Clear
              </button>
            )}
          </form>

          {/* Search Hits List */}
          {searchResults && (
            <div className="mt-3 rounded-2xl border border-amber-500/20 bg-slate-900/80 p-4 space-y-2">
              <div className="text-xs font-semibold text-amber-300 flex items-center justify-between pb-2 border-b border-white/5">
                <span>Search Matches ({searchResults.length})</span>
                <span className="text-[10px] text-slate-400 font-mono">Full-Text Keyword Search</span>
              </div>
              {searchResults.length === 0 ? (
                <p className="text-xs text-slate-400 py-2">No matching text found across documents.</p>
              ) : (
                searchResults.map((hit, i) => (
                  <div
                    key={`${hit.document_id}-${hit.page_number ?? 1}-${i}`}
                    onClick={() => {
                      loadDocumentDetails(hit.document_id);
                      if (hit.page_number) {
                        setActivePageIndex(Math.max(0, hit.page_number - 1));
                      }
                    }}
                    className="p-3 rounded-xl border border-white/5 bg-slate-950/60 hover:border-amber-400/50 cursor-pointer transition text-xs"
                  >
                    <div className="flex items-center justify-between mb-1 text-[11px] font-mono">
                      <span className="font-semibold text-white">{hit.file_name}</span>
                      <span className="rounded bg-amber-500/10 px-2 py-0.5 text-amber-300">
                        Page {hit.page_number ?? 1} ({hit.source_type})
                      </span>
                    </div>
                    <p className="text-slate-300 font-mono text-[11px] leading-relaxed">
                      &quot;{hit.snippet}&quot;
                    </p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* 2-Column Layout: Left Documents List / Right Document Inspector */}
        <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
          {/* LEFT: Documents List */}
          <div className="flex flex-col rounded-3xl border border-white/10 bg-slate-900/60 p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-white/5">
              <div className="flex items-center gap-2">
                <HardDrive className="h-4 w-4 text-amber-400" />
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Local Documents ({documents.length})
                </h2>
              </div>
            </div>

            {loadingState === "LOADING" ? (
              <div className="py-12 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
                <Loader2 className="h-6 w-6 animate-spin text-amber-400" />
                <p>Loading documents from local storage...</p>
              </div>
            ) : documents.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No documents uploaded yet.</p>
                <p className="text-[11px] text-slate-600 mt-1">Upload a PDF or TXT file to begin.</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
                {documents.map((doc) => {
                  const isSelected = selectedDoc?.document_id === doc.document_id;
                  return (
                    <div
                      key={doc.document_id}
                      onClick={() => loadDocumentDetails(doc.document_id)}
                      className={`p-3 rounded-2xl border transition cursor-pointer flex flex-col gap-1.5 text-xs ${
                        isSelected
                          ? "border-amber-400 bg-amber-950/30 shadow-[0_0_15px_rgba(245,158,11,0.15)]"
                          : "border-white/5 bg-slate-950/60 hover:bg-slate-950/90"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-white truncate max-w-[180px]">
                          {doc.file_name}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDocToDelete(doc);
                          }}
                          className="text-slate-500 hover:text-rose-400 transition p-1"
                          title="Delete document"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                        <span>{doc.page_count} page(s)</span>
                        <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 text-amber-300">
                          {doc.extraction_method.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* RIGHT: Document Inspector & Page Viewer */}
          <div className="flex flex-col rounded-3xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl">
            {selectedDoc ? (
              <div className="flex flex-col h-full">
                {/* Document Header Metadata */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 mb-4 border-b border-white/5">
                  <div>
                    <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                      <FileCode className="h-4 w-4 text-amber-400" />
                      <span>{selectedDoc.file_name}</span>
                    </h2>
                    <div className="mt-1 flex items-center gap-3 text-[11px] font-mono text-slate-400">
                      <span>Pages: {selectedDoc.page_count}</span>
                      <span>Extraction: {selectedDoc.extraction_method.toUpperCase()}</span>
                      <span>Processing: {selectedDoc.processing_time_ms ? selectedDoc.processing_time_ms.toFixed(1) : 0} ms</span>
                      <span className="text-amber-400">Host CPU Verified</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Link
                      href={`/chat?document_id=${encodeURIComponent(selectedDoc.document_id)}&page=${activePage ? activePage.page_number : 1}`}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/40 bg-amber-950/40 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-900/40 hover:text-white transition shadow-[0_0_12px_rgba(245,158,11,0.2)]"
                    >
                      <MessageSquare className="h-3.5 w-3.5 text-amber-400" />
                      <span>Ask SENTINEL About This</span>
                    </Link>

                    {/* Page Navigation Controls */}
                    {selectedDocPages.length > 1 && (
                    <div className="flex items-center gap-2 text-xs font-mono">
                      <button
                        type="button"
                        onClick={() => setActivePageIndex(Math.max(0, activePageIndex - 1))}
                        disabled={activePageIndex === 0}
                        className="rounded-lg border border-white/10 bg-slate-950 p-1.5 text-slate-300 hover:text-white disabled:opacity-30"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                      <span className="text-slate-200">
                        Page {activePageIndex + 1} of {selectedDocPages.length}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          setActivePageIndex(
                            Math.min(selectedDocPages.length - 1, activePageIndex + 1)
                          )
                        }
                        disabled={activePageIndex === selectedDocPages.length - 1}
                        className="rounded-lg border border-white/10 bg-slate-950 p-1.5 text-slate-300 hover:text-white disabled:opacity-30"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                  </div>
                </div>

                {/* Page Details Body */}
                {activePage ? (
                  <div className="flex-1 flex flex-col gap-4">
                    {/* Page Sub-bar */}
                    <div className="flex items-center justify-between text-xs font-mono text-slate-400 pb-2 border-b border-white/5">
                      <span>
                        Source: Page {activePage.page_number} • Method:{" "}
                        {(activePage.extraction_method || selectedDoc.extraction_method).toUpperCase()}
                      </span>
                      {(activePage.processing_time_ms || activePage.total_ms) && (
                        <span>Page Ingest Time: {activePage.processing_time_ms || activePage.total_ms} ms</span>
                      )}
                    </div>

                    {/* OCR Bounding Boxes Overlay (if scanned page with OCR regions) */}
                    {((activePage.regions && activePage.regions.length > 0) || (activePage.text_regions && activePage.text_regions.length > 0)) && (
                      <div className="mb-2">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[11px] font-bold text-amber-300 uppercase tracking-wider font-mono">
                            OCR Regions ({(activePage.regions || activePage.text_regions)?.length})
                          </span>
                        </div>
                        <TextOverlay
                          regions={(activePage.regions || activePage.text_regions)!}
                          selectedIndex={selectedRegionIdx}
                          onSelect={(idx) => setSelectedRegionIdx(idx)}
                          className="min-h-[140px]"
                        />
                      </div>
                    )}

                    {/* Extracted Text Content */}
                    <div className="flex-1 flex flex-col rounded-2xl border border-white/5 bg-slate-950/80 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs uppercase font-bold text-slate-400 font-mono">
                          Extracted Page Text
                        </span>
                        <button
                          type="button"
                          onClick={copyPageText}
                          className="flex items-center gap-1.5 text-xs text-amber-300 hover:text-amber-200 transition"
                        >
                          <Copy className="h-3.5 w-3.5" />
                          <span>{copiedText ? "Copied!" : "Copy Text"}</span>
                        </button>
                      </div>

                      <div className="flex-1 max-h-[380px] overflow-y-auto pr-1">
                        <pre className="text-xs text-slate-200 font-mono whitespace-pre-wrap leading-relaxed">
                          {activePage.text || activePage.text_content || "No extractable text found on this page."}
                        </pre>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="py-12 text-center text-xs text-slate-500">
                    <p>No page content available.</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-slate-500">
                <FileSearch className="h-10 w-10 mb-3 opacity-40" />
                <p className="text-sm font-semibold text-slate-300">Select a document to inspect</p>
                <p className="text-xs text-slate-500 mt-1 max-w-sm">
                  Choose a document from the left panel or upload a new PDF / text document.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Confirmation Modal for Document Deletion */}
      <ConfirmationModal
        isOpen={docToDelete !== null}
        title="Delete Document"
        message={`Are you sure you want to delete "${docToDelete?.file_name}"? All extracted page records and OCR metadata will be removed from local storage. Original memory entries will not be deleted.`}
        confirmLabel="Delete Document"
        isDestructive={true}
        onConfirm={handleDelete}
        onClose={() => setDocToDelete(null)}
      />
    </div>
  );
}
