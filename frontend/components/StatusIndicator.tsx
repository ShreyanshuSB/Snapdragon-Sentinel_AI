import React from "react";

interface StatusIndicatorProps {
  tone: "ready" | "not_connected" | "loading" | "error" | "disabled";
  label?: string;
  size?: "sm" | "md";
}

export function StatusIndicator({ tone, label, size = "md" }: StatusIndicatorProps) {
  const dotSize = size === "sm" ? "h-2 w-2" : "h-2.5 w-2.5";
  const textSize = size === "sm" ? "text-xs" : "text-sm";

  const config = {
    ready: {
      color: "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]",
      textColor: "text-emerald-300",
      defaultLabel: "Ready",
    },
    not_connected: {
      color: "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.4)]",
      textColor: "text-amber-300",
      defaultLabel: "Not Connected",
    },
    loading: {
      color: "bg-cyan-400 animate-pulse",
      textColor: "text-cyan-300",
      defaultLabel: "Loading...",
    },
    error: {
      color: "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]",
      textColor: "text-rose-300",
      defaultLabel: "Error",
    },
    disabled: {
      color: "bg-slate-600",
      textColor: "text-slate-400",
      defaultLabel: "Disabled",
    },
  }[tone];

  return (
    <div className="inline-flex items-center gap-2">
      <span className={`inline-block rounded-full ${dotSize} ${config.color}`} aria-hidden="true" />
      <span className={`font-medium ${textSize} ${config.textColor}`}>
        {label || config.defaultLabel}
      </span>
    </div>
  );
}
