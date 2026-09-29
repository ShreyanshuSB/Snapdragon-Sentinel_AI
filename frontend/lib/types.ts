export interface ApiError {
  detail: string;
  code?: string;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  x_abs_min?: number | null;
  y_abs_min?: number | null;
  x_abs_max?: number | null;
  y_abs_max?: number | null;
}

export interface Detection {
  class_id: number;
  label: string;
  confidence: number;
  bbox: BoundingBox;
}

export interface OCRResult {
  text: string;
  confidence: number;
  bbox?: BoundingBox | null;
  line_number?: number | null;
}

export interface TimingMetrics {
  preprocess_ms: number;
  inference_ms: number;
  postprocess_ms: number;
  total_ms: number;
}

export interface ImageMetadata {
  original_width: number;
  original_height: number;
  channels: number;
  aspect_ratio: string;
}

export interface ModelInferenceMetadata {
  name: string;
  version: string;
  source: string;
  license: string;
  format: string;
  input_shape: number[];
  model_size_mb?: number | null;
}

export interface RuntimeVerificationMetadata {
  execution_provider: string;
  npu_verified: boolean;
  verification_method: string;
  display_label: string;
}

export interface VisionResult {
  status: string;
  message: string;
  objects: Detection[];
  ocr: OCRResult[];
  scene: string;
  detected_count: number;
  runtime: string;
  device: string;
  inference_time_ms?: number | null;
  file_id?: string | null;
  timing?: TimingMetrics | null;
  image?: ImageMetadata | null;
  model?: ModelInferenceMetadata | null;
  verification?: RuntimeVerificationMetadata | null;
}

export interface VisionPipelineStatus {
  state: string;
  is_loaded: boolean;
  model_name: string;
  model_path: string;
  input_shape: number[];
  execution_provider: string;
  available_providers: string[];
  npu_verified: boolean;
  warmup_done: boolean;
  total_inferences: number;
  last_inference_ms?: number | null;
  device_label: string;
}

export interface FrameCaptureResponse {
  status: string;
  frame_id: string;
  file_id: string;
  file_path: string;
  size_bytes: number;
  attachment_id?: number | null;
  message: string;
}

export interface RuntimeStatus {
  runtime_name: string;
  execution_provider: string;
  device_target: string;
  local_inference_policy: string;
  model_connection: string;
  npu_status: string;
  hardware_acceleration: string;
  arm_architecture_detected: string;
}

export interface HardwareStatus {
  platform: string;
  processor: string;
  architecture: string;
  python_version: string;
  cpu_cores: string;
  gpu: string;
  npu: string;
}

export interface ModelStatus {
  name: string;
  role: string;
  status: string;
  availability?: string;
  available: boolean;
  version: string;
  runtime: string;
  device: string;
  current_device?: string;
  target_device: string;
  verified_device: string;
  current_verification?: string;
  npu_verification?: string;
  execution_provider?: string;
  quantization: string;
  parameters: string;
  description: string;
  hub_compatible: boolean;
}

export interface ModelStatusResponse {
  models: Record<string, ModelStatus>;
  runtime: RuntimeStatus;
  hardware: HardwareStatus;
}

export interface BenchmarkRecord {
  id: string;
  model_name: string;
  model_version: string;
  runtime: string;
  execution_provider: string;
  device: string;
  timestamp: string;
  input_type: string;
  load_time_ms: number | null;
  first_inference_ms: number | null;
  average_inference_ms: number | null;
  preprocess_ms?: number | null;
  postprocess_ms?: number | null;
  total_pipeline_ms?: number | null;
  cold_warm?: string | null;
  throughput: number | null;
  memory_mb: number | null;
  notes: string;
}

export interface BenchmarkMetric {
  name: string;
  status: string;
  value: number | string | null;
  unit: string;
  description: string;
}

export interface BenchmarkSummary {
  benchmarks: Record<string, BenchmarkMetric>;
  history: BenchmarkRecord[];
  last_run: string | null;
  measured_device: string;
}

