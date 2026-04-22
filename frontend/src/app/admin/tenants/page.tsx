"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Settings, Plus, Edit2, Trash2, Building2, RefreshCw, AlertCircle } from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";

export default function TenantsPage() {
  const { user } = useAuth();
  const [tenants, setTenants] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [user]);

  const fetchData = async () => {
    try {
      if (!user) return;
      setIsLoading(true);
      setError(null);
      const data = await api.getTenants();
      setTenants(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Erro ao carregar cadastros");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    const nome = prompt("Nome do Cadastro (Escritório/Empresa):");
    if (!nome) return;
    const plano = prompt("Plano (free, basic, pro, enterprise):", "free") || "free";
    const saldo = prompt("Saldo inicial de tokens:", "10000") || "10000";

    try {
      await api.createTenant({
        nome,
        plano,
        saldo_tokens: parseInt(saldo, 10),
      });
      alert("Cadastro criado com sucesso!");
      fetchData();
    } catch (e: any) {
      alert("Erro ao criar: " + (e?.response?.data?.detail || e.message));
    }
  };

  const handleEdit = async (t: any) => {
    const nome = prompt("Nome:", t.nome) || t.nome;
    const plano = prompt("Plano (free, basic, pro, enterprise):", t.plano) || t.plano;
    const saldo = prompt("Saldo de tokens:", t.saldo_tokens?.toString()) || t.saldo_tokens;

    try {
      await api.updateTenant(t.id, {
        nome,
        plano,
        saldo_tokens: parseInt(saldo, 10),
      });
      alert("Cadastro atualizado!");
      fetchData();
    } catch (e: any) {
      alert("Erro ao atualizar: " + (e?.response?.data?.detail || e.message));
    }
  };

  if (isLoading) {
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
            <Building2 className="w-6 h-6 text-legal-500" />
            Cadastros (Tenants)
          </h1>
          <p className="text-[var(--muted-foreground)]">Gerencie escritórios e empresas cadastradas no sistema.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchData}
            className="p-2 bg-[var(--secondary)] hover:bg-[var(--secondary)]/80 rounded"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 px-4 py-2 bg-legal-600 text-white hover:bg-legal-700 rounded-lg shadow font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Novo Cadastro
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 p-4 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      <div className="border rounded-xl bg-[var(--card)] overflow-hidden shadow-sm">
        <table className="w-full text-sm text-left">
          <thead className="bg-[var(--secondary)] text-[var(--muted-foreground)]">
            <tr>
              <th className="px-4 py-3 font-medium">ID</th>
              <th className="px-4 py-3 font-medium">Nome</th>
              <th className="px-4 py-3 font-medium">Plano</th>
              <th className="px-4 py-3 font-medium">Saldo Tokens</th>
              <th className="px-4 py-3 font-medium">Criado em</th>
              <th className="px-4 py-3 font-medium text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {tenants.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[var(--muted-foreground)]">Nenhum cadastro encontrado.</td>
              </tr>
            ) : (
              tenants.map((t) => (
                <tr key={t.id} className="hover:bg-[var(--secondary)]/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-[var(--muted-foreground)]">#{t.id}</td>
                  <td className="px-4 py-3 font-medium text-[var(--foreground)]">{t.nome}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider ${
                      t.plano === "enterprise" ? "bg-purple-500/15 text-purple-600" :
                      t.plano === "pro" ? "bg-blue-500/15 text-blue-600" :
                      t.plano === "basic" ? "bg-green-500/15 text-green-600" :
                      "bg-gray-500/10 text-gray-500"
                    }`}>
                      {t.plano}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono">{(t.saldo_tokens ?? 0).toLocaleString("pt-BR")}</td>
                  <td className="px-4 py-3 text-[var(--muted-foreground)]">{t.criado_em ? new Date(t.criado_em + "Z").toLocaleDateString("pt-BR") : "-"}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button onClick={() => handleEdit(t)} className="p-1.5 text-gray-500 hover:text-blue-500 hover:bg-blue-500/10 rounded transition-colors" title="Editar">
                        <Edit2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
