"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import {
  Search,
  AlertCircle,
  FileText,
  Calendar,
  Building2,
  Filter,
  Scale,
  Gavel,
  Tag,
  Users,
  Briefcase,
  CreditCard,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  X,
  Zap,
} from "lucide-react";

interface PublicacaoResult {
  id?: number;
  hash?: string;
  fonte?: string;
  tribunal?: string;
  data_publicacao?: string;
  conteudo?: string;
  numero_processo?: string;
  classe_processual?: string;
  orgao_julgador?: string;
  assuntos?: string[];
  movimentos?: Record<string, unknown>[];
  url_origem?: string;
  caderno?: string;
  pagina?: string;
  oab_encontradas?: string[];
  advogados?: string[];
  partes?: string[];
  [key: string]: unknown;
}

interface BuscaResponse {
  status?: string;
  fonte?: string;
  total?: number;
  tempo_ms?: number;
  resultados?: PublicacaoResult[];
}

interface BuscaUnificadaResponse {
  total_geral?: number;
  tempo_total_ms?: number;
  resultados_por_fonte?: Record<string, BuscaResponse>;
}

interface ResultComFonte extends PublicacaoResult {
  _fonte_label?: string;
  score?: number;
}

/** Formata data para exibição — suporta DD/MM/YYYY, YYYYMMDDHHmmss, YYYYMMDD, ISO */
function formatDateDisplay(raw?: string): string {
  if (!raw) return "";
  const s = raw.trim();
  // DD/MM/YYYY
  const brMatch = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (brMatch) return s;
  // YYYYMMDDHHmmss (14 dígitos)
  const djMatch = s.match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/);
  if (djMatch) return `${djMatch[3]}/${djMatch[2]}/${djMatch[1]}`;
  // YYYYMMDD (8 dígitos)
  const shortMatch = s.match(/^(\d{4})(\d{2})(\d{2})$/);
  if (shortMatch) return `${shortMatch[3]}/${shortMatch[2]}/${shortMatch[1]}`;
  // ISO
  const d = new Date(s);
  if (!isNaN(d.getTime())) {
    return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
  }
  return s;
}

