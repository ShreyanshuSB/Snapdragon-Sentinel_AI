"use client";

import React from "react";
import { TextRegion } from "@/lib/types";

interface TextOverlayProps {
  imageSrc?: string | null;
  regions: TextRegion[];
  selectedIndex: number | null;
  onSelect: (index: number | null) => void;
  className?: string;
}

export function TextOverlay({
  imageSrc,
  regions,
  selectedIndex,
  onSelect,
  className = "",
}: TextOverlayProps) {
  return (
    <div
      className={`relative flex items-center justify-center w-full h-full max-h-[600px] select-none rounded-xl bg-slate-950 overflow-hidden ${className}`}
    >
      <div className="relative inline-block max-w-full max-h-[600px]">
        {/* Base Image if provided */}
        {imageSrc && (
          <img
            src={imageSrc}
            alt="Analyzed Frame"
            className="block max-w-full max-h-[600px] w-auto h-auto object-contain rounded-lg"
          />
        )}

        {/* OCR Text Box Layer */}
        <div className="absolute inset-0 pointer-events-none">
          {regions.map((reg, idx) => {
            const isSelected = selectedIndex === idx;
            const leftPct = (reg.bbox.x !== undefined ? reg.bbox.x : reg.bbox.x_min) * 100;
            const topPct = (reg.bbox.y !== undefined ? reg.bbox.y : reg.bbox.y_min) * 100;
            const widthPct = Math.max(
              0.8,
              (reg.bbox.width !== undefined ? reg.bbox.width : reg.bbox.x_max - reg.bbox.x_min) * 100
            );
            const heightPct = Math.max(
              0.8,
              (reg.bbox.height !== undefined ? reg.bbox.height : reg.bbox.y_max - reg.bbox.y_min) * 100
            );

            const isNearTop = topPct < 7;

            return (
              <div
                key={reg.id || idx}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelect(isSelected ? null : idx);
                }}
                style={{
                  left: `${leftPct}%`,
                  top: `${topPct}%`,
                  width: `${widthPct}%`,
                  height: `${heightPct}%`,
                }}
                className={`absolute pointer-events-auto cursor-pointer border-2 transition-all duration-150 ${
                  isSelected
                    ? "border-amber-400 bg-amber-500/25 shadow-[0_0_15px_rgba(245,158,11,0.6)] z-30 scale-[1.01]"
                    : "border-amber-400/80 bg-amber-500/10 hover:border-amber-300 hover:bg-amber-500/20 z-10"
                }`}
                title={`${reg.text} (${(reg.confidence * 100).toFixed(1)}%)`}
              >
                {/* Region Label Tag */}
                <div
                  className={`absolute ${
                    isNearTop ? "top-1 left-1" : "-top-6 left-0"
                  } flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold font-mono whitespace-nowrap shadow-md transition ${
                    isSelected
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
