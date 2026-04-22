"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Users, UserPlus, Search, Edit2, Trash2 } from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";

export default function UsuariosPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<any[]>([]);
  const [tenants, setTenants] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const isMaster = user?.role === "master";

  useEffect(() => {
    fetchData();
  }, [user]);

  const fetchData = async () => {
    try {
      if (!user) return;
      setIsLoading(true);
      const data = await api.getUsers();
      setUsers(data);
      if (isMaster) {
        const t = await api.getTenants();
        setTenants(t);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateUser = async () => {
    const nome = prompt("Nome completo:") || "";
    if(!nome) return;
    const username = prompt("Username (login):") || "";
    if(!username) return;
    const password = prompt("Senha:") || "";
    if(!password) return;
    const role = prompt("Role (manager, operator, viewer):", "viewer") || "viewer";

    let tenantId = user?.tenant_id;
    if (isMaster) {
      const t = prompt("ID do Tenant (Cadastro) para associar:", tenantId?.toString());
      if (t) tenantId = parseInt(t, 10);
    }

    try {
      await api.createUser({
        username,
        full_name: nome,
        password,
        role,
        tenant_id: tenantId
      });
      alert("Usuário criado com sucesso!");
      fetchData();
    } catch (e: any) {
      alert("Erro ao criar usuário: " + (e?.response?.data?.detail || e.message));
    }
  };

  const handleDeleteUser = async (id: number) => {
    if(!confirm("Tem certeza que deseja deletar este usuário?")) return;
    try {
      await api.deleteUser(id);
      fetchData();
    } catch (e: any) {
      alert("Erro ao deletar: " + (e?.response?.data?.detail || e.message));
    }
  };

  const handleEditUser = async (u: any) => {
    const nome = prompt("Nome completo:", u.full_name) || u.full_name;
    const role = prompt("Role (master, manager, operator, viewer):", u.role) || u.role;
    
    let tenantId = u.tenant_id;
    if (isMaster) {
      const t = prompt("ID do Tenant:", u.tenant_id?.toString());
      if (t) tenantId = parseInt(t, 10);
    }

    const novaSenha = prompt("Nova senha (deixe vazio para manter):", "");

    try {
      await api.updateUser(u.id, {
        full_name: nome,
        role,
        tenant_id: tenantId,
        ...(novaSenha ? { password: novaSenha } : {}),
      });
      alert("Usuário atualizado com sucesso!");
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
            <Users className="w-6 h-6 text-legal-500" />
            Gestão de Usuários
          </h1>
          <p className="text-[var(--muted-foreground)]">Gerencie acessos e permissões para a plataforma.</p>
        </div>
        <button
          onClick={handleCreateUser}
          className="flex items-center gap-2 px-4 py-2 bg-legal-600 text-white hover:bg-legal-700 rounded-lg shadow font-medium transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          Novo Usuário
        </button>
      </div>

      <div className="border rounded-xl bg-[var(--card)] overflow-hidden shadow-sm">
        <div className="p-4 border-b bg-[var(--secondary)]/30 flex justify-between items-center">
          <div className="relative w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" />
            <input type="text" placeholder="Buscar usuários..." className="w-full pl-9 pr-4 py-2 rounded-md border border-[var(--border)] bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-legal-500" />
          </div>
          <span className="text-sm font-medium text-[var(--muted-foreground)]">{users.length} usuários</span>
        </div>
        
        <table className="w-full text-sm text-left">
          <thead className="bg-[var(--secondary)] text-[var(--muted-foreground)]">
            <tr>
              <th className="px-4 py-3 font-medium">Nome / Username</th>
              <th className="px-4 py-3 font-medium">Role (Cargo)</th>
              {isMaster && <th className="px-4 py-3 font-medium">Tenant ID</th>}
              <th className="px-4 py-3 font-medium">Membro desde</th>
              <th className="px-4 py-3 font-medium text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {users.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-[var(--muted-foreground)]">Nenhum usuário encontrado.</td>
              </tr>
            ) : (
              users.map((u) => {
                const isMe = user?.id === u.id;
                return (
                  <tr key={u.id} className="hover:bg-[var(--secondary)]/50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-[var(--foreground)] flex items-center gap-2">
                        {u.full_name}
                        {isMe && <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-600 font-bold uppercase tracking-wider">Você</span>}
                      </div>
                      <div className="text-xs text-[var(--muted-foreground)]">@{u.username}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex px-2 py-1 rounded bg-[var(--secondary)] text-[var(--muted-foreground)] uppercase text-xs font-semibold tracking-wider">
                        {u.role}
                      </span>
                    </td>
                    {isMaster && <td className="px-4 py-3 text-[var(--muted-foreground)]">#{u.tenant_id}</td>}
                    <td className="px-4 py-3 text-[var(--muted-foreground)]">{u.criado_em ? new Date(u.criado_em + 'Z').toLocaleDateString('pt-BR') : '-'}</td>
                    <td className="px-4 py-3 text-right">
                      {!isMe && (
                        <div className="flex items-center justify-end gap-2">
                          <button onClick={() => handleEditUser(u)} className="p-1.5 text-gray-500 hover:text-blue-500 hover:bg-blue-500/10 rounded transition-colors" title="Editar">
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleDeleteUser(u.id)} className="p-1.5 text-gray-500 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors" title="Remover">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
