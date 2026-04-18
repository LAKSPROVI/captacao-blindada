"use client";

import { cn } from "@/lib/utils";
import { ShieldAlert, ShieldCheck, ShieldQuestion, Shield } from "lucide-react";

type RiskLevel = "baixo" | "medio" | "alto" | "critico";

const riskConfig: Record<
  RiskLevel,
  { label: string; color: string; bg: string; icon: typeof Shield }
> = {
  baixo: {
    label: "Baixo",
    color: "text-risco-baixo",
    bg: "bg-green-500/10 border-green-500/30",
    icon: ShieldCheck,
  },
  medio: {
    label: "Medio",
    color: "text-risco-medio",
    bg: "bg-yellow-500/10 border-yellow-500/30",
    icon: ShieldQuestion,
  },
  alto: {
    label: "Alto",
    color: "text-risco-alto",
    bg: "bg-orange-500/10 border-orange-500/30",
    icon: ShieldAlert,
  },
  critico: {
    label: "Critico",
    color: "text-risco-critico",
    bg: "bg-red-500/10 border-red-500/30",
    icon: ShieldAlert,
  },
};

export function RiskBadge({
  level,
  score,
  showIcon = true,
  className,
}: {
  level: RiskLevel;
  score?: number;
  showIcon?: boolean;
  className?: string;
}) {
  const config = riskConfig[level] || riskConfig.medio;
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium",
        config.bg,
        config.color,
        className
      )}
    >
      {showIcon && <Icon className="h-4 w-4" />}
      <span>{config.label}</span>
      {score !== undefined && (
        <span className="ml-1 text-xs opacity-75">({score}%)</span>
      )}
    </div>
  );
}

export function RiskGauge({
  level,
  score = 0,
}: {
  level: RiskLevel;
  score?: number;
}) {
  const colorMap: Record<RiskLevel, string> = {
    baixo: "#22c55e",
    medio: "#eab308",
    alto: "#f97316",
    critico: "#ef4444",
  };

  const color = colorMap[level] || colorMap.medio;
  const rotation = (score / 100) * 180 - 90;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative h-24 w-48 overflow-hidden">
        <svg viewBox="0 0 200 100" className="h-full w-full">
          {/* Background arc */}
          <path
            d="M 20 90 A 80 80 0 0 1 180 90"
            fill="none"
            stroke="var(--border)"
            strokeWidth="12"
            strokeLinecap="round"
          />
          {/* Value arc */}
          <path
            d="M 20 90 A 80 80 0 0 1 180 90"
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${(score / 100) * 251.2} 251.2`}
          />
          {/* Needle */}
          <g transform={`rotate(${rotation}, 100, 90)`}>
            <line
              x1="100"
              y1="90"
              x2="100"
              y2="25"
              stroke="var(--foreground)"
              strokeWidth="2"
            />
            <circle cx="100" cy="90" r="4" fill="var(--foreground)" />
          </g>
        </svg>
      </div>
      <div className="text-center">
        <RiskBadge level={level} score={score} />
      </div>
    </div>
  );
}
