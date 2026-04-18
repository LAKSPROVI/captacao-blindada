"""
Monitor Service - Gerencia o agendamento e execucao dos monitoramentos DJEN.

Responsabilidades:
- Identificar monitorados que precisam de busca (conforme intervalo e horario)
- Executar buscas nas fontes configuradas (DataJud, DJEN API, etc)
- Calcular proxima execucao
- Registrar resultados no banco
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

log = logging.getLogger("captacao.monitor_service")

class MonitorService:
    """
    Service para gerenciar o ciclo de vida dos monitoramentos atomicos (termos, OAB, processos).
    """

    def __init__(self):
        pass

    def _get_db(self):
        from djen.api.app import get_database
        return get_database()

    def _get_source(self, fonte_nome: str):
        """Instancia lazy de fonte de dados."""
        if fonte_nome == "datajud":
            from djen.sources.datajud import DatajudSource
            return DatajudSource()
        elif fonte_nome == "djen_api":
            from djen.sources.djen_source import DjenSource
            return DjenSource()
        return None

    def calcular_proxima_busca(self, intervalo_min: int, h_ini: str, h_fim: str, dias_semana: str) -> str:
        """
        Calcula o proximo timestamp de busca respeitando a janela horaria e dias permitidos.
        """
        agora = datetime.now()
        proxima = agora + timedelta(minutes=intervalo_min)

        # Loop para encontrar o proximo slot valido (max 7 dias de tentativa para evitar loop infinito)
        for _ in range(7 * 24 * 4): # 15 min slots for 1 week
            # Verificar se 'proxima' esta dentro do horario
            try:
                ini_h, ini_m = map(int, h_ini.split(":"))
                fim_h, fim_m = map(int, h_fim.split(":"))
                
                proxima_min = proxima.hour * 60 + proxima.minute
                limite_ini = ini_h * 60 + ini_m
                limite_fim = fim_h * 60 + fim_m

                # Fora do horario? Puclamos para o inicio do proximo dia permitido
                if proxima_min < limite_ini:
                    proxima = proxima.replace(hour=ini_h, minute=ini_m, second=0, microsecond=0)
                elif proxima_min > limite_fim:
                    proxima = proxima + timedelta(days=1)
                    proxima = proxima.replace(hour=ini_h, minute=ini_m, second=0, microsecond=0)

                # Verificar dia da semana (1=seg..7=dom)
                permitidos = [int(d.strip()) for d in dias_semana.split(",") if d.strip()]
                if proxima.isoweekday() in permitidos:
                    break
                else:
                    # Pula para o proximo dia as 00:00 e reavalia
                    proxima = proxima + timedelta(days=1)
                    proxima = proxima.replace(hour=ini_h, minute=ini_m, second=0, microsecond=0)

            except Exception:
                break # Fallback se falhar o parse

        return proxima.isoformat()

    def executar_monitorado(self, mon: Dict) -> Dict[str, Any]:
        """Executa a busca para um monitorado especifico."""
        db = self._get_db()
        mon_id = mon["id"]
        valor = mon["valor"]
        fontes_str = mon.get("fontes") or "datajud,djen_api"
        fontes = [f.strip() for f in fontes_str.split(",")]
        
        log.info("[MonitorService] Executando #%d '%s' (%s)", mon_id, valor, fontes_str)
        
        total_encontrados = 0
        novos_encontrados = 0
        
        for fonte_nome in fontes:
            source = self._get_source(fonte_nome)
            if not source:
                continue
                
            try:
                t0 = time.time()
                resultados = source.buscar(
                    termo=valor,
                    tribunal=mon.get("tribunal"),
                )
                elapsed = int((time.time() - t0) * 1000)
                
                novas_na_fonte = 0
                for pub in resultados:
                    # Salva no banco (deduplicacao ja tratada no DB)
                    saved = db.salvar_publicacao(pub.to_dict(), mon_id)
                    if saved:
                        novas_na_fonte += 1
                
                total_encontrados += len(resultados)
                novos_encontrados += novas_na_fonte
                
                # Registrar a busca individual
                db.registrar_busca(
                    "monitor", fonte_nome, mon.get("tribunal"),
                    valor, len(resultados), "ok", elapsed
                )
                
            except Exception as e:
                log.error("[MonitorService] Erro em %s para %s: %s", fonte_nome, valor, e)
                db.registrar_busca(
                    "monitor", fonte_nome, mon.get("tribunal"),
                    valor, 0, "erro", 0, str(e)
                )

        # Calcular proxima execucao
        proxima = self.calcular_proxima_busca(
            int(mon.get("intervalo_minutos", 120)),
            mon.get("horario_inicio", "06:00"),
            mon.get("horario_fim", "23:00"),
            mon.get("dias_semana", "1,2,3,4,5")
        )
        
        # Atualizar monitorado
        db.atualizar_monitorado_pos_execucao(mon_id, total_encontrados, novos_encontrados, proxima)
        
        return {
            "id": mon_id,
            "total": total_encontrados,
            "novos": novos_encontrados,
            "proxima": proxima
        }

    def executar_todos_pendentes(self) -> List[Dict]:
        """Busca e executa todos os monitorados que estao na hora de rodar."""
        db = self._get_db()
        agora = datetime.now().isoformat()
        
        pendentes = db.listar_monitorados_pendentes(agora)
        if not pendentes:
            return []
            
        log.info("[MonitorService] Encontrados %d monitorados pendentes", len(pendentes))
        resultados = []
        
        for mon in pendentes:
            try:
                res = self.executar_monitorado(mon)
                resultados.append(res)
            except Exception as e:
                log.error("[MonitorService] Falha fatal no monitorado #%d: %s", mon["id"], e)
                
        return resultados

# Singleton
_service = None

def get_monitor_service() -> MonitorService:
    global _service
    if _service is None:
        _service = MonitorService()
    return _service