/** Formata processo no padrão CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO */
function formatProcessoCNJ(raw?: string): string {
  if (!raw) return "";
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 20) {
    return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits.slice(13, 14)}.${digits.slice(14, 16)}.${digits.slice(16, 20)}`;
  }
  return raw;
}


/** Calcula Score de Lead (0 a 100) */
function calcularScore(item: ResultComFonte): number {
  let score = 50;
  const hasAdv = item.advogados && item.advogados.length > 0;
  const hasOab = item.oab_encontradas && item.oab_encontradas.length > 0;
  if (hasAdv || hasOab) score -= 30;
  else score += 30;

  const textStr = `${item.classe_processual || ""} ${item.assuntos?.join(" ") || ""} ${item.conteudo || ""}`.toLowerCase();
  if (textStr.includes("execução fiscal") || textStr.includes("execucao fiscal")) score -= 50;

  return Math.max(0, Math.min(100, score));
}

// Cartão expandível individual
function ResultCard({ item, idx }: { item: ResultComFonte; idx: number }) {
  const [expanded, setExpanded] = useState(false);

  const hasStructured = !!(item.classe_processual || item.orgao_julgador);
  const hasPartes = item.partes && item.partes.length > 0;
  const hasAdvogados = item.advogados && item.advogados.length > 0;
  const hasOABs = item.oab_encontradas && item.oab_encontradas.length > 0;
  const hasMovimentos = item.movimentos && item.movimentos.length > 0;
  const hasConteudo = !!item.conteudo;

  const canExpand =
    hasConteudo ||
    hasPartes ||
    hasAdvogados ||
    hasOABs ||
    hasMovimentos ||
    item.url_origem;

  return (
    <div className="rounded-lg border bg-[var(--card)] shadow-sm transition-shadow hover:shadow-md">
      {/* CabeÃ§alho do card */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="h-4 w-4 text-legal-600 shrink-0" />
              <h3 className="font-semibold text-[var(--card-foreground)] truncate">
                {formatProcessoCNJ(item.numero_processo) || `Resultado ${idx + 1}`}
              </h3>
              {item.score !== undefined && (
                <span title="Score de Lead (0-100)" className={`ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${
                   item.score >= 70 ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" :
                   item.score >= 40 ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400" :
                   item.score >= 20 ? "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400" :
                   "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                }`}>
                   Score: {item.score}
                </span>
              )}
            </div>

            {item.classe_processual && (
              <div className="flex items-center gap-1.5 mt-1.5 text-sm text-[var(--card-foreground)]">
                <Gavel className="h-3.5 w-3.5 text-legal-500 shrink-0" />
                <span className="font-medium">{item.classe_processual}</span>
              </div>
            )}

            {item.orgao_julgador && (
              <div className="flex items-center gap-1.5 mt-1 text-sm text-[var(--muted-foreground)]">
                <Scale className="h-3.5 w-3.5 shrink-0" />
                <span>{item.orgao_julgador}</span>
              </div>
            )}

            {item.assuntos && item.assuntos.length > 0 && (
              <div className="flex items-start gap-1.5 mt-1 text-sm text-[var(--muted-foreground)]">
                <Tag className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                <span className="line-clamp-2">{item.assuntos.join("; ")}</span>
              </div>
            )}

            {/* ConteÃºdo resumido (sempre visÃ­vel, 3 linhas) */}
            {hasConteudo && (
              <p
                className={`text-sm text-[var(--muted-foreground)] mt-2 ${
                  expanded ? "" : "line-clamp-3"
                }`}
              >
                {item.conteudo}
              </p>
            )}

            {/* Partes - visÃ­veis resumidas mesmo sem expandir */}
            {hasPartes && !expanded && (
              <div className="flex items-center gap-1.5 mt-2 text-sm text-[var(--muted-foreground)]">
                <Users className="h-3.5 w-3.5 shrink-0 text-blue-500" />
                <span className="line-clamp-1">
                  <span className="font-medium text-[var(--card-foreground)]">Partes: </span>
                  {item.partes!.slice(0, 3).join(" Â· ")}
                  {item.partes!.length > 3 && ` +${item.partes!.length - 3}`}
                </span>
              </div>
            )}

            {/* Advogados - visÃ­veis resumidos */}
            {hasAdvogados && !expanded && (
              <div className="flex items-center gap-1.5 mt-1 text-sm text-[var(--muted-foreground)]">
                <Briefcase className="h-3.5 w-3.5 shrink-0 text-purple-500" />
                <span className="line-clamp-1">
                  <span className="font-medium text-[var(--card-foreground)]">Advogados: </span>
                  {item.advogados!.slice(0, 2).join(" Â· ")}
                  {item.advogados!.length > 2 && ` +${item.advogados!.length - 2}`}
                </span>
              </div>
            )}

            {/* OABs encontradas */}
            {hasOABs && !expanded && (
              <div className="flex items-center gap-1.5 mt-1 text-sm text-[var(--muted-foreground)]">
                <CreditCard className="h-3.5 w-3.5 shrink-0 text-green-500" />
                <span className="font-medium text-[var(--card-foreground)]">OABs: </span>
                <span>{item.oab_encontradas!.join(", ")}</span>
              </div>
            )}

            {/* Metadata row */}
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-[var(--muted-foreground)]">
              {item.tribunal && (
                <span className="flex items-center gap-1">
                  <Building2 className="h-3 w-3" />
                  {item.tribunal}
                </span>
              )}
              {item.data_publicacao && item.data_publicacao !== "Data indisponivel" && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {formatDateDisplay(item.data_publicacao)}
                </span>
              )}
              {(item._fonte_label || item.fonte) && (
                <span 
                  title={item._fonte_label?.includes("DataJud") ? "Fonte Oficial do Conselho Nacional de Justiça" : "Diário da Justiça Eletrônico Nacional"}
                  className="rounded bg-gold-500/10 px-2 py-0.5 text-xs font-medium text-gold-600 cursor-help border border-gold-500/20"
                >
                  {item._fonte_label || item.fonte}
                </span>
              )}
              {item.caderno && (
                <span className="text-[var(--muted-foreground)]">
                  Caderno: {item.caderno}
                </span>
              )}
              {item.pagina && (
                <span className="text-[var(--muted-foreground)]">
                  PÃ¡g. {item.pagina}
                </span>
              )}
            </div>
          </div>

          {/* BotÃ£o expandir */}
          {canExpand && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="shrink-0 p-1.5 rounded-lg border text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)] transition-colors"
              title={expanded ? "Recolher" : "Ver detalhes completos"}
            >
              {expanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* SeÃ§Ã£o expandida */}
      {expanded && (
        <div className="border-t px-5 pb-5 pt-4 space-y-4 bg-[var(--secondary)]/30">
          {/* ConteÃºdo completo */}
          {hasConteudo && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)] mb-2">
                Texto Completo da PublicaÃ§Ã£o
              </h4>
              <p className="text-sm text-[var(--card-foreground)] whitespace-pre-line leading-relaxed">
                {item.conteudo}
              </p>
            </div>
          )}

          {/* Partes completas */}
          {hasPartes && (
            <div>
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)] mb-2">
                <Users className="h-3.5 w-3.5 text-blue-500" />
                Partes Envolvidas ({item.partes!.length})
              </h4>
              <ul className="space-y-1">
                {item.partes!.map((p, i) => (
                  <li key={i} className="text-sm text-[var(--card-foreground)] flex items-start gap-2">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-blue-400 shrink-0" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Advogados completos */}
          {hasAdvogados && (
            <div>
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)] mb-2">
                <Briefcase className="h-3.5 w-3.5 text-purple-500" />
                Advogados ({item.advogados!.length})
              </h4>
              <ul className="space-y-1">
                {item.advogados!.map((a, i) => (
                  <li key={i} className="text-sm text-[var(--card-foreground)] flex items-start gap-2">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-purple-400 shrink-0" />
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* OABs encontradas */}
          {hasOABs && (
            <div>
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)] mb-2">
                <CreditCard className="h-3.5 w-3.5 text-green-500" />
                OABs Identificadas
              </h4>
              <div className="flex flex-wrap gap-2">
                {item.oab_encontradas!.map((oab, i) => (
                  <span
                    key={i}
                    className="rounded-full bg-green-500/10 px-3 py-0.5 text-xs font-medium text-green-700"
                  >
                    {oab}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Movimentos processuais */}
          {hasMovimentos && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)] mb-2">
                Movimentos Processuais ({item.movimentos!.length})
              </h4>
              <ul className="space-y-2">
                {item.movimentos!.map((m, i) => {
                  const mov = m as Record<string, unknown>;
                  return (
                    <li
                      key={i}
                      className="rounded border bg-[var(--card)] px-3 py-2 text-sm"
                    >
                      {!!mov.data_hora && (
                        <span className="text-xs text-[var(--muted-foreground)] block mb-0.5">
                          {String(mov.data_hora)}
                        </span>
                      )}
                      <span className="text-[var(--card-foreground)]">
                        {String(
                          mov.descricao ||
                            mov.nome ||
                            mov.tipo ||
                            JSON.stringify(mov)
                        )}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {/* Link de origem */}
          {item.url_origem && (
            <div>
              <a
                href={item.url_origem}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg border border-legal-600/40 px-3 py-1.5 text-sm font-medium text-legal-600 hover:bg-legal-600/10 transition-colors"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Ver publicaÃ§Ã£o original
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function BuscaPage() {
  const [termo, setTermo] = useState("");
  const [tribunal, setTribunal] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  // Filtros avanÃ§ados DJEN
  const [numeroOab, setNumeroOab] = useState("");
  const [ufOab, setUfOab] = useState("");
  const [nomeAdvogado, setNomeAdvogado] = useState("");
  const [nomeParte, setNomeParte] = useState("");

  const [fonte, setFonte] = useState<"unificada" | "datajud" | "djen">("unificada");
  const [results, setResults] = useState<ResultComFonte[]>([]);
  const [contagemPorFonte, setContagemPorFonte] = useState<Record<string, number>>({});
  const [tempoMs, setTempoMs] = useState<number | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [excluirFiscais, setExcluirFiscais] = useState(false);
  const [apenasSemAdvogado, setApenasSemAdvogado] = useState(false);
  const [ordenarPorScore, setOrdenarPorScore] = useState(false);

  const clearAvancados = () => {
    setNumeroOab("");
    setUfOab("");
    setNomeAdvogado("");
    setNomeParte("");
    setExcluirFiscais(false);
    setApenasSemAdvogado(false);
    setOrdenarPorScore(false);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!termo.trim() && !numeroOab && !nomeAdvogado && !nomeParte) return;

    setError("");
    setIsSearching(true);
    setHasSearched(true);
    setContagemPorFonte({});
    setTempoMs(null);

    try {
      const params = {
        termo: termo.trim(),
        tribunal: tribunal || undefined,
        data_inicio: dataInicio || undefined,
        data_fim: dataFim || undefined,
        numero_oab: numeroOab || undefined,
        uf_oab: ufOab || undefined,
        nome_advogado: nomeAdvogado || undefined,
        nome_parte: nomeParte || undefined,
      };

      let items: ResultComFonte[] = [];

      // Sempre buscar no banco local em paralelo
      const localPromise: Promise<PublicacaoResult[]> = termo.trim()
        ? api.buscarLocal({
            termo: termo.trim(),
            fonte: fonte === "unificada" ? undefined : (fonte === "djen" ? "djen_api" : "datajud"),
            tribunal: tribunal || undefined,
            limite: 500,
          }).then((items) => items as unknown as PublicacaoResult[]).catch(() => [])
        : Promise.resolve([]);

      switch (fonte) {
        case "datajud": {
          const [data, localItems] = await Promise.all([
            api.buscarDataJud(params) as Promise<BuscaResponse>,
            localPromise,
          ]);
          const apiItems = (data.resultados || []).map((r: PublicacaoResult) => ({ ...r, _fonte_label: "DataJud" }));
          const localMapped = localItems.map((r: PublicacaoResult) => ({ ...r, _fonte_label: r.fonte === "djen_api" ? "DJEN (local)" : "DataJud (local)" }));
          // Merge: API + local, deduplica por hash
          const seen = new Set(apiItems.map((i: PublicacaoResult) => i.hash).filter(Boolean));
          const uniqueLocal = localMapped.filter((i: PublicacaoResult) => !i.hash || !seen.has(i.hash));
          items = [...apiItems, ...uniqueLocal];
          setContagemPorFonte({
            datajud: apiItems.length,
            ...(uniqueLocal.length > 0 ? { "banco_local": uniqueLocal.length } : {}),
          });
          if (data.tempo_ms) setTempoMs(data.tempo_ms);
          break;
        }
        case "djen": {
          const [data, localItems] = await Promise.all([
            api.buscarDJEN(params).catch(() => ({ resultados: [], total: 0 } as BuscaResponse)),
            localPromise,
          ]);
          const apiItems = (data.resultados || []).map((r: PublicacaoResult) => ({ ...r, _fonte_label: "DJEN" }));
          const localMapped = localItems.map((r: PublicacaoResult) => ({ ...r, _fonte_label: "DJEN (local)" }));
          const seen = new Set(apiItems.map((i: PublicacaoResult) => i.hash).filter(Boolean));
          const uniqueLocal = localMapped.filter((i: PublicacaoResult) => !i.hash || !seen.has(i.hash));
          items = [...apiItems, ...uniqueLocal];
          setContagemPorFonte({
            djen: apiItems.length,
            ...(uniqueLocal.length > 0 ? { "banco_local": uniqueLocal.length } : {}),
          });
          if (data.tempo_ms) setTempoMs(data.tempo_ms);
          break;
        }
        default: {
          const [data, localItems] = await Promise.all([
            api.buscaUnificada(params).catch(() => ({ resultados_por_fonte: {} } as BuscaUnificadaResponse)),
            localPromise,
          ]);
          const contagem: Record<string, number> = {};
          const apiItems = (Object.entries(data.resultados_por_fonte || {}) as [string, BuscaResponse][]).flatMap(
            ([fonteKey, f]) => {
              contagem[fonteKey] = f.total ?? (f.resultados?.length ?? 0);
              return (f.resultados || []).map((r: PublicacaoResult) => ({
                ...r,
                _fonte_label: fonteKey,
              }));
            }
          );
          const localMapped = localItems.map((r: PublicacaoResult) => ({ ...r, _fonte_label: r.fonte === "djen_api" ? "DJEN (local)" : "DataJud (local)" }));
          const seen = new Set(apiItems.map((i: ResultComFonte) => i.hash).filter(Boolean));
          const uniqueLocal = localMapped.filter((i: PublicacaoResult) => !i.hash || !seen.has(i.hash));
          items = [...apiItems, ...uniqueLocal];
          if (uniqueLocal.length > 0) contagem["banco_local"] = uniqueLocal.length;
          setContagemPorFonte(contagem);
          if (data.tempo_total_ms) setTempoMs(data.tempo_total_ms);
        }
      }

      // Aplica lógica de IA / Fusão Processos
      items.forEach(i => i.score = calcularScore(i));
      
      if (excluirFiscais) {
        items = items.filter(i => {
           const textStr = `${i.classe_processual || ""} ${i.assuntos?.join(" ") || ""} ${i.conteudo || ""}`.toLowerCase();
           return !textStr.includes("execução fiscal") && !textStr.includes("execucao fiscal");
        });
      }
      
      if (apenasSemAdvogado) {
        items = items.filter(i => !(i.advogados && i.advogados.length > 0) && !(i.oab_encontradas && i.oab_encontradas.length > 0));
      }
      
      if (ordenarPorScore) {
        items.sort((a, b) => (b.score || 0) - (a.score || 0));
      }

      setResults(items);
    } catch (err: unknown) {
      let message = "Erro na busca. Tente novamente.";
      if (err && typeof err === "object" && "response" in err) {
        const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
        if (typeof detail === "string") {
          message = detail;
        } else if (Array.isArray(detail)) {
          message = detail.map((d: { msg?: string }) => d.msg || "").filter(Boolean).join("; ") || message;
        }
      }
      setError(message);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const hasAvancados = numeroOab || ufOab || nomeAdvogado || nomeParte || excluirFiscais || apenasSemAdvogado || ordenarPorScore;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">
          Pesquisa
        </h1>
        <p className="text-sm text-[var(--muted-foreground)] mb-6">
          Pesquise em DataJud, DJEN e outras fontes
        </p>

        {/* Info Banner */}
        <div className="bg-purple-50/50 border border-purple-200 border-l-4 border-l-purple-500 p-4 mb-6 rounded-md shadow-sm">
          <div className="flex">
            <div className="flex-shrink-0">
              <Zap className="h-5 w-5 text-purple-500 mt-0.5" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-semibold text-purple-800">Busca Unificada e Captação de Leads</h3>
              <p className="mt-1 text-sm text-purple-700 leading-relaxed font-normal">
                A <strong>Busca Unificada</strong> realiza varreduras em tempo real no DataJud e DJEN para encontrar novos leads ou processos específicos. Utilize os filtros inteligentes para identificar paradas e oportunidades com alto Score de Lead.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Search form */}
      <div className="rounded-lg border bg-[var(--card)] p-6 shadow-sm">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[var(--muted-foreground)]" />
            <input
              type="text"
              value={termo}
              onChange={(e) => setTermo(e.target.value)}
              placeholder="NÃºmero do processo, nome da parte, palavras-chave..."
              className="w-full rounded-xl border bg-[var(--background)] py-3 pl-12 pr-4 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20"
            />
          </div>

          {/* Source + filtros toggle */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex gap-1 rounded-lg border bg-[var(--secondary)] p-1">
              {(
                [
                  { id: "unificada" as const, label: "Unificada" },
                  { id: "datajud" as const, label: "DataJud" },
                  { id: "djen" as const, label: "DJEN" },
                ] as const
              ).map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setFonte(f.id)}
                  className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                    fonte === f.id
                      ? "bg-legal-600 text-white shadow-sm"
                      : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-1 text-sm transition-colors ${
                hasAvancados
                  ? "text-legal-600 font-medium"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              <Filter className="h-4 w-4" />
              Filtros
              {hasAvancados && (
                <span className="ml-1 rounded-full bg-legal-600 text-white text-xs px-1.5 py-0.5">
                  ativos
                </span>
              )}
            </button>

            {hasAvancados && (
              <button
                type="button"
                onClick={clearAvancados}
                className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 transition-colors"
              >
                <X className="h-3 w-3" />
                Limpar filtros
              </button>
            )}

            <button
              type="submit"
              disabled={isSearching || (!termo.trim() && !numeroOab && !nomeAdvogado && !nomeParte)}
              className="ml-auto flex items-center gap-2 rounded-lg bg-legal-600 px-6 py-2 text-sm font-medium text-white hover:bg-legal-700 disabled:opacity-50 transition-colors"
            >
              {isSearching ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              Buscar
            </button>
          </div>

          {/* Filtros expandidos */}
          {showFilters && (
            <div className="border-t pt-4 space-y-4">
              {/* Filtros base */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                    Tribunal
                  </label>
                  <input
                    type="text"
                    value={tribunal}
                    onChange={(e) => setTribunal(e.target.value)}
                    placeholder="Ex: TJSP, TRF1"
                    className="w-full rounded-lg border bg-[var(--background)] px-4 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                    Data InÃ­cio
                  </label>
                  <input
                    type="date"
                    value={dataInicio}
                    onChange={(e) => setDataInicio(e.target.value)}
                    className="w-full rounded-lg border bg-[var(--background)] px-4 py-2 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                    Data Fim
                  </label>
                  <input
                    type="date"
                    value={dataFim}
                    onChange={(e) => setDataFim(e.target.value)}
                    className="w-full rounded-lg border bg-[var(--background)] px-4 py-2 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none"
                  />
                </div>
              </div>

              {/* Filtros Inteligentes (Fusão com Processos) */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)] mb-3">
                  Filtros Inteligentes (Captação)
                </p>
                <div className="flex flex-wrap gap-4 mb-4">
                  <label className="flex items-center gap-2 text-sm text-[var(--card-foreground)] cursor-pointer">
                    <input type="checkbox" checked={excluirFiscais} onChange={e => setExcluirFiscais(e.target.checked)} className="rounded border-gray-300 text-legal-600 focus:ring-legal-600" />
                    Excluir Execuções Fiscais
                  </label>
                  <label className="flex items-center gap-2 text-sm text-[var(--card-foreground)] cursor-pointer">
                    <input type="checkbox" checked={apenasSemAdvogado} onChange={e => setApenasSemAdvogado(e.target.checked)} className="rounded border-gray-300 text-legal-600 focus:ring-legal-600" />
                    Apenas sem advogado
                  </label>
                  <label className="flex items-center gap-2 text-sm text-[var(--card-foreground)] cursor-pointer">
                    <input type="checkbox" checked={ordenarPorScore} onChange={e => setOrdenarPorScore(e.target.checked)} className="rounded border-gray-300 text-legal-600 focus:ring-legal-600" />
                    Ordenar por Score de Lead
                  </label>
                </div>
              </div>

              {/* Filtros avanÃ§ados DJEN */}
              {(fonte === "djen" || fonte === "unificada") && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)] mb-3">
                    Filtros avanÃ§ados DJEN
                  </p>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div>
                      <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                        NÂº OAB
                      </label>
                      <input
                        type="text"
                        value={numeroOab}
                        onChange={(e) => setNumeroOab(e.target.value)}
                        placeholder="Ex: 123456"
                        className="w-full rounded-lg border bg-[var(--background)] px-4 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                        UF OAB
                      </label>
                      <input
                        type="text"
                        value={ufOab}
                        onChange={(e) => setUfOab(e.target.value.toUpperCase())}
                        placeholder="Ex: SP"
                        maxLength={2}
                        className="w-full rounded-lg border bg-[var(--background)] px-4 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                        Nome do Advogado
                      </label>
                      <input
                        type="text"
                        value={nomeAdvogado}
                        onChange={(e) => setNomeAdvogado(e.target.value)}
                        placeholder="Nome completo"
                        className="w-full rounded-lg border bg-[var(--background)] px-4 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                        Nome da Parte
                      </label>
                      <input
                        type="text"
                        value={nomeParte}
                        onChange={(e) => setNomeParte(e.target.value)}
                        placeholder="Nome completo"
                        className="w-full rounded-lg border bg-[var(--background)] px-4 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading */}
      {isSearching && (
        <div className="rounded-lg border bg-[var(--card)] p-12">
          <LoadingSpinner size="lg" text="Buscando em mÃºltiplas fontes..." />
        </div>
      )}

      {/* Results */}
      {!isSearching && hasSearched && (
        <div className="space-y-4">
          {/* Banner IA (Detecta CNJ) */}
          {termo.replace(/\D/g, "").length === 20 && (
             <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-4 flex items-center justify-between shadow-sm">
               <div className="flex items-center gap-3">
                 <div className="rounded-full bg-blue-500/20 p-2">
                   <AlertCircle className="h-5 w-5 text-blue-600" />
                 </div>
                 <div>
                   <h4 className="font-semibold text-blue-800 dark:text-blue-300">Oportunidade de Análise</h4>
                   <p className="text-sm text-blue-700/80 dark:text-blue-400/80">
                     Detectamos a busca por um número CNJ específico ({formatProcessoCNJ(termo)}).
                   </p>
                 </div>
               </div>
               <button className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors">
                 Analisar com IA
               </button>
             </div>
          )}
          
          {/* Resumo de resultados */}
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-sm text-[var(--muted-foreground)]">
              <span className="font-semibold text-[var(--foreground)]">{results.length}</span> resultado(s)
              {tempoMs && (
                <span className="ml-2 text-xs text-[var(--muted-foreground)]">
                  em {tempoMs < 1000 ? `${tempoMs}ms` : `${(tempoMs / 1000).toFixed(1)}s`}
                </span>
              )}
            </p>

            {/* Contagem por fonte */}
            {Object.keys(contagemPorFonte).length > 0 && (
              <div className="flex flex-wrap gap-2">
                {Object.entries(contagemPorFonte).map(([f, count]) => (
                  <span
                    key={f}
                    className="rounded-full bg-[var(--secondary)] px-3 py-0.5 text-xs font-medium text-[var(--muted-foreground)]"
                  >
                    {f}: {count}
                  </span>
                ))}
              </div>
            )}
          </div>

          {results.length > 0 ? (
            <div className="space-y-3">
              {results.map((item, idx) => (
                <ResultCard key={item.hash ?? idx} item={item} idx={idx} />
              ))}
            </div>
          ) : (
            <div className="rounded-lg border bg-[var(--card)] p-8 text-center">
              <Search className="mx-auto h-12 w-12 text-[var(--muted-foreground)] mb-4 opacity-30" />
              <p className="text-[var(--muted-foreground)]">
                Nenhum resultado encontrado.
              </p>
              <p className="text-xs text-[var(--muted-foreground)] mt-1">
                Tente ajustar os parÃ¢metros ou ampliar o perÃ­odo de busca.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!hasSearched && !isSearching && (
        <div className="rounded-lg border bg-[var(--card)] p-12 text-center">
          <Search className="mx-auto h-16 w-16 text-legal-600/20 mb-4" />
          <h3 className="text-lg font-medium text-[var(--card-foreground)] mb-2">
            Pesquisa
          </h3>
          <p className="text-sm text-[var(--muted-foreground)] max-w-md mx-auto">
            Pesquise processos, publicaÃ§Ãµes e decisÃµes em mÃºltiplas fontes
            simultaneamente. Use o campo acima ou os filtros avanÃ§ados para
            buscar por OAB, nome de advogado ou parte.
          </p>
        </div>
      )}
    </div>
  );
}
