"use client";

import React from "react";
import { BoundingBox, Detection, TextRegion, TrackedObject } from "@/lib/types";

interface DetectionOverlayProps {
  imageSrc?: string;
  detections?: Detection[];
  trackedObjects?: TrackedObject[];
  textRegions?: TextRegion[];
  selectedIndex?: number | null;
  selectedTrackId?: string | null;
  selectedTextIndex?: number | null;
  hoveredIndex?: number | null;
  hoveredTextIndex?: number | null;
  groundedTrackId?: string | null;
  onSelect?: (index: number | null) => void;
  onSelectTrack?: (trackId: string | null) => void;
  onSelectText?: (index: number | null) => void;
  onHover?: (index: number | null) => void;
  onHoverText?: (index: number | null) => void;
  originalWidth?: number;
  originalHeight?: number;
}

// Consistent semantic color palette for object bounding boxes
const COLOR_PALETTE = [
  { border: "border-cyan-400", bg: "bg-cyan-500/20", badge: "bg-cyan-500 text-slate-950", glow: "shadow-[0_0_15px_rgba(6,182,212,0.6)]" },
  { border: "border-emerald-400", bg: "bg-emerald-500/20", badge: "bg-emerald-500 text-slate-950", glow: "shadow-[0_0_15px_rgba(16,185,129,0.6)]" },
  { border: "border-purple-400", bg: "bg-purple-500/20", badge: "bg-purple-500 text-slate-950", glow: "shadow-[0_0_15px_rgba(168,85,247,0.6)]" },
  { border: "border-amber-400", bg: "bg-amber-500/20", badge: "bg-amber-500 text-slate-950", glow: "shadow-[0_0_15px_rgba(245,158,11,0.6)]" },
  { border: "border-blue-400", bg: "bg-blue-500/20", badge: "bg-blue-500 text-slate-950", glow: "shadow-[0_0_15px_rgba(59,130,246,0.6)]" },
  { border: "border-rose-400", bg: "bg-rose-500/20", badge: "bg-rose-500 text-slate-950", glow: "shadow-[0_0_15px_rgba(244,63,94,0.6)]" },
];

