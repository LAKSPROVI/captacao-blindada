"use client";

import Link from "next/link";
import { Home, ArrowLeft, Search } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6 text-center bg-[var(--background)]">
      <div className="w-24 h-24 rounded-3xl bg-[var(--secondary)] flex items-center justify-center mb-6">
        <span className="text-5xl font-bold text-[var(--muted-foreground)]">404</span>
      </div>
      <h1 className="text-2xl font-bold text-[var(--foreground)] mb-2">Página não encontrada</h1>
      <p className="text-sm text-[var(--muted-foreground)] max-w-md mb-8">
        A página que você está procurando não existe ou foi movida. Verifique o endereço ou volte ao painel principal.
      </p>
      <div className="flex gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-legal-600 text-white rounded-lg text-sm font-medium hover:bg-legal-700 transition-colors"
        >
          <Home className="w-4 h-4" />
          Ir ao Painel
        </Link>
        <button
          onClick={() => window.history.back()}
          className="inline-flex items-center gap-2 px-4 py-2.5 border rounded-lg text-sm font-medium hover:bg-[var(--secondary)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Voltar
        </button>
      </div>
    </div>
  );
}
