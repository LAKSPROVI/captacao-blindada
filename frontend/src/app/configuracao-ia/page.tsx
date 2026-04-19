"use client";

import React, { useState, useEffect, useCallback } from "react";
import { api, AIConfig, AIProvider } from "@/lib/api";
import {
  Bot,
  Settings2,
  CheckCircle2,
  XCircle,
  Save,
  RefreshCcw,
  Cpu,
  BrainCircuit,
  Hash,
  FileText,
  Gavel,
  Zap,
  AlertTriangle,
  ChevronDown,
  Sparkles,
  KeyRound,
  ToggleLeft,
  ToggleRight,
  Activity,
} from "lucide-react";

// ── Mapeamentos ──────────────────────────────────────────────────────────────

const FUNCTION_ICONS: Record<string, React.ElementType> = {
  classificacao: Hash,
  previsao: BrainCircuit,
  resumo: FileText,
  jurisprudencia: Gavel,
};

const FUNCTION_LABELS: Record<string, string> = {
  classificacao: "Classificação Jurídica",
  previsao: "Previsão de Resultado",
  resumo: "Resumo Executivo",
  jurisprudencia: "Análise de Jurisprudência",
};

const FUNCTION_DESCRIPTIONS: Record<string, string> = {
  classificacao: "Classifica automaticamente o tipo e área de atuação de cada processo.",
  previsao: "Estima a probabilidade de resultado favorável baseado em jurisprudência.",
  resumo: "Gera resumos executivos das publicações e movimentações processuais.",
  jurisprudencia: "Analisa e correlaciona jurisprudência relevante para cada caso.",
};

const PROVIDER_COLORS: Record<string, string> = {
  openai: "bg-emerald-500/15 text-emerald-600 border-emerald-500/30",
  anthropic: "bg-orange-500/15 text-orange-600 border-orange-500/30",
  gemini: "bg-blue-500/15 text-blue-600 border-blue-500/30",
  google: "bg-blue-500/15 text-blue-600 border-blue-500/30",
  ollama: "bg-purple-500/15 text-purple-600 border-purple-500/30",
  deepseek: "bg-cyan-500/15 text-cyan-600 border-cyan-500/30",
};

// ── Componente principal ─────────────────────────────────────────────────────

