"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { AlertTriangle, CheckCircle, RefreshCw, Terminal, Clock } from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { cn } from "@/lib/utils";

export default function ErrosPage() {
  const { user } = useAuth();
  const [erros, setErros] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterMode, setFilterMode] = useState<"aberto" | "resolvido" | "all">("aberto");

  useEffect(() => {
    fetchErros();
  }, [user, filterMode]);

  const fetchErros = async () => {
    try {
      if (!user || user.role !== "master") return;
      setIsLoading(true);
      const data = await api.getSystemErrors(filterMode, 100, 0);
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

  if(!user || user.role !== "master") {
     return <div className="p-6 text-center text-red-500 font-bold">Acesso restrito.</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-red-500" />
            Mission Control: Erros do Sistema
          </h1>
          <p className="text-[var(--muted-foreground)]">Todas as falhas nas requisições, agentes de IA ou monitoramento de background reportam aqui.</p>
        </div>
        <button
          onClick={fetchErros}
          className="flex items-center justify-center p-2 bg-[var(--secondary)] hover:bg-[var(--secondary)]/80 rounded transition-colors"
          title="Atualizar"
        >
          <RefreshCw className={cn("w-5 h-5 text-[var(--muted-foreground)]", isLoading && "animate-spin")} />
        </button>
      </div>

      <div className="flex gap-2">
        <button onClick={() => setFilterMode("aberto")} className={cn("px-4 py-1.5 rounded-md text-sm font-medium transition-colors border", filterMode === "aberto" ? "bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400" : "bg-[var(--card)] border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]")}>
          Abertos
        </button>
        <button onClick={() => setFilterMode("resolvido")} className={cn("px-4 py-1.5 rounded-md text-sm font-medium transition-colors border", filterMode === "resolvido" ? "bg-green-500/10 border-green-500/30 text-green-700 dark:text-green-400" : "bg-[var(--card)] border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]")}>
          Resolvidos
        </button>
        <button onClick={() => setFilterMode("all")} className={cn("px-4 py-1.5 rounded-md text-sm font-medium transition-colors border", filterMode === "all" ? "bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400" : "bg-[var(--card)] border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]")}>
          Todos
        </button>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner />
        </div>
      ) : (
        <div className="space-y-4">
          {erros.length === 0 ? (
            <div className="p-8 border border-dashed rounded-xl flex flex-col items-center justify-center text-[var(--muted-foreground)] bg-[var(--card)]">
              <CheckCircle className="w-12 h-12 text-green-500/50 mb-3" />
              <p>Nenhum erro no filtro selecionado. Tudo parecendo ótimo!</p>
            </div>
          ) : (
            erros.map(erro => (
              <div key={erro.id} className={cn(
                "p-5 border rounded-xl overflow-hidden shadow-sm transition-colors",
                erro.status === "aberto" ? "bg-red-950/10 border-red-900/30" : "bg-[var(--card)] border-[var(--border)] opacity-60"
              )}>
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-3">
                    <div className={cn("p-2 rounded-lg", erro.status === "aberto" ? "bg-red-500/20 text-red-500" : "bg-green-500/20 text-green-500")}>
                      {erro.status === "aberto" ? <AlertTriangle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5" />}
                    </div>
                    <div>
                      <h3 className={cn("font-bold text-lg", erro.status === "aberto" && "text-red-600 dark:text-red-400")}>
                        {erro.error_type} na {erro.function_name}
                      </h3>
                      <div className="flex items-center gap-4 text-xs font-mono text-[var(--muted-foreground)] mt-1">
                        <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(erro.criado_em + 'Z').toLocaleString('pt-BR')}</span>
                        {erro.tenant_id && <span>T: {erro.tenant_id}</span>}
                        {erro.user_id && <span>U: {erro.user_id}</span>}
                      </div>
                    </div>
                  </div>
                  {erro.status === "aberto" && (
                    <button 
                      onClick={() => handleResolve(erro.id)}
                      className="px-3 py-1.5 bg-green-600 text-white hover:bg-green-700 rounded text-xs font-medium uppercase tracking-wider transition-colors shadow"
                    >
                      Marcar Resolvido
                    </button>
                  )}
                </div>
                
                <div className="text-sm font-medium mb-3 pl-12 text-[var(--foreground)]">
                  {erro.error_message}
                </div>
                
                {erro.stack_trace && (
                  <div className="mt-4 pl-12">
                    <details className="group">
                      <summary className="text-xs font-medium text-blue-500 cursor-pointer flex items-center gap-1 mb-2 hover:underline">
                        <Terminal className="w-3 h-3" /> View Stack Trace
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
      )}
    </div>
  );
}
