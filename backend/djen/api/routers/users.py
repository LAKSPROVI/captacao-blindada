import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from djen.api.auth import get_current_user, require_role, require_master_or_tenant_admin, UserInDB, hash_password
from djen.api.schemas import (
    TenantResponse, TenantCreateRequest, TenantUpdateRequest,
    UserResponse, UserCreateRequest, UserUpdateRequest
)
from djen.api.database import get_database

log = logging.getLogger("captacao.users")

router = APIRouter(prefix="/api/admin", tags=["Administracao"])

# =========================================================================
# Tenants (Apenas Master)
# =========================================================================

@router.get("/tenants", response_model=List[TenantResponse])
def listar_tenants(current_user: UserInDB = Depends(require_role("master"))):
    db = get_database()
    rows = db.conn.execute("SELECT * FROM tenants").fetchall()
    return [TenantResponse(**dict(r)) for r in rows]

@router.post("/tenants", response_model=TenantResponse)
def criar_tenant(tenant: TenantCreateRequest, current_user: UserInDB = Depends(require_role("master"))):
    db = get_database()
    cur = db.conn.execute(
        "INSERT INTO tenants (nome, ativo, saldo_tokens) VALUES (?, ?, ?)",
        (tenant.nome, 1 if tenant.ativo else 0, tenant.saldo_tokens)
    )
    db.conn.commit()
    row = db.conn.execute("SELECT * FROM tenants WHERE id = ?", (cur.lastrowid,)).fetchone()
    return TenantResponse(**dict(row))

@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
def atualizar_tenant(tenant_id: int, tenant: TenantUpdateRequest, current_user: UserInDB = Depends(require_role("master"))):
    db = get_database()
    sets = []
    vals = []
    if tenant.nome is not None:
        sets.append("nome = ?")
        vals.append(tenant.nome)
    if tenant.ativo is not None:
        sets.append("ativo = ?")
        vals.append(1 if tenant.ativo else 0)
    if tenant.saldo_tokens is not None:
        sets.append("saldo_tokens = ?")
        vals.append(tenant.saldo_tokens)
    
    if not sets:
        raise HTTPException(status_code=400, detail="Sem campos para atualizar")
    
    sets.append("atualizado_em = datetime('now')")
    vals.append(tenant_id)
    
    db.conn.execute(f"UPDATE tenants SET {', '.join(sets)} WHERE id = ?", vals)
    db.conn.commit()
    
    row = db.conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant nao encontrado")
    return TenantResponse(**dict(row))

# =========================================================================
# Users (Master ve todos, Tenant Admin ve apenas o seu tenant)
# =========================================================================

@router.get("/users", response_model=List[UserResponse])
def listar_usuarios(current_user: UserInDB = Depends(require_master_or_tenant_admin())):
    db = get_database()
    if current_user.role == "master":
        rows = db.conn.execute("SELECT * FROM users").fetchall()
    else:
        rows = db.conn.execute("SELECT * FROM users WHERE tenant_id = ?", (current_user.tenant_id,)).fetchall()
    return [UserResponse(**dict(r)) for r in rows]

@router.put("/users/{user_id}", response_model=UserResponse)
def atualizar_usuario(user_id: int, user: UserUpdateRequest, current_user: UserInDB = Depends(require_master_or_tenant_admin())):
    db = get_database()
    
    # Check permissions
    target_user = db.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    
    if current_user.role != "master" and target_user["tenant_id"] != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Apenas admin master pode gerenciar usuarios de outro tenant")

    sets = []
    vals = []
    if user.full_name is not None:
        sets.append("full_name = ?")
        vals.append(user.full_name)
    if user.password is not None:
        sets.append("hashed_password = ?")
        vals.append(hash_password(user.password))
    if user.role is not None:
        if current_user.role != "master" and user.role in ("master", "tenant_admin"):
            raise HTTPException(status_code=403, detail="Nao permitido conceder roles altas")
        sets.append("role = ?")
        vals.append(user.role)
    if user.tenant_id is not None:
        if current_user.role != "master":
            raise HTTPException(status_code=403, detail="Apenas master pode mover usuarios entre tenants")
        sets.append("tenant_id = ?")
        vals.append(user.tenant_id)
        
    if not sets:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")
        
    vals.append(user_id)
    db.conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", vals)
    db.conn.commit()
    
    row = db.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return UserResponse(**dict(row))

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_usuario(user_id: int, current_user: UserInDB = Depends(require_master_or_tenant_admin())):
    db = get_database()
    target_user = db.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    
    if current_user.role != "master" and target_user["tenant_id"] != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Sem acesso")
    
    db.conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.conn.commit()


