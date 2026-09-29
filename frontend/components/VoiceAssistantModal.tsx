"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Mic,
  MicOff,
  Square,
  Sparkles,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Layers,
  Search,
  ExternalLink,
  X,
  Volume2,
  Clock,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  MicrophoneState,
  SpeechTranscribeResponse,
  VoiceActionResult,
} from "@/lib/types";
import { useRouter } from "next/navigation";

interface VoiceAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId?: string;
  onActionComplete?: (result: VoiceActionResult) => void;
}

export function VoiceAssistantModal({
  isOpen,
  onClose,
  projectId = "default",
  onActionComplete,
}: VoiceAssistantModalProps) {
  const router = useRouter();
  const [micState, setMicState] = useState<MicrophoneState>("IDLE");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [recordingSeconds, setRecordingSeconds] = useState<number>(0);
  const [transcribeResult, setTranscribeResult] = useState<SpeechTranscribeResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Clean up recording timer and stream on unmount or close
  useEffect(() => {
    return () => {
      stopRecordingResources();
    };
  }, []);

  useEffect(() => {
    if (!isOpen) {
      stopRecordingResources();
      setMicState("IDLE");
      setErrorMessage(null);
    }
  }, [isOpen]);

  const stopRecordingResources = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        console.error("Error stopping recorder", e);
      }
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const startRecording = async () => {
    setErrorMessage(null);
    setTranscribeResult(null);
    setRecordingSeconds(0);
    setMicState("REQUESTING_PERMISSION");

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Microphone API is not supported in this browser environment.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      streamRef.current = stream;
      setMicState("READY");

      // Choose supported MIME type
      let mimeType = "audio/webm";
      if (!MediaRecorder.isTypeSupported("audio/webm")) {
        if (MediaRecorder.isTypeSupported("audio/ogg")) {
          mimeType = "audio/ogg";
        } else {
          mimeType = "";
        }
      }

      const options = mimeType ? { mimeType } : undefined;
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        await handleAudioProcessing();
      };

      mediaRecorder.start(250); // collect 250ms chunks
      setMicState("RECORDING");

      // Start timer (max 30s limit for safety)
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => {
          if (prev >= 29) {
            stopRecording();
            return 30;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err: any) {
      console.error("Microphone access error:", err);
      setMicState("ERROR");
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setErrorMessage("Microphone permission was denied. Please allow microphone access in your browser settings.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setErrorMessage("No microphone device was detected on your computer.");
      } else {
        setErrorMessage(err.message || "Failed to initialize microphone.");
      }
      stopRecordingResources();
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      setMicState("PROCESSING");
      setIsProcessing(true);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      mediaRecorderRef.current.stop();
    }
  };

  const handleAudioProcessing = async () => {
    setIsProcessing(true);
    setMicState("PROCESSING");

    try {
      const audioBlob = new Blob(audioChunksRef.current, {
        type: mediaRecorderRef.current?.mimeType || "audio/webm",
      });

      // Release microphone hardware immediately (Privacy by design)
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }

      // Convert blob to base64
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve, reject) => {
        reader.onloadend = () => {
          const res = reader.result as string;
          resolve(res);
        };
        reader.onerror = reject;
      });
      reader.readAsDataURL(audioBlob);
      const audioBase64 = await base64Promise;

      // Send to local speech engine
      const resp = await api.transcribeSpeech({
        audio_base64: audioBase64,
        audio_format: "wav",
        sample_rate: 16000,
        project_id: projectId,
        route_intent: true,
        save_audio: false, // Invariant: Raw audio discarded
      });

      setTranscribeResult(resp);
      setMicState("TRANSCRIBED");

      if (resp.action_result && onActionComplete) {
        onActionComplete(resp.action_result);
      }
    } catch (err: any) {
      console.error("Transcription error:", err);
      setMicState("ERROR");
      setErrorMessage(err.message || "Failed to transcribe audio.");
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  const action = transcribeResult?.action_result;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-2xl border border-white/10 bg-slate-900/95 p-6 shadow-2xl text-slate-100 flex flex-col gap-5 overflow-hidden">
        {/* Glow Accent */}
        <div className="absolute -top-24 -left-24 h-48 w-48 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 h-48 w-48 rounded-full bg-purple-500/10 blur-3xl pointer-events-none" />

        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-600 to-cyan-400 text-slate-950 shadow-md">
              <Mic className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-lg text-white">Voice Workspace Assistant</h3>
                <span className="rounded-md border border-cyan-500/30 bg-cyan-950/40 px-2 py-0.5 text-[10px] font-medium text-cyan-300">
                  Whisper Local STT
                </span>
              </div>
              <p className="text-xs text-slate-400">Speak commands for Find It, Memory, or Workspace queries</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white/5 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Central Audio Recording Interface */}
        <div className="flex flex-col items-center justify-center py-6 px-4 rounded-xl border border-white/5 bg-slate-950/60 relative">
          {/* Recording Pulse Rings */}
          {micState === "RECORDING" && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <span className="absolute h-32 w-32 rounded-full bg-rose-500/20 animate-ping opacity-60" />
              <span className="absolute h-44 w-44 rounded-full bg-rose-500/10 animate-pulse" />
            </div>
          )}

          {/* Mic Button */}
          <button
            type="button"
            onClick={micState === "RECORDING" ? stopRecording : startRecording}
            disabled={isProcessing || micState === "REQUESTING_PERMISSION"}
            className={`relative z-10 flex h-20 w-20 items-center justify-center rounded-full shadow-2xl transition-all duration-300 ${
              micState === "RECORDING"
                ? "bg-rose-500 text-white hover:bg-rose-600 shadow-[0_0_35px_rgba(244,63,94,0.6)] scale-105"
                : isProcessing
                ? "bg-slate-800 text-cyan-400 animate-pulse cursor-not-allowed border border-cyan-500/30"
                : "bg-gradient-to-tr from-cyan-600 to-cyan-400 text-slate-950 hover:scale-105 shadow-[0_0_25px_rgba(6,182,212,0.4)]"
            }`}
          >
            {micState === "RECORDING" ? (
              <Square className="h-8 w-8 fill-current" />
            ) : isProcessing ? (
              <Cpu className="h-8 w-8 animate-spin" />
            ) : (
              <Mic className="h-8 w-8" />
            )}
          </button>

          {/* Status Label & Timer */}
          <div className="mt-4 flex flex-col items-center gap-1 z-10">
            {micState === "RECORDING" ? (
              <>
                <div className="flex items-center gap-2 text-rose-400 font-semibold text-sm">
                  <span className="h-2 w-2 rounded-full bg-rose-400 animate-ping" />
                  <span>RECORDING (Click to Stop)</span>
                </div>
                <div className="flex items-center gap-1.5 font-mono text-xs text-slate-300">
                  <Clock className="h-3.5 w-3.5 text-slate-400" />
                  <span>00:{recordingSeconds < 10 ? `0${recordingSeconds}` : recordingSeconds} / 00:30</span>
                </div>
              </>
            ) : isProcessing ? (
              <div className="flex items-center gap-2 text-cyan-400 text-sm font-medium animate-pulse">
                <span>Transcribing locally with Whisper CPU...</span>
              </div>
            ) : micState === "TRANSCRIBED" ? (
              <span className="text-xs text-slate-400">Click mic to record another query</span>
            ) : (
              <>
                <span className="text-sm font-medium text-slate-200">Click to Speak</span>
                <span className="text-xs text-slate-500">e.g. &ldquo;Where is my water bottle?&rdquo;</span>
              </>
            )}
          </div>
        </div>

        {/* Error Notification */}
        {errorMessage && (
          <div className="flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold">Microphone Notice: </span>
              {errorMessage}
            </div>
          </div>
        )}

        {/* Transcription and Action Result Display */}
        {transcribeResult && (
          <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-slate-950/70 p-4">
            {/* Recognized Text */}
            <div className="flex items-start justify-between gap-2 border-b border-white/5 pb-2.5">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">You Said</span>
                <p className="text-sm font-medium text-white italic">
                  &ldquo;{transcribeResult.text || "(Silence or no speech detected)"}&rdquo;
                </p>
              </div>
              <div className="flex items-center gap-1.5 text-[10px] font-mono text-cyan-300 bg-cyan-950/50 border border-cyan-800/40 rounded px-2 py-0.5 shrink-0">
                <span>{transcribeResult.duration_ms.toFixed(0)}ms</span>
                {transcribeResult.real_time_factor && (
                  <span>• RTF {transcribeResult.real_time_factor}</span>
                )}
              </div>
            </div>

            {/* Action Result Card */}
            {action && (
              <div className="flex flex-col gap-2 pt-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold tracking-wide text-slate-300">
                    INTENT:{" "}
                    <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-cyan-300 font-mono">
                      {action.intent}
                    </span>
                  </span>
                  {action.grounded_confidence && (
                    <span className="text-[11px] text-emerald-400 font-mono">
                      Confidence: {(action.grounded_confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>

                <div className="rounded-lg border border-cyan-500/20 bg-cyan-950/20 p-3 text-xs text-slate-200">
                  <p className="leading-relaxed">{action.summary}</p>

                  {/* Grounded Workspace Data */}
                  {action.grounded_target_id && (
                    <div className="mt-2.5 flex flex-wrap items-center gap-2 pt-2 border-t border-cyan-900/40">
                      <span className="rounded bg-cyan-900/60 px-2 py-0.5 font-mono text-[10px] text-cyan-200">
                        Track ID: {action.grounded_target_id}
                      </span>
                      {action.grounded_region && (
                        <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300 uppercase">
                          Region: {action.grounded_region}
                        </span>
                      )}
                      {action.grounded_relations.length > 0 && (
                        <span className="text-[11px] text-slate-400">
                          {action.grounded_relations.join(", ")}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Quick Action Navigation */}
                <div className="flex items-center justify-end gap-2 mt-1">
                  {action.intent === "FIND_IT" && (
                    <button
                      onClick={() => {
                        onClose();
                        router.push(`/vision?target=${action.grounded_target_id || ""}`);
                      }}
                      className="flex items-center gap-1.5 rounded-lg bg-cyan-500/20 border border-cyan-400/30 px-3 py-1.5 text-xs font-medium text-cyan-300 hover:bg-cyan-500/30 transition"
                    >
                      <Search className="h-3.5 w-3.5" />
                      <span>Show on Workspace Vision</span>
                    </button>
                  )}
                  {action.intent === "SEARCH_MEMORY" && (
                    <button
                      onClick={() => {
                        onClose();
                        router.push("/memory");
                      }}
                      className="flex items-center gap-1.5 rounded-lg bg-purple-500/20 border border-purple-400/30 px-3 py-1.5 text-xs font-medium text-purple-300 hover:bg-purple-500/30 transition"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      <span>View in Memory</span>
                    </button>
                  )}
                  {(action.intent === "ASK_SENTINEL" || action.intent === "GENERAL_QUERY") && (
                    <button
                      onClick={() => {
                        onClose();
                        router.push(`/chat?q=${encodeURIComponent(transcribeResult.text)}`);
                      }}
                      className="flex items-center gap-1.5 rounded-lg bg-cyan-500/20 border border-cyan-400/30 px-3 py-1.5 text-xs font-medium text-cyan-300 hover:bg-cyan-500/30 transition"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      <span>Open in Ask SENTINEL</span>
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Privacy & Hardware Guarantee Footer */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 border-t border-white/10 pt-3 text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5 text-emerald-400">
            <ShieldCheck className="h-4 w-4 shrink-0" />
            <span>100% Local Inference • Zero Cloud Transmission • Audio Discarded</span>
          </div>
          <div className="flex items-center gap-1 font-mono text-[10px] text-slate-500">
            <span>Target: Snapdragon X Elite (NPU NOT VERIFIED)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
