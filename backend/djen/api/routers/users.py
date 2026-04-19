import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from djen.api.auth import get_current_user, require_role, require_master_or_tenant_admin, UserInDB, hash_password
from djen.api.schemas import (
    TenantResponse, TenantCreateRequest, TenantUpdateRequest,
    UserResponse, UserCreateRequest, UserUpdateRequest
)
from djen.api.app import get_database

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
            raise HTTPException(status_code=403, detail="Aspenas master pode mover usuarios entre tenants")
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
    return None
