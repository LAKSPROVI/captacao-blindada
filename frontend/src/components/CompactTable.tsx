"use client";
import { useState } from "react";
import { Minimize2, Maximize2 } from "lucide-react";

interface CompactTableProps {
  children: React.ReactNode;
  title?: string;
}

export function CompactTable({ children, title }: CompactTableProps) {
  const [compact, setCompact] = useState(() => {
    if (typeof window !== "undefined") return localStorage.getItem("table_compact") === "true";
    return false;
  });

  const toggle = () => {
    const next = !compact;
    setCompact(next);
    localStorage.setItem("table_compact", String(next));
  };

  return (
    <div className={compact ? "text-xs" : "text-sm"}>
      <div className="flex items-center justify-between mb-2">
        {title && <span className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">{title}</span>}
        <button onClick={toggle} className="p-1 rounded hover:bg-[var(--secondary)] text-[var(--muted-foreground)]" title={compact ? "Expandir" : "Compactar"}>
          {compact ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
        </button>
      </div>
      {children}
    </div>
  );
}
