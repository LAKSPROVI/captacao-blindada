"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import {
  ShieldCheck, ShieldAlert, Cpu, RefreshCw, KeyRound,
  Download, FileText, BarChart3, Filter, Clock, Users,
  Activity, Eye, ChevronDown, ChevronUp
} from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { cn } from "@/lib/utils";

const ACTION_COLORS: Record<string, string> = {
  POST: "bg-green-500/15 text-green-600 border-green-500/20",
  PUT: "bg-blue-500/15 text-blue-600 border-blue-500/20",
  DELETE: "bg-red-500/15 text-red-600 border-red-500/20",
  GET: "bg-gray-500/10 text-gray-500 border-gray-500/20",
  LOGIN: "bg-purple-500/15 text-purple-600 border-purple-500/20",
  REGISTER: "bg-amber-500/15 text-amber-600 border-amber-500/20",
};

export default function AuditoriaPage() {
  const { user } = useAuth();
  const [logs, setLogs] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyStatus, setVerifyStatus] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"logs" | "stats">("logs");
  const [filterAction, setFilterAction] = useState("");
  const [filterEntity, setFilterEntity] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    fetchData();
  }, [user]);

  const fetchData = async () => {
    try {
      if (!user || user.role !== "master") return;
      setIsLoading(true);
      const [logsData, statsData] = await Promise.allSettled([
        api.getAuditLogs(500, 0),
        api.client.get("/api/audit/stats").then((r: any) => r.data),
      ]);
      if (logsData.status === "fulfilled") setLogs(logsData.value);
      if (statsData.status === "fulfilled") setStats(statsData.value);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async () => {
    try {
      setIsVerifying(true);
      setVerifyStatus(null);
      const data = await api.verifyAuditChain();
      setVerifyStatus(data);
    } catch (e: any) {
      setVerifyStatus({ status: "error", message: e?.response?.data?.detail || e.message });
    } finally {
      setIsVerifying(false);
    }
  };

  const handleExportCSV = () => {
    const token = localStorage.getItem("token");
    window.open(`${process.env.NEXT_PUBLIC_API_URL || "https://captacao.jurislaw.com.br"}/api/audit/export/csv?limit=10000`, "_blank");
  };

  const handleExportJSON = () => {
    window.open(`${process.env.NEXT_PUBLIC_API_URL || "https://captacao.jurislaw.com.br"}/api/audit/export/json?limit=10000`, "_blank");
  };

  const filteredLogs = logs.filter((l) => {
    if (filterAction && !l.action.toLowerCase().includes(filterAction.toLowerCase())) return false;
    if (filterEntity && !l.entity_type.toLowerCase().includes(filterEntity.toLowerCase())) return false;
    return true;
  });

  if (!user || user.role !== "master") {
    return <div className="p-6 text-center text-red-500 font-bold">Acesso restrito ao Master.</div>;
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-green-500" />
            Cadeia de Custódia
          </h1>
          <p className="text-[var(--muted-foreground)]">
            Log imutável com hash-chain SHA-256. Registra automaticamente todas as ações do sistema.
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={fetchData} className="p-2 bg-[var(--secondary)] hover:bg-[var(--secondary)]/80 rounded" title="Atualizar">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleVerify}
            disabled={isVerifying}
            className="flex items-center gap-2 px-3 py-2 bg-[var(--secondary)] hover:bg-[var(--secondary)]/80 border border-[var(--border)] rounded-lg text-sm font-medium transition-colors"
          >
            {isVerifying ? <LoadingSpinner size="sm" /> : <KeyRound className="w-4 h-4" />}
            Verificar Integridade
          </button>
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Download className="w-4 h-4" />
            CSV
          </button>
          <button
            onClick={handleExportJSON}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Download className="w-4 h-4" />
            JSON
          </button>
        </div>
      </div>

      {/* Verificação */}
      {verifyStatus && (
        <div className={cn(
          "p-4 border rounded-xl flex items-start gap-4",
          verifyStatus.status === "ok" ? "bg-green-500/10 border-green-500/30 text-green-700 dark:text-green-400" : "bg-red-500/10 border-red-500/50 text-red-600 dark:text-red-400"
        )}>
          <div className="pt-0.5">
            {verifyStatus.status === "ok" ? <ShieldCheck className="w-6 h-6" /> : <ShieldAlert className="w-6 h-6" />}
          </div>
          <div className="flex-1">
            <h3 className="font-bold">{verifyStatus.status === "ok" ? "Integridade Confirmada" : "Violação Detectada!"}</h3>
            <p className="text-sm mt-1">{verifyStatus.message}</p>
            {verifyStatus.total_verificados && (
              <p className="text-xs mt-1 opacity-70">{verifyStatus.total_verificados} registros verificados</p>
            )}
            {verifyStatus.erros && (
              <div className="mt-3 text-xs bg-red-950/20 p-3 rounded overflow-x-auto">
                <code className="text-red-300">{JSON.stringify(verifyStatus.erros, null, 2)}</code>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl border bg-[var(--card)]">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-blue-500" />
              <span className="text-xs font-semibold text-[var(--muted-foreground)] uppercase">Total Registros</span>
            </div>
            <p className="text-2xl font-bold font-mono">{stats.total?.toLocaleString("pt-BR")}</p>
          </div>
          <div className="p-4 rounded-xl border bg-[var(--card)]">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-4 h-4 text-green-500" />
              <span className="text-xs font-semibold text-[var(--muted-foreground)] uppercase">Hoje</span>
            </div>
            <p className="text-2xl font-bold font-mono">{stats.hoje?.toLocaleString("pt-BR")}</p>
          </div>
          <div className="p-4 rounded-xl border bg-[var(--card)]">
            <div className="flex items-center gap-2 mb-1">
              <BarChart3 className="w-4 h-4 text-purple-500" />
              <span className="text-xs font-semibold text-[var(--muted-foreground)] uppercase">Tipos de Ação</span>
            </div>
            <p className="text-2xl font-bold font-mono">{stats.por_acao ? Object.keys(stats.por_acao).length : 0}</p>
          </div>
          <div className="p-4 rounded-xl border bg-[var(--card)]">
            <div className="flex items-center gap-2 mb-1">
              <Users className="w-4 h-4 text-amber-500" />
              <span className="text-xs font-semibold text-[var(--muted-foreground)] uppercase">Usuários Ativos</span>
            </div>
            <p className="text-2xl font-bold font-mono">{stats.por_usuario ? Object.keys(stats.por_usuario).length : 0}</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {[
          { key: "logs", label: "Registros", icon: FileText },
          { key: "stats", label: "Estatísticas", icon: BarChart3 },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? "border-legal-600 text-legal-600"
                : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab: Logs */}
      {activeTab === "logs" && (
        <div className="space-y-4">
          {/* Filtros */}
          <div className="flex gap-3 flex-wrap">
            <div className="relative">
              <Filter className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" />
              <input
                type="text"
                placeholder="Filtrar ação..."
                value={filterAction}
                onChange={(e) => setFilterAction(e.target.value)}
                className="pl-9 pr-4 py-2 rounded-lg border bg-[var(--background)] text-sm w-48 focus:outline-none focus:ring-1 focus:ring-legal-500"
              />
            </div>
            <div className="relative">
              <Filter className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" />
              <input
                type="text"
                placeholder="Filtrar entidade..."
                value={filterEntity}
                onChange={(e) => setFilterEntity(e.target.value)}
                className="pl-9 pr-4 py-2 rounded-lg border bg-[var(--background)] text-sm w-48 focus:outline-none focus:ring-1 focus:ring-legal-500"
              />
            </div>
            <span className="text-sm text-[var(--muted-foreground)] self-center">
              {filteredLogs.length} de {logs.length} registros
            </span>
          </div>

          {/* Tabela */}
          <div className="border rounded-xl bg-[var(--card)] overflow-hidden shadow-sm">
            <div className="p-3 border-b bg-[var(--secondary)]/30 flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
              <Cpu className="w-3.5 h-3.5" />
              Protocolo hash-chain SHA-256. Cada registro é encadeado ao anterior.
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-[var(--secondary)] text-[var(--muted-foreground)] sticky top-0">
                  <tr>
                    <th className="px-4 py-3 font-medium w-24">ID / Data</th>
                    <th className="px-4 py-3 font-medium w-20">Ação</th>
                    <th className="px-4 py-3 font-medium">Entidade / Alvo</th>
                    <th className="px-4 py-3 font-medium w-28">Origem</th>
                    <th className="px-4 py-3 font-medium w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {filteredLogs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-[var(--muted-foreground)]">Nenhum evento auditado.</td>
                    </tr>
                  ) : (
                    filteredLogs.map((log) => {
                      const actionColor = ACTION_COLORS[log.action] || ACTION_COLORS["GET"];
                      const isExpanded = expandedId === log.id;
                      return (
                        <tr key={log.id} className="hover:bg-[var(--secondary)]/50 transition-colors">
                          <td className="px-4 py-3">
                            <div className="font-mono text-xs font-bold">#{log.id}</div>
                            <div className="text-[10px] text-[var(--muted-foreground)] mt-0.5">
                              {new Date(log.criado_em + "Z").toLocaleString("pt-BR")}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold border ${actionColor}`}>
                              {log.action}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-xs font-medium truncate max-w-[300px]">{log.entity_type}</div>
                            {log.entity_id && <div className="text-[10px] text-[var(--muted-foreground)] mt-0.5">{log.entity_id}</div>}
                            {isExpanded && log.details && (
                              <div className="mt-2 p-2 rounded bg-[var(--secondary)]/60 text-[10px] font-mono max-w-[400px] overflow-x-auto whitespace-pre-wrap">
                                {log.details}
                              </div>
                            )}
                            {isExpanded && (
                              <div className="mt-1 text-[9px] font-mono text-[var(--muted-foreground)] opacity-60 truncate max-w-[400px]">
                                SHA-256: {log.data_hash}
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3 text-[10px] text-[var(--muted-foreground)]">
                            <div>T:{log.tenant_id ?? "SYS"} U:{log.user_id ?? "ROOT"}</div>
                            {log.ip_address && <div className="opacity-50 mt-0.5">{log.ip_address}</div>}
                          </td>
                          <td className="px-4 py-3">
                            <button
                              onClick={() => setExpandedId(isExpanded ? null : log.id)}
                              className="p-1 hover:bg-[var(--secondary)] rounded transition-colors"
                            >
                              {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Estatísticas */}
      {activeTab === "stats" && stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Por Ação */}
          <div className="border rounded-xl bg-[var(--card)] p-5">
            <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">Por Tipo de Ação</h3>
            <div className="space-y-2">
              {stats.por_acao && Object.entries(stats.por_acao).map(([action, count]) => {
                const pct = Math.round((Number(count) / (stats.total || 1)) * 100);
                const color = ACTION_COLORS[action] || ACTION_COLORS["GET"];
                return (
                  <div key={action} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold border ${color}`}>{action}</span>
                      <span className="font-mono text-[var(--muted-foreground)]">{Number(count).toLocaleString("pt-BR")} ({pct}%)</span>
                    </div>
                    <div className="h-1.5 bg-[var(--secondary)] rounded-full overflow-hidden">
                      <div className="h-full bg-legal-600 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Por Entidade */}
          <div className="border rounded-xl bg-[var(--card)] p-5">
            <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">Por Entidade</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {stats.por_entidade && Object.entries(stats.por_entidade).map(([entity, count]) => (
                <div key={entity} className="flex justify-between items-center p-2 rounded bg-[var(--secondary)]/40 text-sm">
                  <span className="font-mono text-xs truncate max-w-[250px]">{entity}</span>
                  <span className="font-mono font-bold text-xs">{Number(count).toLocaleString("pt-BR")}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Por Usuário */}
          <div className="border rounded-xl bg-[var(--card)] p-5 md:col-span-2">
            <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">Por Usuário</h3>
            <div className="flex flex-wrap gap-3">
              {stats.por_usuario && Object.entries(stats.por_usuario).map(([uid, count]) => (
                <div key={uid} className="flex items-center gap-2 p-3 rounded-lg border bg-[var(--secondary)]/30">
                  <div className="w-8 h-8 rounded-full bg-legal-600 text-white flex items-center justify-center text-xs font-bold">
                    {uid === "null" ? "S" : uid.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="text-sm font-medium">{uid === "null" ? "Sistema" : `User #${uid}`}</div>
                    <div className="text-xs text-[var(--muted-foreground)]">{Number(count).toLocaleString("pt-BR")} ações</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
