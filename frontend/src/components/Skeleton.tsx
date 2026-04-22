"use client";

import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
  variant?: "text" | "card" | "table" | "circle";
  lines?: number;
}

export function Skeleton({ className, variant = "text", lines = 1 }: SkeletonProps) {
  const base = "animate-pulse bg-[var(--secondary)] rounded";

  if (variant === "circle") {
    return <div className={cn(base, "rounded-full w-10 h-10", className)} />;
  }

  if (variant === "card") {
    return (
      <div className={cn("rounded-xl border bg-[var(--card)] p-5 space-y-3", className)}>
        <div className={cn(base, "h-4 w-1/3")} />
        <div className={cn(base, "h-8 w-2/3")} />
        <div className={cn(base, "h-3 w-full")} />
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className={cn("rounded-xl border bg-[var(--card)] overflow-hidden", className)}>
        <div className={cn(base, "h-10 w-full rounded-none")} />
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className="flex gap-4 p-4 border-t border-[var(--border)]">
            <div className={cn(base, "h-4 w-1/4")} />
            <div className={cn(base, "h-4 w-1/3")} />
            <div className={cn(base, "h-4 w-1/5")} />
            <div className={cn(base, "h-4 w-1/6")} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={cn(base, "h-4", i === lines - 1 ? "w-2/3" : "w-full")} />
      ))}
    </div>
  );
}

export function SkeletonDashboard() {
  return (
    <div className="space-y-6 p-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} variant="card" />
        ))}
      </div>
      <Skeleton variant="table" lines={5} />
    </div>
  );
}
