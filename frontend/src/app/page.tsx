"use client";

import { useEffect, useState } from "react";
import { api, ProcessoResult, MonitorStats } from "@/lib/api";
import { StatsCard } from "@/components/StatsCard";
import { ProcessoCard } from "@/components/ProcessoCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import {
  FileText,
  Eye,
  Newspaper,
  Activity,
  Search,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function DashboardPage() {
  const router = useRouter();
  const [resultados, setResultados] = useState<ProcessoResult[]>([]);
  const [stats, setStats] = useState<MonitorStats>({});
  const [totalProcessos, setTotalProcessos] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [resultadosData, statsData] = await Promise.allSettled([
        api.getResultados({ limit: 6 }),
        api.getMonitorStats(),
      ]);

      if (resultadosData.status === "fulfilled") {
        const data = resultadosData.value;
        const items = Array.isArray(data) ? (data as ProcessoResult[]) : (data.items || []);
        setResultados(items);
        setTotalProcessos(
          typeof data === "object" && !Array.isArray(data) && "total" in data
            ? (data as { total: number }).total
            : items.length
        );
      }

      if (statsData.status === "fulfilled") {
        setStats(statsData.value);
      }
    } catch (err) {
      console.error("Erro ao carregar dados:", err);
    } finally {
      setIsLoading(false);
    }
  };

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
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Painel</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Visao geral do sistema juridico
        </p>
      </div>

      {/* Quick search */}
      <form onSubmit={handleSearch} className="relative max-w-2xl">
        <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[var(--muted-foreground)]" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Buscar processo por numero CNJ..."
          className="w-full rounded-xl border bg-[var(--card)] py-3 pl-12 pr-4 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20 shadow-sm"
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg bg-legal-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-legal-700 transition-colors"
        >
          Buscar
        </button>
      </form>

      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Processos Analisados"
          value={totalProcessos}
          icon={FileText}
          description="Total no sistema"
        />
        <StatsCard
          title="Monitores Ativos"
          value={stats.monitorados_ativos || 0}
          icon={Eye}
          description={`${stats.total_monitorados || 0} total`}
        />
        <StatsCard
          title="Publicacoes"
          value={stats.total_publicacoes || 0}
          icon={Newspaper}
          description="Encontradas"
        />
        <StatsCard
          title="Sistema"
          value="Online"
          icon={Activity}
          description="Operacional"
        />
      </div>

      {/* Recent results */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            Analises Recentes
          </h2>
          <Link
            href="/processo"
            className="inline-flex items-center gap-1 text-sm font-medium text-legal-600 hover:text-legal-500"
          >
            Ver todos
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {resultados.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {resultados.map((processo, idx) => (
              <ProcessoCard key={processo.numero_processo || idx} processo={processo} />
            ))}
          </div>
        ) : (
          <div className="rounded-lg border bg-[var(--card)] p-12 text-center">
            <FileText className="mx-auto h-12 w-12 text-[var(--muted-foreground)] mb-4" />
            <h3 className="text-lg font-medium text-[var(--card-foreground)] mb-2">
              Nenhuma analise encontrada
            </h3>
            <p className="text-sm text-[var(--muted-foreground)] mb-4">
              Comece analisando um processo para ver os resultados aqui.
            </p>
            <Link
              href="/processo"
              className="inline-flex items-center gap-2 rounded-lg bg-legal-600 px-4 py-2 text-sm font-medium text-white hover:bg-legal-700"
            >
              <Search className="h-4 w-4" />
              Analisar Processo
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
