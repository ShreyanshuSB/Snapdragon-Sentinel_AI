import {
  Attachment,
  AttachmentUploadResponse,
  BenchmarkRecord,
  BenchmarkSummary,
  ChatMessage,
  ChatResponse,
  Conversation,
  FrameCaptureResponse,
  Memory,
  MemoryStats,
  MetadataValue,
  ModelStatusResponse,
  PrivacyPolicy,
  Project,
  SystemStatus,
  VisionResult,
  VisionPipelineStatus,
  FullDiagnosticsResponse,
  HardwareDiagnosticsResponse,
  ModelCandidateRecord,
  ModelSelectionResponse,
  RuntimeDiagnosticsResponse,
  FullOCRResult,
  OCRStatusResponse,
  DocumentResponse,
  DocumentPageResponse,
  DocumentSearchResponse,
  MemorySearchQuery,
  MemorySearchResponse,
  DuplicateCheckRequest,
  DuplicateCheckResponse,
  EmbeddingStatusResponse,
  MemoryEmbedResponse,
  ReindexResponse,
  ReasoningStatusResponse,
  FindItResponse,
  WorkspaceStateResponse,
  SpeechTranscribeRequest,
  SpeechTranscribeResponse,
  VoiceStatusResponse,
  VoiceBenchmarkResult,
  MicrophoneState,
  MultimodalQueryRequest,
  MultimodalQueryResponse,
} from "./types";


