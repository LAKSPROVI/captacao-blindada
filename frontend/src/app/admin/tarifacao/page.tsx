"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { CreditCard, Settings, RefreshCw, AlertCircle } from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";

export default function TarifacaoPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [costs, setCosts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isMaster = user?.role === "master";

  useEffect(() => {
    fetchData();
  }, [user]);

  const fetchData = async () => {
    try {
      if (!user) return;
      setIsLoading(true);
      setError(null);
      
      const [statsData, logsData] = await Promise.all([
        api.getBillingStats(),
        api.getUsageLogs(50, 0)
      ]);
      setStats(statsData);
      setLogs(logsData);
      
      if (isMaster) {
        const costsData = await api.getFunctionCosts();
        setCosts(costsData);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Erro ao carregar dados de tarifação");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateCost = async (functionName: string, newCostTokens: string) => {
    const cost = parseInt(newCostTokens, 10);
    if (isNaN(cost)) return;
    try {
      await api.updateFunctionCost(functionName, { cost_tokens: cost });
      alert("Custo atualizado com sucesso!");
      fetchData();
    } catch (e: any) {
      alert("Erro ao atualizar: " + (e?.response?.data?.detail || e.message));
    }
  };

  if (isLoading && !stats) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <CreditCard className="w-6 h-6 text-legal-500" />
            Tarifação e Consumo
          </h1>
          <p className="text-[var(--muted-foreground)]">Acompanhe os gastos de tokens em uso de inteligência artificial e requisições no sistema.</p>
        </div>
        <button
          onClick={fetchData}
          className="p-2 bg-[var(--secondary)] hover:bg-[var(--secondary)]/80 rounded"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 p-4 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-6 rounded-xl border bg-[var(--card)] shadow-sm">
            <h3 className="text-sm font-medium text-[var(--muted-foreground)] uppercase tracking-wider mb-2">Saldo Atual</h3>
            <p className="text-3xl font-bold font-mono">{stats.saldo_atual.toLocaleString("pt-BR")} <span className="text-sm font-normal text-[var(--muted-foreground)]">tokens</span></p>
          </div>
          <div className="p-6 rounded-xl border bg-[var(--card)] shadow-sm">
            <h3 className="text-sm font-medium text-[var(--muted-foreground)] uppercase tracking-wider mb-2">Gasto Mês Atual</h3>
            <p className="text-3xl font-bold font-mono text-legal-600 dark:text-legal-400">{stats.total_gasto_mes.toLocaleString("pt-BR")} <span className="text-sm font-normal text-[var(--muted-foreground)]">tokens</span></p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-4">
          <h2 className="text-xl font-semibold">Histórico de Uso</h2>
          <div className="border rounded-xl bg-[var(--card)] overflow-hidden">
            <table className="w-full text-sm text-left">
              <thead className="bg-[var(--secondary)] text-[var(--muted-foreground)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Data/Hora</th>
                  {isMaster && <th className="px-4 py-3 font-medium">Tenant</th>}
                  <th className="px-4 py-3 font-medium">Função</th>
                  <th className="px-4 py-3 font-medium text-right">Tokens</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-[var(--muted-foreground)]">Nenhum registro encontrado.</td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-[var(--secondary)]/50">
                      <td className="px-4 py-3">{new Date(log.data_uso + 'Z').toLocaleString('pt-BR')}</td>
                      {isMaster && <td className="px-4 py-3">Tenant #{log.tenant_id}</td>}
                      <td className="px-4 py-3 font-medium text-legal-600 dark:text-legal-400">{log.function_name}</td>
                      <td className="px-4 py-3 text-right font-mono font-medium">{log.tokens_used}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Gasto por Função</h2>
          <div className="border rounded-xl bg-[var(--card)] p-4 space-y-3">
            {stats && Object.keys(stats.gasto_por_funcao).length > 0 ? (
              Object.entries(stats.gasto_por_funcao).map(([func, val]) => (
                <div key={func} className="flex justify-between items-center bg-[var(--secondary)]/40 p-3 rounded-lg border border-[var(--border)]">
                  <span className="font-medium text-legal-600 dark:text-legal-400">{func}</span>
                  <span className="font-mono font-bold">{Number(val).toLocaleString("pt-BR")} t</span>
                </div>
              ))
            ) : (
                <p className="text-sm text-[var(--muted-foreground)]">Sem dados de uso por função.</p>
            )}
          </div>

          {isMaster && (
            <div className="mt-8 space-y-4">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <Settings className="w-5 h-5 text-legal-500" />
                Custos (Master)
              </h2>
              <div className="border rounded-xl bg-[var(--card)] overflow-hidden">
                <table className="w-full text-sm text-left">
                  <thead className="bg-[var(--secondary)] text-[var(--muted-foreground)]">
                    <tr>
                      <th className="px-4 py-3 font-medium">Função</th>
                      <th className="px-4 py-3 font-medium">Custo Atual (Tokens)</th>
                      <th className="px-4 py-3 font-medium">Alterar</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {costs.map((c) => (
                      <tr key={c.function_name}>
                        <td className="px-4 py-3 font-medium">{c.function_name}</td>
                        <td className="px-4 py-3 font-mono">{c.cost_tokens}</td>
                        <td className="px-4 py-3">
                          <button onClick={() => {
                            const n = prompt("Novo custo em tokens para " + c.function_name, c.cost_tokens.toString());
                            if(n) handleUpdateCost(c.function_name, n);
                          }} className="text-xs text-blue-500 hover:text-blue-700 font-semibold underline">Editar</button>
                        </td>
                      </tr>
                    ))}
                    {costs.length === 0 && (
                      <tr>
                        <td colSpan={3} className="px-4 py-4 text-center text-xs text-[var(--muted-foreground)]">Nenhuma função definida. Adicione através do banco ou execução.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
