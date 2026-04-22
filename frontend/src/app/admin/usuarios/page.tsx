"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Users, UserPlus, Search, Edit2, Trash2, Shield, Lock, Unlock } from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Skeleton } from "@/components/Skeleton";
import { Modal, ConfirmModal } from "@/components/Modal";
import { useToast } from "@/components/Toast";

export default function UsuariosPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [users, setUsers] = useState<any[]>([]);
  const [tenants, setTenants] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [formData, setFormData] = useState({ username: "", full_name: "", password: "", role: "viewer", tenant_id: 1 });

  const isMaster = user?.role === "master";

  useEffect(() => { fetchData(); }, [user]);

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
      toast.error("Erro ao carregar usuários");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.username || !formData.full_name || !formData.password) {
      toast.warning("Preencha todos os campos obrigatórios");
      return;
    }
    try {
      await api.createUser(formData);
      toast.success("Usuário criado com sucesso!");
      setShowCreateModal(false);
      setFormData({ username: "", full_name: "", password: "", role: "viewer", tenant_id: 1 });
      fetchData();
    } catch (e: any) {
      toast.error("Erro ao criar: " + (e?.response?.data?.detail || e.message));
    }
  };

  const handleEdit = async () => {
    if (!selectedUser) return;
    try {
      await api.updateUser(selectedUser.id, {
        full_name: formData.full_name,
        role: formData.role,
        tenant_id: formData.tenant_id,
        ...(formData.password ? { password: formData.password } : {}),
      });
      toast.success("Usuário atualizado!");
      setShowEditModal(false);
      fetchData();
    } catch (e: any) {
      toast.error("Erro ao atualizar: " + (e?.response?.data?.detail || e.message));
    }
  };

  const handleDelete = async () => {
    if (!selectedUser) return;
    try {
      await api.deleteUser(selectedUser.id);
      toast.success("Usuário removido");
      fetchData();
    } catch (e: any) {
      toast.error("Erro ao deletar: " + (e?.response?.data?.detail || e.message));
    }
  };

  const openEdit = (u: any) => {
    setSelectedUser(u);
    setFormData({ username: u.username, full_name: u.full_name, password: "", role: u.role, tenant_id: u.tenant_id });
    setShowEditModal(true);
  };

  const openDelete = (u: any) => {
    setSelectedUser(u);
    setShowDeleteConfirm(true);
  };

  const filteredUsers = users.filter((u) =>
    u.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.username?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const ROLES = [
    { value: "master", label: "Master", desc: "Acesso total ao sistema" },
    { value: "tenant_admin", label: "Admin Tenant", desc: "Administra seu escritório" },
    { value: "manager", label: "Gerente", desc: "Gerencia captações e processos" },
    { value: "operator", label: "Operador", desc: "Opera o sistema no dia a dia" },
    { value: "viewer", label: "Visualizador", desc: "Apenas visualiza dados" },
  ];

  if (isLoading) {
    return <div className="p-6"><Skeleton variant="table" lines={5} /></div>;
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="w-6 h-6 text-legal-500" />
            Gestão de Usuários
          </h1>
          <p className="text-[var(--muted-foreground)]">Gerencie acessos e permissões.</p>
        </div>
        <button
          onClick={() => { setFormData({ username: "", full_name: "", password: "", role: "viewer", tenant_id: user?.tenant_id || 1 }); setShowCreateModal(true); }}
          className="flex items-center gap-2 px-4 py-2 bg-legal-600 text-white hover:bg-legal-700 rounded-lg shadow font-medium transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          Novo Usuário
        </button>
      </div>

      {/* Search + Count */}
      <div className="border rounded-xl bg-[var(--card)] overflow-hidden shadow-sm">
        <div className="p-4 border-b bg-[var(--secondary)]/30 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" />
            <input
              type="text"
              placeholder="Buscar usuários..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-md border border-[var(--border)] bg-transparent text-sm focus:outline-none focus:ring-1 focus:ring-legal-500"
            />
          </div>
          <span className="text-sm font-medium text-[var(--muted-foreground)]">{filteredUsers.length} usuários</span>
        </div>
        
        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-[var(--secondary)] text-[var(--muted-foreground)]">
              <tr>
                <th className="px-4 py-3 font-medium">Nome / Username</th>
                <th className="px-4 py-3 font-medium">Cargo</th>
                {isMaster && <th className="px-4 py-3 font-medium">Tenant</th>}
                <th className="px-4 py-3 font-medium">Desde</th>
                <th className="px-4 py-3 font-medium text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-[var(--muted-foreground)]">Nenhum usuário encontrado.</td>
                </tr>
              ) : (
                filteredUsers.map((u) => {
                  const isMe = user?.id === u.id;
                  const roleColor = u.role === "master" ? "bg-amber-500/15 text-amber-600" : u.role === "tenant_admin" ? "bg-purple-500/15 text-purple-600" : "bg-[var(--secondary)] text-[var(--muted-foreground)]";
                  return (
                    <tr key={u.id} className="hover:bg-[var(--secondary)]/50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-[var(--foreground)] flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-legal-600 text-white flex items-center justify-center text-xs font-bold shrink-0">
                            {u.full_name?.charAt(0)?.toUpperCase() || "?"}
                          </div>
                          <div>
                            <span>{u.full_name}</span>
                            {isMe && <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-600 font-bold uppercase">Você</span>}
                            <div className="text-xs text-[var(--muted-foreground)]">@{u.username}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider ${roleColor}`}>
                          <Shield className="w-3 h-3" />
                          {u.role}
                        </span>
                      </td>
                      {isMaster && <td className="px-4 py-3 text-[var(--muted-foreground)] font-mono">#{u.tenant_id}</td>}
                      <td className="px-4 py-3 text-[var(--muted-foreground)]">{u.criado_em ? new Date(u.criado_em + "Z").toLocaleDateString("pt-BR") : "-"}</td>
                      <td className="px-4 py-3 text-right">
                        {!isMe && (
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => openEdit(u)} className="p-1.5 text-gray-500 hover:text-blue-500 hover:bg-blue-500/10 rounded transition-colors" title="Editar">
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button onClick={() => openDelete(u)} className="p-1.5 text-gray-500 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors" title="Remover">
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

      {/* Modal Criar */}
      <Modal open={showCreateModal} onClose={() => setShowCreateModal(false)} title="Novo Usuário" size="md" footer={
        <>
          <button onClick={() => setShowCreateModal(false)} className="px-4 py-2 rounded-lg border bg-[var(--secondary)] text-sm font-medium">Cancelar</button>
          <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-legal-600 text-white text-sm font-medium hover:bg-legal-700">Criar Usuário</button>
        </>
      }>
        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase block mb-1">Nome Completo *</label>
            <input type="text" value={formData.full_name} onChange={(e) => setFormData({ ...formData, full_name: e.target.value })} className="w-full px-3 py-2 rounded-lg border bg-[var(--background)] text-sm focus:ring-1 focus:ring-legal-500 focus:outline-none" placeholder="Nome completo" />
          </div>
          <div>
            <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase block mb-1">Username (Login) *</label>
            <input type="text" value={formData.username} onChange={(e) => setFormData({ ...formData, username: e.target.value })} className="w-full px-3 py-2 rounded-lg border bg-[var(--background)] text-sm focus:ring-1 focus:ring-legal-500 focus:outline-none" placeholder="username" />
          </div>
          <div>
            <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase block mb-1">Senha *</label>
            <input type="password" value={formData.password} onChange={(e) => setFormData({ ...formData, password: e.target.value })} className="w-full px-3 py-2 rounded-lg border bg-[var(--background)] text-sm focus:ring-1 focus:ring-legal-500 focus:outline-none" placeholder="Senha segura" />
          </div>
          <div>
            <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase block mb-1">Cargo</label>
            <select value={formData.role} onChange={(e) => setFormData({ ...formData, role: e.target.value })} className="w-full px-3 py-2 rounded-lg border bg-[var(--background)] text-sm focus:ring-1 focus:ring-legal-500 focus:outline-none">
              {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label} - {r.desc}</option>)}
            </select>
          </div>
          {isMaster && (
            <div>
              <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase block mb-1">Tenant</label>
              <select value={formData.tenant_id} onChange={(e) => setFormData({ ...formData, tenant_id: parseInt(e.target.value) })} className="w-full px-3 py-2 rounded-lg border bg-[var(--background)] text-sm focus:ring-1 focus:ring-legal-500 focus:outline-none">
                {tenants.map((t) => <option key={t.id} value={t.id}>{t.nome} (#{t.id})</option>)}
              </select>
            </div>
          )}
        </div>
      </Modal>

      {/* Modal Editar */}
      <Modal open={showEditModal} onClose={() => setShowEditModal(false)} title={`Editar: ${selectedUser?.full_name}`} size="md" footer={
        <>
          <button onClick={() => setShowEditModal(false)} className="px-4 py-2 rounded-lg border bg-[var(--secondary)] text-sm font-medium">Cancelar</button>
          <button onClick={handleEdit} className="px-4 py-2 rounded-lg bg-legal-600 text-white text-sm font-medium hover:bg-legal-700">Salvar</button>
        </>
      }>
        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase block mb-1">Nome Completo</label>
            <input type="text" value={formData.full_name} onChange={(e) => setFormData({ ...formData, full_name: e.target.value })} className="w-full px-3 py-2 rounded-lg border bg-[var(--background)] text-sm focus:ring-1 focus:ring-legal-500 focus:outline-none" />
          </div>
          <div>
            <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase block mb-1">Nova Senha (deixe vazio para manter)</label>
            <input type="password" value={formData.password} onChange={(e) => setFormData({ ...formData, password: e.target.value })} className="w-full px-3 py-2 rounded-lg border bg-[var(--background)] text-sm focus:ring-1 focus:ring-legal-500 focus:outline-none" placeholder="Nova senha (opcional)" />
          </div>
          <div>
            <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase block mb-1">Cargo</label>
            <select value={formData.role} onChange={(e) => setFormData({ ...formData, role: e.target.value })} className="w-full px-3 py-2 rounded-lg border bg-[var(--background)] text-sm focus:ring-1 focus:ring-legal-500 focus:outline-none">
              {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label} - {r.desc}</option>)}
            </select>
          </div>
          {isMaster && (
            <div>
              <label className="text-xs font-semibold text-[var(--muted-foreground)] uppercase block mb-1">Tenant</label>
              <select value={formData.tenant_id} onChange={(e) => setFormData({ ...formData, tenant_id: parseInt(e.target.value) })} className="w-full px-3 py-2 rounded-lg border bg-[var(--background)] text-sm focus:ring-1 focus:ring-legal-500 focus:outline-none">
                {tenants.map((t) => <option key={t.id} value={t.id}>{t.nome} (#{t.id})</option>)}
              </select>
            </div>
          )}
        </div>
      </Modal>

      {/* Confirm Delete */}
      <ConfirmModal
        open={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={handleDelete}
        title="Remover Usuário"
        message={`Tem certeza que deseja remover "${selectedUser?.full_name}"? Esta ação não pode ser desfeita.`}
        confirmText="Remover"
        variant="danger"
      />
    </div>
  );
}
