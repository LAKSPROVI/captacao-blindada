"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Home } from "lucide-react";

const ROUTE_LABELS: Record<string, string> = {
  "": "Painel",
  "captacao": "Captação Automatizada",
  "monitor": "DJEN Monitor",
  "processo": "Processos",
  "busca": "Pesquisa Pontual",
  "configuracao-ia": "IA & Modelos",
  "admin": "Administração",
  "tarifacao": "Tarifação",
  "usuarios": "Usuários",
  "tenants": "Cadastros",
  "auditoria": "Cadeia de Custódia",
  "erros": "Erros do Sistema",
  "login": "Login",
};

export function Breadcrumbs() {
  const pathname = usePathname();
  if (pathname === "/" || pathname === "/login") return null;

  const segments = pathname.split("/").filter(Boolean);
  const crumbs = segments.map((seg, i) => ({
    label: ROUTE_LABELS[seg] || seg,
    href: "/" + segments.slice(0, i + 1).join("/"),
    isLast: i === segments.length - 1,
  }));

  return (
    <nav className="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)] mb-4 font-medium">
      <Link href="/" className="flex items-center gap-1 hover:text-[var(--foreground)] transition-colors">
        <Home className="w-3.5 h-3.5" />
        <span>Painel</span>
      </Link>
      {crumbs.map((c) => (
        <span key={c.href} className="flex items-center gap-1.5">
          <ChevronRight className="w-3 h-3 opacity-40" />
          {c.isLast ? (
            <span className="text-[var(--foreground)]">{c.label}</span>
          ) : (
            <Link href={c.href} className="hover:text-[var(--foreground)] transition-colors">{c.label}</Link>
          )}
        </span>
      ))}
    </nav>
  );
}
