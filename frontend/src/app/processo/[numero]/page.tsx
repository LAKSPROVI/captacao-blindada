"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, ProcessoResult, TimelineEvent, RiscoAnalise } from "@/lib/api";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { RiskGauge, RiskBadge } from "@/components/RiskBadge";
import { TimelineView } from "@/components/TimelineView";
import {
  FileText,
  Calendar,
  Building2,
  Users,
  AlertCircle,
  ArrowLeft,
  Clock,
} from "lucide-react";
import Link from "next/link";

export default function ProcessoDetailPage() {
  const params = useParams();
  const numero = decodeURIComponent(params.numero as string);

  const [processo, setProcesso] = useState<ProcessoResult | null>(null);
  const [resumo, setResumo] = useState("");
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [riscos, setRiscos] = useState<RiscoAnalise | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadProcesso();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [numero]);

  const loadProcesso = async () => {
    try {
      const [processoData, resumoData, timelineData, riscosData] =
        await Promise.allSettled([
          api.getProcesso(numero),
          api.getResumo(numero),
          api.getTimeline(numero),
          api.getRiscos(numero),
        ]);

      if (processoData.status === "fulfilled") {
        setProcesso(processoData.value);
      } else {
        setError("Processo nao encontrado.");
      }

      if (resumoData.status === "fulfilled") {
        const val = resumoData.value;
        setResumo(typeof val === "string" ? val : val.resumo || "");
      }

      if (timelineData.status === "fulfilled") {
        setTimeline(
          Array.isArray(timelineData.value) ? timelineData.value : []
        );
      }

      if (riscosData.status === "fulfilled") {
        setRiscos(riscosData.value);
      }
    } catch {
      setError("Erro ao carregar processo.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner size="lg" text="Carregando processo..." />
      </div>
    );
  }

  if (error || !processo) {
    return (
      <div className="space-y-4">
        <Link
          href="/processo"
          className="inline-flex items-center gap-1 text-sm text-legal-600 hover:text-legal-500"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Link>
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-8 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-red-500 mb-4" />
          <p className="text-red-600">{error || "Processo nao encontrado"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            href="/processo"
            className="inline-flex items-center gap-1 text-sm text-legal-600 hover:text-legal-500 mb-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar aos processos
          </Link>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">
            {processo.numero_processo}
          </h1>
          <div className="mt-2 flex items-center gap-4 text-sm text-[var(--muted-foreground)]">
            {processo.tribunal && (
              <span className="flex items-center gap-1">
                <Building2 className="h-4 w-4" />
                {processo.tribunal}
              </span>
            )}
            {processo.data_ajuizamento && (
              <span className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                {processo.data_ajuizamento}
              </span>
            )}
            {processo.status && (
              <span className="rounded bg-legal-600/10 px-2 py-0.5 text-xs font-medium text-legal-600">
                {processo.status}
              </span>
            )}
          </div>
        </div>
        {riscos && (
          <RiskBadge level={riscos.nivel} score={riscos.score} />
        )}
      </div>

      {/* Summary + Risk */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Executive Summary */}
        <div className="lg:col-span-2 rounded-lg border bg-[var(--card)] p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[var(--card-foreground)] mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5 text-legal-600" />
            Resumo Executivo
          </h2>
          {resumo ? (
            <p className="text-sm text-[var(--card-foreground)] whitespace-pre-wrap leading-relaxed">
              {resumo}
            </p>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">
              Resumo nao disponivel para este processo.
            </p>
          )}
          {processo.classe && (
            <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-4 border-t pt-4">
              <div>
                <p className="text-xs text-[var(--muted-foreground)]">Classe</p>
                <p className="text-sm font-medium">{processo.classe}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--muted-foreground)]">Assunto</p>
                <p className="text-sm font-medium">{processo.assunto || "-"}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--muted-foreground)]">Valor da Causa</p>
                <p className="text-sm font-bold text-legal-600">
                  {processo.valor_causa 
                    ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(processo.valor_causa as any)
                    : "Não informado"}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Risk Gauge */}
        <div className="rounded-lg border bg-[var(--card)] p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[var(--card-foreground)] mb-4">
            Nivel de Risco
          </h2>
          {riscos ? (
            <RiskGauge level={riscos.nivel} score={riscos.score} />
          ) : (
            <div className="flex h-32 items-center justify-center text-sm text-[var(--muted-foreground)]">
              Dados de risco indisponiveis
            </div>
          )}
        </div>
      </div>

      {/* Parties */}
      {processo.partes && processo.partes.length > 0 && (
        <div className="rounded-lg border bg-[var(--card)] p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[var(--card-foreground)] mb-4 flex items-center gap-2">
            <Users className="h-5 w-5 text-legal-600" />
            Partes do Processo
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="pb-2 font-medium text-[var(--muted-foreground)]">Nome</th>
                  <th className="pb-2 font-medium text-[var(--muted-foreground)]">Tipo</th>
                  <th className="pb-2 font-medium text-[var(--muted-foreground)]">CPF/CNPJ</th>
                  <th className="pb-2 font-medium text-[var(--muted-foreground)]">Advogados</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {processo.partes.map((parte, idx) => (
                  <tr key={idx}>
                    <td className="py-3 font-medium text-[var(--card-foreground)]">
                      {parte.nome}
                    </td>
                    <td className="py-3">
                      <span className="rounded bg-legal-600/10 px-2 py-0.5 text-xs font-medium text-legal-600">
                        {parte.tipo}
                      </span>
                    </td>
                    <td className="py-3 text-[var(--muted-foreground)]">
                      {parte.cpf_cnpj || "-"}
                    </td>
                    <td className="py-3 text-[var(--muted-foreground)]">
                      {parte.advogados?.join(", ") || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="rounded-lg border bg-[var(--card)] p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-[var(--card-foreground)] mb-4 flex items-center gap-2">
          <Clock className="h-5 w-5 text-legal-600" />
          Timeline
        </h2>
        <TimelineView events={timeline} />
      </div>

      {/* Movimentacoes table */}
      {processo.movimentacoes && processo.movimentacoes.length > 0 && (
        <div className="rounded-lg border bg-[var(--card)] p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-[var(--card-foreground)] mb-4">
            Movimentacoes
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="pb-2 font-medium text-[var(--muted-foreground)]">Data</th>
                  <th className="pb-2 font-medium text-[var(--muted-foreground)]">Descricao</th>
                  <th className="pb-2 font-medium text-[var(--muted-foreground)]">Tipo</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {processo.movimentacoes.map((mov, idx) => (
                  <tr key={idx}>
                    <td className="py-3 whitespace-nowrap text-[var(--muted-foreground)]">
                      {mov.data}
                    </td>
                    <td className="py-3 text-[var(--card-foreground)]">
                      {mov.descricao}
                    </td>
                    <td className="py-3">
                      {mov.tipo && (
                        <span className="rounded bg-[var(--secondary)] px-2 py-0.5 text-xs">
                          {mov.tipo}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
