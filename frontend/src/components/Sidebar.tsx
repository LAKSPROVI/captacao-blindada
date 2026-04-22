"use client";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Search,
  FileText,
  Globe,
  Scale,
  LogOut,
  Moon,
  Sun,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  Users,
  Settings,
  ShieldCheck,
  AlertTriangle,
  Zap,
  Brain,
  User,
} from "lucide-react";
import { useState, useEffect } from "react";

const navItems = [
  { href: "/", label: "Painel", icon: LayoutDashboard },
  { href: "/captacao", label: "Captação", icon: Zap, pipelineNext: true },
  { href: "/monitor", label: "DJEN", icon: Globe },
  { href: "/processo", label: "Processos", icon: FileText },
  { href: "/busca", label: "Pesquisa Pontual", icon: Search },
  { href: "/configuracao-ia", label: "IA & Modelos", icon: Brain },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    setDarkMode(isDark);
  }, []);

  const toggleDarkMode = () => {
    document.documentElement.classList.toggle("dark");
    setDarkMode(!darkMode);
  };

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r bg-[var(--card)] transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo and Collapse Toggle */}
      <div className="flex h-16 items-center justify-between border-b px-4">
        <Link href="/" className="flex items-center gap-2 overflow-hidden">
          <Scale className="h-7 w-7 text-gold-500 shrink-0" />
          {!collapsed && (
            <div className="animate-in fade-in slide-in-from-left-2 duration-300">
              <h1 className="text-lg font-bold text-legal-600 dark:text-legal-400">
                Captacao Blindada
              </h1>
              <p className="text-[10px] text-[var(--muted-foreground)] -mt-1">
                Sistema Juridico
              </p>
            </div>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded-md text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors"
          title={collapsed ? "Expandir menu" : "Recolher menu"}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          const hasPipeline = "pipelineNext" in item && item.pipelineNext;
          return (
            <div key={item.href}>
              <Link
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-legal-600 text-white shadow-sm"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"
                )}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
              {hasPipeline && !collapsed && (
                <div className="flex items-center gap-1 px-3 py-0.5 select-none">
                  <div className="ml-2 w-px h-4 bg-legal-500/30" />
                  <span className="ml-1 text-[9px] font-semibold uppercase tracking-widest text-legal-500/60">alimenta</span>
                </div>
              )}
              {hasPipeline && collapsed && (
                <div className="flex justify-center py-0.5">
                  <div className="w-px h-3 bg-legal-500/30" />
                </div>
              )}
            </div>
          );
        })}
        {user && (user.role === "master" || user.role === "tenant_admin") && (
          <>
            <div className="pt-4 pb-1 px-3">
              {!collapsed && <p className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">Administração</p>}
              {collapsed && <div className="h-px w-full bg-border my-2" />}
            </div>
            
            <div key="/admin/tarifacao">
              <Link
                href="/admin/tarifacao"
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  pathname.startsWith("/admin/tarifacao")
                    ? "bg-legal-600 text-white shadow-sm"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"
                )}
                title={collapsed ? "Tarifação" : undefined}
              >
                <CreditCard className="h-5 w-5 shrink-0" />
                {!collapsed && <span>Tarifação</span>}
              </Link>
            </div>
            
            <div key="/admin/usuarios">
              <Link
                href="/admin/usuarios"
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  pathname.startsWith("/admin/usuarios")
                    ? "bg-legal-600 text-white shadow-sm"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"
                )}
                title={collapsed ? "Usuários" : undefined}
              >
                <Users className="h-5 w-5 shrink-0" />
                {!collapsed && <span>Usuários</span>}
              </Link>
            </div>

            {user.role === "master" && (
              <>
                <div key="/admin/tenants">
                  <Link
                    href="/admin/tenants"
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      pathname.startsWith("/admin/tenants")
                        ? "bg-legal-600 text-white shadow-sm"
                        : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"
                    )}
                    title={collapsed ? "Cadastros / Tenants" : undefined}
                  >
                    <Settings className="h-5 w-5 shrink-0" />
                    {!collapsed && <span>Cadastros</span>}
                  </Link>
                </div>

                <div key="/admin/auditoria">
                  <Link
                    href="/admin/auditoria"
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      pathname.startsWith("/admin/auditoria")
                        ? "bg-legal-600 text-white shadow-sm"
                        : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"
                    )}
                    title={collapsed ? "Cadeia de Custódia" : undefined}
                  >
                    <ShieldCheck className="h-5 w-5 shrink-0" />
                    {!collapsed && <span>Cadeia de Custódia</span>}
                  </Link>
                </div>

                <div key="/admin/erros">
                  <Link
                    href="/admin/erros"
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      pathname.startsWith("/admin/erros")
                        ? "bg-red-600 text-white shadow-sm"
                        : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"
                    )}
                    title={collapsed ? "System Errors" : undefined}
                  >
                    <AlertTriangle className={cn("h-5 w-5 shrink-0", !pathname.startsWith("/admin/erros") && "text-red-500")} />
                    {!collapsed && <span className={cn(!pathname.startsWith("/admin/erros") && "text-red-500 font-semibold")}>Erros do Sistema</span>}
                  </Link>
                </div>
              </>
            )}
          </>
        )}
      </nav>

      {/* Bottom section */}
      <div className="border-t p-3 space-y-2">
        {/* Dark mode toggle */}
        <button
          onClick={toggleDarkMode}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors"
          title={darkMode ? "Modo claro" : "Modo escuro"}
        >
          {darkMode ? (
            <Sun className="h-5 w-5 shrink-0" />
          ) : (
            <Moon className="h-5 w-5 shrink-0" />
          )}
          {!collapsed && <span>{darkMode ? "Modo Claro" : "Modo Escuro"}</span>}
        </button>

        {/* User info */}
        {user && (
          <div
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 cursor-pointer hover:bg-[var(--secondary)] transition-colors",
              collapsed ? "justify-center" : ""
            )}
            onClick={() => {
              if (user.role === "master" || user.role === "tenant_admin") {
                window.location.href = "/admin/usuarios";
              }
            }}
            title={user.role === "master" ? "Painel Master → Gestão de Usuários" : user.role === "tenant_admin" ? "Painel Admin → Gestão de Usuários" : ""}
          >
            <div className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white text-sm font-medium",
              user.role === "master" ? "bg-amber-600 ring-2 ring-amber-400/50" : "bg-legal-600"
            )}>
              {user.username?.charAt(0).toUpperCase() || <User className="h-4 w-4" />}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--card-foreground)] truncate">
                  {user.full_name || user.username}
                </p>
                <p className={cn(
                  "text-xs truncate uppercase font-semibold",
                  user.role === "master" ? "text-amber-500" : "text-legal-500"
                )}>
                  {user.role === "master" ? "Administrador Master" : user.role}
                </p>
                <p className="text-[10px] text-[var(--muted-foreground)] truncate">
                  {user.email || user.username}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Logout */}
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-red-500 hover:bg-red-500/10 transition-colors"
          title="Sair"
        >
          <LogOut className="h-5 w-5 shrink-0" />
          {!collapsed && <span>Sair</span>}
        </button>
      </div>
    </aside>
  );
}
