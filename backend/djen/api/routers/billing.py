import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from djen.api.auth import get_current_user, require_role, require_master_or_tenant_admin, UserInDB
from djen.api.schemas import (
    FunctionCostResponse, FunctionCostUpdateRequest, UsageLogResponse, BillingStatsResponse
)
from djen.api.app import get_database

log = logging.getLogger("captacao.billing")

router = APIRouter(prefix="/api/billing", tags=["Tarifacao"])

# =========================================================================
# Gerenciamento de Custos (Master)
# =========================================================================

@router.get("/costs", response_model=List[FunctionCostResponse])
def listar_custos():
    """Lista o custo atual de todas as funcoes."""
    db = get_database()
    rows = db.conn.execute("SELECT * FROM function_costs").fetchall()
    return [FunctionCostResponse(**dict(r)) for r in rows]

@router.put("/costs/{function_name}", response_model=FunctionCostResponse)
def definir_custo(function_name: str, cost: FunctionCostUpdateRequest, current_user: UserInDB = Depends(require_role("master"))):
    """(Master) Define ou atualiza o custo em tokens de uma funcao."""
    db = get_database()
    
    # Upsert logic
    row = db.conn.execute("SELECT * FROM function_costs WHERE function_name = ?", (function_name,)).fetchone()
    if row:
        sets = []
        vals = []
        if cost.description is not None:
            sets.append("description = ?")
            vals.append(cost.description)
        if cost.cost_tokens is not None:
            sets.append("cost_tokens = ?")
            vals.append(cost.cost_tokens)
            
        if sets:
            sets.append("atualizado_em = datetime('now')")
            vals.append(function_name)
            db.conn.execute(f"UPDATE function_costs SET {', '.join(sets)} WHERE function_name = ?", vals)
    else:
        desc = cost.description or ""
        tokens = cost.cost_tokens or 0
        db.conn.execute(
            "INSERT INTO function_costs (function_name, description, cost_tokens) VALUES (?, ?, ?)",
            (function_name, desc, tokens)
        )
    
    db.conn.commit()
    new_row = db.conn.execute("SELECT * FROM function_costs WHERE function_name = ?", (function_name,)).fetchone()
    return FunctionCostResponse(**dict(new_row))

# =========================================================================
# Uso e Relatorios
# =========================================================================

@router.get("/usage", response_model=List[UsageLogResponse])
def listar_uso(limit: int = 100, offset: int = 0, current_user: UserInDB = Depends(require_master_or_tenant_admin())):
    """(Tenant Admin) Ve logs de uso do seu tenant. (Master) Ve de todos."""
    db = get_database()
    
    query = "SELECT * FROM usage_logs"
    params = []
    
    if current_user.role != "master":
        query += " WHERE tenant_id = ?"
        params.append(current_user.tenant_id)
        
    query += " ORDER BY data_uso DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = db.conn.execute(query, params).fetchall()
    return [UsageLogResponse(**dict(r)) for r in rows]

@router.get("/stats", response_model=BillingStatsResponse)
def obter_estatisticas(tenant_id: int = None, current_user: UserInDB = Depends(require_master_or_tenant_admin())):
    """Obtem dashboard de gastos formatado."""
    db = get_database()
    
    target_tenant = current_user.tenant_id
    if current_user.role == "master" and tenant_id:
        target_tenant = tenant_id

    # Saldo atual
    t_row = db.conn.execute("SELECT saldo_tokens FROM tenants WHERE id = ?", (target_tenant,)).fetchone()
    if not t_row:
        raise HTTPException(status_code=404, detail="Tenant nao encontrado")
        
    saldo = t_row["saldo_tokens"]
    
    # Gasto total do mes
    total_gasto = db.conn.execute(
        "SELECT SUM(tokens_used) as total FROM usage_logs WHERE tenant_id = ? AND strftime('%Y-%m', data_uso) = strftime('%Y-%m', 'now')",
        (target_tenant,)
    ).fetchone()["total"] or 0
    
    # Gasto por funcao
    funcoes = db.conn.execute(
        "SELECT function_name, SUM(tokens_used) as total FROM usage_logs WHERE tenant_id = ? GROUP BY function_name",
        (target_tenant,)
    ).fetchall()
    
    gasto_por_funcao = {r["function_name"]: r["total"] for r in funcoes}
    
    return BillingStatsResponse(
        tenant_id=target_tenant,
        saldo_atual=saldo,
        total_gasto_mes=total_gasto,
        gasto_por_funcao=gasto_por_funcao
    )

# Funcao interna utilitaria para ser chamada do codigo
def registrar_uso(tenant_id: int, user_id: int, function_name: str, count: int = 1, metadata: str = None):
    db = get_database()
    # Pega valor da funcao
    row = db.conn.execute("SELECT cost_tokens FROM function_costs WHERE function_name = ?", (function_name,)).fetchone()
    cost_per_exec = row["cost_tokens"] if row else 0
    
    total_cost = cost_per_exec * count
    if total_cost > 0:
        db.conn.execute(
            "INSERT INTO usage_logs (tenant_id, user_id, function_name, tokens_used, metadata) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, user_id, function_name, total_cost, metadata)
        )
        db.conn.execute("UPDATE tenants SET saldo_tokens = saldo_tokens - ? WHERE id = ?", (total_cost, tenant_id))
        db.conn.commit()
