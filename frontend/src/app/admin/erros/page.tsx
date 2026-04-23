"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { AlertTriangle, CheckCircle, RefreshCw, Terminal, Clock, Search, BarChart3, Filter, Download } from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Skeleton } from "@/components/Skeleton";
import { cn } from "@/lib/utils";

export default function ErrosPage() {
  const { user } = useAuth();
  const [erros, setErros] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterMode, setFilterMode] = useState<"aberto" | "resolvido" | "all">("aberto");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState("");

  useEffect(() => {
    fetchErros();
  }, [user, filterMode]);

  const fetchErros = async () => {
    try {
      if (!user || user.role !== "master") return;
      setIsLoading(true);
      const data = await api.getSystemErrors(filterMode, 500, 0);
      setErros(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResolve = async (id: number) => {
    try {
      await api.resolveSystemError(id);
      fetchErros();
    } catch (e: any) {
      alert("Erro ao marcar como resolvido: " + (e?.response?.data?.detail || e.message));
    }
  };

  if (!user || user.role !== "master") {
    return <div className="p-6 text-center text-red-500 font-bold">Acesso restrito.</div>;
  }

  // Filtros
  const filteredErros = erros.filter((e) => {
    if (searchTerm && !e.error_message?.toLowerCase().includes(searchTerm.toLowerCase()) && !e.function_name?.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    if (filterType && e.error_type !== filterType) return false;
    return true;
  });

  // Contadores
  const totalAbertos = erros.filter((e) => e.status === "aberto").length;
  const totalResolvidos = erros.filter((e) => e.status === "resolvido").length;
  const errorTypes = [...new Set(erros.map((e) => e.error_type).filter(Boolean))];

  // Agrupamento por tipo
  const groupedByType: Record<string, number> = {};
  erros.forEach((e) => {
    const t = e.error_type || "Desconhecido";
    groupedByType[t] = (groupedByType[t] || 0) + 1;
  });

  if (isLoading) {
    return <div className="p-6"><Skeleton variant="table" lines={5} /></div>;
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-red-500" />
            Erros do Sistema
          </h1>
          <p className="text-[var(--muted-foreground)]">Monitoramento de falhas em requisições, agentes de IA e background.</p>
        </div>
        <button onClick={fetchErros} className="p-2 bg-[var(--secondary)] hover:bg-[var(--secondary)]/80 rounded" title="Atualizar">
          <RefreshCw className={cn("w-5 h-5", isLoading && "animate-spin")} />
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl border bg-[var(--card)]">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <span className="text-xs font-semibold text-[var(--muted-foreground)] uppercase">Abertos</span>
          </div>
          <p className="text-2xl font-bold font-mono text-red-600">{totalAbertos}</p>
        </div>
        <div className="p-4 rounded-xl border bg-[var(--card)]">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-xs font-semibold text-[var(--muted-foreground)] uppercase">Resolvidos</span>
          </div>
          <p className="text-2xl font-bold font-mono text-green-600">{totalResolvidos}</p>
        </div>
        <div className="p-4 rounded-xl border bg-[var(--card)]">
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-4 h-4 text-blue-500" />
            <span className="text-xs font-semibold text-[var(--muted-foreground)] uppercase">Total</span>
          </div>
          <p className="text-2xl font-bold font-mono">{erros.length}</p>
        </div>
        <div className="p-4 rounded-xl border bg-[var(--card)]">
          <div className="flex items-center gap-2 mb-1">
            <Filter className="w-4 h-4 text-purple-500" />
            <span className="text-xs font-semibold text-[var(--muted-foreground)] uppercase">Tipos</span>
          </div>
          <p className="text-2xl font-bold font-mono">{errorTypes.length}</p>
        </div>
      </div>

      {/* Agrupamento por tipo */}
      {Object.keys(groupedByType).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(groupedByType).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
            <button
              key={type}
              onClick={() => setFilterType(filterType === type ? "" : type)}
              className={cn(
                "px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors",
                filterType === type
                  ? "bg-red-500/20 border-red-500/40 text-red-600"
                  : "bg-[var(--secondary)] border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/80"
              )}
            >
              {type} ({count})
            </button>
          ))}
          {filterType && (
            <button onClick={() => setFilterType("")} className="px-3 py-1.5 rounded-full text-xs font-semibold text-blue-500 hover:underline">
              Limpar filtro
            </button>
          )}
        </div>
      )}

      {/* Filtros */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex gap-2">
          {(["aberto", "resolvido", "all"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setFilterMode(mode)}
              className={cn(
                "px-4 py-1.5 rounded-md text-sm font-medium transition-colors border",
                filterMode === mode
                  ? mode === "aberto" ? "bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400"
                    : mode === "resolvido" ? "bg-green-500/10 border-green-500/30 text-green-700 dark:text-green-400"
                    : "bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400"
                  : "bg-[var(--card)] border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"
              )}
            >
              {mode === "aberto" ? "Abertos" : mode === "resolvido" ? "Resolvidos" : "Todos"}
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" />
          <input
            type="text"
            placeholder="Buscar por mensagem ou função..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-md border border-[var(--border)] bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-legal-500"
          />
        </div>
        <span className="text-sm text-[var(--muted-foreground)] self-center">{filteredErros.length} erros</span>
      </div>

      {/* Lista */}
      <div className="space-y-3">
        {filteredErros.length === 0 ? (
          <div className="p-8 border border-dashed rounded-xl flex flex-col items-center justify-center text-[var(--muted-foreground)] bg-[var(--card)]">
            <CheckCircle className="w-12 h-12 text-green-500/50 mb-3" />
            <p>Nenhum erro no filtro selecionado.</p>
          </div>
        ) : (
          filteredErros.map((erro) => (
            <div key={erro.id} className={cn(
              "p-5 border rounded-xl overflow-hidden shadow-sm transition-colors",
              erro.status === "aberto" ? "bg-red-950/10 border-red-900/30 dark:bg-red-950/20" : "bg-[var(--card)] border-[var(--border)] opacity-60"
            )}>
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-3">
                  <div className={cn("p-2 rounded-lg", erro.status === "aberto" ? "bg-red-500/20 text-red-500" : "bg-green-500/20 text-green-500")}>
                    {erro.status === "aberto" ? <AlertTriangle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5" />}
                  </div>
                  <div>
                    <h3 className={cn("font-bold", erro.status === "aberto" && "text-red-600 dark:text-red-400")}>
                      {erro.error_type} <span className="font-normal text-[var(--muted-foreground)]">em</span> {erro.function_name}
                    </h3>
                    <div className="flex items-center gap-4 text-xs font-mono text-[var(--muted-foreground)] mt-1">
                      <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(erro.criado_em + "Z").toLocaleString("pt-BR")}</span>
                      {erro.tenant_id && <span>T:{erro.tenant_id}</span>}
                      {erro.user_id && <span>U:{erro.user_id}</span>}
                      <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-bold uppercase", erro.status === "aberto" ? "bg-red-500/20 text-red-600" : "bg-green-500/20 text-green-600")}>
                        {erro.status}
                      </span>
                    </div>
                  </div>
                </div>
                {erro.status === "aberto" && (
                  <button
                    onClick={() => handleResolve(erro.id)}
                    className="px-3 py-1.5 bg-green-600 text-white hover:bg-green-700 rounded text-xs font-medium uppercase tracking-wider transition-colors shadow"
                  >
                    Resolver
                  </button>
                )}
              </div>
              <div className="text-sm font-medium mb-3 pl-12 text-[var(--foreground)]">{erro.error_message}</div>
              {erro.stack_trace && (
                <div className="mt-3 pl-12">
                  <details className="group">
                    <summary className="text-xs font-medium text-blue-500 cursor-pointer flex items-center gap-1 mb-2 hover:underline">
                      <Terminal className="w-3 h-3" /> Stack Trace
                    </summary>
                    <pre className="p-4 bg-black/80 dark:bg-black border border-black/20 text-[10px] text-green-400 font-mono overflow-x-auto rounded-lg shadow-inner max-h-60 overflow-y-auto">
                      {erro.stack_trace}
                    </pre>
                  </details>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
