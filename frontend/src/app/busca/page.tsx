"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import {
  Search,
  Clock,
  Trash2,
  ChevronDown,
  ChevronUp,
  Building2,
  Calendar,
  Globe,
  Gavel,
  Users,
  Briefcase,
  ExternalLink,
  Database,
  Timer,
  Hash,
  FileText,
  RefreshCw,
  X,
  BookOpen,
  Filter,
} from "lucide-react";

// ─── Types ──────────────────────────────────────────────────────────────────

interface PesquisaItem {
  id: number;
  termo: string;
  tipo: string;
  tribunal: string | null;
  data_inicio: string | null;
  data_fim: string | null;
  total_resultados: number;
  tempo_ms: number;
  fontes: string | null;
  criado_em: string;
}

interface PesquisaResultado {
  id: number;
  pesquisa_id: number;
  fonte: string;
  tribunal: string;
  numero_processo: string | null;
  classe_processual: string | null;
  orgao_julgador: string | null;
  data_publicacao: string | null;
  conteudo: string;
  advogados: string[] | string | null;
  partes: string[] | string | null;
  oab_encontradas: string[] | string | null;
  url_origem: string | null;
}

interface PesquisaDetalhada extends PesquisaItem {
  resultados: PesquisaResultado[];
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatDateBR(d: string | null | undefined): string {
  if (!d) return "";
  try {
    return new Date(d).toLocaleString("pt-BR", {
      timeZone: "America/Sao_Paulo",
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return d; }
}

function formatRelativeTime(d: string | null | undefined): string {
  if (!d) return "";
  try {
    const now = new Date(); const date = new Date(d);
    const diffMin = Math.floor((now.getTime() - date.getTime()) / 60000);
    if (diffMin < 1) return "Agora";
    if (diffMin < 60) return `${diffMin}min`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h`;
    return `${Math.floor(diffH / 24)}d`;
  } catch { return ""; }
}

function parseArray(val: string[] | string | null | undefined): string[] {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  try { const parsed = JSON.parse(val); return Array.isArray(parsed) ? parsed : []; }
  catch { return []; }
}

function formatProcessoCNJ(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 20)
    return `${digits.slice(0,7)}-${digits.slice(7,9)}.${digits.slice(9,13)}.${digits.slice(13,14)}.${digits.slice(14,16)}.${digits.slice(16,20)}`;
  return raw;
}

// ─── Page ───────────────────────────────────────────────────────────────────

export default function PesquisasPage() {
  const [pesquisas, setPesquisas] = useState<PesquisaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detalhe, setDetalhe] = useState<PesquisaDetalhada | null>(null);
  const [loadingDetalhe, setLoadingDetalhe] = useState(false);
  const [stats, setStats] = useState<{ total_pesquisas: number; total_resultados: number; ultima_pesquisa: string | null }>({ total_pesquisas: 0, total_resultados: 0, ultima_pesquisa: null });

  // Estado para a nova busca pontual
  const [termo, setTermo] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [tribunal, setTribunal] = useState("");
  const [fontes, setFontes] = useState<string[]>(["datajud", "djen_api"]);
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any>(null);

  const loadPesquisas = useCallback(async () => {
    try {
      setLoading(true);
      const [listRes, statsRes] = await Promise.all([
        fetch("/api/pesquisas/listar?limite=50").then(r => r.json()),
        fetch("/api/pesquisas/stats").then(r => r.json()),
      ]);
      setPesquisas(listRes.pesquisas || []);
      setStats(statsRes);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadPesquisas(); }, [loadPesquisas]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!termo.trim()) return;

    setSearching(true);
    setSearchResults(null);
    try {
      const res = await api.buscaUnificada({
        termo,
        tribunal: tribunal || undefined,
        data_inicio: dataInicio || undefined,
        data_fim: dataFim || undefined,
      });
      setSearchResults(res);
      await loadPesquisas(); // Atualiza histórico
    } catch (err) {
      alert("Erro ao realizar busca unificada");
    } finally {
      setSearching(false);
    }
  };

  const loadDetalhe = useCallback(async (id: number) => {
    if (selectedId === id) { setSelectedId(null); setDetalhe(null); return; }
    setSelectedId(id);
    setLoadingDetalhe(true);
    try {
      const res = await fetch(`/api/pesquisas/${id}`).then(r => r.json());
      setDetalhe(res.pesquisa || null);
    } catch { setDetalhe(null); }
    finally { setLoadingDetalhe(false); }
  }, [selectedId]);

  const handleDelete = async (id: number) => {
    if (!confirm("Excluir esta pesquisa e todos os resultados?")) return;
    try {
      await fetch(`/api/pesquisas/${id}`, { method: "DELETE" });
      if (selectedId === id) { setSelectedId(null); setDetalhe(null); }
      await loadPesquisas();
    } catch { alert("Erro ao excluir"); }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">Pesquisa Pontual</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Busca unificada em DataJud e DJEN (sem monitoramento ativo)
          </p>
        </div>
      </div>

      {/* Formulário de Busca */}
      <div className="rounded-xl border bg-[var(--card)] p-6 shadow-sm">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-2 space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                Termo de Busca (Processo, OAB ou Nome)
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--muted-foreground)]" />
                <input
                  type="text"
                  value={termo}
                  onChange={(e) => setTermo(e.target.value)}
                  placeholder="Ex: 0000000-00.0000.0.00.0000 ou 123456/SP"
                  className="w-full rounded-lg border bg-[var(--background)] py-2 pl-10 pr-4 text-sm focus:ring-2 focus:ring-legal-500"
                  required
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                Tribunal (Opcional)
              </label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--muted-foreground)]" />
                <input
                  type="text"
                  value={tribunal}
                  onChange={(e) => setTribunal(e.target.value)}
                  placeholder="Ex: TJSP, STJ..."
                  className="w-full rounded-lg border bg-[var(--background)] py-2 pl-10 pr-4 text-sm focus:ring-2 focus:ring-legal-500 uppercase"
                />
              </div>
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={searching}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-legal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-legal-700 disabled:opacity-50 transition-all font-inter"
              >
                {searching ? <LoadingSpinner /> : <><Search className="h-4 w-4" /> Pesquisar Agora</>}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                Data Início
              </label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--muted-foreground)]" />
                <input
                  type="date"
                  value={dataInicio}
                  onChange={(e) => setDataInicio(e.target.value)}
                  className="w-full rounded-lg border bg-[var(--background)] py-2 pl-10 pr-4 text-sm focus:ring-2 focus:ring-legal-500"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                Data Fim
              </label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--muted-foreground)]" />
                <input
                  type="date"
                  value={dataFim}
                  onChange={(e) => setDataFim(e.target.value)}
                  className="w-full rounded-lg border bg-[var(--background)] py-2 pl-10 pr-4 text-sm focus:ring-2 focus:ring-legal-500"
                />
              </div>
            </div>
            <div className="md:col-span-2 flex items-center gap-4 pt-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={fontes.includes("datajud")}
                  onChange={(e) => setFontes(e.target.checked ? [...fontes, "datajud"] : fontes.filter(f => f !== "datajud"))}
                  className="rounded text-legal-600 focus:ring-legal-500"
                />
                <span className="text-sm font-medium text-[var(--muted-foreground)]">DataJud</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={fontes.includes("djen_api")}
                  onChange={(e) => setFontes(e.target.checked ? [...fontes, "djen_api"] : fontes.filter(f => f !== "djen_api"))}
                  className="rounded text-legal-600 focus:ring-legal-500"
                />
                <span className="text-sm font-medium text-[var(--muted-foreground)]">DJEN</span>
              </label>
            </div>
          </div>
        </form>
      </div>

      {/* Resultados da Busca Atual */}
      {searchResults && (
        <div className="space-y-4 animate-in fade-in slide-in-from-top-4 duration-500">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <Search className="h-5 w-5 text-legal-600" />
              Resultados da Busca
              <span className="text-sm font-normal text-[var(--muted-foreground)] ml-2">
                ({searchResults.total_geral} encontrados em {searchResults.tempo_total_ms}ms)
              </span>
            </h2>
            <button onClick={() => setSearchResults(null)} className="text-xs text-[var(--muted-foreground)] hover:text-red-500">
              <X className="h-4 w-4 inline mr-1" /> Limpar
            </button>
          </div>
          
          <div className="grid grid-cols-1 gap-3">
            {Object.entries(searchResults.resultados_por_fonte).map(([fonte, data]: [string, any]) => (
              <div key={fonte} className="space-y-2">
                <div className="flex items-center gap-2 px-1">
                   <div className={`h-2 w-2 rounded-full ${fonte === "datajud" ? "bg-blue-500" : "bg-amber-500"}`} />
                   <span className="text-xs tracking-widest uppercase font-bold text-[var(--muted-foreground)]">
                     {fonte === "datajud" ? "DataJud (Metadados)" : "DJEN (Publicações)"}
                   </span>
                </div>
                {data.resultados && data.resultados.length > 0 ? (
                  data.resultados.map((r: any, idx: number) => (
                    <div key={idx} className="rounded-lg border bg-[var(--card)] p-4 hover:shadow-md transition-shadow">
                       <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm font-mono font-bold text-legal-600">
                            {formatProcessoCNJ(r.numero_processo || r.numeroProcesso || "")}
                          </span>
                          <span className="text-xs text-[var(--muted-foreground)]">•</span>
                          <span className="text-xs text-[var(--muted-foreground)]">{r.tribunal}</span>
                          {r.data_publicacao && (
                            <span className="text-xs text-[var(--muted-foreground)] flex items-center gap-1">
                              <Calendar className="h-3 w-3" /> {r.data_publicacao}
                            </span>
                          )}
                       </div>
                       {r.classe_processual && <p className="text-xs font-semibold mb-1">{r.classe_processual}</p>}
                       <p className="text-sm text-[var(--muted-foreground)] line-clamp-3 italic">
                         {r.conteudo || r.movimentos?.[0]?.nome || "Sem conteúdo disponível"}
                       </p>
                       {r.url_origem && (
                         <a href={r.url_origem} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs text-legal-600 hover:underline">
                           <ExternalLink className="h-3 w-3" /> Ver Original
                         </a>
                       )}
                    </div>
                  ))
                ) : (
                  <div className="p-4 bg-[var(--secondary)]/10 rounded-lg border border-dashed text-center text-xs text-[var(--muted-foreground)]">
                    Nenhum resultado encontrado nesta fonte
                  </div>
                )}
              </div>
            ))}
          </div>
          <hr className="border-dashed" />
        </div>
      )}

      {/* Histórico */}
      <div className="flex items-center gap-2 pb-2">
        <Clock className="h-5 w-5 text-[var(--muted-foreground)]" />
        <h2 className="text-lg font-bold text-[var(--foreground)]">Histórico de Pesquisas</h2>
      </div>

      {/* Lista de pesquisas */}
      {loading ? (
        <LoadingSpinner text="Carregando pesquisas..." />
      ) : pesquisas.length === 0 ? (
        <div className="rounded-lg border bg-[var(--card)] p-12 text-center">
          <Search className="mx-auto h-12 w-12 text-[var(--muted-foreground)] mb-4 opacity-30" />
          <h3 className="text-lg font-medium text-[var(--card-foreground)] mb-2">Nenhuma pesquisa realizada</h3>
          <p className="text-sm text-[var(--muted-foreground)]">
            Use a aba Busca Unificada para fazer pesquisas. Os resultados aparecerão aqui.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {pesquisas.map(p => (
            <div key={p.id} className="rounded-lg border bg-[var(--card)] shadow-sm overflow-hidden">
              {/* Header da pesquisa */}
              <div
                className={`flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-[var(--secondary)]/30 transition-colors ${
                  selectedId === p.id ? "bg-legal-600/5 border-b" : ""
                }`}
                onClick={() => loadDetalhe(p.id)}
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className={`rounded-lg p-2 shrink-0 ${p.tipo === "djen" ? "bg-amber-500/10" : "bg-blue-500/10"}`}>
                    {p.tipo === "djen" ? <Globe className="h-4 w-4 text-amber-600" /> : <Search className="h-4 w-4 text-blue-600" />}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-[var(--card-foreground)] truncate">
                      {p.termo || "(sem termo)"}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-[var(--muted-foreground)] mt-0.5">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" /> {formatRelativeTime(p.criado_em)}
                      </span>
                      {p.tribunal && (
                        <span className="flex items-center gap-1">
                          <Building2 className="h-3 w-3" /> {p.tribunal}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Timer className="h-3 w-3" /> {p.tempo_ms}ms
                      </span>
                      {p.fontes && (
                        <span className="flex items-center gap-1">
                          <Database className="h-3 w-3" /> {p.fontes}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${
                    p.total_resultados > 0 ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                  }`}>
                    {p.total_resultados} resultado{p.total_resultados !== 1 ? "s" : ""}
                  </span>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}
                    className="p-1.5 rounded-lg hover:bg-red-100 text-[var(--muted-foreground)] hover:text-red-600 dark:hover:bg-red-900/30"
                    title="Excluir pesquisa"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                  {selectedId === p.id ? <ChevronUp className="h-4 w-4 text-[var(--muted-foreground)]" /> : <ChevronDown className="h-4 w-4 text-[var(--muted-foreground)]" />}
                </div>
              </div>

              {/* Resultados expandidos */}
              {selectedId === p.id && (
                <div className="px-4 py-3 bg-[var(--secondary)]/20">
                  {loadingDetalhe ? (
                    <div className="py-4 text-center"><LoadingSpinner text="Carregando resultados..." /></div>
                  ) : detalhe && detalhe.resultados.length > 0 ? (
                    <div className="space-y-2 max-h-[500px] overflow-y-auto">
                      <p className="text-xs text-[var(--muted-foreground)] mb-2">
                        {detalhe.resultados.length} resultados - pesquisado em {formatDateBR(detalhe.criado_em)}
                      </p>
                      {detalhe.resultados.map((r, idx) => {
                        const advs = parseArray(r.advogados);
                        const pts = parseArray(r.partes);
                        const oabs = parseArray(r.oab_encontradas);
                        return (
                          <div key={r.id || idx} className="rounded-lg border bg-[var(--card)] p-3">
                            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                                r.fonte === "datajud" ? "border-blue-500/20 bg-blue-500/10 text-blue-700" : "border-amber-500/20 bg-amber-500/10 text-amber-700"
                              }`}>
                                {r.fonte === "datajud" ? <Database className="h-3 w-3" /> : <Globe className="h-3 w-3" />}
                                {r.fonte === "datajud" ? "DataJud" : "DJEN"}
                              </span>
                              {r.tribunal && <span className="text-xs text-[var(--muted-foreground)]">{r.tribunal}</span>}
                              {r.data_publicacao && <span className="text-xs text-[var(--muted-foreground)]"><Calendar className="inline h-3 w-3 mr-0.5" />{r.data_publicacao}</span>}
                              {r.numero_processo && (
                                <span className="text-xs font-mono font-bold text-[var(--card-foreground)]">
                                  {formatProcessoCNJ(r.numero_processo)}
                                </span>
                              )}
                            </div>
                            {r.classe_processual && (
                              <p className="text-xs font-medium text-[var(--card-foreground)] mb-1">
                                <Gavel className="inline h-3 w-3 mr-1 text-legal-500" />{r.classe_processual}
                              </p>
                            )}
                            {r.orgao_julgador && (
                              <p className="text-[10px] text-[var(--muted-foreground)] mb-1">{r.orgao_julgador}</p>
                            )}
                            {r.conteudo && (
                              <p className="text-xs text-[var(--muted-foreground)] line-clamp-3 mt-1">{r.conteudo}</p>
                            )}
                            {advs.length > 0 && (
                              <div className="mt-1.5 flex items-center gap-1 text-xs text-[var(--muted-foreground)]">
                                <Briefcase className="h-3 w-3 text-purple-500 shrink-0" />
                                {advs.join(", ")}
                              </div>
                            )}
                            {pts.length > 0 && (
                              <div className="mt-1 flex items-center gap-1 text-xs text-[var(--muted-foreground)]">
                                <Users className="h-3 w-3 text-blue-500 shrink-0" />
                                {pts.join(", ")}
                              </div>
                            )}
                            {r.url_origem && (
                              <a href={r.url_origem} target="_blank" rel="noopener noreferrer" className="mt-1.5 inline-flex items-center gap-1 text-xs text-legal-600 hover:underline">
                                <ExternalLink className="h-3 w-3" /> Ver original
                              </a>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="py-4 text-center text-sm text-[var(--muted-foreground)]">Nenhum resultado salvo para esta pesquisa.</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
