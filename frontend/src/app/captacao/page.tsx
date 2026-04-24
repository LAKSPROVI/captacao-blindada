"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import {
  api,
  CaptacaoItem,
  CaptacaoStats,
  CaptacaoCreateParams,
  CaptacaoExecucao,
  PublicacaoItem,
} from "@/lib/api";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { StatsCard } from "@/components/StatsCard";
import {
  Zap,
  Plus,
  Play,
  Pause,
  RotateCcw,
  Trash2,
  Copy,
  Clock,
  CheckCircle2,
  AlertCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  FileText,
  Activity,
  Calendar,
  Building2,
  Search,
  Eye,
  Edit2,
  ExternalLink,
  Filter,
  Globe,
  Database,
} from "lucide-react";
import Link from "next/link";

// =========================================================================
// Constantes
// =========================================================================

const TIPO_BUSCA_OPTIONS = [
  { value: "processo", label: "Processo (numero CNJ)" },
  { value: "oab", label: "OAB (numero + UF)" },
  { value: "nome_parte", label: "Nome da Parte" },
  { value: "nome_advogado", label: "Nome do Advogado" },
  { value: "classe", label: "Classe Processual (codigo)" },
  { value: "assunto", label: "Assunto (codigo)" },
  { value: "tribunal_geral", label: "Varredura Geral (tribunal)" },
];

const PRIORIDADE_OPTIONS = [
  { value: "urgente", label: "Urgente", color: "text-red-500" },
  { value: "normal", label: "Normal", color: "text-blue-500" },
  { value: "baixa", label: "Baixa", color: "text-gray-500" },
];

const FONTE_OPTIONS = [
  { value: "datajud", label: "DataJud" },
  { value: "djen_api", label: "DJEN" },
];

const INTERVALO_PRESETS = [
  { value: 15, label: "15 min" },
  { value: 30, label: "30 min" },
  { value: 60, label: "1 hora" },
  { value: 120, label: "2 horas" },
  { value: 360, label: "6 horas" },
  { value: 720, label: "12 horas" },
  { value: 1440, label: "24 horas" },
];

// =========================================================================
// Page Component
// =========================================================================