export function DetectionOverlay({
  imageSrc,
  detections = [],
  trackedObjects = [],
  textRegions = [],
  selectedIndex = null,
  selectedTrackId = null,
  selectedTextIndex = null,
  hoveredIndex = null,
  hoveredTextIndex = null,
  groundedTrackId = null,
  onSelect,
  onSelectTrack,
  onSelectText,
  onHover,
  onHoverText,
}: DetectionOverlayProps) {
  // Use trackedObjects if present, else fallback to raw detections
  const hasTracks = trackedObjects.length > 0;

  return (
    <div className="relative flex items-center justify-center w-full h-full max-h-[600px] select-none rounded-xl bg-slate-950 overflow-hidden">
      {/* Container matching rendered image dimensions */}
      <div className="relative inline-block max-w-full max-h-[600px]">
        {/* Base Image */}
        {imageSrc && (
          <img
            src={imageSrc}
            alt="Analyzed Frame"
            className="block max-w-full max-h-[600px] w-auto h-auto object-contain rounded-lg"
          />
        )}

        {/* Bounding Box Overlay Layer */}
        <div className="absolute inset-0 pointer-events-none">
          {/* 1. Tracked Objects (Step 5 Tracking & Grounding) */}
          {hasTracks &&
            trackedObjects.map((track, idx) => {
              const isSelected = selectedTrackId === track.track_id;
              const isGrounded = groundedTrackId === track.track_id;
              const isHovered = hoveredIndex === idx;
              const isActive = isSelected || isHovered || isGrounded;
              const color = COLOR_PALETTE[track.class_id % COLOR_PALETTE.length];

              const box: BoundingBox = track.smoothed_bbox || track.raw_bbox;
              const leftPct = (box.x !== undefined ? box.x : box.x_min) * 100;
              const topPct = (box.y !== undefined ? box.y : box.y_min) * 100;
              const widthPct = Math.max(0.5, (box.width !== undefined ? box.width : box.x_max - box.x_min) * 100);
              const heightPct = Math.max(0.5, (box.height !== undefined ? box.height : box.y_max - box.y_min) * 100);

              const isNearTop = topPct < 7;
              const displayName = track.user_label ? `"${track.user_label}"` : track.class_name;

              return (
                <div
                  key={`track-${track.track_id}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectTrack?.(isSelected ? null : track.track_id);
                  }}
                  onMouseEnter={() => onHover?.(idx)}
                  onMouseLeave={() => onHover?.(null)}
                  style={{
                    left: `${leftPct}%`,
                    top: `${topPct}%`,
                    width: `${widthPct}%`,
                    height: `${heightPct}%`,
                  }}
                  className={`absolute pointer-events-auto cursor-pointer border-2 transition-all duration-150 ${
                    isGrounded
                      ? "border-cyan-300 ring-4 ring-cyan-400/50 bg-cyan-400/25 shadow-[0_0_25px_rgba(34,211,238,0.9)] z-40 animate-pulse"
                      : isActive
                      ? `${color.border} ${color.bg} ${color.glow} z-30 scale-[1.01]`
                      : `${color.border} bg-transparent hover:bg-white/5 z-10`
                  }`}
                  title={`[${track.track_id}] ${displayName} (${(track.confidence * 100).toFixed(0)}%) - ${track.region}`}
                >
                  {/* Target Grounded Badge */}
                  {isGrounded && (
                    <div className="absolute -top-7 right-0 flex items-center gap-1 bg-cyan-400 text-slate-950 px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider shadow-lg">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-950 animate-ping" />
                      Target Found
                    </div>
                  )}

                  {/* Box Tag Header */}
                  <div
                    className={`absolute ${
                      isNearTop ? "top-1 left-1" : "-top-6 left-0"
                    } flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold font-mono whitespace-nowrap shadow-md transition pointer-events-none ${
                      isGrounded
                        ? "bg-cyan-400 text-slate-950 ring-2 ring-white scale-105 opacity-100"
                        : color.badge
                    } ${isActive ? "ring-2 ring-white scale-105 opacity-100" : "opacity-90"}`}
                  >
                    <span className="opacity-80 text-[9px]">[{track.track_id}]</span>
                    <span className="capitalize">{displayName}</span>
                    <span className="opacity-85 text-[9px]">{(track.confidence * 100).toFixed(0)}%</span>
                  </div>

                  {/* Bottom region tag */}
                  <div className="absolute bottom-1 right-1 px-1.5 py-0.2 bg-slate-950/80 text-slate-300 rounded text-[9px] font-mono opacity-85">
                    {track.region}
                  </div>
                </div>
              );
            })}

          {/* 2. Raw Object Detections (when tracking is not active) */}
          {!hasTracks &&
            detections.map((det, idx) => {
              const isSelected = selectedIndex === idx;
              const isHovered = hoveredIndex === idx;
              const isActive = isSelected || isHovered;
              const color = COLOR_PALETTE[det.class_id % COLOR_PALETTE.length];

              const leftPct = (det.bbox.x !== undefined ? det.bbox.x : det.bbox.x_min) * 100;
              const topPct = (det.bbox.y !== undefined ? det.bbox.y : det.bbox.y_min) * 100;
              const widthPct = Math.max(0.5, (det.bbox.width !== undefined ? det.bbox.width : det.bbox.x_max - det.bbox.x_min) * 100);
              const heightPct = Math.max(0.5, (det.bbox.height !== undefined ? det.bbox.height : det.bbox.y_max - det.bbox.y_min) * 100);

              const isNearTop = topPct < 7;

              return (
                <div
                  key={`det-${idx}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelect?.(isSelected ? null : idx);
                  }}
                  onMouseEnter={() => onHover?.(idx)}
                  onMouseLeave={() => onHover?.(null)}
                  style={{
                    left: `${leftPct}%`,
                    top: `${topPct}%`,
                    width: `${widthPct}%`,
                    height: `${heightPct}%`,
                  }}
                  className={`absolute pointer-events-auto cursor-pointer border-2 transition-all duration-150 ${
                    color.border
                  } ${
                    isActive
                      ? `${color.bg} ${color.glow} z-30 scale-[1.01]`
                      : "bg-transparent hover:bg-white/5 z-10"
                  }`}
                  title={`${det.label} (${(det.confidence * 100).toFixed(1)}%)`}
                >
                  <div
                    className={`absolute ${
                      isNearTop ? "top-1 left-1" : "-top-6 left-0"
                    } flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold font-mono whitespace-nowrap shadow-md transition pointer-events-none ${
                      color.badge
                    } ${isActive ? "ring-2 ring-white scale-105 opacity-100" : "opacity-90"}`}
                  >
                    <span className="capitalize">{det.label}</span>
                    <span className="opacity-90">{(det.confidence * 100).toFixed(1)}%</span>
                  </div>
                </div>
              );
            })}

          {/* 3. OCR Text Regions */}
          {textRegions.map((reg, idx) => {
            const isSelected = selectedTextIndex === idx;
            const isHovered = hoveredTextIndex === idx;
            const isActive = isSelected || isHovered;

            const leftPct = (reg.bbox.x !== undefined ? reg.bbox.x : reg.bbox.x_min) * 100;
            const topPct = (reg.bbox.y !== undefined ? reg.bbox.y : reg.bbox.y_min) * 100;
            const widthPct = Math.max(0.8, (reg.bbox.width !== undefined ? reg.bbox.width : reg.bbox.x_max - reg.bbox.x_min) * 100);
            const heightPct = Math.max(0.8, (reg.bbox.height !== undefined ? reg.bbox.height : reg.bbox.y_max - reg.bbox.y_min) * 100);

            const isNearTop = topPct < 7;

            return (
              <div
                key={`ocr-${reg.id || idx}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectText?.(isSelected ? null : idx);
                }}
                onMouseEnter={() => onHoverText?.(idx)}
                onMouseLeave={() => onHoverText?.(null)}
                style={{
                  left: `${leftPct}%`,
                  top: `${topPct}%`,
                  width: `${widthPct}%`,
                  height: `${heightPct}%`,
                }}
                className={`absolute pointer-events-auto cursor-pointer border-2 transition-all duration-150 ${
                  isActive
                    ? "border-amber-400 bg-amber-500/30 shadow-[0_0_15px_rgba(245,158,11,0.7)] z-30 scale-[1.01]"
                    : "border-amber-400/80 bg-amber-500/10 hover:border-amber-300 hover:bg-amber-500/20 z-20"
                }`}
                title={`Text: ${reg.text} (${(reg.confidence * 100).toFixed(1)}%)`}
              >
                <div
                  className={`absolute ${
                    isNearTop ? "top-1 left-1" : "-top-6 left-0"
                  } flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold font-mono whitespace-nowrap shadow-md transition pointer-events-none ${
                    isActive
                      ? "bg-amber-400 text-slate-950 ring-2 ring-white scale-105"
                      : "bg-amber-500/90 text-slate-950 opacity-90"
                  }`}
                >
                  {reg.reading_order && (
                    <span className="opacity-75 font-semibold">#{reg.reading_order}</span>
                  )}
                  <span className="max-w-[120px] truncate">{reg.text}</span>
                  <span className="opacity-80">{(reg.confidence * 100).toFixed(1)}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
