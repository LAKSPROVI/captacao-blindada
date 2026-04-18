"use client";

import React, { useState, useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
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
  Gavel
} from "lucide-react";

const functionIcons: Record<string, any> = {
  classificacao: Hash,
  previsao: BrainCircuit,
  resumo: FileText,
  jurisprudencia: Gavel
};

const functionLabels: Record<string, string> = {
  classificacao: "Classificação Jurídica",
  previsao: "Previsão de Resultado",
  resumo: "Resumo Executivo",
  jurisprudencia: "Análise de Jurisprudência"
};

export default function AIConfigPage() {
  const [configs, setConfigs] = useState<AIConfig[]>([]);
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [testingKey, setTestingKey] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error" | "warning"; text: string } | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [configsData, providersData] = await Promise.all([
        api.getAIConfigs(),
        api.getAvailableAIModels()
      ]);
      setConfigs(configsData);
      setProviders(providersData);
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: "Falha ao carregar configurações de IA" });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (config: AIConfig) => {
    try {
      setSavingKey(config.function_key);
      await api.updateAIConfig(config.function_key, config);
      setMessage({ type: "success", text: `Configuração de ${functionLabels[config.function_key] || config.function_key} atualizada!` });
      setTimeout(() => setMessage(null), 3000);
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
        text: result.message + (result.response ? ` (${result.response})` : "")
      });
      if (result.status === "success") {
        setTimeout(() => setMessage(null), 3000);
      }
    } catch (err) {
      console.error(err);
      setMessage({ type: "error", text: "Erro ao testar conexão" });
    } finally {
      setTestingKey(null);
    }
  };

  const updateLocalConfig = (key: string, field: keyof AIConfig, value: any) => {
    setConfigs(prev => prev.map(c => 
      c.function_key === key ? { ...c, [field]: value } : c
    ));
  };

  if (loading) {
    return (
      <div className="flex h-screen bg-slate-950 text-white">
        <Sidebar aria-label="Navegação lateral" />
        <main className="flex-1 flex items-center justify-center">
          <RefreshCcw className="w-8 h-8 animate-spin text-blue-500" />
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar aria-label="Navegação lateral" />
      
      <main className="flex-1 p-8 overflow-auto">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <div className="p-3 bg-blue-500/10 rounded-xl">
              <Bot className="w-8 h-8 text-blue-500" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">IA &amp; Modelos</h1>
              <p className="text-slate-400">Configure os motores de inteligência artificial para cada função do sistema.</p>
            </div>
          </div>

          {/* Message banner — ONLY when a message exists */}
          {message && (
            <div className={`mb-6 p-4 rounded-xl flex items-center gap-3 border ${
              message.type === "success" 
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" 
                : message.type === "warning"
                ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
                : "bg-red-500/10 border-red-500/20 text-red-400"
            }`}>
              {message.type === "success" ? (
                <CheckCircle2 className="w-5 h-5 shrink-0" />
              ) : message.type === "warning" ? (
                <Settings2 className="w-5 h-5 shrink-0" />
              ) : (
                <XCircle className="w-5 h-5 shrink-0" />
              )}
              <span>{message.text}</span>
              <button
                onClick={() => setMessage(null)}
                className="ml-auto text-current opacity-60 hover:opacity-100"
              >
                ×
              </button>
            </div>
          )}

          {/* Grid de Configurações */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {configs.map((config) => {
              const Icon = functionIcons[config.function_key] || Cpu;
              const provider = providers.find(p => p.id === config.provider);
              
              return (
                <div 
                  key={config.function_key}
                  className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 hover:border-blue-500/30 transition-all group"
                >
                  <div className="flex justify-between items-start mb-6">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-slate-800 rounded-lg group-hover:bg-blue-500/10 transition-colors">
                        <Icon className="w-5 h-5 text-blue-400" />
                      </div>
                      <h3 className="font-semibold text-lg">{functionLabels[config.function_key] || config.function_key}</h3>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input 
                        type="checkbox" 
                        className="sr-only peer"
                        checked={config.enabled}
                        onChange={(e) => updateLocalConfig(config.function_key, "enabled", e.target.checked)}
                      />
                      <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  <div className="space-y-4">
                    {/* Provedor */}
                    <div>
                      <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 block">Provedor</label>
                      <select 
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-blue-500 transition-colors"
                        value={config.provider}
                        onChange={(e) => updateLocalConfig(config.function_key, "provider", e.target.value)}
                      >
                        {providers.map(p => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </select>
                    </div>

                    {/* Modelo */}
                    <div>
                      <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 block">Modelo</label>
                      <select 
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-blue-500 transition-colors"
                        value={config.model_name}
                        onChange={(e) => updateLocalConfig(config.function_key, "model_name", e.target.value)}
                      >
                        {provider?.models.map(m => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                        {!provider?.models.includes(config.model_name) && (
                          <option value={config.model_name}>{config.model_name} (Custom)</option>
                        )}
                      </select>
                    </div>

                    {/* API Key */}
                    <div>
                      <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 block">API Key (Opcional)</label>
                      <input 
                        type="password"
                        placeholder="Deixe em branco para usar a chave padrão"
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-blue-500 transition-colors"
                        value={config.api_key || ""}
                        onChange={(e) => updateLocalConfig(config.function_key, "api_key", e.target.value)}
                      />
                    </div>

                    <div className="pt-4 grid grid-cols-2 gap-3">
                      <button
                        id={`btn-test-${config.function_key}`}
                        onClick={() => handleTest(config)}
                        disabled={testingKey === config.function_key || !config.enabled}
                        className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-xl transition-all flex items-center justify-center gap-2"
                      >
                        <RefreshCcw className={`w-4 h-4 ${testingKey === config.function_key ? "animate-spin" : ""}`} />
                        Testar
                      </button>
                      <button
                        id={`btn-save-${config.function_key}`}
                        onClick={() => handleUpdate(config)}
                        disabled={savingKey === config.function_key}
                        className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white font-medium py-2.5 rounded-xl transition-all flex items-center justify-center gap-2"
                      >
                        <Save className={`w-4 h-4 ${savingKey === config.function_key ? "hidden" : ""}`} />
                        {savingKey === config.function_key ? (
                          <RefreshCcw className="w-4 h-4 animate-spin" />
                        ) : null}
                        Salvar
                      </button>
                    </div>
                  </div>

                  {config.updated_at && (
                    <div className="mt-4 pt-4 border-t border-slate-800 text-[10px] text-slate-500 flex items-center gap-1">
                      <Settings2 className="w-3 h-3" />
                      Atualizado em: {new Date(config.updated_at).toLocaleString('pt-BR')}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-12 p-6 bg-blue-500/5 border border-blue-500/10 rounded-2xl">
            <h4 className="font-semibold flex items-center gap-2 mb-2">
              <Settings2 className="w-4 h-4 text-blue-400" />
              Dica Técnica
            </h4>
            <p className="text-sm text-slate-400 leading-relaxed">
              O sistema utiliza <strong>fallback heurístico</strong> automático. Se você desativar a IA ou houver falha na API, o sistema continuará funcionando utilizando algoritmos tradicionais de análise jurídica, garantindo que você nunca fique sem resultados.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