export interface Attachment {
  id: number;
  file_id: string;
  file_name: string;
  file_path: string;
  file_size: number;
  mime_type?: string | null;
  sha256?: string | null;
  memory_id?: number | null;
  conversation_id?: number | null;
  created_at: string;
}

export interface AttachmentUploadResponse {
  status: string;
  file_id: string;
  file_name: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  sha256: string;
  attachment_id?: number | null;
  message: string;
}

export interface MemoryContext {
  id: number;
  title: string;
  snippet: string;
  category: string;
  relevance_score?: number;
}

export interface ChatContext {
  workspace_note?: string;
  attached_files: string[];
  active_project?: string | null;
}

export type MetadataValue = string | number | boolean | null | undefined | string[];

export interface Memory {
  id: number;
  title: string;
  content: string;
  summary?: string | null;
  category: string;
  source_type: string;
  source_id?: string | null;
  attachment_path?: string | null;
  project_id?: number | null;
  project_name?: string | null;
  importance?: number;
  embedding_status?: "PENDING" | "READY" | "STALE" | "FAILED" | string;
  embedding_model?: string | null;
  embedding_model_version?: string | null;
  embedding_dimension?: number | null;
  metadata?: Record<string, MetadataValue>;
  created_at: string;
  updated_at: string;
}

export interface RetrievalResult {
  id: string | number;
  result_type?: "MEMORY" | "DOCUMENT" | "OCR" | string;
  item_type?: "memory" | "document_chunk";
  title: string;
  content: string;
  score: number;
  semantic_score: number;
  keyword_score: number;
  metadata_score: number;
  source_type: string;
  source_id?: string | null;
  project_id?: number | null;
  project_name?: string | null;
  page_number?: number | null;
  chunk_index?: number | null;
  created_at?: string | null;
  why_matched: string | string[];
  metadata?: Record<string, MetadataValue>;
}

export interface MemorySearchQuery {
  query: string;
  search_mode?: "HYBRID" | "SEMANTIC" | "KEYWORD" | string;
  top_k?: number;
  project_id?: number | null;
  category?: string | null;
  source_type?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  w_semantic?: number;
  w_keyword?: number;
  w_metadata?: number;
  include_documents?: boolean;
}

export interface MemorySearchResponse {
  query: string;
  search_mode: string;
  total_results?: number;
  total_matches?: number;
  query_embed_ms?: number;
  search_latency_ms?: number;
  total_ms?: number;
  took_ms?: number;
  embedding_ms?: number;
  results: RetrievalResult[];
}

export interface DuplicateCheckRequest {
  title?: string;
  content: string;
  project_id?: number | null;
  threshold?: number;
}

export interface DuplicateCheckResponse {
  is_duplicate: boolean;
  similarity: number;
  existing_memory_id?: number | null;
  existing_title?: string | null;
  message?: string;
  recommendation?: string;
}

export interface EmbeddingModelMetadata {
  name: string;
  version: string;
  source: string;
  license: string;
  dimension: number;
  max_sequence_length: number;
  runtime: string;
  execution_provider: string;
  npu_verified: boolean;
  hardware_target: string;
  model_size_mb?: number | null;
  parameters_m?: number | null;
  qualcomm_ai_hub_target?: string | null;
  notes?: string | null;
}

export interface EmbeddingStatusResponse {
  state?: string;
  is_available: boolean;
  is_loaded: boolean;
  model?: EmbeddingModelMetadata;
  ready_memories_count?: number;
  stale_memories_count?: number;
  failed_memories_count?: number;
  reindex_required?: boolean;
  device_label: string;
  last_query_embed_ms?: number | null;
  target_model_name?: string | null;
  target_device?: string | null;
  npu_status?: string | null;
  model_name?: string;
  model_version?: string;
  dimension?: number;
  max_seq_length?: number;
  runtime?: string;
  execution_provider?: string;
  npu_verified?: boolean;
  total_indexed_memories?: number;
  pending_memories?: number;
  stale_memories?: number;
  failed_memories?: number;
  indexed_document_chunks?: number;
  license?: string;
  source?: string;
}