export default function CaptacaoPage() {
  const searchParams = useSearchParams();
  const filterNovos = searchParams.get("filter") === "novos";

  // State
  const [captacoes, setCaptacoes] = useState<CaptacaoItem[]>([]);
  const [stats, setStats] = useState<CaptacaoStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Create form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Detail panel
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detailTab, setDetailTab] = useState<"historico" | "resultados">("historico");
  const [historico, setHistorico] = useState<CaptacaoExecucao[]>([]);
  const [resultados, setResultados] = useState<PublicacaoItem[]>([]);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // Executing
  const [executingId, setExecutingId] = useState<number | null>(null);

  // Edit form
  const [editingCaptacao, setEditingCaptacao] = useState<CaptacaoItem | null>(null);

  // Seen tracking (localStorage)
  const [seenCaptacoes, setSeenCaptacoes] = useState<Record<number, number>>(() => {
    if (typeof window === "undefined") return {};
    try {
      return JSON.parse(localStorage.getItem("captacao_seen_results") || "{}");
    } catch { return {}; }
  });

  const markSeen = useCallback((id: number, total: number) => {
    setSeenCaptacoes(prev => {
      const next = { ...prev, [id]: total };
      localStorage.setItem("captacao_seen_results", JSON.stringify(next));
      return next;
    });
  }, []);

  // =========================================================================
  // Data loading
  // =========================================================================

  const loadData = useCallback(async () => {
    try {
      const [listData, statsData] = await Promise.allSettled([
        api.listarCaptacoes(),
        api.getCaptacaoStats(),
      ]);

      if (listData.status === "fulfilled") {
        const caps = listData.value.captacoes || [];
        setCaptacoes(caps);

        // Auto-expand first captação with novos when ?filter=novos
        if (filterNovos && caps.length > 0) {
          const comNovos = caps.find((c: CaptacaoItem) => c.total_novos > 0);
          if (comNovos) {
            setExpandedId(comNovos.id);
            setDetailTab("resultados");
            // Trigger detail load
            setIsLoadingDetail(true);
            try {
              const [hist, res] = await Promise.allSettled([
                api.historicoCaptacao(comNovos.id, { limite: 500 }),
                api.resultadosCaptacao(comNovos.id, { limite: 500 }),
              ]);
              if (hist.status === "fulfilled") setHistorico(hist.value.execucoes || []);
              if (res.status === "fulfilled") setResultados(res.value.publicacoes || []);
            } finally {
              setIsLoadingDetail(false);
            }
          }
        }
      }
      if (statsData.status === "fulfilled") {
        setStats(statsData.value);
      }
    } catch (err) {
      console.error("Erro ao carregar captacoes:", err);
      setError("Erro ao carregar dados");
    } finally {
      setIsLoading(false);
    }
  }, [filterNovos]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const loadDetail = async (id: number) => {
    setIsLoadingDetail(true);
    try {
      const [hist, res] = await Promise.allSettled([
        api.historicoCaptacao(id, { limite: 500 }),
        api.resultadosCaptacao(id, { limite: 500 }),
      ]);
      if (hist.status === "fulfilled") setHistorico(hist.value.execucoes || []);
      if (res.status === "fulfilled") setResultados(res.value.publicacoes || []);
    } catch (err) {
      console.error("Erro ao carregar detalhes:", err);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // =========================================================================
  // Actions
  // =========================================================================

  const handleExecutar = async (id: number) => {
    setExecutingId(id);
    setError("");
    setSuccess("");
    try {
      const result = await api.executarCaptacao(id);
      setSuccess(
        `Captacao #${id} executada: ${result.total_resultados} resultado(s), ${result.novos_resultados} novo(s)`
      );
      loadData();
      if (expandedId === id) loadDetail(id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro desconhecido";
      setError(`Erro ao executar captacao #${id}: ${msg}`);
    } finally {
      setExecutingId(null);
    }
  };

  const handleClonar = async (id: number) => {
    try {
      const result = await api.clonarCaptacao(id);
      setSuccess(result.message || "Captação clonada com sucesso!");
      loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro desconhecido";
      setError(`Erro ao clonar: ${msg}`);
    }
  };

  const handlePausar = async (id: number) => {
    try {
      await api.pausarCaptacao(id);
      setSuccess(`Captacao #${id} pausada`);
      loadData();
    } catch {
      setError(`Erro ao pausar captacao #${id}`);
    }
  };

  const handleRetomar = async (id: number) => {
    try {
      await api.retomarCaptacao(id);
      setSuccess(`Captacao #${id} retomada`);
      loadData();
    } catch {
      setError(`Erro ao retomar captacao #${id}`);
    }
  };

  const handleDesativar = async (id: number) => {
    if (!confirm(`Desativar captacao #${id}? Ela nao sera mais executada.`)) return;
    try {
      await api.desativarCaptacao(id);
      setSuccess(`Captacao #${id} desativada`);
      loadData();
    } catch {
      setError(`Erro ao desativar captacao #${id}`);
    }
  };

  const handleToggleExpand = (id: number) => {
    if (expandedId === id) {
      setExpandedId(null);
    } else {
      setExpandedId(id);
      setDetailTab("historico");
      loadDetail(id);
      // Mark as seen with current total
      const cap = captacoes.find(c => c.id === id);
      if (cap) markSeen(id, cap.total_resultados);
    }
  };

  // =========================================================================
  // Render
  // =========================================================================

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner size="lg" text="Carregando captacoes..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">
            Captacao Automatizada
          </h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Configure buscas automaticas no DataJud e DJEN
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setIsLoading(true); loadData(); }}
            className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Atualizar
          </button>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="inline-flex items-center gap-2 rounded-lg bg-legal-600 px-4 py-2 text-sm font-medium text-white hover:bg-legal-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Nova Captacao
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
          <button onClick={() => setError("")} className="ml-auto text-red-500 hover:text-red-700">&times;</button>
        </div>
      )}
      {success && (
        <div className="rounded-lg border border-green-300 bg-green-50 dark:bg-green-900/20 p-3 text-sm text-green-700 dark:text-green-400 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {success}
          <button onClick={() => setSuccess("")} className="ml-auto text-green-500 hover:text-green-700">&times;</button>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatsCard
            title="Captacoes Ativas"
            value={stats.captacoes_ativas}
            icon={Zap}
            description={`${stats.total_captacoes} total`}
          />
          <StatsCard
            title="Execucoes Hoje"
            value={stats.execucoes_hoje}
            icon={Activity}
            description={`${stats.total_execucoes} total`}
          />
          <StatsCard
            title="Novos Encontrados"
            value={stats.total_novos_encontrados}
            icon={FileText}
            description="Publicacoes novas"
          />
          <StatsCard
            title="Ultima Execucao"
            value={stats.ultima_execucao ? new Date(stats.ultima_execucao).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "--:--"}
            icon={Clock}
            description={stats.ultima_execucao ? new Date(stats.ultima_execucao).toLocaleDateString("pt-BR") : "Nenhuma"}
          />
        </div>
      )}

      {/* Form (Create or Edit) */}
      {(showCreateForm || editingCaptacao) && (
        <CaptacaoForm
          initialData={editingCaptacao}
          onCreated={() => {
            setShowCreateForm(false);
            setEditingCaptacao(null);
            setSuccess("Captacao criada com sucesso!");
            loadData();
          }}
          onUpdated={() => {
            setEditingCaptacao(null);
            setSuccess("Captacao atualizada com sucesso!");
            loadData();
          }}
          onCancel={() => {
            setShowCreateForm(false);
            setEditingCaptacao(null);
          }}
          isSaving={isCreating}
          setIsSaving={setIsCreating}
          setError={setError}
        />
      )}

      {/* List */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-[var(--foreground)]">
          Captacoes Configuradas ({captacoes.length})
        </h2>

        {captacoes.length === 0 ? (
          <div className="rounded-lg border bg-[var(--card)] p-12 text-center">
            <Zap className="mx-auto h-12 w-12 text-[var(--muted-foreground)] mb-4" />
            <h3 className="text-lg font-medium text-[var(--card-foreground)] mb-2">
              Nenhuma captacao configurada
            </h3>
            <p className="text-sm text-[var(--muted-foreground)] mb-4">
              Crie uma captacao para monitorar automaticamente publicacoes no DataJud e DJEN.
            </p>
            <button
              onClick={() => setShowCreateForm(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-legal-600 px-4 py-2 text-sm font-medium text-white hover:bg-legal-700"
            >
              <Plus className="h-4 w-4" />
              Criar Captacao
            </button>
          </div>
        ) : (
          captacoes.map((cap) => {
            const lastSeen = seenCaptacoes[cap.id] || 0;
            const unseenCount = Math.max(0, cap.total_resultados - lastSeen);
            return (
            <CaptacaoCard
              key={cap.id}
              captacao={cap}
              isExpanded={expandedId === cap.id}
              isExecuting={executingId === cap.id}
              unseenCount={unseenCount}
              onToggleExpand={() => handleToggleExpand(cap.id)}
              onExecutar={() => handleExecutar(cap.id)}
              onClonar={() => handleClonar(cap.id)}
              onPausar={() => handlePausar(cap.id)}
              onRetomar={() => handleRetomar(cap.id)}
              onDesativar={() => handleDesativar(cap.id)}
              detailTab={detailTab}
              setDetailTab={setDetailTab}
              historico={historico}
              resultados={resultados}
              isLoadingDetail={isLoadingDetail}
              onEditar={() => setEditingCaptacao(cap)}
            />
            );
          })
        )}
      </div>
    </div>
  );
}

// =========================================================================
// CaptacaoCard Component
// =========================================================================

function CaptacaoCard({
  captacao,
  isExpanded,
  isExecuting,
  unseenCount,
  onToggleExpand,
  onExecutar,
  onClonar,
  onPausar,
  onRetomar,
  onDesativar,
  detailTab,
  setDetailTab,
  historico,
  resultados,
  isLoadingDetail,
  onEditar,
}: {
  captacao: CaptacaoItem;
  isExpanded: boolean;
  isExecuting: boolean;
  unseenCount: number;
  onToggleExpand: () => void;
  onExecutar: () => void;
  onClonar: () => void;
  onPausar: () => void;
  onRetomar: () => void;
  onDesativar: () => void;
  detailTab: "historico" | "resultados";
  setDetailTab: (tab: "historico" | "resultados") => void;
  historico: CaptacaoExecucao[];
  resultados: PublicacaoItem[];
  isLoadingDetail: boolean;
  onEditar: () => void;
}) {
  const tipoLabel = TIPO_BUSCA_OPTIONS.find((t) => t.value === captacao.tipo_busca)?.label || captacao.tipo_busca;
  const prioridadeInfo = PRIORIDADE_OPTIONS.find((p) => p.value === captacao.prioridade) || PRIORIDADE_OPTIONS[1];
  const intervaloLabel = INTERVALO_PRESETS.find((i) => i.value === captacao.intervalo_minutos)?.label || `${captacao.intervalo_minutos} min`;

  const statusBadge = () => {
    if (!captacao.ativo) {
      return <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs font-medium text-gray-600 dark:text-gray-400"><XCircle className="h-3 w-3" /> Inativa</span>;
    }
    if (captacao.pausado) {
      return <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 dark:bg-yellow-900/30 px-2 py-0.5 text-xs font-medium text-yellow-700 dark:text-yellow-400"><Pause className="h-3 w-3" /> Pausada</span>;
    }
    return <span className="inline-flex items-center gap-1 rounded-full bg-green-100 dark:bg-green-900/30 px-2 py-0.5 text-xs font-medium text-green-700 dark:text-green-400"><CheckCircle2 className="h-3 w-3" /> Ativa</span>;
  };

  // Determine the search target display
  const searchTarget = () => {
    if (captacao.numero_processo) return captacao.numero_processo;
    if (captacao.numero_oab) return `OAB ${captacao.numero_oab}/${captacao.uf_oab || "SP"}`;
    if (captacao.nome_parte) return captacao.nome_parte;
    if (captacao.nome_advogado) return captacao.nome_advogado;
    if (captacao.tribunal) return captacao.tribunal.toUpperCase();
    return "-";
  };

  return (
    <div className="rounded-lg border bg-[var(--card)] shadow-sm overflow-hidden">
      {/* Header row */}
      <div
        className="flex items-center gap-3 p-4 cursor-pointer hover:bg-[var(--secondary)]/50 transition-colors"
        onClick={onToggleExpand}
      >
        {/* Status icon */}
        <div className="shrink-0">
          {isExpanded ? <ChevronUp className="h-5 w-5 text-[var(--muted-foreground)]" /> : <ChevronDown className="h-5 w-5 text-[var(--muted-foreground)]" />}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-[var(--card-foreground)] truncate">{captacao.nome}</h3>
            {statusBadge()}
            <span className={`text-xs font-medium ${prioridadeInfo.color}`}>{prioridadeInfo.label}</span>
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-[var(--muted-foreground)] flex-wrap">
            <span className="inline-flex items-center gap-1"><Search className="h-3 w-3" /> {tipoLabel}</span>
            <span className="inline-flex items-center gap-1"><Eye className="h-3 w-3" /> {searchTarget()}</span>
            <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3" /> {intervaloLabel}</span>
            <span className="inline-flex items-center gap-1"><FileText className="h-3 w-3" /> {captacao.total_resultados} resultados ({captacao.total_novos} novos)</span>
            {unseenCount > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-bold text-white animate-pulse">
                {unseenCount} nao visto{unseenCount > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={onExecutar}
            disabled={isExecuting || !captacao.ativo}
            className="inline-flex items-center gap-1 rounded-md bg-legal-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-legal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Executar agora"
          >
            {isExecuting ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
            {isExecuting ? "Executando..." : "Executar"}
          </button>

          {captacao.ativo && !captacao.pausado && (
            <button
              onClick={onPausar}
              className="rounded-md border px-2 py-1.5 text-xs text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors"
              title="Pausar"
            >
              <Pause className="h-3 w-3" />
            </button>
          )}

          {captacao.ativo && captacao.pausado && (
            <button
              onClick={onRetomar}
              className="rounded-md border px-2 py-1.5 text-xs text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors"
              title="Retomar"
            >
              <RotateCcw className="h-3 w-3" />
            </button>
          )}

          <button
            onClick={onDesativar}
            className="rounded-md border px-2 py-1.5 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            title="Desativar"
          >
            <Trash2 className="h-3 w-3" />
          </button>

          <button
            onClick={onClonar}
            className="rounded-md border px-2 py-1.5 text-xs text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
            title="Clonar captação"
          >
            <Copy className="h-3 w-3" />
          </button>

          <button
            onClick={onEditar}
            className="rounded-md border px-2 py-1.5 text-xs text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
            title="Editar"
          >
            <Edit2 className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="border-t">
          {/* Tabs */}
          <div className="flex border-b">
            <button
              onClick={() => setDetailTab("historico")}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                detailTab === "historico"
                  ? "text-legal-600 border-b-2 border-legal-600"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              Historico de Execucoes
            </button>
            <button
              onClick={() => setDetailTab("resultados")}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                detailTab === "resultados"
                  ? "text-legal-600 border-b-2 border-legal-600"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              Publicacoes Encontradas ({resultados.length})
            </button>
          </div>

          {/* Tab content */}
          <div className="p-4 max-h-96 overflow-y-auto">
            {isLoadingDetail ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner size="default" text="Carregando..." />
              </div>
            ) : detailTab === "historico" ? (
              <HistoricoTable execucoes={historico} />
            ) : (
              <ResultadosList publicacoes={resultados} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// =========================================================================
// HistoricoTable
// =========================================================================

function HistoricoTable({ execucoes }: { execucoes: CaptacaoExecucao[] }) {
  if (execucoes.length === 0) {
    return (
      <p className="text-center text-sm text-[var(--muted-foreground)] py-4">
        Nenhuma execucao registrada ainda.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs text-[var(--muted-foreground)]">
            <th className="pb-2 pr-3">Inicio</th>
            <th className="pb-2 pr-3">Fonte</th>
            <th className="pb-2 pr-3">Status</th>
            <th className="pb-2 pr-3 text-right">Total</th>
            <th className="pb-2 pr-3 text-right">Novos</th>
            <th className="pb-2 text-right">Duracao</th>
          </tr>
        </thead>
        <tbody>
          {execucoes.map((exec) => (
            <tr key={exec.id} className="border-b last:border-0">
              <td className="py-2 pr-3 whitespace-nowrap">
                {exec.inicio ? new Date(exec.inicio).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "-"}
              </td>
              <td className="py-2 pr-3">
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                  exec.fonte === "djen_api" || exec.fonte === "djen"
                    ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                    : "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                }`}>
                  {exec.fonte === "datajud" ? "DataJud" : exec.fonte === "djen_api" ? "DJEN" : exec.fonte}
                </span>
              </td>
              <td className="py-2 pr-3">
                {exec.status === "completed" ? (
                  <span className="inline-flex items-center gap-1 text-green-600"><CheckCircle2 className="h-3 w-3" /> OK</span>
                ) : exec.status === "failed" ? (
                  <span className="inline-flex items-center gap-1 text-red-500" title={exec.erro || ""}><XCircle className="h-3 w-3" /> Erro</span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-yellow-600"><Clock className="h-3 w-3" /> {exec.status}</span>
                )}
              </td>
              <td className="py-2 pr-3 text-right font-mono">{exec.total_resultados}</td>
              <td className="py-2 pr-3 text-right font-mono font-semibold text-green-600">{exec.novos_resultados}</td>
              <td className="py-2 text-right font-mono text-[var(--muted-foreground)]">
                {exec.duracao_ms ? `${(exec.duracao_ms / 1000).toFixed(1)}s` : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// =========================================================================
// ResultadosList
// =========================================================================

function ResultadosList({ publicacoes }: { publicacoes: PublicacaoItem[] }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [fonteFilter, setFonteFilter] = useState<string>("todas");
  const [visibleCount, setVisibleCount] = useState(20);

  const handleFilterChange = (f: string) => {
    setFonteFilter(f);
    setExpandedIdx(null);
    setVisibleCount(20);
  };

  const fontesDisponiveis = useMemo(
    () => Array.from(new Set(publicacoes.map(p => p.fonte).filter(Boolean))),
    [publicacoes]
  );

  if (publicacoes.length === 0) {
    return (
      <p className="text-center text-sm text-[var(--muted-foreground)] py-4">
        Nenhuma publicacao encontrada ainda.
      </p>
    );
  }

  const filtered = fonteFilter === "todas"
    ? publicacoes
    : publicacoes.filter(p => p.fonte === fonteFilter);

  return (
    <div className="space-y-3">
      {/* Filtro por fonte */}
      {fontesDisponiveis.length > 1 && (
        <div className="flex items-center gap-2 pb-2 border-b">
          <Filter className="h-3.5 w-3.5 text-[var(--muted-foreground)]" />
          <span className="text-xs text-[var(--muted-foreground)]">Filtrar:</span>
          <button
            onClick={() => handleFilterChange("todas")}
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
              fonteFilter === "todas"
                ? "bg-legal-600 text-white"
                : "bg-[var(--secondary)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/80"
            }`}
          >
            Todas ({publicacoes.length})
          </button>
          {fontesDisponiveis.map(f => (
            <button
              key={f}
              onClick={() => handleFilterChange(f!)}
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                fonteFilter === f
                  ? f === "datajud" ? "bg-blue-600 text-white" : "bg-amber-600 text-white"
                  : f === "datajud" ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 hover:bg-blue-200" : "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 hover:bg-amber-200"
              }`}
            >
              {f === "datajud" ? <Database className="h-3 w-3" /> : <Globe className="h-3 w-3" />}
              {f === "datajud" ? "DataJud" : f === "djen_api" ? "DJEN" : f} ({publicacoes.filter(p => p.fonte === f).length})
            </button>
          ))}
        </div>
      )}

      {filtered.slice(0, visibleCount).map((pub, idx) => {
        const isExpanded = expandedIdx === idx;
        return (
          <div
            key={pub.id || pub.hash || idx}
            className={`rounded-md border text-sm transition-all cursor-pointer hover:shadow-sm ${
              pub.fonte === "djen_api" || pub.fonte === "djen"
                ? "border-l-2 border-l-amber-400"
                : "border-l-2 border-l-blue-400"
            }`}
            onClick={() => setExpandedIdx(isExpanded ? null : idx)}
          >
            <div className="p-3">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                  pub.fonte === "djen_api" || pub.fonte === "djen"
                    ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                    : "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                }`}>
                  {pub.fonte === "djen_api" || pub.fonte === "djen" ? <Globe className="h-3 w-3" /> : <Database className="h-3 w-3" />}
                  {pub.fonte === "datajud" ? "DataJud" : pub.fonte === "djen_api" ? "DJEN" : pub.fonte}
                </span>
                {pub.tribunal && (
                  <span className="inline-flex items-center gap-1 text-xs text-[var(--muted-foreground)]">
                    <Building2 className="h-3 w-3" /> {pub.tribunal}
                  </span>
                )}
                {pub.data_publicacao && (
                  <span className="inline-flex items-center gap-1 text-xs text-[var(--muted-foreground)]">
                    <Calendar className="h-3 w-3" /> {pub.data_publicacao}
                  </span>
                )}
                {pub.numero_processo && (
                  <Link
                    href={`/processo?q=${encodeURIComponent(pub.numero_processo)}`}
                    onClick={(e) => e.stopPropagation()}
                    className="inline-flex items-center gap-1 font-mono text-xs text-legal-600 hover:text-legal-700 hover:underline"
                  >
                    {pub.numero_processo}
                    <ExternalLink className="h-2.5 w-2.5" />
                  </Link>
                )}
              </div>
              {pub.conteudo && (
                <p className={`text-xs text-[var(--muted-foreground)] mt-1 ${isExpanded ? "" : "line-clamp-3"}`}>
                  {pub.conteudo}
                </p>
              )}
            </div>

            {/* Expanded details */}
            {isExpanded && (
              <div className="border-t px-3 py-2 bg-[var(--secondary)]/30 space-y-2">
                {pub.classe_processual && (
                  <div className="text-xs"><span className="font-medium text-[var(--card-foreground)]">Classe:</span> <span className="text-[var(--muted-foreground)]">{pub.classe_processual}</span></div>
                )}
                {pub.orgao_julgador && (
                  <div className="text-xs"><span className="font-medium text-[var(--card-foreground)]">Orgao:</span> <span className="text-[var(--muted-foreground)]">{pub.orgao_julgador}</span></div>
                )}
                {pub.advogados && pub.advogados.length > 0 && (
                  <div className="text-xs"><span className="font-medium text-[var(--card-foreground)]">Advogados:</span> <span className="text-[var(--muted-foreground)]">{pub.advogados.join(", ")}</span></div>
                )}
                {pub.partes && pub.partes.length > 0 && (
                  <div className="text-xs"><span className="font-medium text-[var(--card-foreground)]">Partes:</span> <span className="text-[var(--muted-foreground)]">{pub.partes.join(", ")}</span></div>
                )}
                {pub.oab_encontradas && pub.oab_encontradas.length > 0 && (
                  <div className="text-xs"><span className="font-medium text-[var(--card-foreground)]">OABs:</span> <span className="text-[var(--muted-foreground)]">{pub.oab_encontradas.join(", ")}</span></div>
                )}
                {pub.numero_processo && (
                  <Link
                    href={`/processo?q=${encodeURIComponent(pub.numero_processo)}`}
                    onClick={(e) => e.stopPropagation()}
                    className="inline-flex items-center gap-1.5 rounded-md bg-legal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-legal-700 transition-colors mt-1"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Ver Processo Completo
                  </Link>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Paginação: Carregar mais */}
      {filtered.length > visibleCount && (
        <div className="flex flex-col items-center gap-2 pt-2 border-t">
          <p className="text-xs text-[var(--muted-foreground)]">
            Exibindo {Math.min(visibleCount, filtered.length)} de {filtered.length} publicacoes
          </p>
          <button
            onClick={() => setVisibleCount(prev => prev + 20)}
            className="inline-flex items-center gap-1.5 rounded-lg border px-4 py-2 text-xs font-medium text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors"
          >
            <ChevronDown className="h-3.5 w-3.5" />
            Carregar mais 20
          </button>
        </div>
      )}
      {filtered.length > 0 && filtered.length <= visibleCount && (
        <p className="text-xs text-[var(--muted-foreground)] text-center pt-2 border-t">
          Total: {filtered.length} publicacao(oes)
        </p>
      )}
    </div>
  );
}

// =========================================================================
// CaptacaoForm Component (Create & Edit)
// =========================================================================

function CaptacaoForm({
  onCreated,
  onUpdated,
  onCancel,
  isSaving,
  setIsSaving,
  setError,
  initialData,
}: {
  onCreated: () => void;
  onUpdated: () => void;
  onCancel: () => void;
  isSaving: boolean;
  setIsSaving: (v: boolean) => void;
  setError: (v: string) => void;
  initialData: CaptacaoItem | null;
}) {
  const [nome, setNome] = useState(initialData?.nome || "");
  const [descricao, setDescricao] = useState(initialData?.descricao || "");
  const [tipoBusca, setTipoBusca] = useState(initialData?.tipo_busca || "processo");
  
  // Parametros especificos
  const [numeroProcesso, setNumeroProcesso] = useState(initialData?.numero_processo || "");
  const [numeroOab, setNumeroOab] = useState(initialData?.numero_oab || "");
  const [ufOab, setUfOab] = useState(initialData?.uf_oab || "SP");
  const [nomeParte, setNomeParte] = useState(initialData?.nome_parte || "");
  const [nomeAdvogado, setNomeAdvogado] = useState(initialData?.nome_advogado || "");
  const [tribunal, setTribunal] = useState(initialData?.tribunal || "");
  const [classeCodigo, setClasseCodigo] = useState(initialData?.classe_codigo?.toString() || "");
  const [assuntoCodigo, setAssuntoCodigo] = useState(initialData?.assunto_codigo?.toString() || "");
  
  const [dataInicio, setDataInicio] = useState(initialData?.data_inicio || "");
  const [dataFim, setDataFim] = useState(initialData?.data_fim || "");
  const [fontes, setFontes] = useState(initialData?.fontes ? initialData.fontes.split(",") : ["datajud", "djen_api"]);
  const [intervalo, setIntervalo] = useState(initialData?.intervalo_minutos || 120);
  const [horarioInicio, setHorarioInicio] = useState(initialData?.horario_inicio || "06:00");
  const [horarioFim, setHorarioFim] = useState(initialData?.horario_fim || "23:00");
  const [diasSemana, setDiasSemana] = useState(initialData?.dias_semana || "1,2,3,4,5");
  const [prioridade, setPrioridade] = useState(initialData?.prioridade || "normal");
  const [autoEnriquecer, setAutoEnriquecer] = useState(initialData?.auto_enriquecer || false);
  const [modalidade, setModalidade] = useState<"recorrente" | "faixa_fixa">(initialData?.modalidade || "recorrente");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nome.trim()) {
      setError("Nome e obrigatorio");
      return;
    }

    setIsSaving(true);
    setError("");

    // Validação de campos obrigatórios
    if (tipoBusca === "processo" && !numeroProcesso.trim()) {
      setError("Número do processo é obrigatório para este tipo de busca.");
      setIsSaving(false); return;
    }
    if (tipoBusca === "oab" && (!numeroOab.trim() || !ufOab.trim())) {
      setError("Número OAB e UF são obrigatórios para este tipo de busca.");
      setIsSaving(false); return;
    }
    if (tipoBusca === "nome_parte" && !nomeParte.trim()) {
      setError("Nome da parte é obrigatório para este tipo de busca.");
      setIsSaving(false); return;
    }
    if (tipoBusca === "nome_advogado" && !nomeAdvogado.trim()) {
      setError("Nome do advogado é obrigatório para este tipo de busca.");
      setIsSaving(false); return;
    }
    if (["classe", "assunto", "tribunal_geral"].includes(tipoBusca) && !tribunal.trim()) {
      setError("Tribunal é obrigatório para este tipo de busca.");
      setIsSaving(false); return;
    }

    if (modalidade === "faixa_fixa" && (!dataInicio || !dataFim)) {
      setError("Data de início e fim são obrigatórias para a modalidade 'Faixa Fixa'.");
      setIsSaving(false); return;
    }
    if (modalidade === "recorrente" && !dataInicio) {
      setError("Data de início é obrigatória para a modalidade 'Recorrente' (será o ponto de partida).");
      setIsSaving(false); return;
    }

    const params: Partial<CaptacaoCreateParams> = {
      nome: nome.trim(),
      descricao: descricao.trim() || "",
      tipo_busca: tipoBusca,
      modalidade,
      fontes,
      intervalo_minutos: intervalo,
      horario_inicio: horarioInicio,
      horario_fim: horarioFim,
      dias_semana: diasSemana,
      prioridade,
      auto_enriquecer: autoEnriquecer,
    };

    // Add type-specific fields
    if (tipoBusca === "processo") params.numero_processo = numeroProcesso.trim();
    if (tipoBusca === "oab") {
      params.numero_oab = numeroOab.trim();
      params.uf_oab = ufOab.trim() || "SP";
    }
    if (tipoBusca === "nome_parte") params.nome_parte = nomeParte.trim();
    if (tipoBusca === "nome_advogado") params.nome_advogado = nomeAdvogado.trim();
    if (["classe", "assunto", "tribunal_geral"].includes(tipoBusca)) {
      params.tribunal = tribunal.trim().toLowerCase();
    }
    if (tipoBusca === "classe") params.classe_codigo = classeCodigo ? parseInt(classeCodigo) : undefined;
    if (tipoBusca === "assunto") params.assunto_codigo = assuntoCodigo ? parseInt(assuntoCodigo) : undefined;
    params.data_inicio = dataInicio || "";
    params.data_fim = dataFim || "";

    try {
      if (initialData?.id) {
        await api.atualizarCaptacao(initialData.id, params);
        onUpdated();
      } else {
        await api.criarCaptacao(params as CaptacaoCreateParams);
        onCreated();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao salvar captacao";
      setError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  const toggleFonte = (fonte: string) => {
    setFontes((prev) =>
      prev.includes(fonte) ? prev.filter((f) => f !== fonte) : [...prev, fonte]
    );
  };

  const inputClass =
    "w-full rounded-lg border bg-[var(--card)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20";
  const labelClass = "block text-sm font-medium text-[var(--card-foreground)] mb-1";

  return (
    <div className="rounded-lg border bg-[var(--card)] p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-[var(--card-foreground)] mb-4">
        {initialData ? `Editar Captacao #${initialData.id}` : "Nova Captacao"}
      </h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Row 1: Nome + Tipo */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Nome *</label>
            <input
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Ex: Monitorar processos TJSP"
              className={inputClass}
              required
            />
          </div>
          <div>
            <label className={labelClass}>Tipo de Busca *</label>
            <select value={tipoBusca} onChange={(e) => setTipoBusca(e.target.value)} className={inputClass}>
              {TIPO_BUSCA_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
        
        {/* Type-specific fields mapping */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tipoBusca === "processo" && (
            <div>
              <label className={labelClass}>Numero do Processo (CNJ)</label>
              <input
                type="text"
                value={numeroProcesso}
                onChange={(e) => setNumeroProcesso(e.target.value)}
                placeholder="0000000-00.0000.0.00.0000"
                className={inputClass}
              />
            </div>
          )}
          {tipoBusca === "oab" && (
            <>
              <div>
                <label className={labelClass}>Numero OAB</label>
                <input
                  type="text"
                  value={numeroOab}
                  onChange={(e) => setNumeroOab(e.target.value)}
                  placeholder="123456"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>UF</label>
                <input
                  type="text"
                  value={ufOab}
                  onChange={(e) => setUfOab(e.target.value)}
                  placeholder="SP"
                  maxLength={2}
                  className={inputClass}
                />
              </div>
            </>
          )}
          {tipoBusca === "nome_parte" && (
            <div>
              <label className={labelClass}>Nome da Parte</label>
              <input
                type="text"
                value={nomeParte}
                onChange={(e) => setNomeParte(e.target.value)}
                placeholder="Nome completo"
                className={inputClass}
              />
            </div>
          )}
          {tipoBusca === "nome_advogado" && (
            <div>
              <label className={labelClass}>Nome do Advogado</label>
              <input
                type="text"
                value={nomeAdvogado}
                onChange={(e) => setNomeAdvogado(e.target.value)}
                placeholder="Nome completo"
                className={inputClass}
              />
            </div>
          )}
          {["classe", "assunto", "tribunal_geral"].includes(tipoBusca) && (
            <div>
              <label className={labelClass}>Tribunal (sigla)</label>
              <input
                type="text"
                value={tribunal}
                onChange={(e) => setTribunal(e.target.value)}
                placeholder="TJSP, TJRJ, TRF3..."
                className={inputClass}
              />
            </div>
          )}
          {tipoBusca === "classe" && (
            <div>
              <label className={labelClass}>Codigo da Classe</label>
              <input
                type="number"
                value={classeCodigo}
                onChange={(e) => setClasseCodigo(e.target.value)}
                placeholder="Ex: 1116"
                className={inputClass}
              />
            </div>
          )}
          {tipoBusca === "assunto" && (
            <div>
              <label className={labelClass}>Codigo do Assunto</label>
              <input
                type="number"
                value={assuntoCodigo}
                onChange={(e) => setAssuntoCodigo(e.target.value)}
                placeholder="Ex: 7619"
                className={inputClass}
              />
            </div>
          )}
        </div>

        {/* Descricao */}
        <div>
          <label className={labelClass}>Descricao (opcional)</label>
          <input
            type="text"
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder="Notas sobre esta captacao"
            className={inputClass}
          />
        </div>

        {/* Modalidade */}
        <div className="space-y-2">
          <label className={labelClass}>Modalidade de Busca *</label>
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setModalidade("recorrente")}
              className={`flex-1 flex flex-col items-center gap-1 p-3 rounded-lg border transition-all ${
                modalidade === "recorrente"
                  ? "bg-legal-600/10 border-legal-600 text-legal-600"
                  : "bg-[var(--background)] border-[var(--border)] text-[var(--muted-foreground)] hover:border-legal-500"
              }`}
            >
              <RefreshCw className="h-5 w-5" />
              <span className="text-sm font-bold">Busca Recorrente</span>
              <span className="text-[10px] text-center">Busca automática diária a partir da data inicial</span>
            </button>
            <button
              type="button"
              onClick={() => setModalidade("faixa_fixa")}
              className={`flex-1 flex flex-col items-center gap-1 p-3 rounded-lg border transition-all ${
                modalidade === "faixa_fixa"
                  ? "bg-amber-600/10 border-amber-600 text-amber-600"
                  : "bg-[var(--background)] border-[var(--border)] text-[var(--muted-foreground)] hover:border-legal-500"
              }`}
            >
              <Calendar className="h-5 w-5" />
              <span className="text-sm font-bold">Faixa Fixa</span>
              <span className="text-[10px] text-center">Busca de uma única vez no período especificado</span>
            </button>
          </div>
        </div>

        {/* Date range */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>{modalidade === "recorrente" ? "Data de Partida *" : "Data Início *"}</label>
            <input type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} className={inputClass} required />
          </div>
          {modalidade === "faixa_fixa" && (
            <div>
              <label className={labelClass}>Data Fim *</label>
              <input type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} className={inputClass} required />
            </div>
          )}
        </div>

        {/* Fontes */}
        <div>
          <label className={labelClass}>Fontes de Dados</label>
          <div className="flex gap-3">
            {FONTE_OPTIONS.map((f) => (
              <label key={f.value} className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={fontes.includes(f.value)}
                  onChange={() => toggleFonte(f.value)}
                  className="rounded border-gray-300 text-legal-600 focus:ring-legal-600"
                />
                <span className="text-sm text-[var(--card-foreground)]">{f.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Scheduler config */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className={labelClass}>Intervalo</label>
            <select value={intervalo} onChange={(e) => setIntervalo(parseInt(e.target.value))} className={inputClass}>
              {INTERVALO_PRESETS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Horario Inicio</label>
            <input type="time" value={horarioInicio} onChange={(e) => setHorarioInicio(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Horario Fim</label>
            <input type="time" value={horarioFim} onChange={(e) => setHorarioFim(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Prioridade</label>
            <select value={prioridade} onChange={(e) => setPrioridade(e.target.value)} className={inputClass}>
              {PRIORIDADE_OPTIONS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Dias semana */}
        <div>
          <label className={labelClass}>Dias da Semana</label>
          <div className="flex gap-2">
            {[
              { day: "1", label: "Seg" },
              { day: "2", label: "Ter" },
              { day: "3", label: "Qua" },
              { day: "4", label: "Qui" },
              { day: "5", label: "Sex" },
              { day: "6", label: "Sab" },
              { day: "7", label: "Dom" },
            ].map(({ day, label }) => {
              const selected = diasSemana.split(",").includes(day);
              return (
                <button
                  key={day}
                  type="button"
                  onClick={() => {
                    const dias = diasSemana.split(",").filter((d) => d);
                    if (selected) {
                      setDiasSemana(dias.filter((d) => d !== day).join(","));
                    } else {
                      setDiasSemana([...dias, day].sort().join(","));
                    }
                  }}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    selected
                      ? "bg-legal-600 text-white"
                      : "border bg-[var(--card)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Auto enriquecer */}
        <div>
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoEnriquecer}
              onChange={(e) => setAutoEnriquecer(e.target.checked)}
              className="rounded border-gray-300 text-legal-600 focus:ring-legal-600"
            />
            <span className="text-sm text-[var(--card-foreground)]">
              Enriquecer automaticamente (executar pipeline multi-agentes nos novos processos)
            </span>
          </label>
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center gap-2 rounded-lg bg-legal-600 px-4 py-2 text-sm font-medium text-white hover:bg-legal-700 disabled:opacity-50 transition-colors"
          >
            {isSaving ? <RefreshCw className="h-4 w-4 animate-spin" /> : initialData ? <Edit2 className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {isSaving ? "Salvando..." : initialData ? "Salvar Alteracoes" : "Criar Captacao"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border px-4 py-2 text-sm font-medium text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors"
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
}
