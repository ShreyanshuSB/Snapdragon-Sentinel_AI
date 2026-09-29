"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  Camera,
  CameraOff,
  CheckCircle2,
  Compass,
  Copy,
  Crosshair,
  Eye,
  FileText,
  FlipHorizontal,
  Layers,
  MapPin,
  MessageSquare,
  Mic,
  Search,
  Server,
  Sparkles,
  Tag,
  Trash2,
  Upload,
} from "lucide-react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { DetectionOverlay } from "@/components/DetectionOverlay";
import { TextOverlay } from "@/components/TextOverlay";
import { VoiceAssistantModal } from "@/components/VoiceAssistantModal";
import { api } from "@/lib/api";
import {
  FindItCandidate,
  FindItResponse,
  FullOCRResult,
  TrackedObject,
  VisionResult,
  WorkspaceStateResponse,
} from "@/lib/types";

export default function VisionPage() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [cameraActive, setCameraActive] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [capturedFileId, setCapturedFileId] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [uploadedFileSize, setUploadedFileSize] = useState<number | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  // Analysis Modes: OBJECTS | TEXT | BOTH
  const [analysisMode, setAnalysisMode] = useState<"OBJECTS" | "TEXT" | "BOTH">("OBJECTS");

  // Step 5: Real-Time Workspace Tracking & Find It
  const [workspaceTrackingActive, setWorkspaceTrackingActive] = useState(false);
  const [workspaceState, setWorkspaceState] = useState<WorkspaceStateResponse | null>(null);
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [groundedTrackId, setGroundedTrackId] = useState<string | null>(null);

  // Find It State
  const [findQuery, setFindQuery] = useState("");
  const [findSearching, setFindSearching] = useState(false);
  const [findResult, setFindResult] = useState<FindItResponse | null>(null);

  // Remember Object State
  const [rememberingTrackId, setRememberingTrackId] = useState<string | null>(null);
  const [rememberLabelInput, setRememberLabelInput] = useState("");
  const [rememberSaving, setRememberSaving] = useState(false);

  // Results
  const [visionResult, setVisionResult] = useState<VisionResult | null>(null);
  const [ocrResult, setOcrResult] = useState<FullOCRResult | null>(null);
  const [selectedDetectionIdx, setSelectedDetectionIdx] = useState<number | null>(null);
  const [hoveredDetectionIdx, setHoveredDetectionIdx] = useState<number | null>(null);
  const [selectedOcrIdx, setSelectedOcrIdx] = useState<number | null>(null);
  const [hoveredOcrIdx, setHoveredOcrIdx] = useState<number | null>(null);

  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);
  const [copiedText, setCopiedText] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);

  // Confidence threshold (default 25%)
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.25);

  // Camera Management
  const [availableDevices, setAvailableDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const [resolution, setResolution] = useState<"720p" | "1080p">("720p");
  const [isMirrored, setIsMirrored] = useState(false);

  // Filtered detections based on interactive confidence threshold
  const visibleObjects = useMemo(() => {
    if (!visionResult?.objects) return [];
    return visionResult.objects.filter((obj) => obj.confidence >= confidenceThreshold);
  }, [visionResult, confidenceThreshold]);

  const visibleOcrRegions = useMemo(() => {
    if (!ocrResult?.regions) return [];
    return ocrResult.regions.filter((reg) => reg.confidence >= confidenceThreshold);
  }, [ocrResult, confidenceThreshold]);

  // Tracked objects filtered by confidence
  const visibleTracks = useMemo(() => {
    if (!workspaceState?.tracked_objects) return [];
    return workspaceState.tracked_objects.filter((t) => t.confidence >= confidenceThreshold);
  }, [workspaceState, confidenceThreshold]);

  // Enumerate cameras
  useEffect(() => {
    async function loadDevices() {
      if (typeof navigator !== "undefined" && navigator.mediaDevices?.enumerateDevices) {
        try {
          const devices = await navigator.mediaDevices.enumerateDevices();
          const videoDevs = devices.filter((d) => d.kind === "videoinput");
          setAvailableDevices(videoDevs);
          if (videoDevs.length > 0 && !selectedDeviceId) {
            setSelectedDeviceId(videoDevs[0].deviceId);
          }
        } catch {
          // Device enumeration optional
        }
      }
    }
    loadDevices();
  }, [selectedDeviceId]);

  // Privacy: Clean up stream and stop tracking on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      api.updateWorkspaceSession("STOPPING").catch(() => {});
    };
  }, []);

  // Start Camera via WebRTC
  const startCamera = async () => {
    setPermissionError(null);
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("WebRTC camera API is not supported in this browser environment.");
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }

      const dims = resolution === "1080p" ? { width: 1920, height: 1080 } : { width: 1280, height: 720 };
      const constraints: MediaStreamConstraints = {
        video: {
          width: { ideal: dims.width },
          height: { ideal: dims.height },
          ...(selectedDeviceId ? { deviceId: { exact: selectedDeviceId } } : { facingMode: "user" }),
        },
        audio: false,
      };

      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = mediaStream;
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
      setCameraActive(true);

      const devices = await navigator.mediaDevices.enumerateDevices();
      setAvailableDevices(devices.filter((d) => d.kind === "videoinput"));
    } catch (err: unknown) {
      let msg = "Camera access is unavailable. Check Windows camera permissions and try again.";
      if (err instanceof Error) {
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
          msg = "Camera permission was denied. Please allow camera access in Windows Settings / browser.";
        } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
          msg = "No physical camera device was detected on this PC.";
        }
      }
      setPermissionError(msg);
      setCameraActive(false);
    }
  };

  // Stop Camera & Privacy Release
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
    setWorkspaceTrackingActive(false);
    api.updateWorkspaceSession("STOPPING").catch(() => {});
  };

  // Capture Frame
  const captureFrame = async () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current || document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      if (isMirrored) {
        ctx.translate(canvas.width, 0);
        ctx.scale(-1, 1);
      }
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.9);

      setCapturedImage(dataUrl);
      setUploadedFileName("Camera_Capture.jpg");
      setUploadedFileSize(Math.round((dataUrl.length * 3) / 4));
      setVisionResult(null);
      setOcrResult(null);
      setSelectedDetectionIdx(null);
      setSelectedOcrIdx(null);
      setFeedbackMsg(null);
      setPermissionError(null);

      try {
        const captureRes = await api.captureVisionFrame(dataUrl);
        setCapturedFileId(captureRes.file_id);
        setFeedbackMsg(`Frame captured locally (${captureRes.file_id}). Ready for analysis & workspace tracking.`);
      } catch {
        setCapturedFileId(null);
        setFeedbackMsg("Frame captured locally. Ready for analysis & workspace tracking.");
      }
    }
  };

  // Handle local image file upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setVisionResult(null);
    setOcrResult(null);
    setSelectedDetectionIdx(null);
    setSelectedOcrIdx(null);
    setFeedbackMsg(null);
    setPermissionError(null);

    try {
      const uploadRes = await api.uploadFile(file);
      setCapturedFileId(uploadRes.file_id);
      setUploadedFileName(file.name);
      setUploadedFileSize(file.size);

      const reader = new FileReader();
      reader.onload = (event) => {
        setCapturedImage(event.target?.result as string);
        setFeedbackMsg(`Loaded image: ${file.name} (${(file.size / 1024).toFixed(1)} KB). Ready for analysis.`);
        setPermissionError(null);
      };
      reader.readAsDataURL(file);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload file.";
      setPermissionError(msg);
      setCapturedImage(null);
      setCapturedFileId(null);
    }
  };

  // Run analysis based on selected mode
  const runAnalysis = async () => {
    if (!capturedImage && !capturedFileId) return;

    setAnalyzing(true);
    setFeedbackMsg(null);
    setPermissionError(null);
    setSelectedDetectionIdx(null);
    setSelectedOcrIdx(null);

    if (analysisMode === "OBJECTS") {
      setVisionResult(null);
    } else if (analysisMode === "TEXT") {
      setOcrResult(null);
    } else {
      setVisionResult(null);
      setOcrResult(null);
    }

    try {
      if (analysisMode === "OBJECTS") {
        const res = await api.analyzeVision({
          file_id: capturedFileId || undefined,
          image: capturedImage || undefined,
          confidence_threshold: confidenceThreshold,
          iou_threshold: 0.45,
        });
        setVisionResult(res);

        // Update tracking layer with detections
        if (res.objects && res.objects.length > 0) {
          const trackRes = await api.trackWorkspaceFrame({
            detections: res.objects,
            confidence_threshold: confidenceThreshold,
          });
          setWorkspaceState(trackRes);
        }

        setFeedbackMsg(`YOLO-X: detected ${res.detected_count} object(s) in ${res.timing?.total_ms || 0} ms.`);
      } else if (analysisMode === "TEXT") {
        const res = await api.analyzeOCR({
          file_id: capturedFileId || undefined,
          image: capturedImage || undefined,
          confidence_threshold: confidenceThreshold,
        });
        setOcrResult(res);
        setFeedbackMsg(`EasyOCR: detected ${res.region_count} text region(s) in ${res.timing?.total_ms || 0} ms.`);
      } else {
        const [vRes, oRes] = await Promise.all([
          api.analyzeVision({
            file_id: capturedFileId || undefined,
            image: capturedImage || undefined,
            confidence_threshold: confidenceThreshold,
            iou_threshold: 0.45,
          }),
          api.analyzeOCR({
            file_id: capturedFileId || undefined,
            image: capturedImage || undefined,
            confidence_threshold: confidenceThreshold,
          }),
        ]);
        setVisionResult(vRes);
        setOcrResult(oRes);

        // Update workspace tracker with both detections and OCR text
        if (vRes.objects) {
          const trackRes = await api.trackWorkspaceFrame({
            detections: vRes.objects,
            ocr_results: oRes.regions || [],
            confidence_threshold: confidenceThreshold,
          });
          setWorkspaceState(trackRes);
        }

        setFeedbackMsg(
          `Analysis complete: ${vRes.detected_count} object(s) + ${oRes.region_count} text region(s). Workspace tracking updated.`
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Inference pipeline failed.";
      setPermissionError(msg);
      if (analysisMode === "OBJECTS") setVisionResult(null);
      if (analysisMode === "TEXT") setOcrResult(null);
      if (analysisMode === "BOTH") {
        setVisionResult(null);
        setOcrResult(null);
      }
    } finally {
      setAnalyzing(false);
    }
  };

  // Toggle Workspace Tracking Mode
  const toggleWorkspaceTracking = async () => {
    if (workspaceTrackingActive) {
      setWorkspaceTrackingActive(false);
      await api.updateWorkspaceSession("PAUSED");
      setFeedbackMsg("Workspace tracking paused.");
    } else {
      setWorkspaceTrackingActive(true);
      await api.updateWorkspaceSession("ACTIVE");
      setFeedbackMsg("Workspace tracking active. Objects will be tracked across frames.");
      // Fetch current workspace state
      try {
        const st = await api.getWorkspaceState();
        setWorkspaceState(st);
      } catch {
        // State will update on next analysis
      }
    }
  };

  // Find It Search Execution
  const handleFindIt = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!findQuery.trim()) return;

    setFindSearching(true);
    setFindResult(null);
    setPermissionError(null);

    try {
      const res = await api.queryFindIt(findQuery.trim());
      setFindResult(res);
      if (res.track_id) {
        setGroundedTrackId(res.track_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Find It query failed.";
      setPermissionError(msg);
    } finally {
      setFindSearching(false);
    }
  };

  // Remember User Label for Track
  const handleSaveRememberLabel = async (trackId: string) => {
    if (!rememberLabelInput.trim()) return;
    setRememberSaving(true);
    try {
      await api.rememberWorkspaceObject(trackId, rememberLabelInput.trim());
      setFeedbackMsg(`Remembered '${rememberLabelInput.trim()}' for track [${trackId}].`);
      setRememberingTrackId(null);
      setRememberLabelInput("");
      // Refresh workspace state
      const st = await api.getWorkspaceState();
      setWorkspaceState(st);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to remember object.";
      setPermissionError(msg);
    } finally {
      setRememberSaving(false);
    }
  };

  const copyExtractedText = () => {
    if (!ocrResult?.full_text) return;
    navigator.clipboard.writeText(ocrResult.full_text);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  const clearAnalysis = () => {
    setCapturedImage(null);
    setCapturedFileId(null);
    setUploadedFileName(null);
    setUploadedFileSize(null);
    setVisionResult(null);
    setOcrResult(null);
    setSelectedDetectionIdx(null);
    setHoveredDetectionIdx(null);
    setSelectedOcrIdx(null);
    setHoveredOcrIdx(null);
    setSelectedTrackId(null);
    setGroundedTrackId(null);
    setFindResult(null);
    setFeedbackMsg(null);
    setPermissionError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">
        {/* Top Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-md border border-cyan-500/30 bg-cyan-950/40 px-2 py-0.5 text-xs font-semibold text-cyan-300">
                Step 5 — Workspace Tracking & Find It
              </span>
              <span className="text-xs text-slate-500">Local YOLO-X + Deterministic Tracker + Spatial Memory</span>
            </div>
            <h1 className="mt-1 text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Desk Tracking & “Find It” Localization
            </h1>
            <p className="mt-1 text-xs text-slate-400">
              Real-time object tracking, spatial relationship modeling, and natural-language workspace search.
            </p>
          </div>

          {/* Mode Switcher & Tracking Pill */}
          <div className="flex items-center gap-2">
            {/* Tracking Toggle Button */}
            <button
              type="button"
              onClick={toggleWorkspaceTracking}
              className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
                workspaceTrackingActive
                  ? "border-emerald-500/40 bg-emerald-950/40 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.3)]"
                  : "border-white/10 bg-slate-900 text-slate-400 hover:text-white"
              }`}
              title="Toggle Workspace Tracking"
            >
              <Crosshair className={`h-3.5 w-3.5 ${workspaceTrackingActive ? "animate-spin text-emerald-400" : ""}`} />
              <span>Tracking: {workspaceTrackingActive ? "ACTIVE" : "IDLE"}</span>
            </button>

            {/* Analysis Mode Switcher */}
            <div className="flex items-center gap-1 rounded-xl bg-slate-900 border border-white/10 p-1">
              <button
                type="button"
                onClick={() => {
                  setAnalysisMode("OBJECTS");
                  setSelectedDetectionIdx(null);
                  setSelectedOcrIdx(null);
                }}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  analysisMode === "OBJECTS"
                    ? "bg-cyan-500 text-slate-950 shadow-[0_0_12px_rgba(6,182,212,0.4)]"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                OBJECTS
              </button>
              <button
                type="button"
                onClick={() => {
                  setAnalysisMode("TEXT");
                  setSelectedDetectionIdx(null);
                  setSelectedOcrIdx(null);
                }}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  analysisMode === "TEXT"
                    ? "bg-amber-400 text-slate-950 shadow-[0_0_12px_rgba(245,158,11,0.4)]"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                TEXT (OCR)
              </button>
              <button
                type="button"
                onClick={() => {
                  setAnalysisMode("BOTH");
                  setSelectedDetectionIdx(null);
                  setSelectedOcrIdx(null);
                }}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  analysisMode === "BOTH"
                    ? "bg-gradient-to-r from-cyan-400 to-amber-400 text-slate-950 shadow-[0_0_12px_rgba(6,182,212,0.4)]"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                BOTH
              </button>
            </div>
          </div>
        </div>

        {/* Error Notice */}
        {permissionError && (
          <div className="mb-6 flex items-start gap-3 rounded-2xl border border-rose-500/30 bg-rose-950/30 p-4 text-sm text-rose-300">
            <AlertCircle className="h-5 w-5 shrink-0 text-rose-400 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium text-rose-200">Execution Notice</p>
              <p className="mt-1 text-xs text-rose-300 leading-relaxed">{permissionError}</p>
            </div>
          </div>
        )}

        {/* Feedback message */}
        {feedbackMsg && (
          <div className="mb-6 flex items-center gap-2 rounded-xl border border-cyan-500/30 bg-cyan-950/30 px-4 py-2.5 text-xs text-cyan-300">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-cyan-400" />
            <span>{feedbackMsg}</span>
          </div>
        )}

        {/* Main Grid: Left Visual Feed / Right Panel */}
        <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          {/* LEFT COLUMN: Feed & Interactive Overlays */}
          <div className="flex flex-col rounded-3xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl">
            {/* Toolbar */}
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Camera className="h-4 w-4 text-cyan-400" />
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                  Workspace Visual Feed
                </h2>
              </div>

              {/* Hardware Selection & Controls */}
              <div className="flex items-center gap-2 text-xs">
                {availableDevices.length > 1 && (
                  <select
                    value={selectedDeviceId}
                    onChange={(e) => setSelectedDeviceId(e.target.value)}
                    className="rounded-lg border border-white/10 bg-slate-950 px-2.5 py-1 text-slate-300"
                    title="Camera Device Selection"
                  >
                    {availableDevices.map((d, i) => (
                      <option key={d.deviceId} value={d.deviceId}>
                        {d.label || `Camera ${i + 1}`}
                      </option>
                    ))}
                  </select>
                )}

                <select
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value as "720p" | "1080p")}
                  className="rounded-lg border border-white/10 bg-slate-950 px-2.5 py-1 text-slate-300"
                  title="Resolution Selection"
                >
                  <option value="720p">720p HD</option>
                  <option value="1080p">1080p FHD</option>
                </select>

                <button
                  type="button"
                  onClick={() => setIsMirrored(!isMirrored)}
                  className={`rounded-lg border p-1.5 transition ${
                    isMirrored
                      ? "border-cyan-500/50 bg-cyan-500/20 text-cyan-300"
                      : "border-white/10 bg-slate-950 text-slate-400 hover:text-white"
                  }`}
                  title="Flip / Mirror Camera"
                >
                  <FlipHorizontal className="h-3.5 w-3.5" />
                </button>

                <span className="text-[11px] text-slate-500 font-mono">
                  {cameraActive ? `CAMERA ACTIVE (${resolution})` : "CAMERA IDLE"}
                </span>
              </div>
            </div>

            {/* Visual Container */}
            <div className="relative aspect-video w-full overflow-hidden rounded-2xl border border-dashed border-white/15 bg-slate-950 flex items-center justify-center min-h-[380px]">
              {capturedImage ? (
                <div className="relative w-full h-full flex items-center justify-center">
                  {/* Mode 1: OBJECTS overlay (supports trackedObjects & grounded highlight) */}
                  {analysisMode === "OBJECTS" && (
                    <DetectionOverlay
                      imageSrc={capturedImage}
                      detections={visibleObjects}
                      trackedObjects={visibleTracks}
                      selectedIndex={selectedDetectionIdx}
                      selectedTrackId={selectedTrackId}
                      groundedTrackId={groundedTrackId}
                      hoveredIndex={hoveredDetectionIdx}
                      onSelect={(idx) => setSelectedDetectionIdx(idx)}
                      onSelectTrack={(tId) => setSelectedTrackId(tId)}
                      onHover={(idx) => setHoveredDetectionIdx(idx)}
                    />
                  )}

                  {/* Mode 2: TEXT overlay */}
                  {analysisMode === "TEXT" && (
                    <TextOverlay
                      imageSrc={capturedImage}
                      regions={visibleOcrRegions}
                      selectedIndex={selectedOcrIdx}
                      onSelect={(idx) => setSelectedOcrIdx(idx)}
                    />
                  )}

                  {/* Mode 3: BOTH overlay */}
                  {analysisMode === "BOTH" && (
                    <DetectionOverlay
                      imageSrc={capturedImage}
                      detections={visibleObjects}
                      trackedObjects={visibleTracks}
                      textRegions={visibleOcrRegions}
                      selectedIndex={selectedDetectionIdx}
                      selectedTrackId={selectedTrackId}
                      groundedTrackId={groundedTrackId}
                      selectedTextIndex={selectedOcrIdx}
                      hoveredIndex={hoveredDetectionIdx}
                      hoveredTextIndex={hoveredOcrIdx}
                      onSelect={(idx) => {
                        setSelectedDetectionIdx(idx);
                        setSelectedOcrIdx(null);
                      }}
                      onSelectTrack={(tId) => setSelectedTrackId(tId)}
                      onSelectText={(idx) => {
                        setSelectedOcrIdx(idx);
                        setSelectedDetectionIdx(null);
                      }}
                      onHover={(idx) => setHoveredDetectionIdx(idx)}
                      onHoverText={(idx) => setHoveredOcrIdx(idx)}
                    />
                  )}
                </div>
              ) : cameraActive ? (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  style={{ transform: isMirrored ? "scaleX(-1)" : "none" }}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex flex-col items-center justify-center p-8 text-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-500 mb-3">
                    <CameraOff className="h-8 w-8" />
                  </div>
                  <p className="text-sm font-semibold text-slate-200">No workspace image loaded</p>
                  <p className="text-xs text-slate-500 max-w-sm mt-1">
                    Start camera or upload an image to track physical desk objects and use Find It.
                  </p>
                </div>
              )}

              {/* Status Pill */}
              {capturedImage && (
                <div className="absolute top-3 left-3 flex items-center gap-2 rounded-full bg-slate-950/90 px-3 py-1 text-[11px] font-medium text-cyan-300 border border-cyan-500/30 font-mono pointer-events-none">
                  <Eye className="h-3.5 w-3.5" />
                  <span>
                    {uploadedFileName || "Workspace Frame"} • {visibleTracks.length} Active Tracks
                  </span>
                </div>
              )}
            </div>

            <canvas ref={canvasRef} className="hidden" />

            {/* Action Toolbar */}
            <div className="mt-6 flex flex-wrap items-center gap-3 pt-4 border-t border-white/5">
              {!cameraActive ? (
                <button
                  type="button"
                  onClick={startCamera}
                  className="inline-flex items-center gap-2 rounded-xl bg-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
                >
                  <Camera className="h-4 w-4" />
                  <span>Start Camera</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={stopCamera}
                  className="inline-flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition"
                >
                  <CameraOff className="h-4 w-4" />
                  <span>Stop Camera</span>
                </button>
              )}

              {cameraActive && (
                <button
                  type="button"
                  onClick={captureFrame}
                  className="inline-flex items-center gap-2 rounded-xl border border-cyan-500/30 bg-cyan-950/40 px-4 py-2.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/40 transition"
                >
                  <Eye className="h-4 w-4" />
                  <span>Capture Frame</span>
                </button>
              )}

              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={handleFileUpload}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:text-white hover:bg-white/10 transition"
              >
                <Upload className="h-4 w-4" />
                <span>Upload Image</span>
              </button>

              {/* Main Analysis Button */}
              <button
                type="button"
                onClick={runAnalysis}
                disabled={analyzing || !capturedImage}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-500 to-amber-500 px-5 py-2.5 text-xs font-semibold text-slate-950 shadow-[0_0_15px_rgba(6,182,212,0.3)] hover:opacity-95 transition disabled:opacity-50"
              >
                <Sparkles className={`h-4 w-4 ${analyzing ? "animate-spin text-slate-950" : ""}`} />
                <span>
                  {analyzing
                    ? "Running Local Inference..."
                    : analysisMode === "OBJECTS"
                    ? "Run YOLO-X Detection & Track"
                    : analysisMode === "TEXT"
                    ? "Run EasyOCR Reading"
                    : "Run Dual Analysis (Vision + OCR)"}
                </span>
              </button>

              {capturedImage && (
                <Link
                  href={`/chat?${capturedFileId ? `image_id=${encodeURIComponent(capturedFileId)}` : ""}`}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-500/40 bg-cyan-950/40 px-4 py-2.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/40 hover:text-white transition shadow-[0_0_12px_rgba(6,182,212,0.2)]"
                >
                  <MessageSquare className="h-4 w-4 text-cyan-400" />
                  <span>Ask SENTINEL</span>
                </Link>
              )}

              {/* Confidence Threshold Control */}
              <div
                className="flex items-center gap-2 ml-auto text-xs font-mono text-slate-400"
                title="Confidence Threshold: Minimum score filter"
              >
                <span className="text-[11px]">Threshold:</span>
                <input
                  type="range"
                  min="0.1"
                  max="0.9"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                  className="w-16 accent-cyan-400 cursor-pointer"
                />
                <span className="text-cyan-300 font-bold w-9 text-right">
                  {(confidenceThreshold * 100).toFixed(0)}%
                </span>
              </div>

              {/* Clear */}
              {(capturedImage || visionResult || ocrResult || workspaceState) && (
                <button
                  type="button"
                  onClick={clearAnalysis}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 px-3 py-2.5 text-xs text-slate-400 hover:text-white hover:bg-white/5 transition"
                  title="Clear image and results"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Clear</span>
                </button>
              )}
            </div>
          </div>

          {/* RIGHT COLUMN: Find It Console, Tracked Objects & Telemetry */}
          <div className="flex flex-col gap-5">
            {/* 1. FIND IT CONSOLE (Section 9, 10, 12) */}
            <div className="rounded-3xl border border-cyan-500/30 bg-slate-900/80 p-5 backdrop-blur-xl shadow-[0_0_20px_rgba(6,182,212,0.15)]">
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-white/10">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-cyan-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">
                    Find It — Workspace Localization
                  </h3>
                </div>
                <span className="text-[10px] font-mono bg-cyan-950/60 text-cyan-300 px-2 py-0.5 rounded border border-cyan-500/30">
                  GROUNDED SEARCH
                </span>
              </div>

              {/* Find It Input */}
              <form onSubmit={handleFindIt} className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type="text"
                    value={findQuery}
                    onChange={(e) => setFindQuery(e.target.value)}
                    placeholder="Where is my water bottle?"
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
                  />
                </div>
                {/* Voice Search Button */}
                <button
                  type="button"
                  onClick={() => setIsVoiceModalOpen(true)}
                  className="flex items-center gap-1 rounded-xl border border-cyan-500/40 bg-cyan-950/40 px-3 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/60 hover:text-white transition"
                  title="Speak Find It Query (Whisper STT)"
                >
                  <Mic className="h-3.5 w-3.5 text-cyan-400" />
                  <span className="hidden sm:inline">Voice</span>
                </button>
                <button
                  type="submit"
                  disabled={findSearching || !findQuery.trim()}
                  className="flex items-center gap-1.5 rounded-xl bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-400 transition disabled:opacity-50"
                >
                  <Crosshair className={`h-3.5 w-3.5 ${findSearching ? "animate-spin" : ""}`} />
                  <span>Find</span>
                </button>
              </form>

              {/* Find It Results Card */}
              {findResult && (
                <div className="mt-3.5 rounded-2xl border border-white/10 bg-slate-950/80 p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold font-mono uppercase ${
                          findResult.match_type === "CURRENT_VISIBLE"
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                            : findResult.match_type === "RECENTLY_SEEN"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : findResult.match_type === "AMBIGUOUS"
                            ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                            : findResult.match_type === "STALE"
                            ? "bg-slate-500/20 text-slate-300 border border-slate-500/30"
                            : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        }`}
                      >
                        {findResult.match_type}
                      </span>
                      <span className="text-xs font-bold text-white capitalize">
                        {findResult.object}
                      </span>
                    </div>

                    {findResult.confidence !== null && findResult.confidence !== undefined && (
                      <span className="text-xs font-mono text-cyan-300">
                        {(findResult.confidence * 100).toFixed(0)}% Match
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    {findResult.message}
                  </p>

                  {/* Spatial Region & Last Seen */}
                  <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-400">
                    {findResult.region && (
                      <span className="flex items-center gap-1 rounded bg-slate-900 px-2 py-0.5 border border-white/5">
                        <MapPin className="h-3 w-3 text-cyan-400" />
                        Region: <strong className="text-slate-200">{findResult.region}</strong>
                      </span>
                    )}
                    {findResult.last_seen && (
                      <span className="rounded bg-slate-900 px-2 py-0.5 border border-white/5">
                        Last seen: <strong className="text-slate-200">{findResult.last_seen}</strong>
                      </span>
                    )}
                  </div>

                  {/* Relations */}
                  {findResult.relations && findResult.relations.length > 0 && (
                    <div className="space-y-1 pt-1 border-t border-white/5">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                        Spatial Relations:
                      </span>
                      {findResult.relations.slice(0, 3).map((rel, rIdx) => (
                        <div key={rIdx} className="flex items-center gap-1.5 text-xs text-slate-300 font-mono">
                          <Compass className="h-3 w-3 text-cyan-400 shrink-0" />
                          <span>{rel}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Ambiguity Candidates */}
                  {findResult.candidates && findResult.candidates.length > 1 && (
                    <div className="pt-2 border-t border-white/5 space-y-1.5">
                      <span className="text-[10px] text-purple-300 font-bold uppercase block">
                        Multiple candidates found:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {findResult.candidates.map((cand, cIdx) => (
                          <button
                            key={cIdx}
                            type="button"
                            onClick={() => {
                              setGroundedTrackId(cand.track_id);
                              setSelectedTrackId(cand.track_id);
                            }}
                            className={`rounded-lg px-2 py-1 text-[11px] font-mono transition border ${
                              groundedTrackId === cand.track_id
                                ? "border-cyan-400 bg-cyan-950 text-cyan-300 ring-2 ring-cyan-400"
                                : "border-white/10 bg-slate-900 text-slate-300 hover:bg-slate-800"
                            }`}
                          >
                            [{cand.track_id}] {cand.object} in {cand.region}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Show on Workspace Action */}
                  {findResult.track_id && (
                    <div className="pt-2 border-t border-white/5 flex items-center justify-between">
                      <button
                        type="button"
                        onClick={() => {
                          setGroundedTrackId(findResult.track_id || null);
                          setSelectedTrackId(findResult.track_id || null);
                        }}
                        className="flex items-center gap-1.5 text-xs font-semibold text-cyan-300 hover:text-cyan-200 transition"
                      >
                        <Crosshair className="h-3.5 w-3.5 text-cyan-400" />
                        <span>Show on workspace</span>
                      </button>

                      {groundedTrackId && (
                        <button
                          type="button"
                          onClick={() => setGroundedTrackId(null)}
                          className="text-[11px] text-slate-400 hover:text-white"
                        >
                          Clear Highlight
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 2. TRACKED OBJECTS & REMEMBER THIS (Section 2, 7, 8) */}
            <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-5 backdrop-blur-xl">
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-cyan-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Tracked Workspace Objects
                  </h3>
                </div>
                <span className="text-xs font-mono text-cyan-300 font-bold">
                  {visibleTracks.length > 0 ? visibleTracks.length : visibleObjects.length} Active
                </span>
              </div>

              {visibleTracks.length > 0 ? (
                <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                  {visibleTracks.map((track) => {
                    const isSelected = selectedTrackId === track.track_id;
                    const isGrounded = groundedTrackId === track.track_id;

                    return (
                      <div
                        key={track.track_id}
                        className={`p-2.5 rounded-2xl border transition text-xs font-mono ${
                          isGrounded
                            ? "border-cyan-400 bg-cyan-950/60 ring-2 ring-cyan-400"
                            : isSelected
                            ? "border-cyan-400 bg-cyan-950/40 shadow-[0_0_15px_rgba(6,182,212,0.2)]"
                            : "border-white/5 bg-slate-950/60 hover:bg-slate-950/90"
                        }`}
                      >
                        <div
                          className="flex items-center justify-between cursor-pointer"
                          onClick={() => setSelectedTrackId(isSelected ? null : track.track_id)}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-cyan-400 font-bold">[{track.track_id}]</span>
                            <span className="font-bold text-white capitalize">
                              {track.user_label ? `"${track.user_label}" (${track.class_name})` : track.class_name}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[11px] text-slate-400">{track.region}</span>
                            <span className="font-bold text-emerald-400">
                              {(track.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>

                        {/* Expandable actions when selected */}
                        {isSelected && (
                          <div className="mt-2.5 pt-2 border-t border-white/5 flex flex-col gap-2">
                            <div className="flex items-center justify-between text-[11px] text-slate-400">
                              <span>Seen: {track.frames_seen} frames</span>
                              <span>Status: {track.visibility_state}</span>
                            </div>

                            {/* Remember This Object Input */}
                            {rememberingTrackId === track.track_id ? (
                              <div className="flex items-center gap-1.5 mt-1">
                                <input
                                  type="text"
                                  value={rememberLabelInput}
                                  onChange={(e) => setRememberLabelInput(e.target.value)}
                                  placeholder="e.g. my water bottle"
                                  className="flex-1 rounded-lg border border-white/10 bg-slate-900 px-2.5 py-1 text-xs text-white"
                                />
                                <button
                                  type="button"
                                  disabled={rememberSaving || !rememberLabelInput.trim()}
                                  onClick={() => handleSaveRememberLabel(track.track_id)}
                                  className="rounded-lg bg-emerald-500 px-2.5 py-1 text-xs font-bold text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
                                >
                                  Save
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setRememberingTrackId(null)}
                                  className="text-xs text-slate-400 hover:text-white px-1"
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                onClick={() => {
                                  setRememberingTrackId(track.track_id);
                                  setRememberLabelInput(track.user_label || "");
                                }}
                                className="flex items-center gap-1.5 text-[11px] text-cyan-300 hover:text-cyan-200 mt-1"
                              >
                                <Tag className="h-3 w-3" />
                                <span>{track.user_label ? "Edit Name" : "Remember This Object"}</span>
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : visibleObjects.length > 0 ? (
                <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                  {visibleObjects.map((det, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-2xl border border-white/5 bg-slate-950/60 flex items-center justify-between text-xs font-mono"
                    >
                      <span className="font-bold text-white capitalize">{det.label}</span>
                      <span className="text-emerald-400 font-bold">{(det.confidence * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-4 text-center text-xs text-slate-500">
                  Run detection to populate tracked workspace objects.
                </p>
              )}
            </div>

            {/* 3. OCR Text Detections */}
            {(analysisMode === "TEXT" || analysisMode === "BOTH") && (
              <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-5 backdrop-blur-xl">
                <div className="flex items-center justify-between mb-3 pb-2 border-b border-white/5">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-amber-400" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                      Workspace Text (OCR)
                    </h3>
                  </div>
                  <span className="text-xs font-mono text-amber-300 font-bold">
                    {visibleOcrRegions.length} Regions
                  </span>
                </div>

                {ocrResult ? (
                  visibleOcrRegions.length > 0 ? (
                    <div className="flex flex-col gap-3">
                      <div className="space-y-2 max-h-[160px] overflow-y-auto pr-1">
                        {visibleOcrRegions.map((reg, idx) => (
                          <div
                            key={reg.id || idx}
                            className="p-2 rounded-xl border border-white/5 bg-slate-950/60 flex items-center justify-between text-xs font-mono"
                          >
                            <span className="font-semibold text-white truncate max-w-[70%]">{reg.text}</span>
                            <span className="text-amber-400 font-bold">{(reg.confidence * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>

                      {/* Full Text Snippet & Copy Action */}
                      <div className="rounded-2xl border border-white/5 bg-slate-950/80 p-3">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[10px] uppercase font-bold text-slate-400 font-mono">
                            Full Recognized Text
                          </span>
                          <button
                            type="button"
                            onClick={copyExtractedText}
                            className="flex items-center gap-1 text-[11px] text-amber-300 hover:text-amber-200 transition"
                          >
                            <Copy className="h-3 w-3" />
                            <span>{copiedText ? "Copied!" : "Copy"}</span>
                          </button>
                        </div>
                        <p className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed bg-slate-900/50 p-2 rounded-xl max-h-[80px] overflow-y-auto">
                          {ocrResult.full_text}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <p className="py-4 text-center text-xs text-slate-500">No supported text detected.</p>
                  )
                ) : (
                  <p className="py-4 text-center text-xs text-slate-500">
                    Run analysis to extract visible text from workspace.
                  </p>
                )}
              </div>
            )}

            {/* 4. Execution Telemetry & Diagnostics Toggle */}
            <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-5 backdrop-blur-xl">
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-cyan-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Execution Telemetry
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowDiagnostics(!showDiagnostics)}
                  className="text-[11px] text-slate-400 hover:text-cyan-300 transition font-mono"
                >
                  {showDiagnostics ? "Hide Diagnostics" : "Show Diagnostics"}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded-xl bg-slate-950/60 border border-white/5">
                  <span className="text-[10px] uppercase text-slate-400 block mb-0.5">Tracking State</span>
                  <span className="font-semibold text-emerald-400">
                    {workspaceTrackingActive ? "ACTIVE" : "IDLE"}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-950/60 border border-white/5">
                  <span className="text-[10px] uppercase text-slate-400 block mb-0.5">Snapdragon NPU</span>
                  <span className="font-semibold text-amber-400">NOT VERIFIED</span>
                </div>
              </div>

              {/* Collapsible Diagnostics Section */}
              {showDiagnostics && (
                <div className="mt-3 pt-3 border-t border-white/5 space-y-2 text-xs font-mono">
                  <div className="flex justify-between text-slate-400 text-[11px]">
                    <span>Active Tracks:</span>
                    <span className="text-slate-200">{visibleTracks.length}</span>
                  </div>
                  {workspaceState?.relations && workspaceState.relations.length > 0 && (
                    <div className="space-y-1 pt-1 border-t border-white/5">
                      <span className="text-[10px] text-slate-400 uppercase">Active Relations:</span>
                      {workspaceState.relations.map((r, i) => (
                        <div key={i} className="text-[11px] text-slate-300">
                          • {r.description}
                        </div>
                      ))}
                    </div>
                  )}
                  {visionResult?.timing && (
                    <div className="space-y-1 pt-1 border-t border-white/5">
                      <div className="flex justify-between text-slate-400 text-[11px]">
                        <span>YOLO-X Latency:</span>
                        <span className="text-cyan-300">{visionResult.timing.total_ms} ms</span>
                      </div>
                      <div className="flex justify-between text-slate-400 text-[11px]">
                        <span>Inference (CPU):</span>
                        <span className="text-slate-300">{visionResult.timing.inference_ms} ms</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Voice Assistant Modal for Vision Find It */}
      <VoiceAssistantModal
        isOpen={isVoiceModalOpen}
        onClose={() => setIsVoiceModalOpen(false)}
        onActionComplete={(act) => {
          if (act.intent === "FIND_IT") {
            setFindQuery(act.raw_query || act.grounded_target_name || "");
            if (act.grounded_target_id) {
              setGroundedTrackId(act.grounded_target_id);
              setSelectedTrackId(act.grounded_target_id);
            }
            if (act.action_data && act.action_data.match_type) {
              setFindResult(act.action_data as FindItResponse);
            }
          }
        }}
      />
    </div>
  );
}
