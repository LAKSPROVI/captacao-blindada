"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import {
  CreditCard, Settings, RefreshCw, AlertCircle, Zap, Globe, FileText,
  Search, Brain, ShieldCheck, Bell, BarChart3, Key, Database, Clock,
  CheckCircle2, Activity, TrendingUp, Users, Building2
} from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";

const SYSTEM_FUNCTIONS = [
  { key: "captacao_executar", label: "Captação Automatizada", desc: "Execução de buscas programadas (DataJud + DJEN)", icon: Zap, category: "core" },
  { key: "captacao_criar", label: "Criar Captação", desc: "Criação de nova captação automatizada", icon: Zap, category: "core" },
  { key: "djen_buscar", label: "Busca DJEN", desc: "Consulta ao Diário de Justiça Eletrônico Nacional", icon: Globe, category: "core" },
  { key: "datajud_buscar", label: "Busca DataJud", desc: "Consulta à API pública do CNJ (metadados processuais)", icon: Globe, category: "core" },
  { key: "processo_analisar", label: "Análise de Processo", desc: "Pipeline multi-agentes para análise completa", icon: FileText, category: "core" },
  { key: "busca_pontual", label: "Pesquisa Pontual", desc: "Busca avulsa em fontes externas", icon: Search, category: "core" },
  { key: "ia_classificacao", label: "IA - Classificação", desc: "Classificação jurídica automática via Gemini", icon: Brain, category: "ia" },
  { key: "ia_previsao", label: "IA - Previsão", desc: "Previsão de resultado processual via Gemini", icon: Brain, category: "ia" },
  { key: "ia_resumo", label: "IA - Resumo", desc: "Resumo executivo de publicações via Gemini", icon: Brain, category: "ia" },
  { key: "ia_jurisprudencia", label: "IA - Jurisprudência", desc: "Análise de jurisprudência via Gemini", icon: Brain, category: "ia" },
  { key: "webhook_trigger", label: "Webhook", desc: "Disparo de notificações automáticas", icon: Bell, category: "infra" },
  { key: "backup_criar", label: "Backup", desc: "Criação de backup do banco de dados", icon: Database, category: "infra" },
  { key: "api_key_criar", label: "API Key", desc: "Criação de chave de API para integração", icon: Key, category: "infra" },
  { key: "validacao_cnj", label: "Validação CNJ", desc: "Validação de número de processo CNJ", icon: CheckCircle2, category: "infra" },
  { key: "validacao_oab", label: "Validação OAB", desc: "Validação de número de OAB", icon: CheckCircle2, category: "infra" },
  { key: "monitor_publicacoes", label: "Monitor Publicações", desc: "Monitoramento de publicações no DJEN", icon: Activity, category: "core" },
  { key: "auth_login", label: "Login", desc: "Autenticação de usuário", icon: Users, category: "infra" },
  { key: "admin_usuarios", label: "Gestão Usuários", desc: "Criação e edição de usuários", icon: Users, category: "admin" },
  { key: "admin_tenants", label: "Gestão Cadastros", desc: "Criação e edição de tenants", icon: Building2, category: "admin" },
  { key: "admin_auditoria", label: "Cadeia de Custódia", desc: "Registro de auditoria do sistema", icon: ShieldCheck, category: "admin" },
];

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  core: { label: "Funções Principais", color: "bg-blue-500/10 text-blue-600 border-blue-500/20" },
  ia: { label: "Inteligência Artificial", color: "bg-purple-500/10 text-purple-600 border-purple-500/20" },
  infra: { label: "Infraestrutura", color: "bg-green-500/10 text-green-600 border-green-500/20" },
  admin: { label: "Administração", color: "bg-amber-500/10 text-amber-600 border-amber-500/20" },
};