export interface ReindexResponse {
  status: string;
  memories_indexed?: number;
  chunks_indexed?: number;
  duration_ms: number;
  message?: string;
  memories_reindexed?: number;
  document_chunks_reindexed?: number;
  model_name?: string;
  dimension?: number;
}

export interface MemoryEmbedRequest {
  text: string;
}

export interface MemoryEmbedResponse {
  dimension: number;
  latency_ms: number;
  model_name: string;
  model_version: string;
  runtime: string;
  execution_provider: string;
  npu_verified: boolean;
  status: string;
}

export interface MemoryStats {
  total_memories: number;
  category_counts: Record<string, number>;
  project_count: number;
  storage_type: string;
}

export interface Project {
  id: number;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  memory_count: number;
}

export interface SourceAttribution {
  type: "MEMORY" | "DOCUMENT" | "OCR" | "VISION" | string;
  id: string | number;
  title: string;
  page?: number | null;
  chunk_index?: number | null;
  snippet?: string | null;
  score?: number | null;
}

export interface ContextUsedSummary {
  vision_count: number;
  ocr_count: number;
  memory_count: number;
  document_count: number;
  project_name?: string | null;
  total_items: number;
}

export interface ReasoningTimingMetrics {
  retrieval_ms: number;
  context_build_ms: number;
  image_prepare_ms: number;
  generation_ms: number;
  total_ms: number;
}

