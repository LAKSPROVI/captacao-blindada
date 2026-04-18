"use client";

import { cn } from "@/lib/utils";
import { ProcessoResult } from "@/lib/api";
import { RiskBadge } from "./RiskBadge";
import { FileText, Calendar, Building2, ArrowRight } from "lucide-react";
import Link from "next/link";

export function ProcessoCard({
  processo,
  className,
}: {
  processo: ProcessoResult;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "group rounded-lg border bg-[var(--card)] p-5 shadow-sm transition-all hover:shadow-md hover:border-legal-600/30",
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-legal-600" />
            <h3 className="font-semibold text-[var(--card-foreground)]">
              {processo.numero_processo}
            </h3>
          </div>
          {processo.classe && (
            <p className="text-sm text-[var(--muted-foreground)]">
              {processo.classe}
            </p>
          )}
        </div>
        {processo.riscos && (
          <RiskBadge level={processo.riscos.nivel} score={processo.riscos.score} />
        )}
      </div>

      {processo.assunto && (
        <p className="mt-3 text-sm text-[var(--card-foreground)] line-clamp-2">
          {processo.assunto}
        </p>
      )}

      <div className="mt-4 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
        {processo.tribunal && (
          <span className="flex items-center gap-1">
            <Building2 className="h-3 w-3" />
            {processo.tribunal}
          </span>
        )}
        {processo.data_ajuizamento && (
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {processo.data_ajuizamento}
          </span>
        )}
        {processo.status && (
          <span className="rounded bg-legal-600/10 px-2 py-0.5 font-medium text-legal-600">
            {processo.status}
          </span>
        )}
      </div>

      <div className="mt-4 border-t pt-3">
        <Link
          href={`/processo/${encodeURIComponent(processo.numero_processo)}`}
          className="inline-flex items-center gap-1 text-sm font-medium text-legal-600 hover:text-legal-500 transition-colors"
        >
          Ver detalhes
          <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-1" />
        </Link>
      </div>
    </div>
  );
}
