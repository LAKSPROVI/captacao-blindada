"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
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
} from "lucide-react";

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
  // State
  const [captacoes, setCaptacoes] = useState<CaptacaoItem[]>([]);
  const [stats, setStats] = useState<CaptacaoStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showMonitorLink, setShowMonitorLink] = useState(false);

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
        setCaptacoes(listData.value.captacoes || []);
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
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const loadDetail = async (id: number) => {
    setIsLoadingDetail(true);
    try {
      const [hist, res] = await Promise.allSettled([
        api.historicoCaptacao(id, { limite: 20 }),
        api.resultadosCaptacao(id, { limite: 50 }),
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
    setShowMonitorLink(false);
    try {
      const result = await api.executarCaptacao(id);
      setSuccess(
        `Captação #${id}: ${result.total_resultados} resultado(s) encontrado(s), ${result.novos_resultados} novo(s) salvos`
      );
      setShowMonitorLink(result.novos_resultados > 0);
      loadData();
      if (expandedId === id) loadDetail(id);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro desconhecido";
      setError(`Erro ao executar captacao #${id}: ${msg}`);
    } finally {
      setExecutingId(null);
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

      {/* 📊 Data Pipeline Banner */}
      <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 dark:border-blue-800/30 dark:bg-blue-900/10">
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/50">
            <Activity className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-300">Hub de Automação & Destino dos Dados</h3>
            <p className="mt-1 text-sm text-blue-700/80 dark:text-blue-400/80 leading-relaxed">
              As captações configuradas aqui funcionam como robôs que varrem tribunais e diários oficiais. 
              <br className="hidden sm:block" />
              <strong>• Publicações (texto):</strong> São enviadas automaticamente para a aba <Link href="/monitor" className="font-semibold underline">DJEN</Link>.
              <br className="hidden sm:block" />
              <strong>• Processos (movimentação):</strong> Dados estruturados são consolidados na aba <Link href="/processos" className="font-semibold underline">Processos</Link>.
            </p>
          </div>
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
        <div className="rounded-lg border border-green-300 bg-green-50 dark:bg-green-900/20 p-3 text-sm text-green-700 dark:text-green-400 flex items-center gap-2 flex-wrap">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span className="flex-1">{success}</span>
          {showMonitorLink && (
            <Link
              href="/monitor"
              className="inline-flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1 text-xs font-semibold text-white hover:bg-green-700 transition-colors"
            >
              <Eye className="h-3 w-3" />
              Ver no DJEN →
            </Link>
          )}
          <button onClick={() => { setSuccess(""); setShowMonitorLink(false); }} className="text-green-500 hover:text-green-700">&times;</button>
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

      {/* Create form */}
      {showCreateForm && (
        <CreateCaptacaoForm
          onCreated={() => {
            setShowCreateForm(false);
            setSuccess("Captacao criada com sucesso!");
            loadData();
          }}
          onCancel={() => setShowCreateForm(false)}
          isCreating={isCreating}
          setIsCreating={setIsCreating}
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
          captacoes.map((cap) => (
            <CaptacaoCard
              key={cap.id}
              captacao={cap}
              isExpanded={expandedId === cap.id}
              isExecuting={executingId === cap.id}
              onToggleExpand={() => handleToggleExpand(cap.id)}
              onExecutar={() => handleExecutar(cap.id)}
              onPausar={() => handlePausar(cap.id)}
              onRetomar={() => handleRetomar(cap.id)}
              onDesativar={() => handleDesativar(cap.id)}
              detailTab={detailTab}
              setDetailTab={setDetailTab}
              historico={historico}
              resultados={resultados}
              isLoadingDetail={isLoadingDetail}
            />
          ))
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
  onToggleExpand,
  onExecutar,
  onPausar,
  onRetomar,
  onDesativar,
  detailTab,
  setDetailTab,
  historico,
  resultados,
  isLoadingDetail,
}: {
  captacao: CaptacaoItem;
  isExpanded: boolean;
  isExecuting: boolean;
  onToggleExpand: () => void;
  onExecutar: () => void;
  onPausar: () => void;
  onRetomar: () => void;
  onDesativar: () => void;
  detailTab: "historico" | "resultados";
  setDetailTab: (tab: "historico" | "resultados") => void;
  historico: CaptacaoExecucao[];
  resultados: PublicacaoItem[];
  isLoadingDetail: boolean;
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
            <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400">
               <Clock className="h-3 w-3" />
               A cada {intervaloLabel} ({captacao.horario_inicio}–{captacao.horario_fim})
            </div>
            <span className="inline-flex items-center gap-1"><FileText className="h-3 w-3" /> {captacao.total_resultados} resultados</span>
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
                <span className="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-400">
                  {exec.fonte}
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
  if (publicacoes.length === 0) {
    return (
      <p className="text-center text-sm text-[var(--muted-foreground)] py-4">
        Nenhuma publicacao encontrada ainda.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {publicacoes.map((pub, idx) => (
        <div key={pub.id || pub.hash || idx} className="rounded-md border p-3 text-sm">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-400">
              {pub.fonte}
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
              <span className="font-mono text-xs text-legal-600">{pub.numero_processo}</span>
            )}
          </div>
          {pub.conteudo && (
            <p className="text-xs text-[var(--muted-foreground)] line-clamp-3 mt-1">
              {pub.conteudo.length > 300 ? pub.conteudo.slice(0, 300) + "..." : pub.conteudo}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

// =========================================================================
// CreateCaptacaoForm
// =========================================================================

function CreateCaptacaoForm({
  onCreated,
  onCancel,
  isCreating,
  setIsCreating,
  setError,
}: {
  onCreated: () => void;
  onCancel: () => void;
  isCreating: boolean;
  setIsCreating: (v: boolean) => void;
  setError: (v: string) => void;
}) {
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [tipoBusca, setTipoBusca] = useState("processo");
  const [numeroProcesso, setNumeroProcesso] = useState("");
  const [numeroOab, setNumeroOab] = useState("");
  const [ufOab, setUfOab] = useState("SP");
  const [nomeParte, setNomeParte] = useState("");
  const [nomeAdvogado, setNomeAdvogado] = useState("");
  const [tribunal, setTribunal] = useState("");
  const [classeCodigo, setClasseCodigo] = useState("");
  const [assuntoCodigo, setAssuntoCodigo] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [fontes, setFontes] = useState(["datajud", "djen_api"]);
  const [intervalo, setIntervalo] = useState(120);
  const [horarioInicio, setHorarioInicio] = useState("06:00");
  const [horarioFim, setHorarioFim] = useState("23:00");
  const [diasSemana, setDiasSemana] = useState("1,2,3,4,5");
  const [prioridade, setPrioridade] = useState("normal");
  const [autoEnriquecer, setAutoEnriquecer] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nome.trim()) {
      setError("Nome e obrigatorio");
      return;
    }

    setIsCreating(true);
    setError("");

    const params: CaptacaoCreateParams = {
      nome: nome.trim(),
      descricao: descricao.trim() || undefined,
      tipo_busca: tipoBusca,
      fontes,
      intervalo_minutos: intervalo,
      horario_inicio: horarioInicio,
      horario_fim: horarioFim,
      dias_semana: diasSemana,
      prioridade,
      auto_enriquecer: autoEnriquecer,
    };

    // Add type-specific fields
    if (tipoBusca === "processo" && numeroProcesso) params.numero_processo = numeroProcesso.trim();
    if (tipoBusca === "oab") {
      params.numero_oab = numeroOab.trim();
      params.uf_oab = ufOab.trim() || "SP";
    }
    if (tipoBusca === "nome_parte" && nomeParte) params.nome_parte = nomeParte.trim();
    if (tipoBusca === "nome_advogado" && nomeAdvogado) params.nome_advogado = nomeAdvogado.trim();
    if (["classe", "assunto", "tribunal_geral"].includes(tipoBusca) && tribunal) {
      params.tribunal = tribunal.trim().toLowerCase();
    }
    if (tipoBusca === "classe" && classeCodigo) params.classe_codigo = parseInt(classeCodigo);
    if (tipoBusca === "assunto" && assuntoCodigo) params.assunto_codigo = parseInt(assuntoCodigo);
    if (dataInicio) params.data_inicio = dataInicio;
    if (dataFim) params.data_fim = dataFim;

    try {
      await api.criarCaptacao(params);
      onCreated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao criar captacao";
      setError(msg);
    } finally {
      setIsCreating(false);
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
      <h3 className="text-lg font-semibold text-[var(--card-foreground)] mb-4">Nova Captacao</h3>
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

        {/* Type-specific fields */}
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

        {/* Date range */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Data Inicio</label>
            <input type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Data Fim</label>
            <input type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} className={inputClass} />
          </div>
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
            disabled={isCreating}
            className="inline-flex items-center gap-2 rounded-lg bg-legal-600 px-4 py-2 text-sm font-medium text-white hover:bg-legal-700 disabled:opacity-50 transition-colors"
          >
            {isCreating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            {isCreating ? "Criando..." : "Criar Captacao"}
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