export interface VerificationInfo {
  current_device: string;
  target_device: string;
  npu_verified: boolean;
  status: string;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatResponse {
  conversation_id: number;
  user_message_id: number;
  assistant_message_id?: number;
  response: string;
  answer?: string;
  status: string;
  mode?: string;
  action?: GroundingAction | null;
  sources?: SourceAttribution[];
  citations: string[];
  context_used?: ContextUsedSummary;
  model: string;
  runtime?: string;
  timing?: ReasoningTimingMetrics;
  verification?: VerificationInfo;
  metadata: Record<string, unknown>;
  created_at: string;
}


export interface ReasoningStatusResponse {
  state: string;
  model_name: string;
  model_version: string;
  runtime: string;
  execution_provider: string;
  device: string;
  npu_verified: boolean;
  context_length: number;
  parameter_count: string;
  license: string;
  is_loaded: boolean;
  total_inferences: number;
  last_generation_ms: number;
  diagnostics?: Record<string, unknown> | null;
}


export interface PrivacyPolicy {
  camera_enabled: boolean;
  microphone_enabled: boolean;
  memory_enabled: boolean;
  local_ai_mode: string;
  cloud_enabled: boolean;
  retention_days: number;
  telemetry_enabled: boolean;
}

export interface SystemIndicator {
  label: string;
  status: string;
  tone: "ready" | "not_connected" | "loading" | "error" | "disabled";
}

export interface SystemStatus {
  app_name: string;
  tagline: string;
  phase: string;
  indicators: Record<string, SystemIndicator>;
  privacy_policy: PrivacyPolicy;
  memory_stats: MemoryStats;
  ai_model_connected: boolean;
  npu_verified?: boolean;
}

// ---------------------------------------------------------------------------
// Step 7: Snapdragon Hardware & Runtime Diagnostics Types
// ---------------------------------------------------------------------------
export type ExecutionProviderState =
  | "NOT_INSTALLED"
  | "AVAILABLE"
  | "SELECTABLE"
  | "SELECTED"
  | "RUNNING"
  | "VERIFIED"
  | "FAILED"
  | "UNKNOWN";

export interface ProviderDiagnostics {
  name: string;
  state: ExecutionProviderState;
  available: boolean;
  selected: boolean;
  running: boolean;
  verified: boolean;
  version?: string | null;
  details: string;
}

export interface TargetProfile {
  target_platform: string;
  target_cpu: string;
  target_gpu: string;
  target_npu: string;
  target_architecture: string;
  target_os: string;
  preferred_runtime: string;
  notes: string;
}

export interface HardwareDiagnosticsResponse {
  os_name: string;
  os_version: string;
  os_build: string;
  system_architecture: string;
  processor_name: string;
  processor_vendor: string;
  processor_architecture: string;
  cpu_cores_physical?: number | null;
  cpu_cores_logical?: number | null;
  ram_total_gb: number;
  ram_available_gb: number;
  ram_used_percent: number;
  gpus: string[];
  npu_detected: boolean;
  npu_device_name?: string | null;
  machine_manufacturer?: string | null;
  machine_model?: string | null;
  snapdragon_detected: boolean;
  snapdragon_platform: string;
  is_development_host: boolean;
  target_comparison: string;
}

export interface MissingDependency {
  name: string;
  why_needed: string;
  how_used: string;
  installation_status: string;
}

export interface RuntimeDiagnosticsResponse {
  python_version: string;
  onnxruntime_installed: boolean;
  onnxruntime_version?: string | null;
  available_providers: string[];
  qnn_available: boolean;
  directml_available: boolean;
  cpu_available: boolean;
  cuda_available: boolean;
  selected_provider: string;
  qnn_version?: string | null;
  provider_states: Record<string, ProviderDiagnostics>;
  npu_detected: boolean;
  npu_execution_verified: boolean;
  verification_method: string;
  missing_dependencies: MissingDependency[];
}

export interface FullDiagnosticsResponse {
  hardware: HardwareDiagnosticsResponse;
  runtime: RuntimeDiagnosticsResponse;
  target_profile: TargetProfile;
  summary: string;
}

export interface ReferenceMetrics {
  reference_latency_ms?: number | null;
  reference_throughput_fps?: number | null;
  reference_device: string;
  reference_source: string;
}

export interface MeasuredMetrics {
  our_latency_ms?: number | null;
  our_throughput_fps?: number | null;
  our_device?: string | null;
  measured_timestamp?: string | null;
}

export interface ModelCandidateRecord {
  id: string;
  name: string;
  version: string;
  task: string;
  source: string;
  license: string;
  format: string;
  input_modalities: string[];
  output_modalities: string[];
  input_width: number;
  input_height: number;
  quantization: string;
  parameter_count: string;
  supported_chipsets: string[];
  supported_runtimes: string[];
  preferred_execution_provider: string;
  status: string;
  reference_metrics: ReferenceMetrics;
  our_metrics: MeasuredMetrics;
  official_hub_url: string;
  export_method: string;
}

export interface ModelEvaluationResult {
  model_id: string;
  name: string;
  compatibility: "COMPATIBLE" | "LIKELY_COMPATIBLE" | "UNVERIFIED" | "INCOMPATIBLE";
  hardware_compatibility: string;
  runtime_compatibility: string;
  provider_compatibility: string;
  input_compatibility: string;
  license_status: string;
  verification_status: string;
  technical_notes: string;
}

export interface ModelSelectionResponse {
  target_hardware: string;
  current_hardware: string;
  active_runtime: string;
  candidates: ModelEvaluationResult[];
  recommended_first_candidate: string;
  selection_rationale: string;
  next_steps: string[];
}

export interface TextRegion {
  id: string;
  text: string;
  confidence: number;
  bbox: BoundingBox;
  polygon?: number[][] | null;
  language?: string | null;
  reading_order?: number | null;
}

export interface OCRTimingMetrics {
  preprocess_ms: number;
  detector_ms: number;
  recognizer_ms: number;
  postprocess_ms: number;
  total_ms: number;
}

export interface OCRModelMetadata {
  name: string;
  detector: string;
  recognizer: string;
  runtime: string;
  license: string;
  languages: string[];
  input_resolution: string;
}

export interface FullOCRResult {
  status: string;
  message: string;
  regions: TextRegion[];
  full_text: string;
  region_count: number;
  timing?: OCRTimingMetrics | null;
  model?: OCRModelMetadata | null;
  execution_provider: string;
  device: string;
  npu_verified: boolean;
  source: string;
}

export interface OCRStatusResponse {
  state: string;
  is_available: boolean;
  is_loaded: boolean;
  model_name: string;
  detector: string;
  recognizer: string;
  runtime: string;
  execution_provider: string;
  npu_verified: boolean;
  supported_languages: string[];
  device_label: string;
}

export interface DocumentPageResponse {
  id: number;
  document_id: number;
  page_number: number;
  width?: number;
  height?: number;
  text?: string;
  text_content?: string;
  has_ocr?: boolean;
  extraction_method?: string;
  regions?: TextRegion[] | null;
  text_regions?: TextRegion[] | null;
  detector_ms?: number | null;
  recognizer_ms?: number | null;
  processing_time_ms?: number | null;
  total_ms?: number | null;
}

export interface DocumentResponse {
  document_id: string;
  file_id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  source_type: string;
  status: string;
  page_count: number;
  ocr_pages_count?: number;
  extracted_text: string;
  extraction_method: string;
  processing_time_ms: number;
  created_at: string;
  updated_at?: string;
  pages?: DocumentPageResponse[] | null;
  metadata?: Record<string, unknown> | null;
  // Aliases for compatibility
  id?: string;
  filename?: string;
  npu_verified?: boolean;
  total_processing_ms?: number | null;
  error_message?: string | null;
}

export interface DocumentSearchHit {
  document_id: string;
  file_id: string;
  file_name: string;
  page_number: number | null;
  source_type: string;
  snippet: string;
  match_count?: number;
  created_at: string;
  // Aliases for compatibility
  filename?: string;
  extraction_method?: string;
  matched_text?: string;
}

export interface DocumentSearchResponse {
  query: string;
  total_hits: number;
  total_matches?: number;
  results: DocumentSearchHit[];
}

export interface TrackedObject {
  track_id: string;
  class_id: number;
  class_name: string;
  confidence: number;
  raw_bbox: BoundingBox;
  smoothed_bbox: BoundingBox;
  center_x: number;
  center_y: number;
  width: number;
  height: number;
  velocity_x?: number;
  velocity_y?: number;
  first_seen_timestamp: number;
  last_seen_timestamp: number;
  frames_seen: number;
  consecutive_misses: number;
  visibility_state: "CURRENT_VISIBLE" | "RECENTLY_SEEN" | "STALE" | "EXPIRED" | string;
  region: string;
  user_label?: string | null;
  ocr_associations: string[];
  ocr_association_conf: number;
  stability_score: number;
  project_id?: string | null;
}

export interface SpatialRelation {
  source_track_id: string;
  relation_type: string;
  target_track_id: string;
  source_label: string;
  target_label: string;
  description: string;
  confidence: number;
}

export interface WorkspaceObservation {
  track_id: string;
  object_label: string;
  user_label?: string | null;
  aliases: string[];
  confidence: number;
  last_seen_timestamp: number;
  last_seen_bbox: BoundingBox;
  normalized_position: { x: number; y: number };
  region: string;
  visibility_state: string;
  source: string;
  project_id?: string | null;
  ocr_associations: string[];
  relations: string[];
}

export interface FindItCandidate {
  track_id: string;
  object: string;
  user_label?: string | null;
  confidence: number;
  region: string;
  normalized_position: { x: number; y: number };
  last_seen: string;
  age_seconds: number;
  relations: string[];
  bbox: BoundingBox;
}

export interface FindItResponse {
  found: boolean;
  match_type: "CURRENT_VISIBLE" | "RECENTLY_SEEN" | "STALE" | "NOT_FOUND" | "AMBIGUOUS" | string;
  object: string;
  track_id?: string | null;
  confidence?: number | null;
  region?: string | null;
  normalized_position?: { x: number; y: number } | null;
  last_seen?: string | null;
  age_seconds?: number | null;
  relations: string[];
  candidates: FindItCandidate[];
  message: string;
  grounding_box?: BoundingBox | null;
}

export interface WorkspaceStateResponse {
  status: string;
  session_state: "IDLE" | "STARTING" | "ACTIVE" | "PAUSED" | "STOPPING" | "ERROR" | string;
  active_tracks_count: number;
  tracked_objects: TrackedObject[];
  relations: SpatialRelation[];
  recent_observations: WorkspaceObservation[];
  timestamp: number;
}

export type MicrophoneState =
  | "IDLE"
  | "REQUESTING_PERMISSION"
  | "READY"
  | "RECORDING"
  | "PROCESSING"
  | "TRANSCRIBED"
  | "ERROR";

export type VoiceIntentType =
  | "FIND_IT"
  | "REMEMBER_OBJECT"
  | "SEARCH_MEMORY"
  | "SEARCH_DOCUMENTS"
  | "ASK_SENTINEL"
  | "GENERAL_QUERY"
  | "UNKNOWN";

export interface VoiceActionResult {
  intent: VoiceIntentType;
  summary: string;
  raw_query: string;
  grounded_target_id?: string | null;
  grounded_target_name?: string | null;
  grounded_region?: string | null;
  grounded_confidence?: number | null;
  grounded_relations: string[];
  action_data: Record<string, any>;
}

export interface SpeechTranscribeRequest {
  audio_base64?: string | null;
  audio_format?: string;
  sample_rate?: number;
  language?: string | null;
  project_id?: string;
  route_intent?: boolean;
  save_audio?: boolean;
}

export interface SpeechTranscribeResponse {
  text: string;
  language?: string | null;
  confidence?: number | null;
  duration_ms: number;
  audio_duration_seconds: number;
  real_time_factor?: number | null;
  model: string;
  runtime: string;
  status: string;
  action_result?: VoiceActionResult | null;
}

export interface VoiceStatusResponse {
  microphone_state: MicrophoneState;
  model_name: string;
  model_family: string;
  active_runtime: string;
  host_hardware: string;
  host_available: boolean;
  snapdragon_target: string;
  snapdragon_verification_status: string;
  privacy_policy: string;
  max_recording_seconds: number;
}

export interface VoiceBenchmarkResult {
  model_name: string;
  device: string;
  runtime: string;
  audio_duration_seconds: number;
  load_latency_ms: number;
  preprocessing_latency_ms: number;
  inference_latency_ms: number;
  total_latency_ms: number;
  real_time_factor: number;
  snapdragon_status: string;
}

export type GroundingActionType =
  | "HIGHLIGHT_OBJECT"
  | "OPEN_VISION"
  | "OPEN_DOCUMENT"
  | "OPEN_MEMORY"
  | "OPEN_SOURCE"
  | "NONE";

export interface GroundingAction {
  action: GroundingActionType;
  target_id?: string | number | null;
  label?: string | null;
  box_2d?: BoundingBox | null;
  zone?: string | null;
  document_id?: string | null;
  page?: number | null;
  memory_id?: number | null;
  confidence?: number | null;
  description?: string | null;
}

export interface EvidenceItem {
  category: "OBSERVED" | "RETRIEVED" | "INFERRED" | "CONVERSATION";
  source_type: string;
  source_id: string | number;
  title: string;
  snippet: string;
  score?: number | null;
  page?: number | null;
  metadata?: Record<string, unknown>;
}

export interface OrchestratorTiming {
  input_normalization_ms: number;
  evidence_collection_ms: number;
  retrieval_ms: number;
  context_build_ms: number;
  image_prepare_ms: number;
  generation_ms: number;
  validation_ms: number;
  action_generation_ms: number;
  total_ms: number;
  model_inference_status: string;
}

export interface MultimodalQueryRequest {
  query: string;
  source?: "text" | "voice" | "vision" | "document" | string;
  conversation_id?: number | null;
  project_id?: number | null;
  image_id?: string | null;
  image_context?: string | null;
  document_id?: string | null;
  page_number?: number | null;
  memory_id?: number | null;
  voice_transcript?: string | null;
  voice_metadata?: Record<string, unknown> | null;
  mode?: "live" | "demo" | string;
}

export interface MultimodalQueryResponse {
  query: string;
  answer: string;
  status: string;
  mode: string;
  sources: SourceAttribution[];
  citations: string[];
  evidence: EvidenceItem[];
  action: GroundingAction;
  observed_facts: string[];
  retrieved_facts: string[];
  inferred_facts: string[];
  uncertainties: string[];
  context_summary: ContextUsedSummary;
  timing: OrchestratorTiming;
  verification: VerificationInfo;
  conversation_id?: number | null;
  user_message_id?: number | null;
  assistant_message_id?: number | null;
}


