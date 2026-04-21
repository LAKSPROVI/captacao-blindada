"""
Backup Automático para CAPTAÇÃO BLINDADA.

Backup automático do banco de dados.
"""
import logging
import os
import shutil
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import sqlite3

log = logging.getLogger("captacao.backup")


# =============================================================================
# Backup Manager
# =============================================================================

class BackupManager:
    """
    Gerenciador de backups automáticos.
    """
    
    def __init__(self):
        self._backups_dir = "/app/data/backups"
        self._max_backups = 10
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False
    
    def configure(
        self,
        backups_dir: str = "/app/data/backups",
        max_backups: int = 10,
    ):
        """Configura backup."""
        self._backups_dir = backups_dir
        self._max_backups = max_backups
        
        # Cria diretório
        os.makedirs(backups_dir, exist_ok=True)
    
    def create_backup(
        self,
        db_path: str = "/app/data/captacao_blindada.db",
        name: Optional[str] = None,
    ) -> Optional[str]:
        """Cria backup."""
        if not os.path.exists(db_path):
            log.error(f"[Backup] Banco não encontrado: {db_path}")
            return None
        
        # Nome padrão
        if not name:
            name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        backup_path = os.path.join(self._backups_dir, f"captacao_{name}.db")
        
        try:
            # SQLite backup
            conn = sqlite3.connect(db_path)
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            conn.close()
            backup_conn.close()
            
            log.info(f"[Backup] Criado: {backup_path}")
            return backup_path
        
        except Exception as e:
            log.error(f"[Backup] Erro: {e}")
            return None
    
    def restore(
        self,
        backup_path: str,
        db_path: str = "/app/data/captacao_blindada.db",
    ) -> bool:
        """Restaura backup."""
        if not os.path.exists(backup_path):
            log.error(f"[Backup] Arquivo não encontrado: {backup_path}")
            return False
        
        try:
            # Backup original
            temp_path = db_path + ".temp"
            if os.path.exists(db_path):
                shutil.copy2(db_path, temp_path)
            
            # Restaura
            conn = sqlite3.connect(backup_path)
            target = sqlite3.connect(db_path)
            conn.backup(target)
            conn.close()
            target.close()
            
            log.info(f"[Backup] Restaurado de: {backup_path}")
            return True
        
        except Exception as e:
            log.error(f"[Backup] Erro ao restaurar: {e}")
            return False
    
    def list_backups(self) -> List[Dict]:
        """Lista backups disponíveis."""
        if not os.path.exists(self._backups_dir):
            return []
        
        backups = []
        for f in os.listdir(self._backups_dir):
            if f.startswith("captacao_") and f.endswith(".db"):
                path = os.path.join(self._backups_dir, f)
                stat = os.stat(path)
                backups.append({
                    "name": f,
                    "path": path,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                })
        
        # Ordena por data
        backups.sort(key=lambda x: x["created"], reverse=True)
        return backups
    
    def rotate_backups(self):
        """Remove backups antigos."""
        backups = self.list_backups()
        
        if len(backups) > self._max_backups:
            for backup in backups[self._max_backups:]:
                try:
                    os.remove(backup["path"])
                    log.info(f"[Backup] Removido: {backup['name']}")
                except Exception as e:
                    log.error(f"[Backup] Erro ao remover {backup['name']}: {e}")
    
    def auto_backup(
        self,
        db_path: str = "/app/data/captacao_blindada.db",
        interval_hours: int = 24,
    ):
        """
        Inicia backup automático.
        
        Use em background thread.
        """
        def run():
            while self._running:
                try:
                    # Criar backup
                    self.create_backup(db_path)
                    
                    # Rotacionar
                    self.rotate_backups()
                
                except Exception as e:
                    log.error(f"[Backup] Erro: {e}")
                
                # Aguarda
                time.sleep(interval_hours * 3600)
        
        self._running = True
        self._scheduler_thread = threading.Thread(target=run, daemon=True)
        self._scheduler_thread.start()
        log.info(f"[Backup] Agendado a cada {interval_hours} horas")
    
    def stop(self):
        """Para backup automático."""
        self._running = False


# =============================================================================
# Instância Global
# =============================================================================

_backup_manager: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    """Retorna gerenciador de backup."""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager


log.info("Backup manager loaded")