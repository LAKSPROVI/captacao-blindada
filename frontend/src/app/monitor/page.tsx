"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { api, MonitorItem, MonitorStats, PublicacaoItem } from "@/lib/api";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { StatsCard } from "@/components/StatsCard";
import {
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle2,
  Clock,
  Newspaper,
  Activity,
  FileText,
  Calendar,
  Building2,
  Scale,
  Gavel,
  Tag,
  ChevronDown,
  ChevronUp,
  Users,
  Briefcase,
  CreditCard,
  ExternalLink,
  Search,
  X,
  ArrowUpDown,
  SlidersHorizontal,
  Filter,
  BookOpen,
  Globe,
  Layers,
  TrendingUp,
  Trash2,
  RefreshCw,
  Mail,
  MailOpen,
  Zap,
} from "lucide-react";

const TIPO_OPTIONS = [
  { value: "processo", label: "Processo" },
  { value: "oab", label: "OAB" },
  { value: "nome", label: "Nome" },
  { value: "parte", label: "Parte" },
  { value: "advogado", label: "Advogado" },
];

    // DataJud busca APENAS por processo/classe/assunto/orgão — não por nome/OAB/advogado.
    // Fontes pré-definidas por tipo para evitar buscas incorretas.
    function getFontesForTipo(tipo: string): string[] {
        return tipo === "processo" ? ["datajud", "djen_api"] : ["djen_api"];
    }

    function getInfoForTipo(tipo: string): string {
        switch (tipo) {
            case "processo": return "DataJud (metadados processuais + movimentacoes) + DJEN (diarios oficiais)";
            case "oab":      return "DJEN - busca por numero OAB nos diarios oficiais. Formato: 123456/SP";
            case "advogado": return "DJEN - busca por nome de advogado nos diarios oficiais";
            case "nome":     return "DJEN - busca por nome de pessoa/parte nos diarios oficiais";
            case "parte":    return "DJEN - busca por nome de parte nos diarios oficiais";
            default:         return "DJEN (diarios oficiais)";
        }
    }

    function getPlaceholderForTipo(tipo: string): string {
        switch (tipo) {
            case "processo": return "0000000-00.0000.0.00.0000";
            case "oab":      return "123456/SP";
            case "advogado": return "Nome completo do advogado";
            case "nome":     return "Nome completo da pessoa";
            case "parte":    return "Nome completo da parte";
            default:         return "Valor a monitorar";
        }
    }

type SortOption = "date-desc" | "date-asc" | "tribunal-az" | "tribunal-za" | "fonte-az" | "score-desc" | "score-asc";

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "date-desc", label: "Mais recentes primeiro" },
  { value: "date-asc", label: "Mais antigas primeiro" },
  { value: "tribunal-az", label: "Tribunal A → Z" },
  { value: "tribunal-za", label: "Tribunal Z → A" },
  { value: "fonte-az", label: "Fonte A → Z" },
  { value: "score-desc", label: "Score Lead ↓ (melhor)" },
  { value: "score-asc", label: "Score Lead ↑ (pior)" },
];

// ─── Tipos de período para atalhos ──────────────────────────────────────────
type PeriodFilter = "todos" | "hoje" | "ontem" | "7dias";

// ─── Helpers ────────────────────────────────────────────────────────────────

/** Formata processo CNJ: 20 dígitos → NNNNNNN-DD.AAAA.J.TR.OOOO */
function formatProcessoCNJ(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 20) {
    return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits.slice(13, 14)}.${digits.slice(14, 16)}.${digits.slice(16, 20)}`;
  }
  return raw;
}

/** Parseia datas nos formatos DD/MM/YYYY, YYYYMMDDHHmmss, YYYYMMDD ou ISO e retorna Date (ou null) */
function parseFlexDate(raw: string | undefined | null): Date | null {
  if (!raw || raw === "Data indisponivel") return null;
  const s = raw.trim();
  // DD/MM/YYYY
  const brMatch = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (brMatch) {
    const [, dd, mm, yyyy] = brMatch;
    return new Date(Number(yyyy), Number(mm) - 1, Number(dd));
  }
  // YYYYMMDDHHmmss (14 dígitos — formato DataJud)
  const djMatch = s.match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/);
  if (djMatch) {
    const [, yyyy, mm, dd, hh, mi, ss] = djMatch;
    return new Date(Number(yyyy), Number(mm) - 1, Number(dd), Number(hh), Number(mi), Number(ss));
  }
  // YYYYMMDD (8 dígitos)
  const shortMatch = s.match(/^(\d{4})(\d{2})(\d{2})$/);
  if (shortMatch) {
    const [, yyyy, mm, dd] = shortMatch;
    return new Date(Number(yyyy), Number(mm) - 1, Number(dd));
  }
  // ISO ou outros formatos
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

/** Formata data para exibição amigável */
function formatDateDisplay(raw: string | undefined | null): string | null {
  if (!raw || raw === "Data indisponivel") return null;
  const d = parseFlexDate(raw);
  if (!d) return raw;
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
}

/** Timestamp numérico para ordenação (datas normalizadas) */
function dateToSortKey(raw: string | undefined | null): number {
  const d = parseFlexDate(raw);
  return d ? d.getTime() : 0;
}

/** Retorna o início do dia (meia-noite) para uma Date */
function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

/** Verifica se uma publicação pertence a um determinado período */
function pubMatchesPeriod(pub: PublicacaoItem, period: PeriodFilter): boolean {
  if (period === "todos") return true;
  const pubDate = parseFlexDate(pub.data_publicacao);
  if (!pubDate) return false;
  const now = new Date();
  const today = startOfDay(now);
  const pubDay = startOfDay(pubDate);

  switch (period) {
    case "hoje":
      return pubDay.getTime() === today.getTime();
    case "ontem": {
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      return pubDay.getTime() === yesterday.getTime();
    }
    case "7dias": {
      const sevenDaysAgo = new Date(today);
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      return pubDay.getTime() >= sevenDaysAgo.getTime();
    }
    default:
      return true;
  }
}

// ─── Inteligência de Lead ───────────────────────────────────────────────────────────────

const FERIADOS_BR = new Set([
  "2025-01-01","2025-04-18","2025-04-21","2025-05-01","2025-06-19",
  "2025-09-07","2025-10-12","2025-11-02","2025-11-15","2025-12-25",
  "2026-01-01","2026-04-03","2026-04-21","2026-05-01","2026-06-04",
  "2026-09-07","2026-10-12","2026-11-02","2026-11-15","2026-12-25",
]);

function isExecucaoFiscal(item: PublicacaoItem): boolean {
  const haystack = [
    item.classe_processual || "",
    item.conteudo || "",
    ...(item.assuntos || []),
  ].join(" ").toLowerCase();
  return (
    haystack.includes("execução fiscal") ||
    haystack.includes("execucao fiscal") ||
    haystack.includes("dívida ativa") ||
    haystack.includes("divida ativa") ||
    haystack.includes("cobrança fiscal") ||
    haystack.includes("cobranca fiscal")
  );
}

type ScoreInfo = { score: number; label: string; corClasses: string };

function calcularScoreLead(item: PublicacaoItem): ScoreInfo {
  let score = 50;
  const temAdv = !!(item.advogados && item.advogados.length > 0);
  const numAdv = item.advogados?.length ?? 0;
  const numPartes = item.partes?.length ?? 0;
  const numMov = item.movimentos?.length ?? 0;
  const ef = isExecucaoFiscal(item);
  const classe = (item.classe_processual || "").toLowerCase();

  if (!temAdv) score += 40;
  if (numPartes > 0 && numPartes <= 2) score += 15;
  if (ef) score -= 80;
  if (numMov > 0 && numMov <= 3) score += 5;
  if (numAdv >= 3) score -= 40;
  if (classe.includes("recurso") || classe.includes("agravo")) score -= 25;
  if (classe.includes("embargos")) score -= 20;
  if (classe.includes("procedimento comum") || classe.includes("ordinário")) score += 10;

  score = Math.max(0, Math.min(100, score));
  if (score >= 75) return { score, label: "Lead A", corClasses: "bg-green-500/15 text-green-700 border-green-500/30" };
  if (score >= 55) return { score, label: "Lead B", corClasses: "bg-blue-500/15 text-blue-700 border-blue-500/30" };
  if (score >= 35) return { score, label: "Lead C", corClasses: "bg-amber-500/15 text-amber-700 border-amber-500/30" };
  return { score, label: "Baixo", corClasses: "bg-gray-500/10 text-gray-500 border-gray-500/20" };
}

function ScoreBadge({ info }: { info: ScoreInfo }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold ${info.corClasses}`}>
      <TrendingUp className="h-3 w-3" />
      {info.label} {info.score}
    </span>
  );
}

