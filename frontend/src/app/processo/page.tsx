"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { api, ProcessoResult, ProcessoMonitorado, ProcessoMonitoradoStats, PublicacaoItem, ProcMonitorHistory } from "@/lib/api";
import { ProcessoCard } from "@/components/ProcessoCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { TimelineView } from "@/components/TimelineView";
import { RiskBadge } from "@/components/RiskBadge";
import {
  Search,
  Zap,
  AlertCircle,
  FileText,
  Clock,
  ShieldAlert,
  Database,
  RefreshCw,
  Trash2,
  Eye,
  Activity,
  CheckCircle2,
  XCircle,
  Plus,
  X,
  ArrowUpDown,
  SlidersHorizontal,
  Filter,
  Building2,
  Calendar,
  Gavel,
  Scale,
  Tag,
  ChevronDown,
  ChevronUp,
  Briefcase,
  Users,
  ExternalLink,
  BookOpen,
  Globe,
  Hash,
  CreditCard,
  Settings,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

// ─── Helpers ────────────────────────────────────────────────────────────────

/** Formata data para horário de Brasília (UTC-3) */
function formatDateBR(d: string | null | undefined): string {
  if (!d) return "Nunca";
  try {
    return new Date(d).toLocaleString("pt-BR", {
      timeZone: "America/Sao_Paulo",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return d || "Nunca";
  }
}

/** Formata processo CNJ: 20 dígitos → NNNNNNN-DD.AAAA.J.TR.OOOO */
function formatProcessoCNJ(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 20) {
    return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits.slice(13, 14)}.${digits.slice(14, 16)}.${digits.slice(16, 20)}`;
  }
  return raw;
}

/** Parseia data flexível para Date */
function parseFlexDate(raw: string | undefined | null): Date | null {
  if (!raw || raw === "Nunca" || raw === "Data indisponivel") return null;
  const s = raw.trim();
  const brMatch = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (brMatch) return new Date(Number(brMatch[3]), Number(brMatch[2]) - 1, Number(brMatch[1]));
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

/** Timestamp para ordenação */
function dateToSortKey(raw: string | undefined | null): number {
  const d = parseFlexDate(raw);
  return d ? d.getTime() : 0;
}

// ─── Tipos de ordenação ─────────────────────────────────────────────────────

type SortOption =
  | "movim-desc"
  | "movim-asc"
  | "processo-az"
  | "processo-za"
  | "tribunal-az"
  | "tribunal-za"
  | "total-movim-desc"
  | "total-movim-asc"
  | "criado-desc"
  | "criado-asc";

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "movim-desc", label: "Última movimentação (recente)" },
  { value: "movim-asc", label: "Última movimentação (antiga)" },
  { value: "total-movim-desc", label: "Mais movimentações" },
  { value: "total-movim-asc", label: "Menos movimentações" },
  { value: "tribunal-az", label: "Tribunal A → Z" },
  { value: "tribunal-za", label: "Tribunal Z → A" },
  { value: "processo-az", label: "Número processo A → Z" },
  { value: "processo-za", label: "Número processo Z → A" },
  { value: "criado-desc", label: "Adicionado recentemente" },
  { value: "criado-asc", label: "Adicionado há mais tempo" },
];

// ─── Highlight de busca ─────────────────────────────────────────────────────

function HighlightText({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === query.toLowerCase() ? (
          <mark key={i} className="bg-yellow-200/80 text-yellow-900 rounded px-0.5">{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

// ─── Componente Principal ───────────────────────────────────────────────────

function ProcessoPageInner() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  // Modo da pagina
  const [pageMode, setPageMode] = useState<"monitorados" | "analise">("monitorados");

  // === Estado Analise IA ===
  const [numero, setNumero] = useState(initialQuery);
  const [tribunal, setTribunal] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ProcessoResult | null>(null);
  const [resumo, setResumo] = useState<string>("");
  const [timeline, setTimeline] = useState<ProcessoResult["timeline"]>([]);
  const [riscos, setRiscos] = useState<ProcessoResult["riscos"]>(undefined);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("resumo");
  const [resultados, setResultados] = useState<ProcessoResult[]>([]);
  const [loadingResults, setLoadingResults] = useState(true);

  // === Dados DJEN do processo selecionado ===
  const [djenData, setDjenData] = useState<PublicacaoItem[]>([]);
  const [loadingDjen, setLoadingDjen] = useState(false);

  // === Estado Processos Monitorados ===
  const [processos, setProcessos] = useState<ProcessoMonitorado[]>([]);
  const [processosStats, setProcessosStats] = useState<ProcessoMonitoradoStats | null>(null);
  const [loadingProcessos, setLoadingProcessos] = useState(true);
  const [verificando, setVerificando] = useState(false);
  const [selectedProcesso, setSelectedProcesso] = useState<ProcessoMonitorado | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [novoProcesso, setNovoProcesso] = useState({ numero_processo: "", tribunal: "" });
  const [addingProcesso, setAddingProcesso] = useState(false);

  // === Histórico de Verificações ===
  const [history, setHistory] = useState<ProcMonitorHistory[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // === BUSCA E FILTROS ===
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("movim-desc");
  const [filterTribunal, setFilterTribunal] = useState("todos");
  const [filterStatus, setFilterStatus] = useState("todos");
  const [filterMovimentacao, setFilterMovimentacao] = useState("todos");
  const [showFilters, setShowFilters] = useState(false);

  // === CONFIGURAÇÃO DE CICLO ===
  const [showSettings, setShowSettings] = useState(false);
  const [datajudInterval, setDatajudInterval] = useState(6);
  const [isSavingSettings, setIsSavingSettings] = useState(false);

  // === Controle de visto/não visto (localStorage) ===
  const [seenProcessos, setSeenProcessos] = useState<Record<string, number>>(() => {
    if (typeof window === "undefined") return {};
    try { return JSON.parse(localStorage.getItem("captacao_seen_processos") || "{}"); }
    catch { return {}; }
  });

  const markProcessoSeen = useCallback((numero: string, total: number) => {
    setSeenProcessos(prev => {
      const next = { ...prev, [numero]: total };
      try { localStorage.setItem("captacao_seen_processos", JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const markAllProcessosSeen = useCallback(() => {
    const all: Record<string, number> = {};
    processos.forEach(p => { all[p.numero_processo] = p.total_movimentacoes; });
    setSeenProcessos(all);
    try { localStorage.setItem("captacao_seen_processos", JSON.stringify(all)); } catch {}
  }, [processos]);

  // === Listas dinâmicas para dropdowns de filtro ===
  const tribunaisDisponiveis = useMemo(() => {
    const set = new Set<string>();
    processos.forEach(p => { if (p.tribunal) set.add(p.tribunal); });
    return Array.from(set).sort();
  }, [processos]);

  // === FILTRAGEM E ORDENAÇÃO COMPLETA ===
  const processosFiltrados = useMemo(() => {
    let filtered = [...processos];

    // Filtro por tribunal
    if (filterTribunal !== "todos") {
      filtered = filtered.filter(p => p.tribunal === filterTribunal);
    }

    // Filtro por status
    if (filterStatus !== "todos") {
      if (filterStatus === "ativo") filtered = filtered.filter(p => p.status === "ativo");
      if (filterStatus === "inativo") filtered = filtered.filter(p => p.status !== "ativo");
    }

    // Filtro por movimentação
    if (filterMovimentacao !== "todos") {
      if (filterMovimentacao === "com") filtered = filtered.filter(p => p.total_movimentacoes > 0);
      if (filterMovimentacao === "sem") filtered = filtered.filter(p => p.total_movimentacoes === 0);
      if (filterMovimentacao === "recente") {
        const umaSemanaAtras = Date.now() - 7 * 24 * 60 * 60 * 1000;
        filtered = filtered.filter(p => {
          const dt = parseFlexDate(p.data_ultima_movimentacao);
          return dt && dt.getTime() > umaSemanaAtras;
        });
      }
      if (filterMovimentacao === "novas") {
        filtered = filtered.filter(p =>
          p.total_movimentacoes > 0 &&
          p.total_movimentacoes !== (seenProcessos[p.numero_processo] ?? -1)
        );
      }
    }

    // Busca textual robusta: multi-token AND em todos campos
    if (searchQuery.trim()) {
      const tokens = searchQuery.toLowerCase().split(/\s+/).filter(Boolean);
      filtered = filtered.filter(p => {
        const searchable = [
          p.numero_processo || "",
          formatProcessoCNJ(p.numero_processo || ""),
          p.tribunal || "",
          p.classe_processual || "",
          p.orgao_julgador || "",
          p.status || "",
          p.origem || "",
          ...(Array.isArray(p.assuntos) ? p.assuntos : typeof p.assuntos === "string" ? [p.assuntos] : []),
          ...(p.movimentacoes || []).map(m =>
            [m.nome || "", m.complemento || "", String(m.codigo || "")].join(" ")
          ),
        ].join(" ").toLowerCase();
        return tokens.every(tok => searchable.includes(tok));
      });
    }

    // Ordenação
    filtered.sort((a, b) => {
      switch (sortBy) {
        case "movim-desc":
          return dateToSortKey(b.data_ultima_movimentacao) - dateToSortKey(a.data_ultima_movimentacao);
        case "movim-asc":
          return dateToSortKey(a.data_ultima_movimentacao) - dateToSortKey(b.data_ultima_movimentacao);
        case "total-movim-desc":
          return b.total_movimentacoes - a.total_movimentacoes;
        case "total-movim-asc":
          return a.total_movimentacoes - b.total_movimentacoes;
        case "tribunal-az":
          return (a.tribunal || "").localeCompare(b.tribunal || "");
        case "tribunal-za":
          return (b.tribunal || "").localeCompare(a.tribunal || "");
        case "processo-az":
          return (a.numero_processo || "").localeCompare(b.numero_processo || "");
        case "processo-za":
          return (b.numero_processo || "").localeCompare(a.numero_processo || "");
        case "criado-desc":
          return dateToSortKey(b.criado_em) - dateToSortKey(a.criado_em);
        case "criado-asc":
          return dateToSortKey(a.criado_em) - dateToSortKey(b.criado_em);
        default:
          return 0;
      }
    });

    return filtered;
  }, [processos, filterTribunal, filterStatus, filterMovimentacao, searchQuery, sortBy, seenProcessos]);

  // Contagem de filtros ativos
  const activeFilterCount = useMemo(() => {
    let c = 0;
    if (filterTribunal !== "todos") c++;
    if (filterStatus !== "todos") c++;
    if (filterMovimentacao !== "todos") c++;
    if (searchQuery.trim()) c++;
    if (sortBy !== "movim-desc") c++;
    return c;
  }, [filterTribunal, filterStatus, filterMovimentacao, searchQuery, sortBy]);

  const clearAllFilters = useCallback(() => {
    setSearchQuery("");
    setFilterTribunal("todos");
    setFilterStatus("todos");
    setFilterMovimentacao("todos");
    setSortBy("movim-desc");
  }, []);

  // === Carregar dados DJEN de um processo ===
  const loadDjenData = useCallback(async (numProcesso: string) => {
    setLoadingDjen(true);
    setDjenData([]);
    try {
      const items = await api.buscarLocal({ termo: numProcesso, limite: 1000000 });
      setDjenData(items);
    } catch {
      // silently fail — DJEN data é complementar
    } finally {
      setLoadingDjen(false);
    }
  }, []);

  const loadHistory = useCallback(async (numProcesso: string) => {
    setLoadingHistory(true);
    try {
      const h = await api.getProcessoMonitoradoHistory(numProcesso);
      setHistory(h);
    } catch {
      setHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  // === Carregar processos monitorados ===
  const loadProcessos = useCallback(async () => {
    try {
      setLoadingProcessos(true);
      const [lista, stats] = await Promise.all([
        api.listarProcessosMonitorados({ limite: 1000000 }),
        api.getProcessoMonitoradoStats(),
      ]);
      setProcessos(lista.processos || []);
      setProcessosStats(stats);
    } catch {
      // silently fail
    } finally {
      setLoadingProcessos(false);
    }
  }, []);

  const loadSettings = useCallback(async () => {
    try {
      const s = await api.getSettings();
      if (s.datajud_update_interval_hours) {
        setDatajudInterval(parseInt(s.datajud_update_interval_hours));
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadProcessos();
    loadResultados();
    loadSettings();
  }, [loadProcessos, loadSettings]);

  useEffect(() => {
    if (initialQuery) {
      setPageMode("analise");
      handleAnalyze();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Quando seleciona um processo, carrega dados DJEN em paralelo
  useEffect(() => {
    if (selectedProcesso) {
      loadDjenData(selectedProcesso.numero_processo);
      loadHistory(selectedProcesso.numero_processo);
    }
  }, [selectedProcesso, loadDjenData, loadHistory]);

  const loadResultados = async () => {
    try {
      const data = await api.getResultados({ limit: 1000000 });
      setResultados(Array.isArray(data) ? data : data.items || []);
    } catch {
      // silently fail
    } finally {
      setLoadingResults(false);
    }
  };

  const handleAnalyze = async () => {
    if (!numero.trim()) return;
    setError("");
    setIsAnalyzing(true);
    setResult(null);
    setResumo("");
    setTimeline([]);
    setRiscos(undefined);
    setDjenData([]);

    try {
      // Busca DataJud + DJEN em paralelo
      const [data, djenItems] = await Promise.all([
        api.analisarProcesso({
          numero_processo: numero.trim(),
          tribunal: tribunal || undefined,
        }),
        api.buscarLocal({ termo: numero.trim(), limite: 1000000 }).catch(() => []),
      ]);
      setResult(data);
      setDjenData(djenItems);

      const [resumoData, timelineData, riscosData] = await Promise.allSettled([
        api.getResumo(numero.trim()),
        api.getTimeline(numero.trim()),
        api.getRiscos(numero.trim()),
      ]);

      if (resumoData.status === "fulfilled") {
        setResumo(typeof resumoData.value === "string" ? resumoData.value : resumoData.value.resumo || "");
      }
      if (timelineData.status === "fulfilled") {
        setTimeline(Array.isArray(timelineData.value) ? timelineData.value : []);
      }
      if (riscosData.status === "fulfilled") {
        setRiscos(riscosData.value);
      }
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setError(message || "Erro ao analisar processo. Verifique o numero e tente novamente.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleVerificarAgora = async () => {
    setVerificando(true);
    try {
      await api.verificarProcessosAgora();
      await loadProcessos();
    } catch {
      // ignore
    } finally {
      setVerificando(false);
    }
  };

  const handleDeletar = async (numero: string) => {
    if (!confirm(`Desativar monitoramento do processo ${numero}?`)) return;
    try {
      await api.deletarProcessoMonitorado(numero);
      await loadProcessos();
      if (selectedProcesso?.numero_processo === numero) setSelectedProcesso(null);
    } catch {
      alert("Erro ao desativar processo");
    }
  };

  const handleAddProcesso = async () => {
    if (!novoProcesso.numero_processo.trim()) return;
    setAddingProcesso(true);
    try {
      await api.registrarProcessoMonitorado({
        numero_processo: novoProcesso.numero_processo.trim(),
        tribunal: novoProcesso.tribunal || undefined,
        origem: "manual",
      });
      setNovoProcesso({ numero_processo: "", tribunal: "" });
      setShowAddForm(false);
      await loadProcessos();
    } catch {
      alert("Erro ao registrar processo. Verifique se o número é válido.");
    } finally {
      setAddingProcesso(false);
    }
  };

  const handleSaveInterval = async (val: number) => {
    setIsSavingSettings(true);
    try {
      await api.updateSetting("datajud_update_interval_hours", val.toString());
      setDatajudInterval(val);
      setShowSettings(false);
      // Recarregar stats para ver se a proxima verificacao mudou (embora o backend faca isso)
      loadProcessos();
    } catch {
      alert("Erro ao salvar configuração");
    } finally {
      setIsSavingSettings(false);
    }
  };

  const tabs = [
    { id: "resumo", label: "Resumo", icon: FileText },
    { id: "timeline", label: "Timeline Unificada", icon: Clock },
    { id: "historico", label: "Histórico de Verificações", icon: Activity },
    { id: "riscos", label: "Riscos", icon: ShieldAlert },
    { id: "djen", label: "Publicações DJEN", icon: Globe },
    { id: "dados", label: "Dados Completos", icon: Database },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">Processos</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Monitore processos judiciais e acompanhe movimentações
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setPageMode("monitorados"); setResult(null); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              pageMode === "monitorados"
                ? "bg-legal-600 text-white"
                : "bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:bg-[var(--secondary)]/80"
            }`}
          >
            <Activity className="h-4 w-4 inline mr-1.5" />
            Monitorados
          </button>
          <button
            onClick={() => setPageMode("analise")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              pageMode === "analise"
                ? "bg-legal-600 text-white"
                : "bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:bg-[var(--secondary)]/80"
            }`}
          >
            <Search className="h-4 w-4 inline mr-1.5" />
            Análise IA
          </button>
        </div>
      </div>

      {/* ==================== MODO: PROCESSOS MONITORADOS ==================== */}
      {pageMode === "monitorados" && (
        <>
          {/* Info Banner */}
          <div className="bg-amber-50/50 border border-amber-200 border-l-4 border-l-amber-500 p-4 mb-2 rounded-md shadow-sm">
            <div className="flex">
              <div className="flex-shrink-0">
                <Scale className="h-5 w-5 text-amber-500 mt-0.5" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-semibold text-amber-800">Acompanhamento Processual Unificado</h3>
                <p className="mt-1 text-sm text-amber-700 leading-relaxed font-normal">
                  Nesta aba você acompanha a <strong>Timeline Unificada</strong> dos seus processos. Consolidamos dados estruturados do DataJud (movimentações) e publicações do DJEN em um único fluxo cronológico para facilitar seu controle e gestão.
                </p>
              </div>
            </div>
          </div>

          {/* Stats Cards */}
          {processosStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-lg border bg-[var(--card)] p-4">
                <p className="text-xs text-[var(--muted-foreground)]">Total</p>
                <p className="text-2xl font-bold text-[var(--card-foreground)]">{processosStats.total}</p>
              </div>
              <div className="rounded-lg border bg-[var(--card)] p-4">
                <p className="text-xs text-[var(--muted-foreground)]">Com Movimentações</p>
                <p className="text-2xl font-bold text-green-600">{processosStats.com_movimentacoes}</p>
              </div>
              <div className="rounded-lg border bg-[var(--card)] p-4">
                <p className="text-xs text-[var(--muted-foreground)]">Verificados Hoje</p>
                <p className="text-2xl font-bold text-blue-600">{processosStats.verificados_hoje}</p>
              </div>
              <div className="rounded-lg border bg-[var(--card)] p-4">
                <p className="text-xs text-[var(--muted-foreground)]">Última Verificação</p>
                <p className="text-sm font-medium text-[var(--card-foreground)]">{formatDateBR(processosStats.ultima_verificacao)}</p>
              </div>
            </div>
          )}

          {/* ══════ TOOLBAR: BUSCA + FILTROS + AÇÕES ══════ */}
          <div className="rounded-lg border bg-[var(--card)] p-4 shadow-sm space-y-3">
            {/* Linha 1: Busca + botões */}
            <div className="flex flex-col sm:flex-row gap-3">
              {/* Campo de busca robusta */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Buscar por processo, tribunal, classe, assunto, órgão julgador, movimentação..."
                  className="w-full rounded-lg border bg-[var(--background)] py-2.5 pl-10 pr-10 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>

              {/* Botão filtros */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors shrink-0 ${
                  showFilters || activeFilterCount > 0
                    ? "border-legal-600/40 bg-legal-600/5 text-legal-600"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"
                }`}
              >
                <SlidersHorizontal className="h-4 w-4" />
                Filtros
                {activeFilterCount > 0 && (
                  <span className="rounded-full bg-legal-600 px-1.5 py-0.5 text-xs text-white leading-none">
                    {activeFilterCount}
                  </span>
                )}
              </button>

              {/* Ordenação */}
              <div className="flex items-center gap-2 shrink-0">
                <ArrowUpDown className="h-4 w-4 text-[var(--muted-foreground)]" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  className="rounded-lg border bg-[var(--background)] px-3 py-2.5 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none"
                >
                  {SORT_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Linha 2: Filtros avançados (colapsável) */}
            {showFilters && (
              <div className="flex flex-col sm:flex-row gap-3 rounded-lg border bg-[var(--secondary)]/30 p-3">
                {/* Filtro Tribunal */}
                <div className="flex-1">
                  <label className="block text-xs font-medium text-[var(--muted-foreground)] mb-1.5">
                    <Building2 className="inline h-3 w-3 mr-1" /> Tribunal
                  </label>
                  <select
                    value={filterTribunal}
                    onChange={(e) => setFilterTribunal(e.target.value)}
                    className="w-full rounded-lg border bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none"
                  >
                    <option value="todos">Todos os tribunais</option>
                    {tribunaisDisponiveis.map(t => (
                      <option key={t} value={t}>{t} ({processos.filter(p => p.tribunal === t).length})</option>
                    ))}
                  </select>
                </div>

                {/* Filtro Status */}
                <div className="flex-1">
                  <label className="block text-xs font-medium text-[var(--muted-foreground)] mb-1.5">
                    <CheckCircle2 className="inline h-3 w-3 mr-1" /> Status
                  </label>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="w-full rounded-lg border bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none"
                  >
                    <option value="todos">Todos</option>
                    <option value="ativo">Ativos</option>
                    <option value="inativo">Inativos</option>
                  </select>
                </div>

                {/* Filtro Movimentação */}
                <div className="flex-1">
                  <label className="block text-xs font-medium text-[var(--muted-foreground)] mb-1.5">
                    <Activity className="inline h-3 w-3 mr-1" /> Movimentação
                  </label>
                  <select
                    value={filterMovimentacao}
                    onChange={(e) => setFilterMovimentacao(e.target.value)}
                    className="w-full rounded-lg border bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none"
                  >
                    <option value="todos">Todos</option>
                    <option value="com">Com movimentações</option>
                    <option value="sem">Sem movimentações</option>
                    <option value="recente">Movimentação nos últimos 7 dias</option>
                    <option value="novas">Novas não visualizadas</option>
                  </select>
                </div>

                {/* Limpar tudo */}
                {activeFilterCount > 0 && (
                  <div className="flex items-end">
                    <button
                      onClick={clearAllFilters}
                      className="flex items-center gap-1.5 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-500/10 transition-colors"
                    >
                      <X className="h-3.5 w-3.5" /> Limpar
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Barra de status */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <p className="text-xs text-[var(--muted-foreground)]">
                Exibindo <span className="font-semibold text-[var(--card-foreground)]">{processosFiltrados.length}</span> de {processos.length} processos
              </p>

              {/* Tags de filtros ativos */}
              {activeFilterCount > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {filterTribunal !== "todos" && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2 py-0.5 text-xs text-blue-700">
                      {filterTribunal} <button onClick={() => setFilterTribunal("todos")}><X className="h-3 w-3" /></button>
                    </span>
                  )}
                  {filterStatus !== "todos" && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-green-500/10 px-2 py-0.5 text-xs text-green-700">
                      {filterStatus} <button onClick={() => setFilterStatus("todos")}><X className="h-3 w-3" /></button>
                    </span>
                  )}
                  {filterMovimentacao !== "todos" && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-700">
                      {filterMovimentacao} <button onClick={() => setFilterMovimentacao("todos")}><X className="h-3 w-3" /></button>
                    </span>
                  )}
                  {sortBy !== "movim-desc" && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/10 px-2 py-0.5 text-xs text-purple-700">
                      Ord: {SORT_OPTIONS.find(o => o.value === sortBy)?.label}
                      <button onClick={() => setSortBy("movim-desc")}><X className="h-3 w-3" /></button>
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Toolbar de ações */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={handleVerificarAgora}
                disabled={verificando}
                className="flex items-center gap-2 rounded-lg bg-legal-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-legal-700 disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${verificando ? "animate-spin" : ""}`} />
                {verificando ? "Verificando DataJud..." : "Verificar Agora"}
              </button>
              <button
                onClick={() => setShowAddForm(!showAddForm)}
                className="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium text-[var(--foreground)] transition-colors hover:bg-[var(--secondary)]"
              >
                <Plus className="h-4 w-4" /> Adicionar Processo
              </button>
              <button
                onClick={() => setShowSettings(true)}
                className="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium text-[var(--foreground)] transition-colors hover:bg-[var(--secondary)]"
              >
                <Settings className="h-4 w-4" /> Configurar Ciclo
              </button>
            </div>
            <div className="flex gap-2">
              <button
                onClick={loadProcessos}
                className="flex items-center gap-2 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              >
                <RefreshCw className="h-3.5 w-3.5" /> Atualizar
              </button>
              {processos.length > 0 && (
                <button
                  onClick={markAllProcessosSeen}
                  className="flex items-center gap-2 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  <Eye className="h-3.5 w-3.5" /> Marcar todas vistas
                </button>
              )}
            </div>
          </div>

          {/* Add Form */}
          {showAddForm && (
            <div className="rounded-lg border bg-[var(--card)] p-4">
              <h3 className="text-sm font-semibold text-[var(--card-foreground)] mb-3">Adicionar Processo para Monitoramento</h3>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={novoProcesso.numero_processo}
                  onChange={(e) => setNovoProcesso({ ...novoProcesso, numero_processo: e.target.value })}
                  placeholder="Número CNJ: 0000000-00.0000.0.00.0000"
                  className="flex-1 rounded-lg border bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)]"
                />
                <input
                  type="text"
                  value={novoProcesso.tribunal}
                  onChange={(e) => setNovoProcesso({ ...novoProcesso, tribunal: e.target.value })}
                  placeholder="Tribunal (ex: TJSP)"
                  className="w-36 rounded-lg border bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)]"
                />
                <button
                  onClick={handleAddProcesso}
                  disabled={addingProcesso || !novoProcesso.numero_processo.trim()}
                  className="rounded-lg bg-legal-600 px-4 py-2 text-sm font-medium text-white hover:bg-legal-700 disabled:opacity-50"
                >
                  {addingProcesso ? "Salvando..." : "Salvar"}
                </button>
              </div>
            </div>
          )}

          {/* Config Settings Modal */}
          {showSettings && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
              <div className="w-full max-w-md rounded-xl border bg-[var(--card)] p-6 shadow-2xl animate-in fade-in zoom-in duration-200">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-legal-600/10 text-legal-600">
                      <Settings className="h-5 w-5" />
                    </div>
                    <h3 className="text-lg font-bold text-[var(--card-foreground)]">Configuração de Ciclo</h3>
                  </div>
                  <button onClick={() => setShowSettings(false)} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-semibold text-[var(--card-foreground)] mb-2">
                      Frequência de Verificação no DataJud
                    </label>
                    <p className="text-xs text-[var(--muted-foreground)] mb-4 leading-relaxed">
                      Defina de quanto em quanto tempo o sistema deve consultar o CNJ para buscar novas movimentações nos processos monitorados abaixo.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-3">
                      {[1, 3, 6, 12, 24, 48].map((h) => (
                        <button
                          key={h}
                          onClick={() => handleSaveInterval(h)}
                          disabled={isSavingSettings}
                          className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all ${
                            datajudInterval === h
                              ? "border-legal-600 bg-legal-600/5 text-legal-600"
                              : "border-[var(--secondary)] bg-[var(--secondary)]/20 text-[var(--muted-foreground)] hover:border-legal-600/30 hover:text-[var(--foreground)]"
                          }`}
                        >
                          <span className="text-lg font-bold">{h}h</span>
                          <span className="text-[10px] uppercase tracking-wider font-semibold">
                            {h === 1 ? "Cada hora" : `A cada ${h}h`}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="p-4 rounded-lg bg-blue-50/50 border border-blue-100">
                    <div className="flex gap-3">
                      <Clock className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
                      <div className="text-xs text-blue-800 leading-relaxed">
                        <strong>Dica:</strong> Intervalos mais curtos garantem dados mais recentes, mas podem aumentar a latência se você tiver centenas de processos.
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-8 flex justify-end">
                  <button
                    onClick={() => setShowSettings(false)}
                    className="px-6 py-2.5 rounded-lg text-sm font-medium text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors"
                  >
                    Fechar
                  </button>
                </div>
              </div>
            </div>
          )}


          {/* ══════ DETALHE DO PROCESSO SELECIONADO — TIMELINE UNIFICADA ══════ */}
          {selectedProcesso && (() => {
            // Monta timeline unificada mesclando DataJud + DJEN
            const datajudCount = selectedProcesso.movimentacoes?.length || 0;
            const djenCount = djenData.length;
            const totalCount = datajudCount + djenCount;

            type MovItem = { codigo?: number; nome: string; dataHora: string; complemento?: string };
            type UnifiedItem =
              | { source: "datajud"; date: Date | null; sortKey: number; mov: MovItem }
              | { source: "djen"; date: Date | null; sortKey: number; pub: PublicacaoItem };

            const unifiedItems: UnifiedItem[] = [];

            // DataJud movimentações → usa campo dataHora (ISO)
            ((selectedProcesso.movimentacoes || []) as MovItem[]).forEach(mov => {
              const d = parseFlexDate(mov.dataHora);
              unifiedItems.push({ source: "datajud", date: d, sortKey: d ? d.getTime() : -1, mov });
            });

            // DJEN publicações → usa campo data_publicacao (DD/MM/YYYY ou ISO)
            djenData.forEach(pub => {
              const d = parseFlexDate(pub.data_publicacao);
              unifiedItems.push({ source: "djen", date: d, sortKey: d ? d.getTime() : -1, pub });
            });

            // Ordem cronológica decrescente; itens sem data vão pro final
            unifiedItems.sort((a, b) => {
              if (a.sortKey === -1 && b.sortKey === -1) return 0;
              if (a.sortKey === -1) return 1;
              if (b.sortKey === -1) return -1;
              return b.sortKey - a.sortKey;
            });

            return (
            <div className="rounded-lg border bg-[var(--card)] p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-[var(--card-foreground)] font-mono">
                    {formatProcessoCNJ(selectedProcesso.numero_processo)}
                  </h3>
                  <p className="text-sm text-[var(--muted-foreground)]">
                    {selectedProcesso.tribunal} {selectedProcesso.classe_processual ? `- ${selectedProcesso.classe_processual}` : ""}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedProcesso(null)}
                  className="p-2 rounded-lg hover:bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Info grid — dados do processo */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4 text-sm">
                <div>
                  <span className="text-[var(--muted-foreground)] text-xs">Orgao Julgador</span>
                  <p className="font-medium text-[var(--card-foreground)]">{selectedProcesso.orgao_julgador || "-"}</p>
                </div>
                <div>
                  <span className="text-[var(--muted-foreground)] text-xs">Origem</span>
                  <p className="font-medium text-[var(--card-foreground)]">{selectedProcesso.origem}</p>
                </div>
                <div>
                  <span className="text-[var(--muted-foreground)] text-xs">Ultima Movimentacao</span>
                  <p className="font-medium text-[var(--card-foreground)]">
                    {selectedProcesso.data_ultima_movimentacao
                      ? formatDateBR(selectedProcesso.data_ultima_movimentacao)
                      : <span className="text-[var(--muted-foreground)] italic">sem movimentacoes</span>}
                  </p>
                </div>
                <div>
                  <span className="text-[var(--muted-foreground)] text-xs">Ultima Verificacao</span>
                  <p className="font-medium text-[var(--card-foreground)]">{formatDateBR(selectedProcesso.ultima_verificacao)}</p>
                </div>
                <div>
                  <span className="text-[var(--muted-foreground)] text-xs">Total Movimentacoes</span>
                  <p className="font-medium text-[var(--card-foreground)]">{selectedProcesso.total_movimentacoes}</p>
                </div>
                <div>
                  <span className="text-[var(--muted-foreground)] text-xs">Adicionado em</span>
                  <p className="font-medium text-[var(--card-foreground)]">{formatDateBR(selectedProcesso.criado_em)}</p>
                </div>
                {selectedProcesso.assuntos && (
                  <div className="col-span-2 md:col-span-3">
                    <span className="text-[var(--muted-foreground)] text-xs">Assuntos</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {(Array.isArray(selectedProcesso.assuntos) ? selectedProcesso.assuntos : [selectedProcesso.assuntos]).filter(Boolean).map((a, i) => (
                        <span key={i} className="rounded-md bg-[var(--secondary)] px-2 py-0.5 text-xs text-[var(--muted-foreground)]">{a}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* ══════ TIMELINE UNIFICADA ══════ */}
              <div>
                <h4 className="text-sm font-semibold text-[var(--card-foreground)] mb-3 flex items-center gap-2">
                  <Clock className="h-4 w-4 text-legal-600" />
                  Timeline Unificada
                  {loadingDjen && <div className="h-3 w-3 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" />}
                </h4>

                {/* Barra de resumo */}
                <div className="flex flex-wrap items-center gap-3 rounded-lg bg-[var(--secondary)]/50 px-4 py-2.5 mb-4 text-xs">
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-500" />
                    <span className="font-medium text-[var(--card-foreground)]">{datajudCount}</span>
                    <span className="text-[var(--muted-foreground)]">movimentacoes DataJud</span>
                  </span>
                  <span className="text-[var(--muted-foreground)]">+</span>
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-500" />
                    <span className="font-medium text-[var(--card-foreground)]">{djenCount}</span>
                    <span className="text-[var(--muted-foreground)]">publicacoes DJEN</span>
                  </span>
                  <span className="text-[var(--muted-foreground)]">=</span>
                  <span className="font-semibold text-[var(--card-foreground)]">{totalCount} total</span>
                </div>

                {/* Legenda */}
                <div className="flex items-center gap-4 mb-3 text-xs text-[var(--muted-foreground)]">
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-2 w-2 rounded-full bg-blue-500" /> DataJud
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-2 w-2 rounded-full bg-amber-500" /> DJEN
                  </span>
                </div>

                {loadingDjen && djenCount === 0 && datajudCount === 0 ? (
                  <div className="rounded-lg bg-[var(--secondary)] p-4 text-center text-sm text-[var(--muted-foreground)]">
                    Carregando dados...
                  </div>
                ) : unifiedItems.length > 0 ? (
                  <div className="relative max-h-[800px] overflow-y-auto">
                    {/* Linha vertical da timeline */}
                    <div className="absolute left-[11px] top-0 bottom-0 w-px bg-[var(--border)]" />

                    <div className="space-y-1">
                      {unifiedItems.map((item, idx) => {
                        const isDatajud = item.source === "datajud";
                        const dotColor = isDatajud ? "bg-blue-500" : "bg-amber-500";
                        const borderColor = isDatajud ? "border-blue-500/20" : "border-amber-500/20";
                        const bgColor = isDatajud ? "bg-blue-500/5" : "bg-amber-500/5";
                        const dateStr = item.date
                          ? item.date.toLocaleString("pt-BR", {
                              timeZone: "America/Sao_Paulo",
                              day: "2-digit",
                              month: "2-digit",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "Data indisponivel";

                        if (isDatajud) {
                          const mov = item.mov;
                          const movAny = mov as Record<string, unknown>;
                          return (
                            <div key={`dj-${idx}`} className="relative flex items-start gap-3 pl-0">
                              {/* Dot */}
                              <div className={`relative z-10 mt-2 h-[10px] w-[10px] rounded-full ${dotColor} ring-2 ring-[var(--card)] shrink-0 ml-[6px]`} />
                              {/* Card */}
                              <div className={`flex-1 rounded-lg border ${borderColor} ${bgColor} p-3`}>
                                <div className="flex items-center gap-2 mb-1 flex-wrap">
                                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-semibold text-blue-700 uppercase tracking-wider">
                                    <Activity className="h-3 w-3" /> DataJud
                                  </span>
                                  <span className="text-xs text-[var(--muted-foreground)]">{dateStr}</span>
                                  {mov.codigo && (
                                    <span className="text-[10px] text-[var(--muted-foreground)] font-mono bg-[var(--secondary)] rounded px-1.5 py-0.5">Cod: {String(mov.codigo)}</span>
                                  )}
                                </div>
                                <p className="text-sm font-medium text-[var(--card-foreground)]">{String(mov.nome)}</p>
                                {mov.complemento && (
                                  <p className="text-xs text-[var(--card-foreground)] mt-1 whitespace-pre-line leading-relaxed">{String(mov.complemento)}</p>
                                )}
                                {/* Campos extras que a API pode retornar */}
                                {!!movAny.tipo && String(movAny.tipo) !== String(mov.nome) && (
                                  <p className="text-[11px] text-[var(--muted-foreground)] mt-1"><span className="font-semibold">Tipo:</span> {String(movAny.tipo)}</p>
                                )}
                                {!!movAny.descricao && String(movAny.descricao) !== String(mov.nome) && String(movAny.descricao) !== String(mov.complemento ?? "") && (
                                  <p className="text-[11px] text-[var(--muted-foreground)] mt-0.5"><span className="font-semibold">Descricao:</span> {String(movAny.descricao)}</p>
                                )}
                                {!!(movAny.complementosTabelados && Array.isArray(movAny.complementosTabelados) && movAny.complementosTabelados.length > 0) && (
                                  <div className="mt-1.5 flex flex-wrap gap-1">
                                    {(movAny.complementosTabelados as Array<Record<string, unknown>>).map((c, ci) => (
                                      <span key={ci} className="rounded bg-blue-500/10 px-2 py-0.5 text-[10px] text-blue-700">
                                        {String(c.descricao ?? c.nome ?? JSON.stringify(c))}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        } else {
                          const pub = item.pub;
                          return (
                            <div key={`djen-${pub.id ?? idx}`} className="relative flex items-start gap-3 pl-0">
                              {/* Dot */}
                              <div className={`relative z-10 mt-2 h-[10px] w-[10px] rounded-full ${dotColor} ring-2 ring-[var(--card)] shrink-0 ml-[6px]`} />
                              {/* Card */}
                              <div className={`flex-1 rounded-lg border ${borderColor} ${bgColor} p-3`}>
                                <div className="flex items-center gap-2 mb-1 flex-wrap">
                                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[10px] font-semibold text-amber-700 uppercase tracking-wider">
                                    <Globe className="h-3 w-3" /> {pub.fonte || "DJEN"}
                                  </span>
                                  <span className="text-xs text-[var(--muted-foreground)]">{dateStr}</span>
                                  {pub.tribunal && <span className="text-[10px] text-[var(--muted-foreground)]"><Building2 className="inline h-3 w-3 mr-0.5" />{pub.tribunal}</span>}
                                  {pub.caderno && <span className="text-[10px] text-[var(--muted-foreground)]">Caderno {pub.caderno}{pub.pagina ? `, p. ${pub.pagina}` : ""}</span>}
                                </div>
                                {pub.numero_processo && (
                                  <p className="text-xs text-[var(--muted-foreground)] font-mono mb-1">
                                    <FileText className="inline h-3 w-3 mr-1" />{formatProcessoCNJ(pub.numero_processo)}
                                  </p>
                                )}
                                {pub.classe_processual && (
                                  <p className="text-xs font-medium text-[var(--card-foreground)] mb-1">
                                    <Gavel className="inline h-3 w-3 mr-1 text-legal-500" />{pub.classe_processual}
                                  </p>
                                )}
                                {pub.orgao_julgador && (
                                  <p className="text-[11px] text-[var(--muted-foreground)] mb-1">
                                    <Scale className="inline h-3 w-3 mr-1" />{pub.orgao_julgador}
                                  </p>
                                )}
                                {pub.assuntos && pub.assuntos.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mb-1.5">
                                    <Tag className="h-3 w-3 text-[var(--muted-foreground)] shrink-0 mt-0.5" />
                                    {pub.assuntos.map((a, i) => (
                                      <span key={i} className="rounded-md bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-700">{a}</span>
                                    ))}
                                  </div>
                                )}
                                {pub.conteudo && (
                                  <div className="rounded-lg bg-[var(--secondary)]/50 p-2.5 mt-1.5">
                                    <p className="text-xs text-[var(--card-foreground)] whitespace-pre-line leading-relaxed">{pub.conteudo}</p>
                                  </div>
                                )}
                                {pub.partes && pub.partes.length > 0 && (
                                  <div className="mt-2">
                                    <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600 mb-1"><Users className="inline h-3 w-3 mr-1" />Partes ({pub.partes.length})</p>
                                    <ul className="space-y-0.5 ml-4">
                                      {pub.partes.map((pt, i) => <li key={i} className="text-xs text-[var(--card-foreground)] list-disc">{pt}</li>)}
                                    </ul>
                                  </div>
                                )}
                                {pub.advogados && pub.advogados.length > 0 && (
                                  <div className="mt-2">
                                    <p className="text-[10px] font-bold uppercase tracking-wider text-purple-600 mb-1"><Briefcase className="inline h-3 w-3 mr-1" />Advogados ({pub.advogados.length})</p>
                                    <ul className="space-y-0.5 ml-4">
                                      {pub.advogados.map((a, i) => <li key={i} className="text-xs text-[var(--card-foreground)] list-disc">{a}</li>)}
                                    </ul>
                                  </div>
                                )}
                                {pub.oab_encontradas && pub.oab_encontradas.length > 0 && (
                                  <div className="mt-2 flex flex-wrap gap-1.5">
                                    <CreditCard className="h-3 w-3 text-green-500 shrink-0 mt-0.5" />
                                    {pub.oab_encontradas.map((oab, i) => (
                                      <span key={i} className="rounded-full border border-green-500/30 bg-green-500/10 px-2 py-0.5 text-[10px] font-bold text-green-700">{oab}</span>
                                    ))}
                                  </div>
                                )}
                                {pub.movimentos && pub.movimentos.length > 0 && (
                                  <div className="mt-2">
                                    <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted-foreground)] mb-1"><Activity className="inline h-3 w-3 mr-1" />Movimentos ({pub.movimentos.length})</p>
                                    <div className="space-y-1 ml-4">
                                      {pub.movimentos.map((m, mi) => {
                                        const movObj = m as Record<string, unknown>;
                                        return (
                                          <div key={mi} className="text-xs text-[var(--card-foreground)] flex items-start gap-2">
                                            {!!movObj.data_hora && <span className="shrink-0 rounded bg-[var(--secondary)] px-1.5 py-0.5 text-[10px] font-mono text-[var(--muted-foreground)]">{String(movObj.data_hora)}</span>}
                                            <span>{String(movObj.descricao ?? movObj.nome ?? movObj.tipo ?? JSON.stringify(movObj))}</span>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  </div>
                                )}
                                {pub.url_origem && (
                                  <a
                                    href={pub.url_origem}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="mt-2 inline-flex items-center gap-1 text-xs text-legal-600 hover:underline"
                                  >
                                    <ExternalLink className="h-3 w-3" /> Ver publicacao original
                                  </a>
                                )}
                              </div>
                            </div>
                          );
                        }
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-lg bg-[var(--secondary)] p-4 text-center text-sm text-[var(--muted-foreground)]">
                    Nenhuma movimentacao ou publicacao encontrada. Clique em &quot;Verificar Agora&quot; para buscar no DataJud.
                  </div>
                )}
              </div>
            </div>
            );
          })()}

          {/* ══════ LISTA DE PROCESSOS ══════ */}
          {loadingProcessos ? (
            <LoadingSpinner text="Carregando processos monitorados..." />
          ) : processosFiltrados.length > 0 ? (
            <div className="rounded-lg border bg-[var(--card)] shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-[var(--secondary)]">
                    <th className="text-left px-4 py-3 font-medium text-[var(--muted-foreground)]">Processo</th>
                    <th className="text-left px-4 py-3 font-medium text-[var(--muted-foreground)]">Tribunal</th>
                    <th className="text-left px-4 py-3 font-medium text-[var(--muted-foreground)] hidden md:table-cell">Classe</th>
                    <th className="text-center px-4 py-3 font-medium text-[var(--muted-foreground)]">Movim.</th>
                    <th className="text-left px-4 py-3 font-medium text-[var(--muted-foreground)] hidden lg:table-cell">Últ. Movim.</th>
                    <th className="text-center px-4 py-3 font-medium text-[var(--muted-foreground)]">Status</th>
                    <th className="text-right px-4 py-3 font-medium text-[var(--muted-foreground)]">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {processosFiltrados.map((p) => {
                    const hasUnseen = p.total_movimentacoes > 0 && p.total_movimentacoes !== (seenProcessos[p.numero_processo] ?? -1);
                    return (
                       <tr
                        key={p.id}
                        className={`border-b hover:bg-[var(--secondary)]/50 cursor-pointer transition-colors ${
                          selectedProcesso?.id === p.id ? "bg-legal-600/10" : hasUnseen ? "bg-blue-50 dark:bg-blue-500/10 border-l-[3px] border-l-blue-500" : "opacity-75 border-l-[3px] border-l-transparent"
                        }`}
                        onClick={() => {
                          const next = selectedProcesso?.id === p.id ? null : p;
                          setSelectedProcesso(next);
                          if (next) markProcessoSeen(p.numero_processo, p.total_movimentacoes);
                        }}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            {hasUnseen && (
                             <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-500 animate-pulse shrink-0" title="Novas movimentações" />
                            )}
                            <span className={`font-mono text-xs ${hasUnseen ? "font-bold text-[var(--card-foreground)]" : "font-medium text-[var(--muted-foreground)]"}`}>
                              <HighlightText text={formatProcessoCNJ(p.numero_processo)} query={searchQuery} />
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                            {p.tribunal || "-"}
                          </span>
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell">
                          <span className="text-xs text-[var(--muted-foreground)] truncate max-w-[200px] block">
                            <HighlightText text={p.classe_processual || "-"} query={searchQuery} />
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${
                            p.total_movimentacoes > 0
                              ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                              : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                          }`}>
                            {p.total_movimentacoes}
                          </span>
                        </td>
                        <td className="px-4 py-3 hidden lg:table-cell">
                          <span className="text-xs text-[var(--muted-foreground)]">
                            {p.data_ultima_movimentacao ? formatDateBR(p.data_ultima_movimentacao) : formatDateBR(p.ultima_verificacao)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {p.status === "ativo" ? (
                            <CheckCircle2 className="h-4 w-4 text-green-600 inline" />
                          ) : (
                            <XCircle className="h-4 w-4 text-gray-400 inline" />
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                            <button
                              onClick={() => setSelectedProcesso(p)}
                              className="p-1.5 rounded-lg hover:bg-[var(--secondary)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                              title="Ver detalhes"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDeletar(p.numero_processo)}
                              className="p-1.5 rounded-lg hover:bg-red-100 text-[var(--muted-foreground)] hover:text-red-600 dark:hover:bg-red-900/30"
                              title="Desativar monitoramento"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="p-3 border-t text-center text-xs text-[var(--muted-foreground)]">
                Total: <span className="font-semibold text-[var(--card-foreground)]">{processosFiltrados.length}</span> processos
                {processosFiltrados.length !== processos.length && (
                  <> (filtrado de {processos.length})</>
                )}
              </div>
            </div>
          ) : processos.length > 0 ? (
            <div className="rounded-lg border bg-[var(--card)] p-8 text-center text-[var(--muted-foreground)]">
              <Search className="mx-auto h-12 w-12 mb-4 opacity-30" />
              <p>Nenhum processo encontrado com os filtros aplicados.</p>
              <button onClick={clearAllFilters} className="mt-2 text-sm text-legal-600 hover:underline">
                Limpar filtros
              </button>
            </div>
          ) : (
            <div className="rounded-lg border bg-[var(--card)] p-8 text-center text-[var(--muted-foreground)]">
              Nenhum processo monitorado. Processos do monitor serão adicionados automaticamente.
            </div>
          )}
        </>
      )}

      {/* ==================== MODO: ANALISE IA ==================== */}
      {pageMode === "analise" && (
        <>
          {/* Search form */}
          <div className="rounded-lg border bg-[var(--card)] p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-[var(--card-foreground)] mb-4">
              Analisar Processo
            </h2>
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                  Numero CNJ
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
                  <input
                    type="text"
                    value={numero}
                    onChange={(e) => setNumero(e.target.value)}
                    placeholder="0000000-00.0000.0.00.0000"
                    className="w-full rounded-lg border bg-[var(--background)] py-2.5 pl-10 pr-4 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20"
                    onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
                  />
                </div>
              </div>
              <div className="w-full sm:w-48">
                <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                  Tribunal (opcional)
                </label>
                <input
                  type="text"
                  value={tribunal}
                  onChange={(e) => setTribunal(e.target.value)}
                  placeholder="Ex: TJSP"
                  className="w-full rounded-lg border bg-[var(--background)] px-4 py-2.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleAnalyze}
                  disabled={isAnalyzing || !numero.trim()}
                  className="flex items-center gap-2 rounded-lg bg-legal-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-legal-700 disabled:opacity-50"
                >
                  {isAnalyzing ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <Zap className="h-4 w-4" />
                  )}
                  {isAnalyzing ? "Analisando..." : "Analisar"}
                </button>
              </div>
            </div>

            {error && (
              <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Analysis Results */}
          {isAnalyzing && (
            <div className="rounded-lg border bg-[var(--card)] p-12">
              <LoadingSpinner size="lg" text="Analisando processo com IA... Isso pode levar alguns minutos." />
            </div>
          )}

          {result && !isAnalyzing && (
            <div className="space-y-4">
              {/* Tabs — agora com aba DJEN */}
              <div className="flex gap-1 rounded-lg border bg-[var(--card)] p-1 overflow-x-auto">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap ${
                      activeTab === tab.id
                        ? "bg-legal-600 text-white shadow-sm"
                        : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"
                    }`}
                  >
                    <tab.icon className="h-4 w-4" />
                    {tab.label}
                    {tab.id === "djen" && djenData.length > 0 && (
                      <span className="rounded-full bg-amber-500/20 text-amber-700 text-xs px-1.5">{djenData.length}</span>
                    )}
                  </button>
                ))}
              </div>

              <div className="rounded-lg border bg-[var(--card)] p-6 shadow-sm">
                {activeTab === "resumo" && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-[var(--card-foreground)]">Resumo Executivo</h3>
                    {resumo ? (
                      <div className="prose prose-sm max-w-none text-[var(--card-foreground)]">
                        <p className="whitespace-pre-wrap leading-relaxed">{resumo}</p>
                      </div>
                    ) : (
                      <p className="text-[var(--muted-foreground)]">Resumo nao disponivel.</p>
                    )}
                    {result.classe && (
                      <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t">
                        <div>
                          <p className="text-xs text-[var(--muted-foreground)]">Classe</p>
                          <p className="text-sm font-medium text-[var(--card-foreground)]">{result.classe}</p>
                        </div>
                        <div>
                          <p className="text-xs text-[var(--muted-foreground)]">Assunto</p>
                          <p className="text-sm font-medium text-[var(--card-foreground)]">{result.assunto || "-"}</p>
                        </div>
                        <div>
                          <p className="text-xs text-[var(--muted-foreground)]">Tribunal</p>
                          <p className="text-sm font-medium text-[var(--card-foreground)]">{result.tribunal || "-"}</p>
                        </div>
                        <div>
                          <p className="text-xs text-[var(--muted-foreground)]">Status</p>
                          <p className="text-sm font-medium text-[var(--card-foreground)]">{result.status || "-"}</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === "timeline" && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-[var(--card-foreground)]">Timeline do Processo</h3>
                    <TimelineView events={timeline || []} />
                  </div>
                )}

                {activeTab === "riscos" && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-[var(--card-foreground)]">Analise de Riscos</h3>
                    {riscos ? (
                      <div className="space-y-6">
                        <div className="flex items-center gap-4">
                          <RiskBadge level={riscos.nivel} score={riscos.score} />
                        </div>
                        {riscos.fatores && riscos.fatores.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold text-[var(--card-foreground)] mb-2">Fatores de Risco</h4>
                            <ul className="space-y-2">
                              {riscos.fatores.map((fator, idx) => (
                                <li key={idx} className="flex items-start gap-2 text-sm text-[var(--card-foreground)]">
                                  <AlertCircle className="h-4 w-4 mt-0.5 text-risco-alto shrink-0" />
                                  {fator}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {riscos.recomendacoes && riscos.recomendacoes.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold text-[var(--card-foreground)] mb-2">Recomendacoes</h4>
                            <ul className="space-y-2">
                              {riscos.recomendacoes.map((rec, idx) => (
                                <li key={idx} className="flex items-start gap-2 text-sm text-[var(--card-foreground)]">
                                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-legal-600 shrink-0" />
                                  {rec}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-[var(--muted-foreground)]">Analise de riscos nao disponivel.</p>
                    )}
                  </div>
                )}

                {activeTab === "historico" && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold text-[var(--card-foreground)] flex items-center gap-2">
                        <Activity className="h-5 w-5 text-legal-600" />
                        Histórico de Verificações
                      </h3>
                      <button 
                        onClick={() => selectedProcesso && loadHistory(selectedProcesso.numero_processo)}
                        className="text-xs text-legal-600 hover:underline flex items-center gap-1"
                      >
                        <RefreshCw className={`h-3 w-3 ${loadingHistory ? 'animate-spin' : ''}`} />
                        Atualizar
                      </button>
                    </div>

                    {loadingHistory ? (
                      <div className="py-12 text-center">
                        <div className="h-8 w-8 animate-spin rounded-full border-4 border-legal-600 border-t-transparent mx-auto mb-4" />
                        <p className="text-sm text-[var(--muted-foreground)]">Carregando histórico...</p>
                      </div>
                    ) : history.length > 0 ? (
                      <div className="rounded-lg border overflow-hidden">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="bg-[var(--secondary)] border-b">
                              <th className="text-left px-4 py-3 font-medium text-[var(--muted-foreground)]">Data/Hora</th>
                              <th className="text-left px-4 py-3 font-medium text-[var(--muted-foreground)] font-mono">Fonte</th>
                              <th className="text-center px-4 py-3 font-medium text-[var(--muted-foreground)]">Status</th>
                              <th className="text-left px-4 py-3 font-medium text-[var(--muted-foreground)] font-mono">Resultado</th>
                              <th className="text-left px-4 py-3 font-medium text-[var(--muted-foreground)]">Detalhes</th>
                            </tr>
                          </thead>
                          <tbody>
                            {history.map((h) => (
                              <tr key={h.id} className="border-b hover:bg-[var(--secondary)]/30 transition-colors">
                                <td className="px-4 py-3 whitespace-nowrap text-xs text-[var(--card-foreground)]">
                                  {formatDateBR(h.data_verificacao)}
                                </td>
                                <td className="px-4 py-3">
                                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                                    h.fonte === 'datajud' 
                                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' 
                                      : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                                  }`}>
                                    {h.fonte}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-center">
                                  {h.status === 'ok' ? (
                                    <CheckCircle2 className="h-4 w-4 text-green-600 mx-auto" title="Sucesso" />
                                  ) : h.status === 'sem_mudancas' ? (
                                    <Clock className="h-4 w-4 text-gray-400 mx-auto" title="Sem mudanças" />
                                  ) : (
                                    <AlertCircle className="h-4 w-4 text-red-500 mx-auto" title="Erro" />
                                  )}
                                </td>
                                <td className="px-4 py-3">
                                  <div className="flex flex-col gap-0.5">
                                    <span className="text-xs font-medium text-[var(--card-foreground)]">
                                      {h.total_movimentacoes} Encontrados
                                    </span>
                                    {h.novas_movimentacoes > 0 && (
                                      <span className="text-[10px] font-bold text-green-600">
                                        +{h.novas_movimentacoes} novos
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="px-4 py-3">
                                  <p className="text-xs text-[var(--muted-foreground)] line-clamp-2" title={h.detalhes}>
                                    {h.detalhes || "-"}
                                  </p>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="rounded-lg bg-[var(--secondary)] p-8 text-center text-sm text-[var(--muted-foreground)]">
                        <Activity className="h-10 w-10 mx-auto mb-3 opacity-20" />
                        Ainda não há registros de verificação automática para este processo.
                      </div>
                    )}
                  </div>
                )}

                {/* ══════ ABA DJEN — Publicações do Diário ══════ */}
                {activeTab === "djen" && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-[var(--card-foreground)] flex items-center gap-2">
                      <Globe className="h-5 w-5 text-amber-600" />
                      Publicações DJEN
                      {loadingDjen && <div className="h-4 w-4 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" />}
                    </h3>
                    {djenData.length > 0 ? (
                      <div className="space-y-3">
                        {djenData.map((pub, idx) => (
                          <div key={pub.id ?? idx} className="rounded-lg border p-4">
                            <div className="flex items-center gap-2 mb-2 flex-wrap">
                              <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
                                <Globe className="h-3 w-3" /> {pub.fonte || "DJEN"}
                              </span>
                              {pub.tribunal && <span className="text-xs text-[var(--muted-foreground)]"><Building2 className="inline h-3 w-3 mr-0.5" />{pub.tribunal}</span>}
                              {pub.data_publicacao && <span className="text-xs text-[var(--muted-foreground)]"><Calendar className="inline h-3 w-3 mr-0.5" />{pub.data_publicacao}</span>}
                              {pub.caderno && <span className="text-xs text-[var(--muted-foreground)]">Caderno {pub.caderno}{pub.pagina ? `, p. ${pub.pagina}` : ""}</span>}
                            </div>
                            {pub.classe_processual && (
                              <p className="text-sm font-medium text-[var(--card-foreground)] mb-1">
                                <Gavel className="inline h-3.5 w-3.5 mr-1 text-legal-500" />{pub.classe_processual}
                              </p>
                            )}
                            {pub.conteudo && (
                              <p className="text-sm text-[var(--muted-foreground)] whitespace-pre-line leading-relaxed">{pub.conteudo}</p>
                            )}
                            {pub.advogados && pub.advogados.length > 0 && (
                              <div className="mt-2">
                                <p className="text-xs font-semibold text-purple-600 mb-1"><Briefcase className="inline h-3 w-3 mr-1" />Advogados</p>
                                <ul className="space-y-0.5">
                                  {pub.advogados.map((a, i) => <li key={i} className="text-xs text-[var(--card-foreground)]">- {a}</li>)}
                                </ul>
                              </div>
                            )}
                            {pub.partes && pub.partes.length > 0 && (
                              <div className="mt-2">
                                <p className="text-xs font-semibold text-blue-600 mb-1"><Users className="inline h-3 w-3 mr-1" />Partes</p>
                                <ul className="space-y-0.5">
                                  {pub.partes.map((pt, i) => <li key={i} className="text-xs text-[var(--card-foreground)]">- {pt}</li>)}
                                </ul>
                              </div>
                            )}
                            {pub.url_origem && (
                              <a href={pub.url_origem} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs text-legal-600 hover:underline">
                                <ExternalLink className="h-3 w-3" /> Ver publicação original
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[var(--muted-foreground)]">
                        {loadingDjen ? "Buscando publicações..." : "Nenhuma publicação DJEN encontrada para este processo."}
                      </p>
                    )}
                  </div>
                )}

                {activeTab === "dados" && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-[var(--card-foreground)]">Dados Completos</h3>
                    <pre className="overflow-auto rounded-lg bg-[var(--secondary)] p-4 text-xs text-[var(--secondary-foreground)] max-h-[600px]">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Stored results list */}
          {!result && !isAnalyzing && (
            <div>
              <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4">
                Processos Armazenados
              </h2>
              {loadingResults ? (
                <LoadingSpinner text="Carregando processos..." />
              ) : resultados.length > 0 ? (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {resultados.map((p, idx) => (
                    <ProcessoCard key={p.numero_processo || idx} processo={p} />
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border bg-[var(--card)] p-8 text-center text-[var(--muted-foreground)]">
                  Nenhum processo armazenado ainda.
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function ProcessoPage() {
  return (
    <Suspense fallback={<LoadingSpinner size="lg" text="Carregando..." className="mt-20" />}>
      <ProcessoPageInner />
    </Suspense>
  );
}
