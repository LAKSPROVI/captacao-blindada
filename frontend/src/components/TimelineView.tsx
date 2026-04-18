"use client";

import { cn } from "@/lib/utils";
import { TimelineEvent } from "@/lib/api";
import { Calendar, FileText, AlertTriangle, CheckCircle2, Clock } from "lucide-react";

const typeIcons: Record<string, typeof Calendar> = {
  decisao: CheckCircle2,
  despacho: FileText,
  intimacao: AlertTriangle,
  audiencia: Clock,
  default: Calendar,
};

export function TimelineView({
  events,
  className,
}: {
  events: TimelineEvent[];
  className?: string;
}) {
  if (!events || events.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-[var(--muted-foreground)]">
        <p>Nenhum evento na timeline</p>
      </div>
    );
  }

  return (
    <div className={cn("relative", className)}>
      {/* Vertical line */}
      <div className="absolute left-6 top-0 h-full w-0.5 bg-[var(--border)]" />

      <div className="space-y-6">
        {events.map((event, index) => {
          const Icon = typeIcons[event.tipo || "default"] || typeIcons.default;
          return (
            <div key={index} className="relative flex gap-4 pl-2">
              {/* Icon circle */}
              <div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-legal-600 bg-[var(--card)]">
                <Icon className="h-4 w-4 text-legal-600" />
              </div>

              {/* Content */}
              <div className="flex-1 rounded-lg border bg-[var(--card)] p-4 shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="font-medium text-[var(--card-foreground)]">
                    {event.titulo}
                  </h4>
                  <time className="whitespace-nowrap text-xs text-[var(--muted-foreground)]">
                    {formatDate(event.data)}
                  </time>
                </div>
                {event.descricao && (
                  <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                    {event.descricao}
                  </p>
                )}
                {event.tipo && (
                  <span className="mt-2 inline-block rounded bg-legal-600/10 px-2 py-0.5 text-xs font-medium text-legal-600">
                    {event.tipo}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}
