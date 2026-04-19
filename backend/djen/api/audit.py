import logging
import hashlib
import json
import traceback
from typing import Optional, Any
from djen.api.app import get_database

log = logging.getLogger("captacao.audit")

def _hash_data(previous_hash: str, payload_str: str) -> str:
    """Gera um hash SHA-256 integrando o hash da linha anterior para simular cadeia."""
    raw = f"{previous_hash}|{payload_str}".encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def registrar_auditoria(
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    ip_address: Optional[str] = None
) -> None:
    """Registra uma acao no log de auditoria, criando um hash acorrentado."""
    try:
        db = get_database()
        
        # Obter o ultimo hash. Se master/seed (toda a db) entao um default.
        last_log = db.conn.execute("SELECT data_hash FROM audit_logs ORDER BY id DESC LIMIT 1").fetchone()
        previous_hash = last_log["data_hash"] if last_log else "0000000000000000000000000000000000000000000000000000000000000000"
        
        details_str = json.dumps(details, ensure_ascii=False) if details else ""
        
        # Montar a string canonica de payload
        payload_str = f"{action}:{entity_type}:{entity_id}:{tenant_id}:{user_id}:{details_str}"
        new_hash = _hash_data(previous_hash, payload_str)
        
        db.conn.execute(
            """INSERT INTO audit_logs 
               (tenant_id, user_id, action, entity_type, entity_id, details, ip_address, data_hash) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tenant_id, user_id, action, entity_type, entity_id, details_str, ip_address, new_hash)
        )
        db.conn.commit()
    except Exception as e:
        log.error("Erro critico ao registrar log de auditoria: %s", e)

def registrar_erro_sistema(
    function_name: str,
    error_type: str,
    error_message: str,
    stack_trace: Optional[str] = None,
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> None:
    """Registra um erro nao tratado no sistema."""
    try:
        db = get_database()
        db.conn.execute(
            """INSERT INTO system_errors 
               (tenant_id, user_id, function_name, error_type, error_message, stack_trace) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tenant_id, user_id, function_name, error_type, error_message, stack_trace)
        )
        db.conn.commit()
    except Exception as e:
        log.error("Erro muito critico ao gravar erro de sistema: %s", e)
