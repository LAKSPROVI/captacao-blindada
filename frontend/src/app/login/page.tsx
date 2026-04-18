"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Scale, LogIn, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await login(username, password);
      window.location.href = "/";
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setError(message || "Credenciais invalidas. Tente novamente.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left panel - branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-legal-600 items-center justify-center p-12">
        <div className="max-w-md text-center">
          <Scale className="mx-auto h-20 w-20 text-gold-500 mb-8" />
          <h1 className="text-4xl font-bold text-white mb-4">OpenClaw</h1>
          <p className="text-lg text-legal-200 mb-6">
            Sistema Juridico Inteligente
          </p>
          <p className="text-legal-300 text-sm leading-relaxed">
            Plataforma avancada de automacao juridica com inteligencia artificial
            para analise de processos, monitoramento de publicacoes e busca
            unificada em tribunais brasileiros.
          </p>
          <div className="mt-12 grid grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-2xl font-bold text-gold-400">IA</p>
              <p className="text-xs text-legal-300 mt-1">Analise Inteligente</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gold-400">24/7</p>
              <p className="text-xs text-legal-300 mt-1">Monitoramento</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gold-400">Multi</p>
              <p className="text-xs text-legal-300 mt-1">Tribunais</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel - login form */}
      <div className="flex w-full lg:w-1/2 items-center justify-center p-8 bg-[var(--background)]">
        <div className="w-full max-w-md">
          <div className="lg:hidden text-center mb-8">
            <Scale className="mx-auto h-12 w-12 text-gold-500 mb-4" />
            <h1 className="text-2xl font-bold text-legal-600">OpenClaw</h1>
          </div>

          <div className="rounded-xl border bg-[var(--card)] p-8 shadow-lg">
            <h2 className="text-2xl font-bold text-[var(--card-foreground)] mb-2">
              Entrar
            </h2>
            <p className="text-sm text-[var(--muted-foreground)] mb-6">
              Acesse sua conta para continuar
            </p>

            {error && (
              <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                  Usuario
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full rounded-lg border bg-[var(--background)] px-4 py-2.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20"
                  placeholder="Seu usuario"
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--card-foreground)] mb-1.5">
                  Senha
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border bg-[var(--background)] px-4 py-2.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:border-legal-600 focus:outline-none focus:ring-2 focus:ring-legal-600/20"
                  placeholder="Sua senha"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={isLoading}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-legal-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-legal-700 disabled:opacity-50"
              >
                {isLoading ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <LogIn className="h-4 w-4" />
                )}
                {isLoading ? "Entrando..." : "Entrar"}
              </button>
            </form>
          </div>

          <p className="mt-6 text-center text-xs text-[var(--muted-foreground)]">
            OpenClaw VLS - Sistema Juridico Inteligente
          </p>
        </div>
      </div>
    </div>
  );
}