# =========================================================================
# Bloqueio/Desbloqueio de Usuário
# =========================================================================

@router.put("/users/{user_id}/bloquear")
def bloquear_usuario(user_id: int, current_user: UserInDB = Depends(require_master_or_tenant_admin())):
    """Bloqueia um usuário sem deletar."""
    db = get_database()
    try:
        db.conn.execute("ALTER TABLE users ADD COLUMN bloqueado INTEGER DEFAULT 0")
        db.conn.commit()
    except Exception:
        pass
    db.conn.execute("UPDATE users SET bloqueado = 1 WHERE id = ?", (user_id,))
    db.conn.commit()
    return {"status": "success", "message": f"Usuário {user_id} bloqueado"}


@router.put("/users/{user_id}/desbloquear")
def desbloquear_usuario(user_id: int, current_user: UserInDB = Depends(require_master_or_tenant_admin())):
    """Desbloqueia um usuário."""
    db = get_database()
    db.conn.execute("UPDATE users SET bloqueado = 0 WHERE id = ?", (user_id,))
    db.conn.commit()
    return {"status": "success", "message": f"Usuário {user_id} desbloqueado"}


# =========================================================================
# Último Acesso
# =========================================================================

@router.get("/users/{user_id}/atividade")
def atividade_usuario(user_id: int, current_user: UserInDB = Depends(require_master_or_tenant_admin())):
    """Retorna atividade recente de um usuário."""
    db = get_database()
    user = db.conn.execute("SELECT id, username, full_name, role, criado_em FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    ultimo_login = db.conn.execute(
        "SELECT criado_em FROM audit_logs WHERE user_id = ? AND action = 'LOG_IN' ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    total_acoes = db.conn.execute(
        "SELECT COUNT(*) as c FROM audit_logs WHERE user_id = ?", (user_id,)
    ).fetchone()["c"]
    
    ultimas = db.conn.execute(
        "SELECT action, entity_type, criado_em FROM audit_logs WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (user_id,)
    ).fetchall()
    
    return {
        "status": "success",
        "usuario": dict(user),
        "ultimo_login": dict(ultimo_login)["criado_em"] if ultimo_login else None,
        "total_acoes": total_acoes,
        "ultimas_acoes": [dict(r) for r in ultimas],
    }


# =========================================================================
# Estatísticas por Tenant
# =========================================================================

@router.get("/tenants/{tenant_id}/stats")
def stats_tenant(tenant_id: int, current_user: UserInDB = Depends(require_role("master"))):
    """Estatísticas de uso por tenant."""
    db = get_database()
    
    usuarios = db.conn.execute("SELECT COUNT(*) as c FROM users WHERE tenant_id = ?", (tenant_id,)).fetchone()["c"]
    
    tenant = db.conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    
    captacoes = db.conn.execute("SELECT COUNT(*) as c FROM captacoes WHERE tenant_id = ?", (tenant_id,)).fetchone()["c"]
    
    execucoes = db.conn.execute("""
        SELECT COUNT(*) as c FROM execucoes_captacao e
        JOIN captacoes c ON e.captacao_id = c.id
        WHERE c.tenant_id = ?
    """, (tenant_id,)).fetchone()["c"]
    
    acoes = db.conn.execute("SELECT COUNT(*) as c FROM audit_logs WHERE tenant_id = ?", (tenant_id,)).fetchone()["c"]
    
    return {
        "status": "success",
        "tenant": dict(tenant),
        "usuarios": usuarios,
        "captacoes": captacoes,
        "execucoes": execucoes,
        "acoes_auditoria": acoes,
    }
    return None
