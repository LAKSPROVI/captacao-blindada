"use client";

import { useEffect, useState, useMemo } from "react";
import { api, MonitorStats, ProcessoMonitoradoStats, CaptacaoStats, PublicacaoItem, ProcessoMonitorado } from "@/lib/api";
import { StatsCard } from "@/components/StatsCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import {
  FileText,
  Eye,
  Newspaper,
  Activity,
  Search,
  ArrowRight,
  Zap,
  Clock,
  TrendingUp,
  BarChart3,
  PieChart,
  Shield,
  Globe,
  Scale,
  Building2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Calendar,
  Hash,
  Database,
  Wifi,
  WifiOff,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Timer,
  Gavel,
  Users,
  Briefcase,
  MapPin,
  UserCheck,
  Landmark,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatDateBR(d: string | null | undefined): string {
  if (!d) return "Nunca";
  try {
    return new Date(d).toLocaleString("pt-BR", {
      timeZone: "America/Sao_Paulo",
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return d || "Nunca"; }
}

function formatRelativeTime(d: string | null | undefined): string {
  if (!d) return "Nunca";
  try {
    const now = new Date();
    const date = new Date(d);
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    const diffH = Math.floor(diffMin / 60);
    const diffD = Math.floor(diffH / 24);
    if (diffMin < 1) return "Agora";
    if (diffMin < 60) return `${diffMin}min atras`;
    if (diffH < 24) return `${diffH}h atras`;
    if (diffD < 7) return `${diffD}d atras`;
    return formatDateBR(d);
  } catch { return d || "Nunca"; }
}

function formatProcessoCNJ(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 20)
    return `${digits.slice(0,7)}-${digits.slice(7,9)}.${digits.slice(9,13)}.${digits.slice(13,14)}.${digits.slice(14,16)}.${digits.slice(16,20)}`;
  return raw;
}

// ─── Classificação por Área do Direito ──────────────────────────────────────

interface AreaDireito {
  nome: string;
  color: string;
  keywords: RegExp;
}

const AREAS_DIREITO: AreaDireito[] = [
  {
    nome: "Civel",
    color: "bg-blue-500",
    keywords: /c[ií]vel|c[ií]v\b|obriga[çc][aã]o|cobran[çc]a|indeniza[çc][aã]o|monitoria|execu[çc][aã]o.*(t[ií]tulo|fiscal)|a[çc][aã]o\s+(de\s+)?cobran[çc]a|procedimento\s+comum|sum[aá]rio|ordin[aá]rio|a[çc][aã]o\s+civil|consigna[çc][aã]o|despejo|reintegra[çc][aã]o|imiss[aã]o|usucapi[aã]o|inventario|arrolamento|interdi[çc][aã]o/i,
  },
  {
    nome: "Trabalhista",
    color: "bg-amber-500",
    keywords: /trabalh|reclama[çc][aã]o\s+trabalhista|diss[ií]dio|rescis[aã]o.*contrato.*trabalho|FGTS|aviso\s+pr[eé]vio|horas?\s+extra|adicional.*noturno|insalubridade|periculosidade/i,
  },
  {
    nome: "Criminal",
    color: "bg-red-500",
    keywords: /criminal|penal|crime|a[çc][aã]o\s+penal|inqu[eé]rito|habeas\s+corpus|exec.*penal|pris[aã]o|liberdade|fiança|cautelar.*penal|medida.*protetiva|lei\s+maria/i,
  },
  {
    nome: "Tributario",
    color: "bg-green-600",
    keywords: /tribut[aá]|fiscal|imposto|ICMS|ISS|IPTU|IPVA|IR\b|IPI|contribui[çc][aã]o|mandado.*seguran[çc]a.*tribut|execu[çc][aã]o\s+fiscal|anu(la|lat)[oó]ria.*d[eé]bito|embargos.*execu[çc][aã]o\s+fiscal|repeti[çc][aã]o.*ind[eé]bito/i,
  },
  {
    nome: "Familia",
    color: "bg-pink-500",
    keywords: /fam[ií]lia|div[oó]rcio|alimentos|guarda|regulamenta[çc][aã]o.*visita|investiga[çc][aã]o.*paternidade|ado[çc][aã]o|tutela|curatela|uni[aã]o\s+est[aá]vel|partilha.*bens/i,
  },
  {
    nome: "Consumidor",
    color: "bg-cyan-500",
    keywords: /consumidor|CDC|rela[çc][aã]o.*consumo|produto.*defeito|v[ií]cio.*produto|propaganda.*enganosa|juizado.*especial.*c[ií]vel/i,
  },
  {
    nome: "Administrativo",
    color: "bg-indigo-500",
    keywords: /administrativ|mandado.*seguran[çc]a|a[çc][aã]o.*popular|a[çc][aã]o.*civil.*p[uú]blica|improbidade|licita[çc][aã]o|concurso.*p[uú]blico|servidor.*p[uú]blico|desapropria[çc][aã]o/i,
  },
  {
    nome: "Empresarial",
    color: "bg-violet-500",
    keywords: /empresarial|fal[eê]ncia|recupera[çc][aã]o.*judicial|societ[aá]ri|dissoluc[aã]o.*sociedade|marca|patente|propriedade.*industrial|contrato.*comercial/i,
  },
];

function classificarArea(classeProcessual: string | undefined | null): string {
  if (!classeProcessual) return "Outros";
  for (const area of AREAS_DIREITO) {
    if (area.keywords.test(classeProcessual)) return area.nome;
  }
  return "Outros";
}

function getAreaColor(nomeArea: string): string {
  const area = AREAS_DIREITO.find(a => a.nome === nomeArea);
  return area?.color || "bg-gray-400";
}

// ─── Extração de Cidade/Comarca ─────────────────────────────────────────────

function extrairCidade(orgaoJulgador: string | undefined | null): string {
  if (!orgaoJulgador) return "Desconhecida";

  // Pattern: "... de <Cidade>" or "... - <Cidade>" or "Comarca de <Cidade>"
  const patterns = [
    /comarca\s+de\s+([A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+(?:\s+(?:de?|d[aoe]s?)\s+)?[A-Z\u00C0-\u024F]?[a-z\u00C0-\u024F]*)/i,
    /(?:foro|vara|ju[ií]zo).*?(?:de|da|do)\s+([A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+(?:\s+(?:de?|d[aoe]s?|e)\s+[A-Z\u00C0-\u024F]?[a-z\u00C0-\u024F]+)*)\s*$/i,
    /[-–]\s*([A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+(?:\s+(?:de?|d[aoe]s?|e)\s+[A-Z\u00C0-\u024F]?[a-z\u00C0-\u024F]+)*)\s*$/i,
    /(?:seção|subseção|foro)\s+(?:de|da|do)\s+([A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+(?:\s+[A-Z\u00C0-\u024F]?[a-z\u00C0-\u024F]+)*)/i,
  ];

  for (const pattern of patterns) {
    const match = orgaoJulgador.match(pattern);
    if (match && match[1]) {
      const cidade = match[1].trim();
      // Filter out common false positives
      if (cidade.length > 2 && !/^(vara|foro|juiz|tribunal|turma|seção|câmara|gabinete)$/i.test(cidade)) {
        return cidade;
      }
    }
  }

  // Fallback: try to extract capitalized words at the end
  const endMatch = orgaoJulgador.match(/([A-Z\u00C0-\u024F][a-z\u00C0-\u024F]{2,}(?:\s+(?:de?|d[aoe]s?|e)\s+[A-Z\u00C0-\u024F]?[a-z\u00C0-\u024F]+)*)\s*$/);
  if (endMatch && endMatch[1] && endMatch[1].length > 3) {
    return endMatch[1].trim();
  }

  // Last fallback: return full string truncated
  return orgaoJulgador.length > 30 ? orgaoJulgador.slice(0, 30) + "..." : orgaoJulgador;
}

// ─── Mini Components ────────────────────────────────────────────────────────

function ClickableMetricCard({ label, value, sub, icon: Icon, color = "legal", href }: {
  label: string; value: string | number; sub?: string;
  icon: typeof Activity; color?: string; href: string;
}) {
  const colorMap: Record<string, string> = {
    legal: "bg-legal-600/10 text-legal-600",
    blue: "bg-blue-500/10 text-blue-600",
    green: "bg-green-500/10 text-green-600",
    amber: "bg-amber-500/10 text-amber-600",
    red: "bg-red-500/10 text-red-600",
    purple: "bg-purple-500/10 text-purple-600",
    cyan: "bg-cyan-500/10 text-cyan-600",
  };
  return (
    <Link href={href} className="block group">
      <div className="rounded-xl border bg-[var(--card)] p-4 shadow-sm hover:shadow-md hover:border-legal-600/30 transition-all cursor-pointer">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-[var(--muted-foreground)] uppercase tracking-wider">{label}</span>
          <div className="flex items-center gap-1.5">
            <div className={`rounded-lg p-2 ${colorMap[color] || colorMap.legal}`}>
              <Icon className="h-4 w-4" />
            </div>
            <ArrowUpRight className="h-3 w-3 text-[var(--muted-foreground)] opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
        <p className="text-2xl font-bold text-[var(--card-foreground)]">{value}</p>
        {sub && <p className="text-xs text-[var(--muted-foreground)] mt-1">{sub}</p>}
      </div>
    </Link>
  );
}

function MetricCard({ label, value, sub, icon: Icon, color = "legal" }: {
  label: string; value: string | number; sub?: string;
  icon: typeof Activity; color?: string;
}) {
  const colorMap: Record<string, string> = {
    legal: "bg-legal-600/10 text-legal-600",
    blue: "bg-blue-500/10 text-blue-600",
    green: "bg-green-500/10 text-green-600",
    amber: "bg-amber-500/10 text-amber-600",
    red: "bg-red-500/10 text-red-600",
    purple: "bg-purple-500/10 text-purple-600",
    cyan: "bg-cyan-500/10 text-cyan-600",
  };
  return (
    <div className="rounded-xl border bg-[var(--card)] p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-[var(--muted-foreground)] uppercase tracking-wider">{label}</span>
        <div className={`rounded-lg p-2 ${colorMap[color] || colorMap.legal}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="text-2xl font-bold text-[var(--card-foreground)]">{value}</p>
      {sub && <p className="text-xs text-[var(--muted-foreground)] mt-1">{sub}</p>}
    </div>
  );
}

function ProgressBar({ value, max, label, color = "bg-legal-600" }: {
  value: number; max: number; label: string; color?: string;
}) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-[var(--muted-foreground)]">{label}</span>
        <span className="font-semibold text-[var(--card-foreground)]">{value} <span className="text-[var(--muted-foreground)] font-normal">/ {max}</span></span>
      </div>
      <div className="h-2 rounded-full bg-[var(--secondary)]">
        <div className={`h-2 rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [refreshing, setRefreshing] = useState(false);

  // Data stores
  const [monitorStats, setMonitorStats] = useState<MonitorStats>({});
  const [processosStats, setProcessosStats] = useState<ProcessoMonitoradoStats | null>(null);
  const [captacaoStats, setCaptacaoStats] = useState<CaptacaoStats | null>(null);
  const [publicacoes, setPublicacoes] = useState<PublicacaoItem[]>([]);
  const [processos, setProcessos] = useState<ProcessoMonitorado[]>([]);
  const [healthOk, setHealthOk] = useState(true);
  const [backendLatency, setBackendLatency] = useState(0);

  const loadData = async (silent = false) => {
    if (!silent) setIsLoading(true);
    else setRefreshing(true);

    const t0 = performance.now();

    try {
      const [mStats, pStats, cStats, pubs, procs, health] = await Promise.allSettled([
        api.getMonitorStats(),
        api.getProcessoMonitoradoStats(),
        api.getCaptacaoStats(),
        api.getPublicacoesRecentes({ limite: 500 }),
        api.listarProcessosMonitorados({ limite: 500 }),
        api.health(),
      ]);

      if (mStats.status === "fulfilled") setMonitorStats(mStats.value);
      if (pStats.status === "fulfilled") setProcessosStats(pStats.value);
      if (cStats.status === "fulfilled") setCaptacaoStats(cStats.value);
      if (pubs.status === "fulfilled") setPublicacoes(pubs.value);
      if (procs.status === "fulfilled") setProcessos(procs.value.processos || []);
      setHealthOk(health.status === "fulfilled" && health.value?.status === "ok");
      setBackendLatency(Math.round(performance.now() - t0));
      setLastRefresh(new Date());
    } catch {
      setHealthOk(false);
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  // ── Metricas derivadas ──
  const metricas = useMemo(() => {
    // Publicacoes por fonte
    const porFonte: Record<string, number> = {};
    const porTribunal: Record<string, number> = {};
    const porDia: Record<string, number> = {};
    let comAdvogado = 0, semAdvogado = 0;
    let comPartes = 0;

    publicacoes.forEach(p => {
      const f = p.fonte || "desconhecida";
      porFonte[f] = (porFonte[f] || 0) + 1;
      if (p.tribunal) porTribunal[p.tribunal] = (porTribunal[p.tribunal] || 0) + 1;
      if (p.data_publicacao) {
        const dia = p.data_publicacao.slice(0, 10);
        porDia[dia] = (porDia[dia] || 0) + 1;
      }
      if (p.advogados && p.advogados.length > 0) comAdvogado++; else semAdvogado++;
      if (p.partes && p.partes.length > 0) comPartes++;
    });

    // Top 5 tribunais
    const topTribunais = Object.entries(porTribunal)
      .sort((a, b) => b[1] - a[1]);

    // Processos com movimentacao recente (7 dias)
    const umaSemana = Date.now() - 7 * 24 * 60 * 60 * 1000;
    const procRecentes = processos.filter(p => {
      if (!p.data_ultima_movimentacao) return false;
      return new Date(p.data_ultima_movimentacao).getTime() > umaSemana;
    });

    // Top classes processuais
    const porClasse: Record<string, number> = {};
    processos.forEach(p => {
      if (p.classe_processual) porClasse[p.classe_processual] = (porClasse[p.classe_processual] || 0) + 1;
    });
    const topClasses = Object.entries(porClasse).sort((a, b) => b[1] - a[1]);

    // Processos com mais movimentacoes
    const topMovimentados = [...processos]
      .filter(p => p.total_movimentacoes > 0)
      .sort((a, b) => b.total_movimentacoes - a.total_movimentacoes);

    // ── NOVAS METRICAS ──

    // Metricas por Area do Direito
    const porArea: Record<string, number> = {};
    processos.forEach(p => {
      const area = classificarArea(p.classe_processual);
      porArea[area] = (porArea[area] || 0) + 1;
    });
    const areasOrdenadas = Object.entries(porArea).sort((a, b) => b[1] - a[1]);

    // Metricas por Cidade/Comarca
    const porCidade: Record<string, number> = {};
    processos.forEach(p => {
      const cidade = extrairCidade(p.orgao_julgador);
      porCidade[cidade] = (porCidade[cidade] || 0) + 1;
    });
    const topCidades = Object.entries(porCidade)
      .sort((a, b) => b[1] - a[1]);

    // Metricas por Orgao Julgador
    const porOrgao: Record<string, number> = {};
    processos.forEach(p => {
      if (p.orgao_julgador) {
        porOrgao[p.orgao_julgador] = (porOrgao[p.orgao_julgador] || 0) + 1;
      }
    });
    const topOrgaos = Object.entries(porOrgao)
      .sort((a, b) => b[1] - a[1]);

    return {
      porFonte, porTribunal, topTribunais, porDia,
      comAdvogado, semAdvogado, comPartes,
      procRecentes, topClasses, topMovimentados,
      totalFontes: Object.keys(porFonte).length,
      totalTribunais: Object.keys(porTribunal).length,
      diasComDados: Object.keys(porDia).length,
      // Novas
      porArea, areasOrdenadas,
      topCidades,
      topOrgaos,
    };
  }, [publicacoes, processos]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/processo?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner size="lg" text="Carregando painel..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ══════ HEADER + STATUS BAR ══════ */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">Painel de Comando</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Visao completa do sistema - {formatDateBR(new Date().toISOString())}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* System status */}
          <div className="flex items-center gap-2 rounded-lg border bg-[var(--card)] px-3 py-2 text-xs">
            <StatusDot ok={healthOk} />
            <span className="text-[var(--card-foreground)] font-medium">{healthOk ? "Sistema Online" : "Sistema Offline"}</span>
            <span className="text-[var(--muted-foreground)]">{backendLatency}ms</span>
          </div>
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Atualizar
          </button>
        </div>
      </div>

      {/* ══════ BUSCA RAPIDA ══════ */}
      <form onSubmit={handleSearch} className="relative max-w-2xl">
        <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[var(--muted-foreground)]" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Buscar processo por numero CNJ, nome, OAB..."
          className="w-full rounded-xl border bg-[var(--card)] py-3 pl-12 pr-24 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20 shadow-sm"
        />
        <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg bg-legal-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-legal-700 transition-colors">
          Buscar
        </button>
      </form>

      {/* ══════ METRICAS PRINCIPAIS (6 cards clicaveis) ══════ */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <ClickableMetricCard
          label="Processos Monitorados"
          value={processosStats?.total || 0}
          sub={`${processosStats?.com_movimentacoes || 0} com movimentacoes`}
          icon={FileText}
          color="legal"
          href="/processo"
        />
        <ClickableMetricCard
          label="Publicacoes"
          value={monitorStats.total_publicacoes || publicacoes.length}
          sub={`${metricas.totalFontes} fontes ativas`}
          icon={Newspaper}
          color="blue"
          href="/monitor"
        />
        <ClickableMetricCard
          label="Monitores Ativos"
          value={monitorStats.monitorados_ativos || 0}
          sub={`${monitorStats.total_monitorados || 0} total cadastrados`}
          icon={Eye}
          color="green"
          href="/monitor"
        />
        <ClickableMetricCard
          label="Captacoes"
          value={captacaoStats?.total_captacoes || 0}
          sub={`${captacaoStats?.captacoes_ativas || 0} ativas, ${captacaoStats?.captacoes_pausadas || 0} pausadas`}
          icon={Zap}
          color="amber"
          href="/captacao"
        />
        <ClickableMetricCard
          label="Movim. Recentes"
          value={metricas.procRecentes.length}
          sub={`ultimos 7 dias`}
          icon={Activity}
          color="purple"
          href="/processo?filter=recente"
        />
        <ClickableMetricCard
          label="Sem Advogado"
          value={metricas.semAdvogado}
          sub={`${publicacoes.length > 0 ? Math.round((metricas.semAdvogado / publicacoes.length) * 100) : 0}% das publicacoes`}
          icon={AlertTriangle}
          color="red"
          href="/monitor?filter=sem-advogado"
        />
      </div>

      {/* ══════ METRICAS EXTRAS (2 cards nao clicaveis) ══════ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Tribunais" value={metricas.totalTribunais} sub={`cobrindo ${metricas.diasComDados} dias`} icon={Building2} color="cyan" />
        <MetricCard label="Execucoes Captacao" value={captacaoStats?.total_execucoes || 0} sub={`${captacaoStats?.execucoes_hoje || 0} hoje`} icon={Timer} color="legal" />
        <MetricCard label="Areas do Direito" value={metricas.areasOrdenadas.length} sub={`${processos.length} processos classificados`} icon={Scale} color="purple" />
        <MetricCard label="Cidades/Comarcas" value={metricas.topCidades.length > 0 ? metricas.topCidades.length + "+" : 0} sub={`orgaos julgadores mapeados`} icon={MapPin} color="green" />
      </div>

      {/* ══════ GRID 3 COLUNAS: AREAS | CIDADES | ORGAOS ══════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Metricas por Area do Direito */}
        <div className="rounded-xl border bg-[var(--card)] p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-[var(--card-foreground)] mb-4 flex items-center gap-2">
            <Scale className="h-4 w-4 text-legal-600" /> Processos por Area do Direito
          </h3>
          <div className="space-y-3">
            {metricas.areasOrdenadas.length > 0 ? (
              <>
                {metricas.areasOrdenadas.map(([area, count]) => (
                  <ProgressBar
                    key={area}
                    label={area}
                    value={count}
                    max={processos.length}
                    color={getAreaColor(area)}
                  />
                ))}
                <p className="text-xs text-[var(--muted-foreground)] pt-2 border-t">
                  Total: <span className="font-semibold text-[var(--card-foreground)]">{processos.length}</span> processos classificados
                </p>
              </>
            ) : (
              <p className="text-xs text-[var(--muted-foreground)] text-center py-4">Sem processos para classificar</p>
            )}
          </div>
        </div>

        {/* Metricas por Cidade/Comarca */}
        <div className="rounded-xl border bg-[var(--card)] p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-[var(--card-foreground)] mb-4 flex items-center gap-2">
            <MapPin className="h-4 w-4 text-green-600" /> Top Cidades / Comarcas
          </h3>
          <div className="space-y-2">
            {metricas.topCidades.length > 0 ? (
              metricas.topCidades.map(([cidade, count], idx) => (
                <div key={cidade} className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className={`text-xs font-bold w-5 text-center shrink-0 ${idx === 0 ? "text-amber-500" : idx === 1 ? "text-gray-400" : idx === 2 ? "text-amber-700" : "text-[var(--muted-foreground)]"}`}>
                      {idx + 1}
                    </span>
                    <span className="text-sm text-[var(--card-foreground)] font-medium truncate">{cidade}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="w-16 h-1.5 rounded-full bg-[var(--secondary)]">
                      <div className="h-1.5 rounded-full bg-green-500" style={{ width: `${metricas.topCidades[0] ? Math.round((count / metricas.topCidades[0][1]) * 100) : 0}%` }} />
                    </div>
                    <span className="text-xs font-semibold text-[var(--card-foreground)] w-8 text-right">{count}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-[var(--muted-foreground)] text-center py-4">Sem dados de comarca</p>
            )}
            {metricas.topCidades.length > 0 && (
              <p className="text-xs text-[var(--muted-foreground)] pt-2 border-t">
                Extraido de <span className="font-semibold text-[var(--card-foreground)]">{processos.filter(p => p.orgao_julgador).length}</span> orgaos julgadores
              </p>
            )}
          </div>
        </div>

        {/* Metricas por Juiz/Orgao Julgador */}
        <div className="rounded-xl border bg-[var(--card)] p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-[var(--card-foreground)] mb-4 flex items-center gap-2">
            <Landmark className="h-4 w-4 text-indigo-600" /> Top Orgaos Julgadores
          </h3>
          <div className="space-y-2">
            {metricas.topOrgaos.length > 0 ? (
              metricas.topOrgaos.map(([orgao, count], idx) => (
                <div key={orgao} className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className={`text-xs font-bold w-5 text-center shrink-0 ${idx === 0 ? "text-amber-500" : idx === 1 ? "text-gray-400" : idx === 2 ? "text-amber-700" : "text-[var(--muted-foreground)]"}`}>
                      {idx + 1}
                    </span>
                    <span className="text-xs text-[var(--card-foreground)] font-medium truncate" title={orgao}>{orgao}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="w-12 h-1.5 rounded-full bg-[var(--secondary)]">
                      <div className="h-1.5 rounded-full bg-indigo-500" style={{ width: `${metricas.topOrgaos[0] ? Math.round((count / metricas.topOrgaos[0][1]) * 100) : 0}%` }} />
                    </div>
                    <span className="text-xs font-semibold text-[var(--card-foreground)] w-8 text-right">{count}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-[var(--muted-foreground)] text-center py-4">Sem dados de orgaos</p>
            )}
            {metricas.topOrgaos.length > 0 && (
              <p className="text-xs text-[var(--muted-foreground)] pt-2 border-t">
                Total: <span className="font-semibold text-[var(--card-foreground)]">{Object.keys(metricas.topOrgaos).length}</span> de {Object.keys(processos.reduce((acc, p) => { if (p.orgao_julgador) acc[p.orgao_julgador] = true; return acc; }, {} as Record<string, boolean>)).length} orgaos unicos
              </p>
            )}
          </div>
        </div>
      </div>

      {/* ══════ GRID 3 COLUNAS: FONTES | TRIBUNAIS | STATUS ══════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Distribuicao por Fonte */}
        <div className="rounded-xl border bg-[var(--card)] p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-[var(--card-foreground)] mb-4 flex items-center gap-2">
            <PieChart className="h-4 w-4 text-legal-600" /> Publicacoes por Fonte
          </h3>
          <div className="space-y-3">
            {Object.entries(metricas.porFonte).sort((a, b) => b[1] - a[1]).map(([fonte, count]) => (
              <ProgressBar
                key={fonte}
                label={fonte === "datajud" ? "DataJud" : fonte === "djen_api" ? "DJEN" : fonte}
                value={count}
                max={publicacoes.length}
                color={fonte === "datajud" ? "bg-blue-500" : fonte === "djen_api" ? "bg-amber-500" : "bg-gray-400"}
              />
            ))}
            <p className="text-xs text-[var(--muted-foreground)] pt-2 border-t">
              Total: <span className="font-semibold text-[var(--card-foreground)]">{publicacoes.length}</span> publicacoes
            </p>
          </div>
        </div>

        {/* Top Tribunais */}
        <div className="rounded-xl border bg-[var(--card)] p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-[var(--card-foreground)] mb-4 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-blue-600" /> Top Tribunais
          </h3>
          <div className="space-y-2">
            {metricas.topTribunais.map(([tribunal, count], idx) => (
              <div key={tribunal} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-bold w-5 text-center ${idx === 0 ? "text-amber-500" : idx === 1 ? "text-gray-400" : idx === 2 ? "text-amber-700" : "text-[var(--muted-foreground)]"}`}>
                    {idx + 1}
                  </span>
                  <span className="text-sm text-[var(--card-foreground)] font-medium">{tribunal}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-20 h-1.5 rounded-full bg-[var(--secondary)]">
                    <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${metricas.topTribunais[0] ? Math.round((count / metricas.topTribunais[0][1]) * 100) : 0}%` }} />
                  </div>
                  <span className="text-xs font-semibold text-[var(--card-foreground)] w-8 text-right">{count}</span>
                </div>
              </div>
            ))}
            {metricas.topTribunais.length === 0 && (
              <p className="text-xs text-[var(--muted-foreground)] text-center py-4">Sem dados</p>
            )}
          </div>
        </div>

        {/* Status do Sistema */}
        <div className="rounded-xl border bg-[var(--card)] p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-[var(--card-foreground)] mb-4 flex items-center gap-2">
            <Shield className="h-4 w-4 text-green-600" /> Status do Sistema
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--muted-foreground)]">Backend API</span>
              <div className="flex items-center gap-2">
                <StatusDot ok={healthOk} />
                <span className="text-xs font-medium text-[var(--card-foreground)]">{healthOk ? "Online" : "Offline"}</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--muted-foreground)]">Latencia</span>
              <span className={`text-xs font-bold ${backendLatency < 1000 ? "text-green-600" : backendLatency < 3000 ? "text-amber-600" : "text-red-600"}`}>{backendLatency}ms</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--muted-foreground)]">Ultima Verif. Processos</span>
              <span className="text-xs text-[var(--card-foreground)]">{formatRelativeTime(processosStats?.ultima_verificacao)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--muted-foreground)]">Ultima Busca Monitor</span>
              <span className="text-xs text-[var(--card-foreground)]">{formatRelativeTime(monitorStats.ultima_busca)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--muted-foreground)]">Verif. Hoje</span>
              <span className="text-xs font-bold text-[var(--card-foreground)]">{processosStats?.verificados_hoje || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--muted-foreground)]">Exec. Captacao Hoje</span>
              <span className="text-xs font-bold text-[var(--card-foreground)]">{captacaoStats?.execucoes_hoje || 0}</span>
            </div>
            <div className="border-t pt-2 mt-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--muted-foreground)]">Fuso Horario</span>
                <span className="text-xs font-medium text-[var(--card-foreground)]">America/Sao_Paulo</span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-sm text-[var(--muted-foreground)]">Atualizado</span>
                <span className="text-xs text-[var(--card-foreground)]">{formatRelativeTime(lastRefresh.toISOString())}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ══════ GRID 2 COLUNAS: PROCESSOS RECENTES | INSIGHTS ══════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Processos com Movimentacao Recente — clicaveis */}
        <div className="rounded-xl border bg-[var(--card)] p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--card-foreground)] flex items-center gap-2">
              <Activity className="h-4 w-4 text-purple-600" /> Processos com Movim. Recente
            </h3>
            <Link href="/processo?filter=recente" className="text-xs text-legal-600 hover:underline flex items-center gap-1">
              Ver todos <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          {metricas.topMovimentados.length > 0 ? (
            <div className="space-y-2">
              {metricas.topMovimentados.map(p => (
                <Link
                  key={p.id}
                  href={`/processo?q=${encodeURIComponent(p.numero_processo)}`}
                  className="flex items-center justify-between rounded-lg bg-[var(--secondary)]/40 px-3 py-2.5 hover:bg-[var(--secondary)]/70 transition-colors cursor-pointer group"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-mono font-bold text-[var(--card-foreground)] truncate group-hover:text-legal-600 transition-colors">
                      {formatProcessoCNJ(p.numero_processo)}
                    </p>
                    <p className="text-[10px] text-[var(--muted-foreground)]">
                      {p.tribunal} {p.classe_processual ? `- ${p.classe_processual}` : ""}
                    </p>
                  </div>
                  <div className="text-right shrink-0 ml-3 flex items-center gap-2">
                    <div>
                      <span className="inline-flex items-center rounded-full bg-purple-500/10 px-2 py-0.5 text-xs font-bold text-purple-700">
                        {p.total_movimentacoes} mov.
                      </span>
                      {p.data_ultima_movimentacao && (
                        <p className="text-[10px] text-[var(--muted-foreground)] mt-0.5">
                          {formatRelativeTime(p.data_ultima_movimentacao)}
                        </p>
                      )}
                    </div>
                    <ArrowRight className="h-3 w-3 text-[var(--muted-foreground)] opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[var(--muted-foreground)] text-center py-4">Nenhuma movimentacao recente</p>
          )}
        </div>

        {/* Insights & Classes Processuais */}
        <div className="rounded-xl border bg-[var(--card)] p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-[var(--card-foreground)] mb-4 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-600" /> Insights
          </h3>
          <div className="space-y-3">
            {/* Insight: Sem Advogado */}
            {metricas.semAdvogado > 0 && (
              <Link href="/monitor?filter=sem-advogado" className="flex items-start gap-3 rounded-lg bg-red-500/5 border border-red-500/10 px-3 py-2.5 hover:bg-red-500/10 transition-colors cursor-pointer group">
                <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <p className="text-xs font-semibold text-[var(--card-foreground)]">
                    {metricas.semAdvogado} publicacoes sem advogado
                  </p>
                  <p className="text-[10px] text-[var(--muted-foreground)]">
                    {publicacoes.length > 0 ? Math.round((metricas.semAdvogado / publicacoes.length) * 100) : 0}% do total - potenciais leads de captacao
                  </p>
                </div>
                <ArrowRight className="h-3 w-3 text-[var(--muted-foreground)] mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
              </Link>
            )}

            {/* Insight: Movimentacoes Recentes */}
            {metricas.procRecentes.length > 0 && (
              <Link href="/processo?filter=recente" className="flex items-start gap-3 rounded-lg bg-purple-500/5 border border-purple-500/10 px-3 py-2.5 hover:bg-purple-500/10 transition-colors cursor-pointer group">
                <Activity className="h-4 w-4 text-purple-500 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <p className="text-xs font-semibold text-[var(--card-foreground)]">
                    {metricas.procRecentes.length} processos movimentaram esta semana
                  </p>
                  <p className="text-[10px] text-[var(--muted-foreground)]">
                    {processosStats?.total ? Math.round((metricas.procRecentes.length / processosStats.total) * 100) : 0}% dos processos monitorados
                  </p>
                </div>
                <ArrowRight className="h-3 w-3 text-[var(--muted-foreground)] mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
              </Link>
            )}

            {/* Insight: Captacao */}
            {captacaoStats && captacaoStats.total_novos_encontrados > 0 && (
              <Link href="/captacao?filter=novos" className="flex items-start gap-3 rounded-lg bg-green-500/5 border border-green-500/10 px-3 py-2.5 hover:bg-green-500/10 transition-colors cursor-pointer group">
                <Zap className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <p className="text-xs font-semibold text-[var(--card-foreground)]">
                    {captacaoStats.total_novos_encontrados} novos resultados de captacao
                  </p>
                  <p className="text-[10px] text-[var(--muted-foreground)]">
                    Em {captacaoStats.total_execucoes} execucoes automaticas
                  </p>
                </div>
                <ArrowRight className="h-3 w-3 text-[var(--muted-foreground)] mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
              </Link>
            )}

            {/* Insight: Area mais frequente */}
            {metricas.areasOrdenadas.length > 0 && (
              <div className="flex items-start gap-3 rounded-lg bg-legal-600/5 border border-legal-600/10 px-3 py-2.5">
                <Scale className="h-4 w-4 text-legal-600 mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-[var(--card-foreground)]">
                    Area predominante: {metricas.areasOrdenadas[0][0]}
                  </p>
                  <p className="text-[10px] text-[var(--muted-foreground)]">
                    {metricas.areasOrdenadas[0][1]} processos ({processos.length > 0 ? Math.round((metricas.areasOrdenadas[0][1] / processos.length) * 100) : 0}% do total)
                  </p>
                </div>
              </div>
            )}

            {/* Top Classes Processuais */}
            {metricas.topClasses.length > 0 && (
              <div className="border-t pt-3 mt-2">
                <p className="text-xs font-semibold text-[var(--muted-foreground)] mb-2 flex items-center gap-1">
                  <Gavel className="h-3.5 w-3.5" /> Classes Processuais mais frequentes
                </p>
                <div className="space-y-1.5">
                  {metricas.topClasses.map(([classe, count]) => (
                    <div key={classe} className="flex items-center justify-between text-xs">
                      <span className="text-[var(--card-foreground)] truncate max-w-[70%]">{classe}</span>
                      <span className="font-semibold text-[var(--muted-foreground)]">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ══════ ATALHOS RAPIDOS ══════ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Link href="/processo" className="flex items-center gap-3 rounded-xl border bg-[var(--card)] p-4 hover:shadow-md hover:border-legal-600/30 transition-all group">
          <div className="rounded-lg bg-legal-600/10 p-2.5 group-hover:bg-legal-600/20 transition-colors">
            <FileText className="h-5 w-5 text-legal-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--card-foreground)]">Processos</p>
            <p className="text-xs text-[var(--muted-foreground)]">{processosStats?.total || 0} monitorados</p>
          </div>
        </Link>
        <Link href="/busca" className="flex items-center gap-3 rounded-xl border bg-[var(--card)] p-4 hover:shadow-md hover:border-blue-600/30 transition-all group">
          <div className="rounded-lg bg-blue-500/10 p-2.5 group-hover:bg-blue-500/20 transition-colors">
            <Search className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--card-foreground)]">Busca Unificada</p>
            <p className="text-xs text-[var(--muted-foreground)]">DataJud + DJEN</p>
          </div>
        </Link>
        <Link href="/monitor" className="flex items-center gap-3 rounded-xl border bg-[var(--card)] p-4 hover:shadow-md hover:border-green-600/30 transition-all group">
          <div className="rounded-lg bg-green-500/10 p-2.5 group-hover:bg-green-500/20 transition-colors">
            <Eye className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--card-foreground)]">Monitor</p>
            <p className="text-xs text-[var(--muted-foreground)]">{monitorStats.total_publicacoes || 0} publicacoes</p>
          </div>
        </Link>
        <Link href="/captacao" className="flex items-center gap-3 rounded-xl border bg-[var(--card)] p-4 hover:shadow-md hover:border-amber-600/30 transition-all group">
          <div className="rounded-lg bg-amber-500/10 p-2.5 group-hover:bg-amber-500/20 transition-colors">
            <Zap className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--card-foreground)]">Captacao</p>
            <p className="text-xs text-[var(--muted-foreground)]">{captacaoStats?.captacoes_ativas || 0} ativas</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