export default function TarifacaoPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [costs, setCosts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"resumo" | "historico" | "funcoes" | "custos">("resumo");

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
        api.getUsageLogs(100, 0)
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

  const categories = ["core", "ia", "infra", "admin"];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <CreditCard className="w-6 h-6 text-legal-500" />
            Tarifação e Consumo
          </h1>
          <p className="text-[var(--muted-foreground)]">Controle completo de uso, custos e funções do sistema.</p>
        </div>
        <button onClick={fetchData} className="p-2 bg-[var(--secondary)] hover:bg-[var(--secondary)]/80 rounded">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 p-4 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-5 rounded-xl border bg-[var(--card)] shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-blue-500" />
              <h3 className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">Saldo Atual</h3>
            </div>
            <p className="text-2xl font-bold font-mono">{(stats.saldo_atual ?? 0).toLocaleString("pt-BR")} <span className="text-xs font-normal text-[var(--muted-foreground)]">tokens</span></p>
          </div>
          <div className="p-5 rounded-xl border bg-[var(--card)] shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-4 h-4 text-legal-600" />
              <h3 className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">Gasto Mês</h3>
            </div>
            <p className="text-2xl font-bold font-mono text-legal-600">{(stats.total_gasto_mes ?? 0).toLocaleString("pt-BR")} <span className="text-xs font-normal text-[var(--muted-foreground)]">tokens</span></p>
          </div>
          <div className="p-5 rounded-xl border bg-[var(--card)] shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-green-500" />
              <h3 className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">Funções do Sistema</h3>
            </div>
            <p className="text-2xl font-bold font-mono">{SYSTEM_FUNCTIONS.length}</p>
          </div>
          <div className="p-5 rounded-xl border bg-[var(--card)] shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-4 h-4 text-purple-500" />
              <h3 className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">Registros de Uso</h3>
            </div>
            <p className="text-2xl font-bold font-mono">{logs.length}</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {[
          { key: "resumo", label: "Resumo", icon: BarChart3 },
          { key: "funcoes", label: "Funções do Sistema", icon: Zap },
          { key: "historico", label: "Histórico de Uso", icon: Clock },
          ...(isMaster ? [{ key: "custos", label: "Custos (Master)", icon: Settings }] : []),
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

      {/* Tab: Resumo */}
      {activeTab === "resumo" && stats && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Gasto por Função */}
            <div className="border rounded-xl bg-[var(--card)] p-5">
              <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">Gasto por Função</h3>
              {stats.gasto_por_funcao && Object.keys(stats.gasto_por_funcao).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(stats.gasto_por_funcao).map(([func, val]) => {
                    const total = stats.total_gasto_mes || 1;
                    const pct = Math.round((Number(val) / total) * 100);
                    return (
                      <div key={func} className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="font-medium">{func}</span>
                          <span className="font-mono text-[var(--muted-foreground)]">{Number(val).toLocaleString("pt-BR")} t ({pct}%)</span>
                        </div>
                        <div className="h-2 bg-[var(--secondary)] rounded-full overflow-hidden">
                          <div className="h-full bg-legal-600 rounded-full transition-all" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">Sem dados de uso por função.</p>
              )}
            </div>

            {/* Últimos registros */}
            <div className="border rounded-xl bg-[var(--card)] p-5">
              <h3 className="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">Últimos Registros</h3>
              {logs.length > 0 ? (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {logs.slice(0, 10).map((log) => (
                    <div key={log.id} className="flex justify-between items-center p-2 rounded bg-[var(--secondary)]/40 text-sm">
                      <div>
                        <span className="font-medium text-legal-600">{log.function_name}</span>
                        <span className="text-[var(--muted-foreground)] ml-2 text-xs">{new Date(log.data_uso + "Z").toLocaleString("pt-BR")}</span>
                      </div>
                      <span className="font-mono font-bold">{log.tokens_used} t</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">Nenhum registro encontrado.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab: Funções do Sistema */}
      {activeTab === "funcoes" && (
        <div className="space-y-6">
          {categories.map((cat) => {
            const catInfo = CATEGORY_LABELS[cat];
            const funcs = SYSTEM_FUNCTIONS.filter((f) => f.category === cat);
            return (
              <div key={cat}>
                <div className="flex items-center gap-2 mb-3">
                  <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-bold border ${catInfo.color}`}>
                    {catInfo.label}
                  </span>
                  <span className="text-xs text-[var(--muted-foreground)]">{funcs.length} funções</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {funcs.map((f) => {
                    const Icon = f.icon;
                    const costEntry = costs.find((c) => c.function_name === f.key);
                    const usageEntry = stats?.gasto_por_funcao?.[f.key];
                    return (
                      <div key={f.key} className="border rounded-lg bg-[var(--card)] p-4 hover:shadow-sm transition-shadow">
                        <div className="flex items-start gap-3">
                          <div className="p-2 rounded-lg bg-[var(--secondary)]">
                            <Icon className="w-4 h-4 text-legal-600" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-semibold text-[var(--foreground)]">{f.label}</h4>
                            <p className="text-xs text-[var(--muted-foreground)] mt-0.5">{f.desc}</p>
                            <div className="flex items-center gap-3 mt-2">
                              {costEntry && (
                                <span className="text-[10px] font-mono bg-blue-500/10 text-blue-600 px-1.5 py-0.5 rounded">
                                  {costEntry.cost_tokens} t/uso
                                </span>
                              )}
                              {usageEntry && (
                                <span className="text-[10px] font-mono bg-green-500/10 text-green-600 px-1.5 py-0.5 rounded">
                                  {Number(usageEntry).toLocaleString("pt-BR")} t gastos
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tab: Histórico */}
      {activeTab === "historico" && (
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
                    <td className="px-4 py-3 text-[var(--muted-foreground)]">{new Date(log.data_uso + "Z").toLocaleString("pt-BR")}</td>
                    {isMaster && <td className="px-4 py-3 text-[var(--muted-foreground)]">#{log.tenant_id}</td>}
                    <td className="px-4 py-3 font-medium text-legal-600 dark:text-legal-400">{log.function_name}</td>
                    <td className="px-4 py-3 text-right font-mono font-bold">{log.tokens_used}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Custos (Master) */}
      {activeTab === "custos" && isMaster && (
        <div className="space-y-4">
          <p className="text-sm text-[var(--muted-foreground)]">
            Configure o custo em tokens para cada função do sistema. Funções sem custo definido não consomem tokens.
          </p>
          <div className="border rounded-xl bg-[var(--card)] overflow-hidden">
            <table className="w-full text-sm text-left">
              <thead className="bg-[var(--secondary)] text-[var(--muted-foreground)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Função</th>
                  <th className="px-4 py-3 font-medium">Descrição</th>
                  <th className="px-4 py-3 font-medium">Categoria</th>
                  <th className="px-4 py-3 font-medium text-right">Custo (Tokens)</th>
                  <th className="px-4 py-3 font-medium text-right">Ação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {SYSTEM_FUNCTIONS.map((f) => {
                  const costEntry = costs.find((c) => c.function_name === f.key);
                  const catInfo = CATEGORY_LABELS[f.category];
                  return (
                    <tr key={f.key} className="hover:bg-[var(--secondary)]/50">
                      <td className="px-4 py-3 font-medium">{f.label}</td>
                      <td className="px-4 py-3 text-xs text-[var(--muted-foreground)]">{f.desc}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold border ${catInfo.color}`}>
                          {catInfo.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono">{costEntry ? costEntry.cost_tokens : "—"}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => {
                            const n = prompt("Custo em tokens para " + f.label, costEntry?.cost_tokens?.toString() || "0");
                            if (n) handleUpdateCost(f.key, n);
                          }}
                          className="text-xs text-blue-500 hover:text-blue-700 font-semibold"
                        >
                          Editar
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