// ─── Realce de termos buscados ──────────────────────────────────────────────
function HighlightText({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === query.toLowerCase() ? (
          <mark key={i} className="bg-yellow-200/80 text-yellow-900 rounded px-0.5">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}


// --- Sanitizacao defensiva de dados ---
function sanitizePublicacao(pub: PublicacaoItem): PublicacaoItem {
  return {
    ...pub,
    advogados: Array.isArray(pub.advogados) ? pub.advogados.filter(Boolean) : [],
    partes: Array.isArray(pub.partes) ? pub.partes.filter(Boolean) : [],
    oab_encontradas: Array.isArray(pub.oab_encontradas) ? pub.oab_encontradas.filter(Boolean) : [],
    assuntos: Array.isArray(pub.assuntos) ? pub.assuntos.filter(Boolean) : [],
    movimentos: Array.isArray(pub.movimentos) ? pub.movimentos : [],
    data_publicacao: pub.data_publicacao || "",
    conteudo: pub.conteudo || "",
    fonte: pub.fonte || "desconhecida",
    tribunal: pub.tribunal || "",
  };
}

// ─── Badge de fonte colorido ────────────────────────────────────────────────
const FONTE_META: Record<string, { label: string; colors: string; icon: typeof Globe }> = {
  datajud:  { label: "DataJud",  colors: "bg-blue-500/10 text-blue-700 border-blue-500/20",   icon: Scale },
  djen_api: { label: "DJEN",     colors: "bg-amber-500/10 text-amber-700 border-amber-500/20", icon: Globe },
  djen:     { label: "DJEN",     colors: "bg-amber-500/10 text-amber-700 border-amber-500/20", icon: Globe },
};

function FonteBadge({ fonte, showLabel }: { fonte?: string; showLabel?: boolean }) {
  if (!fonte) return null;
  const raw = fonte.toLowerCase().replace(/ *\(.*\)$/, "");
  const meta = FONTE_META[raw] || { label: fonte, colors: "bg-gray-500/10 text-gray-600 border-gray-500/20", icon: Layers };
  const Icon = meta.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${meta.colors}`}>
      <Icon className="h-3 w-3" />
      {showLabel ? meta.label : fonte}
    </span>
  );
}

// ─── Barra lateral colorida por fonte ───────────────────────────────────────
function FonteStripe({ fonte }: { fonte?: string }) {
  const raw = (fonte || "").toLowerCase();
  const color = raw.includes("djen") ? "bg-amber-500" : raw === "datajud" ? "bg-blue-500" : "bg-gray-400";
  return <div className={`absolute left-0 top-0 bottom-0 w-1 ${color} rounded-l-lg`} />;
}

// ─── Card de publicação expandível (redesenhado) ────────────────────────────
function PubCard({ pub: rawPub, idx, searchQuery, onDelete, seen, onSeen, onToggleUnseen }: { pub: PublicacaoItem; idx: number; searchQuery: string; onDelete?: (id: number) => void; seen?: boolean; onSeen?: () => void; onToggleUnseen?: () => void }) {
  const pub = useMemo(() => sanitizePublicacao(rawPub), [rawPub]);
  const [expanded, setExpanded] = useState(false);
  const scoreInfo = calcularScoreLead(pub);

  const hasPartes = pub.partes && pub.partes.length > 0;
  const hasAdvogados = pub.advogados && pub.advogados.length > 0;
  const hasOABs = pub.oab_encontradas && pub.oab_encontradas.length > 0;
  const hasMovimentos = pub.movimentos && pub.movimentos.length > 0;
  const hasConteudo = !!pub.conteudo;

  const canExpand =
    hasConteudo || hasPartes || hasAdvogados || hasOABs || hasMovimentos || pub.url_origem;

  // Formatar processo CNJ (para DJEN que vem sem formato)
  const processoFormatado = useMemo(() => {
    if (!pub.numero_processo) return null;
    return formatProcessoCNJ(pub.numero_processo);
  }, [pub.numero_processo]);

  // Formatar data legível (suporta DD/MM/YYYY do DJEN e ISO do DataJud)
  const dataFormatada = useMemo(() => formatDateDisplay(pub.data_publicacao), [pub.data_publicacao]);

  // Contagem de informações extras para badge
  const infoCount = useMemo(() => {
    let c = 0;
    if (hasPartes) c += pub.partes!.length;
    if (hasAdvogados) c += pub.advogados!.length;
    if (hasOABs) c += pub.oab_encontradas!.length;
    if (hasMovimentos) c += pub.movimentos!.length;
    return c;
  }, [hasPartes, hasAdvogados, hasOABs, hasMovimentos, pub]);

  return (
    <div className={`relative group border-b last:border-b-0 transition-colors ${expanded ? "bg-[var(--secondary)]/20" : "hover:bg-[var(--secondary)]/10"} ${!seen ? "bg-blue-50 dark:bg-blue-500/10 border-l-[3px] border-l-blue-500" : "opacity-75 border-l-[3px] border-l-transparent"}`}>
      <FonteStripe fonte={pub.fonte} />
      {/* Cabeçalho do card */}
      <div
        className="p-4 pl-5 cursor-pointer select-none"
        onClick={() => { if (canExpand) { if (!expanded && !seen && onSeen) onSeen(); setExpanded(!expanded); } }}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {/* Número do processo como título principal */}
            <div className="flex items-center gap-2 flex-wrap">
              <FileText className="h-4 w-4 text-legal-600 shrink-0" />
              <h3 className={`text-sm text-[var(--card-foreground)] font-mono tracking-tight ${!seen ? "font-bold" : "font-medium"}`}>
                <HighlightText text={processoFormatado || `Publicação #${pub.id ?? idx + 1}`} query={searchQuery} />
              </h3>
              <FonteBadge fonte={pub.fonte} showLabel />
              <ScoreBadge info={scoreInfo} />
              {!seen && typeof pub.id === "number" && (
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-500 animate-pulse shrink-0" title="Não lida" />
              )}
              {infoCount > 0 && (
                <span className="rounded-full bg-[var(--secondary)] px-2 py-0.5 text-[10px] font-bold text-[var(--muted-foreground)]">
                  {infoCount} info{infoCount > 1 ? "s" : ""}
                </span>
              )}
            </div>

            {/* Dados estruturados em grid */}
            <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-1">
              {pub.classe_processual && (
                <div className="flex items-center gap-1.5 text-sm">
                  <Gavel className="h-3.5 w-3.5 text-legal-500 shrink-0" />
                  <span className="font-medium text-[var(--card-foreground)] truncate">
                    <HighlightText text={pub.classe_processual} query={searchQuery} />
                  </span>
                </div>
              )}
              {pub.orgao_julgador && (
                <div className="flex items-center gap-1.5 text-sm">
                  <Scale className="h-3.5 w-3.5 text-[var(--muted-foreground)] shrink-0" />
                  <span className="text-[var(--muted-foreground)] truncate">
                    <HighlightText text={pub.orgao_julgador} query={searchQuery} />
                  </span>
                </div>
              )}
              {pub.tribunal && (
                <div className="flex items-center gap-1.5 text-sm">
                  <Building2 className="h-3.5 w-3.5 text-[var(--muted-foreground)] shrink-0" />
                  <span className="text-[var(--muted-foreground)]">{pub.tribunal}</span>
                </div>
              )}
              {dataFormatada && (
                <div className="flex items-center gap-1.5 text-sm">
                  <Calendar className="h-3.5 w-3.5 text-[var(--muted-foreground)] shrink-0" />
                  <span className="text-[var(--muted-foreground)]">{dataFormatada}</span>
                </div>
              )}
              {pub.caderno && (
                <div className="flex items-center gap-1.5 text-sm">
                  <BookOpen className="h-3.5 w-3.5 text-[var(--muted-foreground)] shrink-0" />
                  <span className="text-[var(--muted-foreground)]">Caderno {pub.caderno}{pub.pagina ? `, p. ${pub.pagina}` : ""}</span>
                </div>
              )}
              {pub.url_origem && (
                <div className="flex items-center gap-1.5 text-sm">
                  <ExternalLink className="h-3.5 w-3.5 text-legal-500 shrink-0" />
                  <a
                    href={pub.url_origem}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-legal-600 hover:underline truncate"
                  >
                    Fonte original
                  </a>
                </div>
              )}
            </div>

            {/* Assuntos como tags */}
            {pub.assuntos && pub.assuntos.length > 0 && (
              <div className="flex items-start gap-1.5 mt-2 flex-wrap">
                <Tag className="h-3.5 w-3.5 text-[var(--muted-foreground)] shrink-0 mt-0.5" />
                {pub.assuntos.map((a, i) => (
                  <span key={i} className="rounded-md bg-[var(--secondary)] px-2 py-0.5 text-xs text-[var(--muted-foreground)]">
                    {a}
                  </span>
                ))}
              </div>
            )}

            {/* Conteúdo resumido (3 linhas) */}
            {hasConteudo && !expanded && (
              <p className="text-sm text-[var(--muted-foreground)] mt-2 line-clamp-3 leading-relaxed">
                <HighlightText text={pub.conteudo!} query={searchQuery} />
              </p>
            )}

            {/* Mini-resumo de partes/advogados/OABs inline */}
            {!expanded && (hasPartes || hasAdvogados || hasOABs) && (
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--muted-foreground)]">
                {hasPartes && (
                  <span className="flex items-center gap-1">
                    <Users className="h-3 w-3 text-blue-500" />
                    <span className="font-medium text-[var(--card-foreground)]">{pub.partes!.length}</span> parte{pub.partes!.length > 1 ? "s" : ""}
                  </span>
                )}
                {hasAdvogados && (
                  <span className="flex items-center gap-1">
                    <Briefcase className="h-3 w-3 text-purple-500" />
                    <span className="font-medium text-[var(--card-foreground)]">{pub.advogados!.length}</span> advogado{pub.advogados!.length > 1 ? "s" : ""}
                  </span>
                )}
                {hasOABs && (
                  <span className="flex items-center gap-1">
                    <CreditCard className="h-3 w-3 text-green-500" />
                    {pub.oab_encontradas!.map((oab, i) => (
                      <span key={i} className="rounded bg-green-500/10 px-1.5 py-0 text-green-700 font-medium">{oab}</span>
                    ))}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Indicador expandir + botão lido/não lido */}
          <div className="shrink-0 flex flex-col items-center gap-1">
            {/* Botão toggle lido/não lido */}
            {typeof pub.id === "number" && onToggleUnseen && (
              <button
                onClick={(e) => { e.stopPropagation(); onToggleUnseen(); }}
                className={`p-1.5 rounded-lg border transition-colors ${
                  seen
                    ? "text-[var(--muted-foreground)] hover:bg-blue-500/10 hover:text-blue-600 hover:border-blue-500/30"
                    : "text-blue-600 bg-blue-500/10 border-blue-500/30 hover:bg-blue-500/20"
                }`}
                title={seen ? "Marcar como não lida" : "Marcar como lida"}
              >
                {seen ? <Mail className="h-4 w-4" /> : <MailOpen className="h-4 w-4" />}
              </button>
            )}
            {canExpand && (
              <button
                onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
                className="p-1.5 rounded-lg border text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)] transition-colors"
                title={expanded ? "Recolher" : "Ver detalhes completos"}
              >
                {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ──── Seção expandida com dados completos ──── */}
      {expanded && (
        <div className="mx-4 mb-4 ml-5 rounded-xl border bg-[var(--card)] shadow-sm overflow-hidden">
          {/* Header expandido com resumo */}
          <div className="px-4 py-3 border-b bg-[var(--secondary)]/30 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3 flex-wrap text-xs text-[var(--muted-foreground)]">
              <FonteBadge fonte={pub.fonte} showLabel />
              {pub.tribunal && <span className="font-medium">{pub.tribunal}</span>}
              {dataFormatada && <span>{dataFormatada}</span>}
              {pub.caderno && <span>Caderno {pub.caderno}{pub.pagina ? `, p. ${pub.pagina}` : ""}</span>}
            </div>
            {pub.url_origem && (
              <a
                href={pub.url_origem}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-md border border-legal-600/40 bg-legal-600/5 px-3 py-1 text-xs font-medium text-legal-600 hover:bg-legal-600/15 transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                Ver original
              </a>
            )}
          </div>

          {/* Conteúdo completo */}
          {hasConteudo && (
            <div className="p-4 border-b">
              <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)] mb-3">
                <BookOpen className="h-3.5 w-3.5" />
                Texto Completo da Publicação
              </h4>
              <div className="rounded-lg bg-[var(--secondary)]/40 p-4 max-h-96 overflow-y-auto">
                <p className="text-sm text-[var(--card-foreground)] whitespace-pre-line leading-relaxed">
                  <HighlightText text={pub.conteudo!} query={searchQuery} />
                </p>
              </div>
            </div>
          )}

          {/* Grid 2 colunas: Partes | Advogados */}
          {(hasPartes || hasAdvogados) && (
            <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x">
              {hasPartes && (
                <div className="p-4">
                  <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-blue-600 mb-3">
                    <Users className="h-3.5 w-3.5" />
                    Partes Envolvidas ({pub.partes!.length})
                  </h4>
                  <ul className="space-y-1.5">
                    {pub.partes!.map((p, i) => (
                      <li key={i} className="text-sm text-[var(--card-foreground)] flex items-start gap-2">
                        <span className="mt-2 h-1.5 w-1.5 rounded-full bg-blue-400 shrink-0" />
                        <HighlightText text={p} query={searchQuery} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {hasAdvogados && (
                <div className="p-4">
                  <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-purple-600 mb-3">
                    <Briefcase className="h-3.5 w-3.5" />
                    Advogados ({pub.advogados!.length})
                  </h4>
                  <ul className="space-y-1.5">
                    {pub.advogados!.map((a, i) => (
                      <li key={i} className="text-sm text-[var(--card-foreground)] flex items-start gap-2">
                        <span className="mt-2 h-1.5 w-1.5 rounded-full bg-purple-400 shrink-0" />
                        <HighlightText text={a} query={searchQuery} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* OABs */}
          {hasOABs && (
            <div className="p-4 border-t">
              <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-green-600 mb-3">
                <CreditCard className="h-3.5 w-3.5" />
                OABs Identificadas
              </h4>
              <div className="flex flex-wrap gap-2">
                {pub.oab_encontradas!.map((oab, i) => (
                  <span key={i} className="rounded-full border border-green-500/30 bg-green-500/10 px-3 py-1 text-xs font-bold text-green-700 tracking-wide">
                    <HighlightText text={oab} query={searchQuery} />
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Movimentos */}
          {hasMovimentos && (
            <div className="p-4 border-t">
              <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[var(--muted-foreground)] mb-3">
                <Activity className="h-3.5 w-3.5" />
                Movimentos Processuais ({pub.movimentos!.length})
              </h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {pub.movimentos!.map((m, i) => {
                  const mov = m as Record<string, unknown>;
                  return (
                    <div key={i} className="flex items-start gap-3 rounded-lg bg-[var(--secondary)]/40 px-3 py-2">
                      {!!mov.data_hora && (
                        <span className="shrink-0 rounded bg-[var(--secondary)] px-2 py-0.5 text-xs font-mono text-[var(--muted-foreground)]">
                          {String(mov.data_hora)}
                        </span>
                      )}
                      <span className="text-sm text-[var(--card-foreground)]">
                        {String(mov.descricao || mov.nome || mov.tipo || JSON.stringify(mov))}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Monitor selecionado para filtrar publicações ───────────────────────────
function MonitorRow({
  monitor,
  selected,
  onSelect,
}: {
  monitor: MonitorItem;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <tr
      onClick={onSelect}
      className={`cursor-pointer hover:bg-[var(--secondary)]/50 transition-colors ${selected ? "bg-legal-600/5 ring-1 ring-inset ring-legal-600/20" : ""}`}
    >
      <td className="px-4 py-3">
        <span className="rounded bg-legal-500/10 px-2 py-0.5 text-xs font-medium text-legal-600 uppercase">
          {monitor.tipo}
        </span>
      </td>
      <td className="px-4 py-3">
        <p className="font-medium text-[var(--card-foreground)]">{monitor.valor}</p>
        {monitor.nome_amigavel && (
          <p className="text-xs text-[var(--muted-foreground)] mt-0.5">
            {monitor.nome_amigavel}
          </p>
        )}
      </td>
      <td className="px-4 py-3 text-[var(--muted-foreground)]">
        {monitor.tribunal || "-"}
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
            monitor.ativo
              ? "bg-green-500/10 text-green-600"
              : "bg-[var(--secondary)] text-[var(--muted-foreground)]"
          }`}
        >
          {monitor.ativo ? (
            <CheckCircle2 className="h-3 w-3" />
          ) : (
            <Clock className="h-3 w-3" />
          )}
          {monitor.ativo ? "Ativo" : "Inativo"}
        </span>
      </td>
      <td className="px-4 py-3 text-[var(--muted-foreground)] text-xs">
        {monitor.ultima_busca || "-"}
      </td>
      <td className="px-4 py-3 text-[var(--muted-foreground)]">
        {monitor.total_publicacoes}
      </td>
    </tr>
  );
}

// ─── Página principal ───────────────────────────────────────────────────────
export default function MonitorPage() {
  const [monitors, setMonitors] = useState<MonitorItem[]>([]);
  const [stats, setStats] = useState<MonitorStats>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Publicações — sem limite, carrega todas
  const [publicacoes, setPublicacoes] = useState<PublicacaoItem[]>([]);
  const [showPublicacoes, setShowPublicacoes] = useState(false);
  const [isLoadingPubs, setIsLoadingPubs] = useState(false);
  const [selectedMonitorId, setSelectedMonitorId] = useState<number | null>(null);

  // Filtros e ordenação
  const [pubBusca, setPubBusca] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("date-desc");
  const [filterFonte, setFilterFonte] = useState<string>("todas");
  const [filterTribunal, setFilterTribunal] = useState<string>("todos");

  // === NOVO: Filtro de período (atalhos rápidos) ===
  const [filterPeriod, setFilterPeriod] = useState<PeriodFilter>("todos");

  // === NOVO: Filtro mostrar apenas não lidas ===
  const [showOnlyUnread, setShowOnlyUnread] = useState(false);

  // === Controle de visto/não visto para publicações (localStorage) ===
  const [seenPubs, setSeenPubs] = useState<Set<number>>(() => {
    if (typeof window === "undefined") return new Set();
    try { return new Set(JSON.parse(localStorage.getItem("captacao_seen_pubs") || "[]") as number[]); }
    catch { return new Set(); }
  });
  const markPubSeen = useCallback((id: number) => {
    setSeenPubs(prev => {
      if (prev.has(id)) return prev;
      const next = new Set(prev); next.add(id);
      try { localStorage.setItem("captacao_seen_pubs", JSON.stringify([...next])); } catch {}
      return next;
    });
  }, []);
  const markAllPubsSeen = useCallback(() => {
    setSeenPubs(prev => {
      const ids = publicacoes.map(p => p.id).filter((id): id is number => typeof id === "number");
      const next = new Set([...prev, ...ids]);
      try { localStorage.setItem("captacao_seen_pubs", JSON.stringify([...next])); } catch {}
      return next;
    });
  }, [publicacoes]);

  // === NOVO: Marcar individual como não lido (toggle) ===
  const togglePubSeen = useCallback((id: number) => {
    setSeenPubs(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      try { localStorage.setItem("captacao_seen_pubs", JSON.stringify([...next])); } catch {}
      return next;
    });
  }, []);

  const [showFilters, setShowFilters] = useState(false);
  const [filtroExcluirEF, setFiltroExcluirEF] = useState(false);
  const [filtroSemAdvogado, setFiltroSemAdvogado] = useState(false);

  // Listas únicas de fontes e tribunais para dropdowns
  const fontesDisponiveis = useMemo(() => {
    const set = new Set<string>();
    publicacoes.forEach((p) => { if (p.fonte) set.add(p.fonte); });
    return Array.from(set).sort();
  }, [publicacoes]);

  const tribunaisDisponiveis = useMemo(() => {
    const set = new Set<string>();
    publicacoes.forEach((p) => { if (p.tribunal) set.add(p.tribunal); });
    return Array.from(set).sort();
  }, [publicacoes]);

  // Contagem por fonte
  const contagemPorFonte = useMemo(() => {
    const map: Record<string, number> = {};
    publicacoes.forEach((p) => {
      const key = p.fonte || "sem_fonte";
      map[key] = (map[key] || 0) + 1;
    });
    return map;
  }, [publicacoes]);

  // === NOVO: Contagem de publicações por período (para exibir nos botões de atalho) ===
  const periodCounts = useMemo(() => {
    let countHoje = 0;
    let countOntem = 0;
    let count7dias = 0;
    publicacoes.forEach((p) => {
      if (pubMatchesPeriod(p, "hoje")) countHoje++;
      if (pubMatchesPeriod(p, "ontem")) countOntem++;
      if (pubMatchesPeriod(p, "7dias")) count7dias++;
    });
    return { hoje: countHoje, ontem: countOntem, "7dias": count7dias, todos: publicacoes.length };
  }, [publicacoes]);

  // ── Busca robusta: tokeniza query em termos, publica match se TODOS os termos batem ──
  const pubFiltradas = useMemo(() => {
    // Filtro base: apenas publicações de diários oficiais (DJEN)
    let filtered = publicacoes.filter(p => 
      p.fonte === "djen_api" || p.fonte === "djen"
    );

    // Filtro por monitor selecionado
    if (selectedMonitorId !== null) {
      const mon = monitors.find((m) => m.id === selectedMonitorId);
      if (mon) {
        const mv = mon.valor.toLowerCase().replace(/\D/g, "") || mon.valor.toLowerCase();
        filtered = filtered.filter((p) => {
          const procDigits = (p.numero_processo || "").replace(/\D/g, "");
          return (
            procDigits.includes(mv) ||
            (p.numero_processo || "").toLowerCase().includes(mon.valor.toLowerCase()) ||
            (p.conteudo || "").toLowerCase().includes(mon.valor.toLowerCase()) ||
            (p.partes || []).some((pt) => pt.toLowerCase().includes(mon.valor.toLowerCase())) ||
            (p.advogados || []).some((a) => a.toLowerCase().includes(mon.valor.toLowerCase())) ||
            (p.oab_encontradas || []).some((o) => o.toLowerCase().includes(mon.valor.toLowerCase()))
          );
        });
      }
    }

    // Filtro por fonte
    if (filterFonte !== "todas") {
      filtered = filtered.filter((p) => p.fonte === filterFonte);
    }

    // Filtro por tribunal
    if (filterTribunal !== "todos") {
      filtered = filtered.filter((p) => p.tribunal === filterTribunal);
    }

    // === NOVO: Filtro por período ===
    if (filterPeriod !== "todos") {
      filtered = filtered.filter((p) => pubMatchesPeriod(p, filterPeriod));
    }

    // === NOVO: Filtro mostrar apenas não lidas ===
    if (showOnlyUnread) {
      filtered = filtered.filter((p) => typeof p.id === "number" && !seenPubs.has(p.id));
    }

    // Filtro Inteligência de Lead
    if (filtroExcluirEF) {
      filtered = filtered.filter((p) => !isExecucaoFiscal(p));
    }
    if (filtroSemAdvogado) {
      filtered = filtered.filter((p) => !(p.advogados && p.advogados.length > 0));
    }

    // Busca robusta: multi-token, busca em TODOS os campos disponíveis
    if (pubBusca.trim()) {
      const tokens = pubBusca.toLowerCase().split(/\s+/).filter(Boolean);
      filtered = filtered.filter((p) => {
        // Constrói um "documento" com todos os campos pesquisáveis concatenados
        const searchable = [
          p.numero_processo || "",
          p.numero_processo ? formatProcessoCNJ(p.numero_processo) : "",
          p.conteudo || "",
          p.orgao_julgador || "",
          p.classe_processual || "",
          p.tribunal || "",
          p.fonte || "",
          p.data_publicacao || "",
          formatDateDisplay(p.data_publicacao) || "",
          p.caderno || "",
          p.pagina || "",
          p.url_origem || "",
          ...(p.partes || []),
          ...(p.advogados || []),
          ...(p.oab_encontradas || []),
          ...(p.assuntos || []),
          ...(p.movimentos || []).map((m) => {
            const mov = m as Record<string, unknown>;
            return [String(mov.descricao || ""), String(mov.nome || ""), String(mov.tipo || ""), String(mov.data_hora || "")].join(" ");
          }),
        ].join(" ").toLowerCase();

        // Todos os tokens devem ser encontrados (AND semântico, busca por substring)
        return tokens.every((tok) => searchable.indexOf(tok) !== -1);
      });
    }

    // Ordenação — usa dateToSortKey para normalizar datas DD/MM/YYYY e ISO
    filtered.sort((a, b) => {
      switch (sortBy) {
        case "date-desc":
          return dateToSortKey(b.data_publicacao) - dateToSortKey(a.data_publicacao);
        case "date-asc":
          return dateToSortKey(a.data_publicacao) - dateToSortKey(b.data_publicacao);
        case "tribunal-az":
          return (a.tribunal || "").localeCompare(b.tribunal || "");
        case "tribunal-za":
          return (b.tribunal || "").localeCompare(a.tribunal || "");
        case "fonte-az":
          return (a.fonte || "").localeCompare(b.fonte || "");
        case "score-desc":
          return calcularScoreLead(b).score - calcularScoreLead(a).score;
        case "score-asc":
          return calcularScoreLead(a).score - calcularScoreLead(b).score;
        default:
          return 0;
      }
    });

    return filtered;
  }, [publicacoes, selectedMonitorId, monitors, filterFonte, filterTribunal, pubBusca, sortBy, filtroExcluirEF, filtroSemAdvogado, filterPeriod, showOnlyUnread, seenPubs]);

  const unseenCount = useMemo(
    () => pubFiltradas.filter(p => typeof p.id === "number" && !seenPubs.has(p.id)).length,
    [pubFiltradas, seenPubs]
  );

  // === NOVO: Contagens de lidos/não lidos/total para a barra de resumo ===
  const readUnreadStats = useMemo(() => {
    const total = pubFiltradas.length;
    const unread = pubFiltradas.filter(p => typeof p.id === "number" && !seenPubs.has(p.id)).length;
    const read = total - unread;
    return { total, unread, read };
  }, [pubFiltradas, seenPubs]);

  // Contagem de filtros ativos
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filterFonte !== "todas") count++;
    if (filterTribunal !== "todos") count++;
    if (pubBusca.trim()) count++;
    if (selectedMonitorId !== null) count++;
    if (sortBy !== "date-desc") count++;
    if (filtroExcluirEF) count++;
    if (filtroSemAdvogado) count++;
    if (filterPeriod !== "todos") count++;
    if (showOnlyUnread) count++;
    return count;
  }, [filterFonte, filterTribunal, pubBusca, selectedMonitorId, sortBy, filtroExcluirEF, filtroSemAdvogado, filterPeriod, showOnlyUnread]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [monitorsData, statsData] = await Promise.allSettled([
        api.listMonitors(),
        api.getMonitorStats(),
      ]);
      if (monitorsData.status === "fulfilled") setMonitors(monitorsData.value);
      if (statsData.status === "fulfilled") setStats(statsData.value);
    } catch {
      setError("Erro ao carregar monitores.");
    } finally {
      setIsLoading(false);
    }
  };

  const loadPublicacoes = useCallback(async () => {
    setIsLoadingPubs(true);
    try {
      // Sem limite — carrega TUDO do bank
      const rawPubs = await api.getPublicacoesRecentes({ limite: 1000000 });
      const pubs = rawPubs.map(sanitizePublicacao);
      setPublicacoes(pubs);
      setShowPublicacoes(true);
    } catch {
      setError("Erro ao carregar publicações.");
    } finally {
      setIsLoadingPubs(false);
    }
  }, []);

  const handleTogglePublicacoes = useCallback(() => {
    if (!showPublicacoes) {
      loadPublicacoes();
    } else {
      setShowPublicacoes(false);
    }
  }, [showPublicacoes, loadPublicacoes]);

  const handleSelectMonitor = useCallback((id: number) => {
    if (selectedMonitorId === id) {
      setSelectedMonitorId(null);
    } else {
      setSelectedMonitorId(id);
      if (!showPublicacoes) loadPublicacoes();
    }
  }, [selectedMonitorId, showPublicacoes, loadPublicacoes]);


  const handleDeletePub = useCallback(async (pubId: number) => {
    if (!confirm("Excluir esta publicacao?")) return;
    try {
      await api.deletePublicacao(pubId);
      setPublicacoes((prev) => prev.filter((p) => p.id !== pubId));
      setSuccess("Publicacao excluida.");
      setTimeout(() => setSuccess(""), 3000);
    } catch {
      setError("Erro ao excluir publicacao.");
    }
  }, []);

  const clearAllFilters = useCallback(() => {
    setPubBusca("");
    setFilterFonte("todas");
    setFilterTribunal("todos");
    setSortBy("date-desc");
    setSelectedMonitorId(null);
    setFiltroExcluirEF(false);
    setFiltroSemAdvogado(false);
    setFilterPeriod("todos");
    setShowOnlyUnread(false);
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner size="lg" text="Carregando monitores..." />
      </div>
    );
  }

  const selectedMonitor = monitors.find((m) => m.id === selectedMonitorId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">Monitor DJEN</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Publicações de diários oficiais dos seus monitoramentos
          </p>
        </div>
        <a
          href="/captacao"
          className="flex items-center gap-2 rounded-lg border border-legal-600 px-4 py-2 text-sm font-medium text-legal-600 hover:bg-legal-600/10 transition-colors"
        >
          <Zap className="h-4 w-4" />
          Gerenciar Captações
        </a>
      </div>

      {/* Info Banner */}
      <div className="bg-amber-50/50 border border-amber-200 border-l-4 border-l-amber-500 p-4 mb-2 rounded-md shadow-sm">
        <div className="flex">
          <div className="flex-shrink-0">
            <Newspaper className="h-5 w-5 text-amber-500 mt-0.5" />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-semibold text-amber-800">Feed de Publicações dos Diários Oficiais</h3>
            <p className="mt-1 text-sm text-amber-700 leading-relaxed">
              Esta aba exibe as publicações coletadas dos Diários Oficiais (DJEN) para os termos monitorados.
              Para adicionar ou gerenciar captações automáticas, use a aba{" "}
              <a href="/captacao" className="font-semibold underline hover:text-amber-900">Captação</a>.
            </p>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatsCard
          title="Total de Monitores"
          value={stats.total_monitorados ?? monitors.length}
          icon={Eye}
        />
        <StatsCard
          title="Monitores Ativos"
          value={stats.monitorados_ativos ?? 0}
          icon={Activity}
        />
        <div
          onClick={handleTogglePublicacoes}
          className="cursor-pointer hover:ring-2 hover:ring-legal-600/30 rounded-lg transition-all"
        >
          <StatsCard
            title="Publicações Encontradas"
            value={stats.total_publicacoes ?? 0}
            icon={Newspaper}
          />
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 rounded-lg border border-green-500/30 bg-green-500/10 p-3 text-sm text-green-600">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Monitors list */}
      <div className="rounded-lg border bg-[var(--card)] shadow-sm">
        <div className="border-b p-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[var(--card-foreground)]">
            Monitores Cadastrados
          </h2>
          {selectedMonitorId !== null && (
            <div className="flex items-center gap-2 rounded-full bg-legal-600/10 px-3 py-1 text-xs font-medium text-legal-600">
              <span>Filtrando: {selectedMonitor?.nome_amigavel || selectedMonitor?.valor}</span>
              <button onClick={() => setSelectedMonitorId(null)}>
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>
        {monitors.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-[var(--secondary)]">
                  <th className="px-4 py-3 text-left font-medium text-[var(--muted-foreground)]">Tipo</th>
                  <th className="px-4 py-3 text-left font-medium text-[var(--muted-foreground)]">Valor / Nome</th>
                  <th className="px-4 py-3 text-left font-medium text-[var(--muted-foreground)]">Tribunal</th>
                  <th className="px-4 py-3 text-left font-medium text-[var(--muted-foreground)]">Status</th>
                  <th className="px-4 py-3 text-left font-medium text-[var(--muted-foreground)]">Última Busca</th>
                  <th className="px-4 py-3 text-left font-medium text-[var(--muted-foreground)]">Publicações</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {monitors.map((monitor, idx) => (
                  <MonitorRow
                    key={monitor.id ?? idx}
                    monitor={monitor}
                    selected={selectedMonitorId === monitor.id}
                    onSelect={() => handleSelectMonitor(monitor.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-[var(--muted-foreground)]">
            <Eye className="mx-auto h-12 w-12 mb-4 opacity-30" />
            <p>Nenhum monitor cadastrado ainda.</p>
            <p className="text-xs mt-1">Clique em &quot;Novo Monitor&quot; para começar.</p>
          </div>
        )}
        {monitors.length > 0 && (
          <div className="border-t px-4 py-2 text-xs text-[var(--muted-foreground)]">
            Clique em uma linha para filtrar as publicações por esse monitor
          </div>
        )}
      </div>

      {/* ══════════════════ Publicações Encontradas ══════════════════ */}
      <div className="rounded-lg border bg-[var(--card)] shadow-sm">
        {/* Header da seção */}
        <div
          className="border-b p-4 flex items-center justify-between cursor-pointer hover:bg-[var(--secondary)]/50 transition-colors"
          onClick={handleTogglePublicacoes}
        >
          <div className="flex items-center gap-2">
            <Newspaper className="h-5 w-5 text-legal-600" />
            <h2 className="text-lg font-semibold text-[var(--card-foreground)]">
              Publicações Encontradas
            </h2>
            <span className="rounded-full bg-legal-500/10 px-2.5 py-0.5 text-xs font-medium text-legal-600">
              {showPublicacoes ? pubFiltradas.length : stats.total_publicacoes ?? 0}
            </span>
            {/* Badges de contagem por fonte */}
            {showPublicacoes && Object.entries(contagemPorFonte).map(([fonte, count]) => (
              <FonteBadge key={fonte} fonte={`${fonte} (${count})`} />
            ))}
            {selectedMonitor && (
              <span className="rounded-full bg-legal-600/10 px-2.5 py-0.5 text-xs font-medium text-legal-600">
                {selectedMonitor.nome_amigavel || selectedMonitor.valor}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {showPublicacoes && (
              <button
                onClick={(e) => { e.stopPropagation(); loadPublicacoes(); }}
                className="p-1.5 rounded-lg border text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)] transition-colors"
                title="Recarregar publicacoes"
              >
                <RefreshCw className={`h-4 w-4 ${isLoadingPubs ? "animate-spin" : ""}`} />
              </button>
            )}
            {showPublicacoes && unseenCount > 0 && (
              <button
                onClick={(e) => { e.stopPropagation(); markAllPubsSeen(); }}
                className="p-1.5 rounded-lg border text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)] transition-colors text-xs px-2"
                title="Marcar todas publicações como vistas"
              >
                Marcar todas vistas
              </button>
            )}
            {showPublicacoes ? (
              <ChevronUp className="h-5 w-5 text-[var(--muted-foreground)]" />
            ) : (
              <ChevronDown className="h-5 w-5 text-[var(--muted-foreground)]" />
            )}
          </div>
        </div>

        {isLoadingPubs && (
          <div className="p-8">
            <LoadingSpinner size="lg" text="Carregando publicações..." />
          </div>
        )}

        {showPublicacoes && !isLoadingPubs && (
          <>
            {/* ── NOVO: Barra de resumo lidos/não lidos ── */}
            <div className="px-4 py-3 border-b bg-[var(--secondary)]/20">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                {/* Contadores */}
                <div className="flex items-center gap-3 flex-wrap">
                  <div className="flex items-center gap-1.5 text-sm">
                    <Mail className="h-4 w-4 text-blue-500" />
                    <span className="font-bold text-blue-600">{readUnreadStats.unread}</span>
                    <span className="text-[var(--muted-foreground)]">não lida{readUnreadStats.unread !== 1 ? "s" : ""}</span>
                  </div>
                  <span className="text-[var(--muted-foreground)]">|</span>
                  <div className="flex items-center gap-1.5 text-sm">
                    <MailOpen className="h-4 w-4 text-green-500" />
                    <span className="font-bold text-green-600">{readUnreadStats.read}</span>
                    <span className="text-[var(--muted-foreground)]">lida{readUnreadStats.read !== 1 ? "s" : ""}</span>
                  </div>
                  <span className="text-[var(--muted-foreground)]">|</span>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Newspaper className="h-4 w-4 text-[var(--muted-foreground)]" />
                    <span className="font-bold text-[var(--card-foreground)]">{readUnreadStats.total}</span>
                    <span className="text-[var(--muted-foreground)]">total</span>
                  </div>
                </div>

                {/* Ações */}
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Botão marcar todas como lidas */}
                  {readUnreadStats.unread > 0 && (
                    <button
                      onClick={markAllPubsSeen}
                      className="flex items-center gap-1.5 rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-500/20 transition-colors"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Marcar todas como lidas
                    </button>
                  )}
                  {/* Toggle mostrar apenas não lidas */}
                  <button
                    onClick={() => setShowOnlyUnread(!showOnlyUnread)}
                    className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                      showOnlyUnread
                        ? "border-blue-500/40 bg-blue-500/15 text-blue-700"
                        : "border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"
                    }`}
                  >
                    {showOnlyUnread ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    {showOnlyUnread ? "Mostrando apenas não lidas" : "Mostrar apenas não lidas"}
                  </button>
                </div>
              </div>
            </div>

            {/* ── NOVO: Atalhos de período ── */}
            <div className="px-4 py-2.5 border-b bg-[var(--secondary)]/10">
              <div className="flex items-center gap-2 flex-wrap">
                <Calendar className="h-4 w-4 text-[var(--muted-foreground)] shrink-0" />
                <span className="text-xs font-medium text-[var(--muted-foreground)] mr-1">Período:</span>
                {([
                  { value: "todos" as PeriodFilter, label: "Todos" },
                  { value: "hoje" as PeriodFilter, label: "Hoje" },
                  { value: "ontem" as PeriodFilter, label: "Ontem" },
                  { value: "7dias" as PeriodFilter, label: "Últimos 7 dias" },
                ]).map((period) => {
                  const count = periodCounts[period.value];
                  const isActive = filterPeriod === period.value;
                  return (
                    <button
                      key={period.value}
                      onClick={() => setFilterPeriod(period.value)}
                      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                        isActive
                          ? "bg-legal-600 text-white shadow-sm"
                          : "bg-[var(--secondary)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/80 hover:text-[var(--card-foreground)]"
                      }`}
                    >
                      {period.label}
                      <span className={`rounded-full px-1.5 py-0 text-[10px] font-bold ${
                        isActive ? "bg-white/20 text-white" : "bg-[var(--background)] text-[var(--card-foreground)]"
                      }`}>
                        {count}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ── Toolbar: busca + filtros + ordenação ── */}
            <div className="p-4 border-b space-y-3">
              {/* Linha 1: Busca + botão filtros + ordenação */}
              <div className="flex flex-col sm:flex-row gap-3">
                {/* Campo de busca */}
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
                  <input
                    type="text"
                    value={pubBusca}
                    onChange={(e) => setPubBusca(e.target.value)}
                    placeholder="Busca completa: processo, parte, advogado, OAB, conteúdo, tribunal, classe, assuntos..."
                    className="w-full rounded-lg border bg-[var(--background)] py-2 pl-10 pr-10 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20"
                  />
                  {pubBusca && (
                    <button
                      onClick={() => setPubBusca("")}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>

                {/* Botão filtros avançados */}
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
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

                {/* Seletor de ordenação */}
                <div className="flex items-center gap-2">
                  <ArrowUpDown className="h-4 w-4 text-[var(--muted-foreground)] shrink-0" />
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as SortOption)}
                    className="rounded-lg border bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20"
                  >
                    {SORT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Linha 2: Filtros avançados (colapsável) */}
              {showFilters && (
                <>
                <div className="flex flex-col sm:flex-row gap-3 rounded-lg border bg-[var(--secondary)]/30 p-3">
                  {/* Filtro por fonte */}
                  <div className="flex-1">
                    <label className="block text-xs font-medium text-[var(--muted-foreground)] mb-1.5">
                      <Filter className="inline h-3 w-3 mr-1" />
                      Fonte
                    </label>
                    <select
                      value={filterFonte}
                      onChange={(e) => setFilterFonte(e.target.value)}
                      className="w-full rounded-lg border bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none"
                    >
                      <option value="todas">Todas as fontes</option>
                      {fontesDisponiveis.map((f) => (
                        <option key={f} value={f}>
                          {f} ({contagemPorFonte[f] || 0})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Filtro por tribunal */}
                  <div className="flex-1">
                    <label className="block text-xs font-medium text-[var(--muted-foreground)] mb-1.5">
                      <Building2 className="inline h-3 w-3 mr-1" />
                      Tribunal
                    </label>
                    <select
                      value={filterTribunal}
                      onChange={(e) => setFilterTribunal(e.target.value)}
                      className="w-full rounded-lg border bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none"
                    >
                      <option value="todos">Todos os tribunais</option>
                      {tribunaisDisponiveis.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>

                  {/* Botão limpar filtros */}
                  {activeFilterCount > 0 && (
                    <div className="flex items-end">
                      <button
                        onClick={clearAllFilters}
                        className="flex items-center gap-1.5 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-500/10 transition-colors"
                      >
                        <X className="h-3.5 w-3.5" />
                        Limpar tudo
                      </button>
                    </div>
                  )}
                </div>

                {/* Inteligência de Lead */}
                <div className="border-t pt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)] mb-2 flex items-center gap-1.5">
                    <TrendingUp className="h-3.5 w-3.5 text-legal-600" />
                    Inteligência de Lead
                  </p>
                  <div className="flex flex-wrap gap-5">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={filtroExcluirEF}
                        onChange={(e) => setFiltroExcluirEF(e.target.checked)}
                        className="h-4 w-4 rounded border-gray-300 text-legal-600 focus:ring-legal-600/40"
                      />
                      <span className="text-sm text-[var(--card-foreground)]">Excluir Execuções Fiscais</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={filtroSemAdvogado}
                        onChange={(e) => setFiltroSemAdvogado(e.target.checked)}
                        className="h-4 w-4 rounded border-gray-300 text-legal-600 focus:ring-legal-600/40"
                      />
                      <span className="text-sm text-[var(--card-foreground)]">Apenas sem advogado</span>
                    </label>
                  </div>
                </div>
                </>
              )}

              {/* Barra de status: contagem + filtros ativos */}
              <div className="flex items-center justify-between">
                <p className="text-xs text-[var(--muted-foreground)]">
                  Exibindo <span className="font-semibold text-[var(--card-foreground)]">{pubFiltradas.length}</span> de {publicacoes.length} publicações (todas as fontes)
                  {selectedMonitor && (
                    <> · filtradas por: <span className="font-medium text-legal-600">{selectedMonitor.nome_amigavel || selectedMonitor.valor}</span></>
                  )}
                </p>
                {/* Tags dos filtros ativos */}
                {activeFilterCount > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {filterFonte !== "todas" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2 py-0.5 text-xs text-blue-700">
                        Fonte: {filterFonte}
                        <button onClick={() => setFilterFonte("todas")}><X className="h-3 w-3" /></button>
                      </span>
                    )}
                    {filterTribunal !== "todos" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-700">
                        Tribunal: {filterTribunal}
                        <button onClick={() => setFilterTribunal("todos")}><X className="h-3 w-3" /></button>
                      </span>
                    )}
                    {filterPeriod !== "todos" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-500/10 px-2 py-0.5 text-xs text-green-700">
                        Período: {filterPeriod === "hoje" ? "Hoje" : filterPeriod === "ontem" ? "Ontem" : "Últimos 7 dias"}
                        <button onClick={() => setFilterPeriod("todos")}><X className="h-3 w-3" /></button>
                      </span>
                    )}
                    {showOnlyUnread && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2 py-0.5 text-xs text-blue-700">
                        Apenas não lidas
                        <button onClick={() => setShowOnlyUnread(false)}><X className="h-3 w-3" /></button>
                      </span>
                    )}
                    {sortBy !== "date-desc" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/10 px-2 py-0.5 text-xs text-purple-700">
                        Ordem: {SORT_OPTIONS.find((o) => o.value === sortBy)?.label}
                        <button onClick={() => setSortBy("date-desc")}><X className="h-3 w-3" /></button>
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* ── Lista de publicações ── */}
            {pubFiltradas.length > 0 ? (
              <div>
                {pubFiltradas.map((pub, idx) => (
                  <PubCard
                    key={pub.id ?? idx}
                    pub={pub}
                    idx={idx}
                    searchQuery={pubBusca}
                    onDelete={handleDeletePub}
                    seen={typeof pub.id === "number" ? seenPubs.has(pub.id) : true}
                    onSeen={() => { if (typeof pub.id === "number") markPubSeen(pub.id); }}
                    onToggleUnseen={() => { if (typeof pub.id === "number") togglePubSeen(pub.id); }}
                  />
                ))}

                {/* Rodapé total */}
                <div className="p-3 border-t text-center text-xs text-[var(--muted-foreground)]">
                  Total carregado: <span className="font-semibold text-[var(--card-foreground)]">{publicacoes.length}</span> publicações de todas as fontes
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-[var(--muted-foreground)]">
                <Newspaper className="mx-auto h-12 w-12 mb-4 opacity-30" />
                <p>
                  {pubBusca || selectedMonitorId !== null || filterFonte !== "todas" || filterTribunal !== "todos" || filterPeriod !== "todos" || showOnlyUnread
                    ? "Nenhuma publicação encontrada com os filtros aplicados."
                    : "Nenhuma publicação encontrada no banco de dados."}
                </p>
                {activeFilterCount > 0 && (
                  <button
                    onClick={clearAllFilters}
                    className="mt-3 inline-flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm font-medium text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors"
                  >
                    <X className="h-3.5 w-3.5" />
                    Limpar filtros e tentar novamente
                  </button>
                )}
                {activeFilterCount === 0 && (
                  <p className="text-xs mt-1">
                    As publicações aparecem aqui após buscas ou quando o monitor automático encontrar resultados.
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