const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const isFormData = options?.body instanceof FormData;
    const headers: Record<string, string> = {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...((options?.headers as Record<string, string>) || {}),
    };

    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}`;
      try {
        const errJson = (await res.json()) as { detail?: string; message?: string };
        errorDetail = errJson.detail || errJson.message || errorDetail;
      } catch {
        const text = await res.text();
        if (text) errorDetail = text;
      }
      throw new Error(errorDetail);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof Error) {
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        throw new Error(
          "Backend service unreachable. Ensure SENTINEL backend is running on http://localhost:8000."
        );
      }
      throw err;
    }
    throw new Error("An unexpected error occurred while communicating with SENTINEL backend.");
  }
}

export const api = {
  // Health & Status
  async getHealth(): Promise<{ status: string; service: string }> {
    return request("/api/health");
  },

  async getStatus(): Promise<SystemStatus> {
    return request("/api/status");
  },

  // Privacy
  async getPrivacy(): Promise<PrivacyPolicy> {
    return request("/api/privacy");
  },

  async updatePrivacy(policy: Partial<PrivacyPolicy>): Promise<PrivacyPolicy> {
    return request("/api/privacy", {
      method: "PUT",
      body: JSON.stringify(policy),
    });
  },

  // Memory
  async getMemories(params?: {
    category?: string;
    search?: string;
    project_id?: number;
  }): Promise<Memory[]> {
    const query = new URLSearchParams();
    if (params?.category && params.category !== "all") query.set("category", params.category);
    if (params?.search) query.set("search", params.search);
    if (params?.project_id) query.set("project_id", params.project_id.toString());
    const qs = query.toString() ? `?${query.toString()}` : "";
    return request(`/api/memory${qs}`);
  },

  async getMemory(id: number): Promise<Memory> {
    return request(`/api/memory/${id}`);
  },

  async getMemoryStats(): Promise<MemoryStats> {
    return request("/api/memory/stats");
  },

  async createMemory(payload: {
    title: string;
    content: string;
    category?: string;
    source_type?: string;
    project_id?: number | null;
    metadata?: Record<string, MetadataValue>;
  }): Promise<Memory> {
    return request("/api/memory", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateMemory(
    id: number,
    payload: {
      title?: string;
      content?: string;
      category?: string;
      source_type?: string;
      project_id?: number | null;
    }
  ): Promise<Memory> {
    return request(`/api/memory/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async deleteMemory(id: number): Promise<{ status: string; message: string }> {
    return request(`/api/memory/${id}`, {
      method: "DELETE",
    });
  },

  async deleteAllMemories(): Promise<{ status: string; message: string; deleted_count: number }> {
    return request("/api/memory?confirm=true", {
      method: "DELETE",
    });
  },

  async searchMemories(payload: MemorySearchQuery): Promise<MemorySearchResponse> {
    return request("/api/memory/search", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async checkDuplicateMemory(payload: DuplicateCheckRequest): Promise<DuplicateCheckResponse> {
    return request("/api/memory/check-duplicate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getEmbeddingStatus(): Promise<EmbeddingStatusResponse> {
    return request("/api/memory/embedding-status");
  },

  async embedText(text: string): Promise<MemoryEmbedResponse> {
    return request("/api/memory/embed", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
  },

  async reindexMemories(force: boolean = false, includeDocuments: boolean = true): Promise<ReindexResponse> {
    return request(`/api/memory/reindex?force=${force}&include_documents=${includeDocuments}`, {
      method: "POST",
    });
  },

  // Projects
  async getProjects(): Promise<Project[]> {
    return request("/api/projects");
  },

  async createProject(payload: { name: string; description?: string }): Promise<Project> {
    return request("/api/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async deleteProject(id: number): Promise<{ status: string; message: string }> {
    return request(`/api/projects/${id}`, {
      method: "DELETE",
    });
  },

  // Chat & Multimodal Reasoning (Step 4)
  async sendChatMessage(payload: {
    conversation_id?: number;
    text: string;
    project_id?: number | null;
    image_id?: string | null;
    image_context?: string;
    document_id?: string | null;
    page_number?: number | null;
    memory_id?: number | null;
    context?: string[];
    memory_context?: string[];
    model?: string;
    mode?: string;
  }): Promise<ChatResponse> {
    return request("/api/chat", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },


  async getReasoningStatus(): Promise<ReasoningStatusResponse> {
    return request("/api/chat/reasoning-status");
  },

  async getConversations(): Promise<Conversation[]> {
    return request("/api/chat/conversations");
  },

  async createConversation(title?: string): Promise<Conversation> {
    return request("/api/chat/conversations", {
      method: "POST",
      body: JSON.stringify({ title: title || "New Workspace Chat" }),
    });
  },

  async getConversationMessages(conversationId: number): Promise<ChatMessage[]> {
    return request(`/api/chat/conversations/${conversationId}/messages`);
  },

  // Uploads & Attachments
  async uploadFile(
    file: File,
    options?: { memory_id?: number; conversation_id?: number }
  ): Promise<AttachmentUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    if (options?.memory_id !== undefined) {
      formData.append("memory_id", options.memory_id.toString());
    }
    if (options?.conversation_id !== undefined) {
      formData.append("conversation_id", options.conversation_id.toString());
    }
    return request("/api/files/upload", {
      method: "POST",
      body: formData,
    });
  },

  async getAttachments(params?: {
    memory_id?: number;
    conversation_id?: number;
  }): Promise<Attachment[]> {
    const query = new URLSearchParams();
    if (params?.memory_id !== undefined) query.set("memory_id", params.memory_id.toString());
    if (params?.conversation_id !== undefined) query.set("conversation_id", params.conversation_id.toString());
    const qs = query.toString() ? `?${query.toString()}` : "";
    return request(`/api/attachments${qs}`);
  },

  async getAttachment(fileId: string): Promise<Attachment> {
    return request(`/api/attachments/${fileId}`);
  },

  // Vision (Section 6, 8, 14, 20)
  async analyzeVision(payload?: {
    file_id?: string;
    image?: string;
    prompt?: string;
    confidence_threshold?: number;
    iou_threshold?: number;
  }): Promise<VisionResult> {
    return request("/api/vision/analyze", {
      method: "POST",
      body: JSON.stringify(payload || {}),
    });
  },

  async captureVisionFrame(imageBase64: string): Promise<FrameCaptureResponse> {
    return request("/api/vision/capture", {
      method: "POST",
      body: JSON.stringify({ image_base64: imageBase64 }),
    });
  },

  async getVisionModelStatus(): Promise<VisionPipelineStatus> {
    return request("/api/vision/model/status");
  },

  async loadVisionModel(): Promise<VisionPipelineStatus & { status: string; message: string }> {
    return request("/api/vision/model/load", {
      method: "POST",
    });
  },

  async unloadVisionModel(): Promise<VisionPipelineStatus & { status: string; message: string }> {
    return request("/api/vision/model/unload", {
      method: "POST",
    });
  },

  async runVisionBenchmark(params?: {
    file_id?: string;
    warmup?: number;
    runs?: number;
  }): Promise<BenchmarkRecord> {
    const qs = new URLSearchParams();
    if (params?.file_id) qs.set("file_id", params.file_id);
    if (params?.warmup !== undefined) qs.set("warmup", params.warmup.toString());
    if (params?.runs !== undefined) qs.set("runs", params.runs.toString());
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return request(`/api/vision/benchmark${query}`, {
      method: "POST",
    });
  },

  // AI Lab & Models
  async getModelStatus(): Promise<ModelStatusResponse> {
    return request("/api/models/status");
  },

  async getBenchmarks(): Promise<BenchmarkSummary> {
    return request("/api/benchmarks");
  },

  async runBenchmarkBaseline(): Promise<BenchmarkRecord> {
    return request("/api/benchmarks/run", {
      method: "POST",
    });
  },

  // Snapdragon Hardware & Runtime Diagnostics (Step 7)
  async getHardwareDiagnostics(): Promise<HardwareDiagnosticsResponse> {
    return request("/api/system/hardware");
  },

  async getRuntimeDiagnostics(): Promise<RuntimeDiagnosticsResponse> {
    return request("/api/system/runtime");
  },

  async getFullDiagnostics(): Promise<FullDiagnosticsResponse> {
    return request("/api/system/diagnostics");
  },

  async getEnvironmentReport(): Promise<{ report: string }> {
    return request("/api/system/environment-report");
  },

  async getModelCandidates(): Promise<ModelCandidateRecord[]> {
    return request("/api/models/candidates");
  },

  async getModelSelection(): Promise<ModelSelectionResponse> {
    return request("/api/models/selection");
  },

  // OCR & Document Intelligence (Step 9)
  async analyzeOCR(payload: {
    file_id?: string;
    image?: string;
    confidence_threshold?: number;
    languages?: string[];
  }): Promise<FullOCRResult> {
    return request("/api/ocr/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getOCRStatus(): Promise<OCRStatusResponse> {
    return request("/api/ocr/status");
  },

  async runOCRBenchmark(params?: {
    file_id?: string;
    warmup?: number;
    runs?: number;
  }): Promise<BenchmarkRecord> {
    const qs = new URLSearchParams();
    if (params?.file_id) qs.set("file_id", params.file_id);
    if (params?.warmup !== undefined) qs.set("warmup", params.warmup.toString());
    if (params?.runs !== undefined) qs.set("runs", params.runs.toString());
    const query = qs.toString() ? `?${qs.toString()}` : "";
    return request(`/api/ocr/benchmark${query}`, {
      method: "POST",
    });
  },

  async uploadDocument(file: File): Promise<DocumentResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const uploadRes = await request<AttachmentUploadResponse>("/api/files/upload", {
      method: "POST",
      body: formData,
    });
    return request<DocumentResponse>("/api/documents", {
      method: "POST",
      body: JSON.stringify({ file_id: uploadRes.file_id }),
    });
  },

  async getDocuments(): Promise<DocumentResponse[]> {
    return request("/api/documents");
  },

  async getDocument(id: string | number): Promise<DocumentResponse> {
    return request(`/api/documents/${id}`);
  },

  async getDocumentPages(id: string | number): Promise<DocumentPageResponse[]> {
    return request(`/api/documents/${id}/pages`);
  },

  async getDocumentText(id: string | number): Promise<{ document_id: string; file_name: string; text: string; page_count: number }> {
    return request(`/api/documents/${id}/text`);
  },

  async deleteDocument(id: string | number): Promise<{ status: string; message: string; document_id: string }> {
    return request(`/api/documents/${id}`, {
      method: "DELETE",
    });
  },

  async searchDocuments(query: string): Promise<DocumentSearchResponse> {
    const qs = new URLSearchParams({ q: query });
    return request(`/api/search/documents?${qs.toString()}`);
  },

  // Workspace Tracking & Find It (Step 5)
  async trackWorkspaceFrame(payload: {
    image?: string;
    file_id?: string;
    detections?: any[];
    ocr_results?: any[];
    project_id?: string;
    confidence_threshold?: number;
  }): Promise<WorkspaceStateResponse> {
    return request("/api/vision/track", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getWorkspaceState(): Promise<WorkspaceStateResponse> {
    return request("/api/workspace/state");
  },

  async queryFindIt(query: string, projectId?: string, targetLabel?: string): Promise<FindItResponse> {
    return request("/api/workspace/find", {
      method: "POST",
      body: JSON.stringify({ query, project_id: projectId, target_label: targetLabel }),
    });
  },

  async rememberWorkspaceObject(trackId: string, userLabel: string, projectId?: string): Promise<{ status: string; message: string; track_id: string; user_label: string }> {
    return request("/api/workspace/remember", {
      method: "POST",
      body: JSON.stringify({ track_id: trackId, user_label: userLabel, project_id: projectId }),
    });
  },

  async updateWorkspaceSession(state: "ACTIVE" | "PAUSED" | "STOPPING" | "IDLE"): Promise<{ status: string; session_state: string; message: string }> {
    return request(`/api/workspace/session?state=${state}`, {
      method: "POST",
    });
  },

  async clearWorkspaceState(): Promise<{ status: string; message: string }> {
    return request("/api/workspace/state", {
      method: "DELETE",
    });
  },

  // Local Speech Engine & Voice Interaction (Step 6)
  async transcribeSpeech(payload: SpeechTranscribeRequest): Promise<SpeechTranscribeResponse> {
    return request("/api/speech/transcribe", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getSpeechStatus(): Promise<VoiceStatusResponse> {
    return request("/api/speech/status");
  },

  async setMicrophoneState(state: MicrophoneState): Promise<VoiceStatusResponse> {
    return request(`/api/speech/status?state=${state}`, {
      method: "POST",
    });
  },

  async runSpeechBenchmark(duration: number = 3.0): Promise<VoiceBenchmarkResult> {
    return request(`/api/speech/benchmark?duration=${duration}`, {
      method: "POST",
    });
  },

  // Sentinel Multimodal Orchestrator (Step 7)
  async querySentinel(payload: MultimodalQueryRequest): Promise<MultimodalQueryResponse> {
    return request("/api/sentinel/query", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getSentinelDemoFixtures(): Promise<Record<string, unknown>> {
    return request("/api/sentinel/demo-fixtures");
  },
};

