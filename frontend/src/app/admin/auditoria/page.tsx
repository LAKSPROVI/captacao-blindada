"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { ShieldCheck, Search, ShieldAlert, Cpu, RefreshCw, KeyRound, AlertCircle } from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { cn } from "@/lib/utils";

export default function AuditoriaPage() {
  const { user } = useAuth();
  const [logs, setLogs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyStatus, setVerifyStatus] = useState<any>(null);

  useEffect(() => {
    fetchLogs();
  }, [user]);

  const fetchLogs = async () => {
    try {
      if (!user || user.role !== "master") return;
      setIsLoading(true);
      const data = await api.getAuditLogs(100, 0);
      setLogs(data);
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

  if(!user || user.role !== "master") {
     return <div className="p-6 text-center text-red-500 font-bold">Acesso restrito.</div>;
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-green-500" />
            Cadeia de Custódia (Auditoria)
          </h1>
          <p className="text-[var(--muted-foreground)]">Painel restrito para Master. Log imutável encadeado por Hashes SHA-256 de todas as transações de metadados.</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchLogs}
            className="flex items-center justify-center p-2 bg-[var(--secondary)] hover:bg-[var(--secondary)]/80 rounded transition-colors"
            title="Atualizar Logs"
          >
            <RefreshCw className="w-5 h-5 text-[var(--muted-foreground)]" />
          </button>
          
          <button
            onClick={handleVerify}
            disabled={isVerifying}
            className="flex items-center gap-2 px-4 py-2 bg-[var(--secondary)] hover:bg-[var(--secondary)]/80 border border-[var(--border)] rounded-lg shadow-sm font-medium transition-colors"
          >
            {isVerifying ? <LoadingSpinner size="sm" /> : <KeyRound className="w-4 h-4 text-[var(--muted-foreground)]" />}
            Assinatura em Bloco
          </button>
        </div>
      </div>

      {verifyStatus && (
        <div className={cn(
          "p-4 border rounded-xl flex items-start gap-4",
          verifyStatus.status === "ok" ? "bg-green-500/10 border-green-500/30 text-green-700 dark:text-green-400" : "bg-red-500/10 border-red-500/50 text-red-600 dark:text-red-400"
        )}>
          <div className="pt-0.5">
            {verifyStatus.status === "ok" ? <ShieldCheck className="w-6 h-6" /> : <ShieldAlert className="w-6 h-6" />}
          </div>
          <div className="flex-1">
            <h3 className="font-bold">{verifyStatus.status === "ok" ? "Integridade Confirmada" : "Violação de Custódia Detectada!"}</h3>
            <p className="text-sm mt-1">{verifyStatus.message}</p>
            {verifyStatus.erros && (
              <div className="mt-3 text-xs bg-red-950/20 p-3 rounded overflow-x-auto">
                <code className="text-red-300">
                  {JSON.stringify(verifyStatus.erros, null, 2)}
                </code>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="border rounded-xl bg-[var(--card)] overflow-hidden shadow-sm">
        <div className="p-4 border-b bg-[var(--secondary)]/30">
           <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
             <Cpu className="w-4 h-4" />
             <span>Transações recentes gravadas no banco de dados com protocolo de hash-chain.</span>
           </div>
        </div>
        
        <table className="w-full text-sm text-left">
          <thead className="bg-[var(--secondary)] text-[var(--muted-foreground)]">
            <tr>
              <th className="px-4 py-3 font-medium">Data / ID</th>
              <th className="px-4 py-3 font-medium">Ação</th>
              <th className="px-4 py-3 font-medium">Entidade & Alvo</th>
              <th className="px-4 py-3 font-medium">Metadados Origem (T/U)</th>
              <th className="px-4 py-3 font-medium">Digital Signature (Hash)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-[var(--muted-foreground)]">Nenhum evento auditado ainda.</td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-[var(--secondary)]/50 transition-colors">
                   <td className="px-4 py-3">
                      <div className="font-medium text-[var(--foreground)]">#{log.id}</div>
                      <div className="text-[10px] text-[var(--muted-foreground)] leading-tight mt-1">{new Date(log.criado_em + 'Z').toLocaleString('pt-BR')}</div>
                   </td>
                   <td className="px-4 py-3">
                     <span className="font-mono text-xs px-2 py-1 bg-[var(--secondary)] rounded text-legal-500 font-bold">{log.action}</span>
                   </td>
                   <td className="px-4 py-3">
                      <div className="text-[11px] font-semibold uppercase tracking-widest text-[var(--muted-foreground)]">{log.entity_type}</div>
                      <div className="text-xs font-mono truncate max-w-[200px] mt-0.5">{log.details || "-"}</div>
                   </td>
                   <td className="px-4 py-3 text-xs text-[var(--muted-foreground)]">
                      T: {log.tenant_id ?? "Sys"} <br /> U: {log.user_id ?? "ROOT"}
                      {log.ip_address && <div className="opacity-50 mt-1">{log.ip_address}</div>}
                   </td>
                   <td className="px-4 py-3">
                     <div className="max-w-[250px] truncate text-[10px] font-mono opacity-60 hover:opacity-100 transition-opacity cursor-crosshair">
                        {log.data_hash}
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