export default function AIConfigPage() {
  const [configs, setConfigs] = useState<AIConfig[]>([]);
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [testingKey, setTestingKey] = useState<string | null>(null);
  const [message, setMessage] = useState<{
    type: "success" | "error" | "warning";
    text: string;
  } | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [configsData, providersData] = await Promise.all([
        api.getAIConfigs(),
        api.getAvailableAIModels(),
      ]);
      setConfigs(configsData);
      setProviders(providersData);
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: "Falha ao carregar configurações de IA" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleUpdate = async (config: AIConfig) => {
    try {
      setSavingKey(config.function_key);
      await api.updateAIConfig(config.function_key, config);
      setMessage({
        type: "success",
        text: `${FUNCTION_LABELS[config.function_key] || config.function_key} atualizado com sucesso!`,
      });
      setTimeout(() => setMessage(null), 4000);
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: "Erro ao salvar configuração" });
    } finally {
      setSavingKey(null);
    }
  };

  const handleTest = async (config: AIConfig) => {
    try {
      setTestingKey(config.function_key);
      const result = await api.testAIConfig(config);
      setMessage({
        type: result.status as "success" | "error" | "warning",
        text: result.message + (result.response ? ` · ${result.response}` : ""),
      });
      if (result.status === "success") setTimeout(() => setMessage(null), 4000);
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: "Erro ao testar conexão" });
    } finally {
      setTestingKey(null);
    }
  };

  const updateLocalConfig = (key: string, field: keyof AIConfig, value: unknown) => {
    setConfigs((prev) =>
      prev.map((c) => (c.function_key === key ? { ...c, [field]: value } : c))
    );
  };

  // ── Contadores de status ────────────────────────────────────────────────
  const enabledCount = configs.filter((c) => c.enabled).length;
  const totalCount = configs.length;

  // ── Loading ─────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-legal-600/10 flex items-center justify-center">
              <Bot className="w-8 h-8 text-legal-600" />
            </div>
            <div className="absolute -top-1 -right-1 w-5 h-5 bg-legal-600 rounded-full animate-pulse" />
          </div>
          <p className="text-sm text-[var(--muted-foreground)] animate-pulse">Carregando configurações de IA...</p>
        </div>
      </div>
    );
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-legal-600/10 border border-legal-600/20">
            <Sparkles className="w-7 h-7 text-legal-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[var(--foreground)]">IA & Modelos</h1>
            <p className="text-sm text-[var(--muted-foreground)]">
              Configure os motores de inteligência artificial para cada função do sistema
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Status geral */}
          <div className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm">
            <Activity className="w-4 h-4 text-legal-600" />
            <span className="text-[var(--foreground)] font-medium">
              {enabledCount}/{totalCount} ativos
            </span>
          </div>
          <button
            onClick={loadData}
            className="inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors"
          >
            <RefreshCcw className="w-4 h-4" />
            Atualizar
          </button>
        </div>
      </div>

      {/* ── Banner de mensagem ── */}
      {message && (
        <div
          className={`flex items-start gap-3 rounded-xl border p-4 text-sm ${
            message.type === "success"
              ? "bg-green-500/10 border-green-500/20 text-green-700 dark:text-green-400"
              : message.type === "warning"
              ? "bg-amber-500/10 border-amber-500/20 text-amber-700 dark:text-amber-400"
              : "bg-red-500/10 border-red-500/20 text-red-700 dark:text-red-400"
          }`}
        >
          {message.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
          ) : message.type === "warning" ? (
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-5 h-5 shrink-0 mt-0.5" />
          )}
          <span className="flex-1 leading-relaxed">{message.text}</span>
          <button
            onClick={() => setMessage(null)}
            className="text-current opacity-50 hover:opacity-100 transition-opacity text-lg leading-none"
          >
            ×
          </button>
        </div>
      )}

      {/* ── Provedores disponíveis ── */}
      {providers.length > 0 && (
        <div className="rounded-xl border bg-[var(--card)] p-4">
          <p className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-3">
            Provedores disponíveis
          </p>
          <div className="flex flex-wrap gap-2">
            {providers.map((p) => {
              const colorClass =
                PROVIDER_COLORS[p.id.toLowerCase()] ||
                "bg-gray-500/10 text-gray-600 border-gray-500/20";
              return (
                <div
                  key={p.id}
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${colorClass}`}
                >
                  <Cpu className="w-3 h-3" />
                  {p.name}
                  <span className="opacity-60">({p.models.length} modelos)</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Grid de configurações ── */}
      {configs.length === 0 ? (
        <div className="rounded-xl border bg-[var(--card)] p-12 text-center">
          <Bot className="w-12 h-12 text-[var(--muted-foreground)] mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-[var(--card-foreground)] mb-2">
            Nenhuma configuração encontrada
          </h3>
          <p className="text-sm text-[var(--muted-foreground)]">
            As configurações de IA serão criadas automaticamente na primeira execução.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          {configs.map((config) => {
            const Icon = FUNCTION_ICONS[config.function_key] || Cpu;
            const provider = providers.find((p) => p.id === config.provider);
            const providerColor =
              PROVIDER_COLORS[config.provider?.toLowerCase() || ""] ||
              "bg-gray-500/10 text-gray-600 border-gray-500/20";
            const isSaving = savingKey === config.function_key;
            const isTesting = testingKey === config.function_key;

            return (
              <div
                key={config.function_key}
                className={`rounded-xl border bg-[var(--card)] overflow-hidden transition-all duration-200 hover:shadow-md ${
                  config.enabled
                    ? "border-[var(--border)] hover:border-legal-600/40"
                    : "border-[var(--border)] opacity-70"
                }`}
              >
                {/* Card header */}
                <div className="flex items-start justify-between p-5 border-b border-[var(--border)]">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2.5 rounded-xl ${
                        config.enabled
                          ? "bg-legal-600/10 border border-legal-600/20"
                          : "bg-[var(--secondary)] border border-[var(--border)]"
                      }`}
                    >
                      <Icon
                        className={`w-5 h-5 ${
                          config.enabled ? "text-legal-600" : "text-[var(--muted-foreground)]"
                        }`}
                      />
                    </div>
                    <div>
                      <h3 className="font-semibold text-[var(--card-foreground)]">
                        {FUNCTION_LABELS[config.function_key] || config.function_key}
                      </h3>
                      <p className="text-xs text-[var(--muted-foreground)] mt-0.5 max-w-xs">
                        {FUNCTION_DESCRIPTIONS[config.function_key] || ""}
                      </p>
                    </div>
                  </div>

                  {/* Toggle on/off */}
                  <button
                    onClick={() =>
                      updateLocalConfig(config.function_key, "enabled", !config.enabled)
                    }
                    className={`shrink-0 p-1 rounded-lg transition-colors ${
                      config.enabled
                        ? "text-legal-600 hover:bg-legal-600/10"
                        : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"
                    }`}
                    title={config.enabled ? "Desativar" : "Ativar"}
                  >
                    {config.enabled ? (
                      <ToggleRight className="w-8 h-8" />
                    ) : (
                      <ToggleLeft className="w-8 h-8" />
                    )}
                  </button>
                </div>

                {/* Card body */}
                <div className="p-5 space-y-4">
                  {/* Provedor + Modelo */}
                  <div className="grid grid-cols-2 gap-3">
                    {/* Provedor */}
                    <div>
                      <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-1.5 block">
                        Provedor
                      </label>
                      <div className="relative">
                        <select
                          className="w-full appearance-none rounded-lg border bg-[var(--background)] px-3 py-2 pr-8 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20 transition-colors disabled:opacity-50"
                          value={config.provider}
                          disabled={!config.enabled}
                          onChange={(e) =>
                            updateLocalConfig(config.function_key, "provider", e.target.value)
                          }
                        >
                          {providers.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.name}
                            </option>
                          ))}
                        </select>
                        <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--muted-foreground)] pointer-events-none" />
                      </div>
                      {/* Badge do provedor selecionado */}
                      <div className={`mt-1.5 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold ${providerColor}`}>
                        <Zap className="w-2.5 h-2.5" />
                        {config.provider}
                      </div>
                    </div>

                    {/* Modelo */}
                    <div>
                      <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-1.5 block">
                        Modelo
                      </label>
                      <div className="relative">
                        <select
                          className="w-full appearance-none rounded-lg border bg-[var(--background)] px-3 py-2 pr-8 text-sm text-[var(--foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20 transition-colors disabled:opacity-50"
                          value={config.model_name}
                          disabled={!config.enabled}
                          onChange={(e) =>
                            updateLocalConfig(config.function_key, "model_name", e.target.value)
                          }
                        >
                          {provider?.models.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                          {!provider?.models.includes(config.model_name) && (
                            <option value={config.model_name}>
                              {config.model_name} (Custom)
                            </option>
                          )}
                        </select>
                        <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--muted-foreground)] pointer-events-none" />
                      </div>
                      <p className="mt-1.5 text-[10px] text-[var(--muted-foreground)]">
                        {provider?.models.length ?? 0} modelos disponíveis
                      </p>
                    </div>
                  </div>

                  {/* API Key */}
                  <div>
                    <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                      <KeyRound className="w-3 h-3" />
                      API Key
                      <span className="normal-case font-normal text-[var(--muted-foreground)]">(opcional)</span>
                    </label>
                    <input
                      type="password"
                      placeholder="Deixe em branco para usar a chave padrão do sistema"
                      className="w-full rounded-lg border bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20 transition-colors disabled:opacity-50"
                      value={config.api_key || ""}
                      disabled={!config.enabled}
                      onChange={(e) =>
                        updateLocalConfig(config.function_key, "api_key", e.target.value)
                      }
                    />
                  </div>

                  {/* Ações */}
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <button
                      id={`btn-test-${config.function_key}`}
                      onClick={() => handleTest(config)}
                      disabled={isTesting || !config.enabled}
                      className="inline-flex items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium text-[var(--foreground)] hover:bg-[var(--secondary)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      <RefreshCcw
                        className={`w-3.5 h-3.5 ${isTesting ? "animate-spin" : ""}`}
                      />
                      {isTesting ? "Testando..." : "Testar"}
                    </button>
                    <button
                      id={`btn-save-${config.function_key}`}
                      onClick={() => handleUpdate(config)}
                      disabled={isSaving}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-legal-600 px-4 py-2 text-sm font-medium text-white hover:bg-legal-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      {isSaving ? (
                        <RefreshCcw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Save className="w-3.5 h-3.5" />
                      )}
                      {isSaving ? "Salvando..." : "Salvar"}
                    </button>
                  </div>
                </div>

                {/* Footer com timestamp */}
                {config.updated_at && (
                  <div className="px-5 py-2.5 border-t border-[var(--border)] bg-[var(--secondary)]/30 flex items-center gap-1.5 text-[10px] text-[var(--muted-foreground)]">
                    <Settings2 className="w-3 h-3" />
                    Atualizado em{" "}
                    {new Date(config.updated_at).toLocaleString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Nota técnica ── */}
      <div className="rounded-xl border border-legal-600/20 bg-legal-600/5 p-5 flex items-start gap-4">
        <div className="p-2 rounded-lg bg-legal-600/10 shrink-0">
          <BrainCircuit className="w-5 h-5 text-legal-600" />
        </div>
        <div>
          <h4 className="font-semibold text-[var(--foreground)] mb-1">Fallback Automático</h4>
          <p className="text-sm text-[var(--muted-foreground)] leading-relaxed">
            O sistema possui <strong className="text-[var(--foreground)]">fallback heurístico automático</strong>. Se uma função de IA for desativada ou ocorrer falha na API, o sistema continuará operando com algoritmos tradicionais de análise jurídica — garantindo disponibilidade total em qualquer cenário.
          </p>
        </div>
      </div>
    </div>
  );
}
