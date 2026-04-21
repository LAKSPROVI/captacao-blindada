"""
Captacao Service - Facade para execucao de captacoes automatizadas.

Orquestra:
- Execucao de buscas parametrizadas (DataJud + DJEN)
- Deduplicacao de resultados
- Registro de execucoes no banco
- Enriquecimento automatico (pipeline multi-agentes)
- Deteccao de diff entre execucoes
- Preview (dry-run)
"""

import json
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

BRASILIA_TZ = ZoneInfo("America/Sao_Paulo")


def agora_brasilia() -> datetime:
    """Retorna datetime atual no fuso de Brasília."""
    return datetime.now(tz=BRASILIA_TZ)

log = logging.getLogger("captacao.captacao_service")


class CaptacaoService:
    """
    Facade principal para executar captacoes automatizadas.

    Uso:
        from djen.agents.captacao_service import get_captacao_service
        service = get_captacao_service()
        result = service.executar(captacao_id=1)
    """

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self._lock = threading.Lock()

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

    def _montar_parametros_datajud(self, cap: Dict) -> Optional[Dict]:
        """Monta parametros de busca para DataJud conforme tipo_busca."""
        tipo = cap["tipo_busca"]

        data_inicio = cap.get("data_inicio")
        data_fim = cap.get("data_fim")
        modalidade = cap.get("modalidade", "recorrente")
        
        # Logica de modalidade
        if modalidade == "recorrente":
            if not data_fim:
                data_fim = agora_brasilia().strftime("%Y-%m-%d")
            if not data_inicio:
                # Default 30 dias se nao especificado
                data_inicio = (agora_brasilia() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        if tipo == "processo":
            numero = cap.get("numero_processo")
            if not numero:
                return None
            tribunal = cap.get("tribunal")
            if not tribunal:
                # Tentar extrair do numero CNJ (digitos 14-15 = justica.tribunal)
                limpo = numero.replace("-", "").replace(".", "")
                if len(limpo) >= 18:
                    j = limpo[13]
                    tr = limpo[14:16]
                    # Fallback: buscar em tribunais prioritarios
                    return {
                        "numero_processo": numero, 
                        "tribunal": None, 
                        "tamanho": 5, 
                        "data_inicio": data_inicio, 
                        "data_fim": data_fim
                    }
            return {
                "numero_processo": numero,
                "tribunal": tribunal,
                "tamanho": 10,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
            }

        elif tipo == "classe":
            tribunal = cap.get("tribunal")
            if not tribunal:
                return None
            return {
                "tribunal": tribunal,
                "classe_codigo": cap.get("classe_codigo"),
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "tamanho": 20,
            }

        elif tipo == "assunto":
            tribunal = cap.get("tribunal")
            if not tribunal:
                return None
            return {
                "tribunal": tribunal,
                "assunto_codigo": cap.get("assunto_codigo"),
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "tamanho": 20,
            }

        elif tipo == "tribunal_geral":
            tribunal = cap.get("tribunal")
            if not tribunal:
                return None
            return {
                "tribunal": tribunal,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "tamanho": 20,
            }

        # oab, nome_parte, nome_advogado -> DataJud nao suporta
        return None

    def _montar_parametros_djen(self, cap: Dict) -> Optional[Dict]:
        """Monta parametros de busca para DJEN conforme tipo_busca."""
        tipo = cap["tipo_busca"]

        data_inicio = cap.get("data_inicio")
        data_fim = cap.get("data_fim")
        modalidade = cap.get("modalidade", "recorrente")
        
        if modalidade == "recorrente":
            if not data_fim:
                data_fim = agora_brasilia().strftime("%Y-%m-%d")
            if not data_inicio:
                data_inicio = (agora_brasilia() - timedelta(days=30)).strftime("%Y-%m-%d")

        base = {
            "tribunal": cap.get("tribunal"),
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "tipo_comunicacao": cap.get("tipo_comunicacao"),
            "orgao_id": cap.get("orgao_id"),
        }

        if tipo == "processo":
            numero = cap.get("numero_processo")
            if not numero:
                return None
            base["numero_processo"] = numero
            return base

        elif tipo == "oab":
            oab = cap.get("numero_oab")
            uf = cap.get("uf_oab")
            if not oab:
                return None
            base["numero_oab"] = oab
            base["uf_oab"] = uf or "SP"
            return base

        elif tipo == "nome_parte":
            nome = cap.get("nome_parte")
            if not nome:
                return None
            base["nome_parte"] = nome
            return base

        elif tipo == "nome_advogado":
            nome = cap.get("nome_advogado")
            if not nome:
                return None
            base["nome_advogado"] = nome
            return base

        elif tipo in ("tribunal_geral",):
            if not cap.get("tribunal"):
                return None
            return base

        # classe, assunto -> DJEN nao suporta diretamente
        return None

    def _executar_datajud(self, cap: Dict, params: Dict) -> Tuple[List, Dict]:
        """Executa busca no DataJud e retorna (resultados, info)."""
        source = self._get_source("datajud")
        if not source:
            return [], {"erro": "DatajudSource indisponivel"}

        try:
            # Se tem tribunal, busca direto
            tribunal = params.get("tribunal")
            tribunais_buscar = []

            if tribunal:
                tribunais_buscar = [tribunal]
            elif cap.get("tribunais"):
                tribunais_buscar = [t.strip().lower() for t in cap["tribunais"].split(",")]
            else:
                # Busca em tribunais prioritarios
                from djen.sources.datajud import TRIBUNAIS_PRIORITARIOS
                tribunais_buscar = TRIBUNAIS_PRIORITARIOS[:5]

            all_results = []
            for trib in tribunais_buscar:
                try:
                    results = source.buscar(
                        termo=params.get("numero_processo", ""),
                        tribunal=trib,
                        data_inicio=params.get("data_inicio"),
                        data_fim=params.get("data_fim"),
                        classe_codigo=params.get("classe_codigo"),
                        assunto_codigo=params.get("assunto_codigo"),
                        tamanho=params.get("tamanho", 10),
                    )
                    all_results.extend(results)
                except Exception as e:
                    log.warning("[Captacao] DataJud %s erro: %s", trib, e)

            return all_results, {"tribunais": tribunais_buscar, "total": len(all_results)}

        except Exception as e:
            log.error("[Captacao] DataJud erro geral: %s", e)
            return [], {"erro": str(e)}

    def _executar_djen(self, cap: Dict, params: Dict) -> Tuple[List, Dict]:
        """Executa busca no DJEN e retorna (resultados, info)."""
        source = self._get_source("djen_api")
        if not source:
            return [], {"erro": "DjenSource indisponivel"}

        try:
            tipo = cap["tipo_busca"]
            max_paginas = 10  # Até 10 páginas = ~1000 resultados

            if tipo == "processo":
                results = source.buscar_por_processo(params["numero_processo"])
            elif tipo == "oab":
                results = source.buscar_paginado(
                    paginas=max_paginas,
                    termo=f"OAB {params['numero_oab']}/{params.get('uf_oab', 'SP')}",
                    numero_oab=params["numero_oab"],
                    uf_oab=params.get("uf_oab", "SP"),
                    data_inicio=params.get("data_inicio"),
                    data_fim=params.get("data_fim"),
                )
            elif tipo == "nome_parte":
                results = source.buscar_paginado(
                    paginas=max_paginas,
                    termo=params["nome_parte"],
                    tribunal=params.get("tribunal"),
                    data_inicio=params.get("data_inicio"),
                    data_fim=params.get("data_fim"),
                    nome_parte=params["nome_parte"],
                )
            elif tipo == "nome_advogado":
                results = source.buscar_paginado(
                    paginas=max_paginas,
                    termo=params["nome_advogado"],
                    tribunal=params.get("tribunal"),
                    data_inicio=params.get("data_inicio"),
                    data_fim=params.get("data_fim"),
                    nome_advogado=params["nome_advogado"],
                )
            elif tipo == "tribunal_geral":
                results = source.buscar_paginado(
                    paginas=max_paginas,
                    termo="",
                    tribunal=params.get("tribunal"),
                    data_inicio=params.get("data_inicio"),
                    data_fim=params.get("data_fim"),
                )
            else:
                return [], {"info": f"DJEN nao suporta tipo_busca={tipo}"}

            return results, {"total": len(results)}

        except Exception as e:
            log.error("[Captacao] DJEN erro: %s", e)
            return [], {"erro": str(e)}

    def executar(self, captacao_id: int) -> Dict[str, Any]:
        """
        Executa uma captacao: busca em todas as fontes configuradas,
        salva novos resultados, opcionalmente enriquece.

        Returns:
            Dict com status, totais, execucoes, etc.
        """
        db = self._get_db()
        cap = db.obter_captacao(captacao_id)
        if not cap:
            return {"status": "error", "erro": f"Captacao {captacao_id} nao encontrada"}

        if not cap.get("ativo"):
            return {"status": "error", "erro": "Captacao inativa"}

        t0 = time.time()
        fontes = (cap.get("fontes") or "datajud,djen_api").split(",")
        fontes = [f.strip() for f in fontes]

        log.info("[Captacao] Executando #%d '%s' (tipo=%s, fontes=%s)",
                 captacao_id, cap["nome"], cap["tipo_busca"], fontes)

        resultado = {
            "captacao_id": captacao_id,
            "status": "completed",
            "fontes_consultadas": [],
            "total_resultados": 0,
            "novos_resultados": 0,
            "execucoes": [],
            "processos_enriquecidos": [],
            "erro": None,
        }

        for fonte_nome in fontes:
            # Montar parametros
            if fonte_nome == "datajud":
                params = self._montar_parametros_datajud(cap)
            elif fonte_nome == "djen_api":
                params = self._montar_parametros_djen(cap)
            else:
                continue

            if params is None:
                log.info("[Captacao] %s: parametros insuficientes para tipo_busca=%s, pulando",
                         fonte_nome, cap["tipo_busca"])
                continue

            # Registrar inicio
            exec_id = db.iniciar_execucao_captacao(
                captacao_id, fonte_nome,
                json.dumps(params, ensure_ascii=False, default=str),
            )

            te0 = time.time()
            try:
                # Executar busca
                if fonte_nome == "datajud":
                    results, info = self._executar_datajud(cap, params)
                elif fonte_nome == "djen_api":
                    results, info = self._executar_djen(cap, params)
                else:
                    results, info = [], {}

                # Deduplicar e salvar
                novos = 0
                for pub in results:
                    pub_dict = pub.to_dict() if hasattr(pub, "to_dict") else pub
                    saved = db.salvar_publicacao_captacao(pub_dict, captacao_id)
                    if saved:
                        novos += 1

                duracao = int((time.time() - te0) * 1000)

                db.finalizar_execucao_captacao(
                    exec_id, "completed", len(results), novos, duracao,
                )

                resultado["fontes_consultadas"].append(fonte_nome)
                resultado["total_resultados"] += len(results)
                resultado["novos_resultados"] += novos
                resultado["execucoes"].append({
                    "id": exec_id,
                    "fonte": fonte_nome,
                    "status": "completed",
                    "total_resultados": len(results),
                    "novos_resultados": novos,
                    "duracao_ms": duracao,
                })

                log.info("[Captacao] %s: %d resultados, %d novos (%dms)",
                         fonte_nome, len(results), novos, duracao)

            except Exception as e:
                duracao = int((time.time() - te0) * 1000)
                db.finalizar_execucao_captacao(exec_id, "failed", 0, 0, duracao, str(e))
                resultado["execucoes"].append({
                    "id": exec_id,
                    "fonte": fonte_nome,
                    "status": "failed",
                    "total_resultados": 0,
                    "novos_resultados": 0,
                    "duracao_ms": duracao,
                    "erro": str(e),
                })
                log.error("[Captacao] %s erro: %s", fonte_nome, e)

        # Atualizar captacao pos-execucao
        db.atualizar_captacao_pos_execucao(
            captacao_id,
            resultado["total_resultados"],
            resultado["novos_resultados"],
            cap.get("intervalo_minutos", 120),
        )

        # Enriquecimento automatico
        if cap.get("auto_enriquecer") and resultado["novos_resultados"] > 0:
            try:
                from djen.agents.pipeline_service import get_pipeline_service
                pipeline = get_pipeline_service()

                # Coletar numeros de processo unicos das publicacoes novas
                pubs = db.buscar_publicacoes_captacao(captacao_id, limite=resultado["novos_resultados"])
                processos_vistos = set()
                for pub in pubs:
                    num = pub.get("numero_processo")
                    if num and num not in processos_vistos:
                        processos_vistos.add(num)
                        try:
                            pipeline.analisar(num)
                            resultado["processos_enriquecidos"].append(num)
                            log.info("[Captacao] Enriquecido: %s", num)
                        except Exception as e:
                            log.warning("[Captacao] Enriquecimento falhou para %s: %s", num, e)

            except ImportError:
                log.warning("[Captacao] Pipeline service nao disponivel para enriquecimento")

        resultado["tempo_total_ms"] = int((time.time() - t0) * 1000)

        log.info("[Captacao] #%d completa: %d resultados, %d novos, %dms",
                 captacao_id, resultado["total_resultados"],
                 resultado["novos_resultados"], resultado["tempo_total_ms"])

        return resultado

    def executar_todas(self) -> List[Dict[str, Any]]:
        """
        Executa todas as captacoes pendentes (ativas, nao pausadas,
        proxima_execucao <= agora, dentro do horario permitido).
        """
        db = self._get_db()
        agora = agora_brasilia()
        agora_iso = agora.isoformat()

        pendentes = db.listar_captacoes_pendentes(agora_iso)
        executaveis = []

        for cap in pendentes:
            if self._dentro_do_horario(cap, agora):
                executaveis.append(cap)

        if not executaveis:
            log.info("[Captacao] Nenhuma captacao pendente no horario")
            return []

        log.info("[Captacao] Executando %d captacoes pendentes", len(executaveis))
        resultados = []

        for cap in executaveis:
            try:
                result = self.executar(cap["id"])
                resultados.append(result)
            except Exception as e:
                log.error("[Captacao] Erro executando #%d: %s", cap["id"], e)
                resultados.append({
                    "captacao_id": cap["id"],
                    "status": "error",
                    "erro": str(e),
                })

        return resultados

    def preview(self, params: Dict) -> List[Dict]:
        """
        Executa busca sem salvar (dry-run) para validar parametros.

        Args:
            params: Dict com tipo_busca, fontes, e parametros de busca

        Returns:
            Lista de publicacoes encontradas (sem salvar)
        """
        tipo = params.get("tipo_busca", "processo")
        fontes = params.get("fontes", ["datajud", "djen_api"])
        if isinstance(fontes, str):
            fontes = fontes.split(",")

        # Converter fontes enum para string se necessario
        fontes_str = []
        for f in fontes:
            fontes_str.append(f.value if hasattr(f, "value") else str(f))

        cap = {
            "tipo_busca": tipo,
            "numero_processo": params.get("numero_processo"),
            "numero_oab": params.get("numero_oab"),
            "uf_oab": params.get("uf_oab"),
            "nome_parte": params.get("nome_parte"),
            "nome_advogado": params.get("nome_advogado"),
            "tribunal": params.get("tribunal"),
            "tribunais": params.get("tribunais"),
            "classe_codigo": params.get("classe_codigo"),
            "assunto_codigo": params.get("assunto_codigo"),
            "orgao_id": params.get("orgao_id"),
            "tipo_comunicacao": params.get("tipo_comunicacao"),
            "data_inicio": params.get("data_inicio"),
            "data_fim": params.get("data_fim"),
        }

        all_results = []

        for fonte_nome in fontes_str:
            if fonte_nome == "datajud":
                p = self._montar_parametros_datajud(cap)
                if p:
                    results, _ = self._executar_datajud(cap, p)
                    all_results.extend(results)
            elif fonte_nome == "djen_api":
                p = self._montar_parametros_djen(cap)
                if p:
                    results, _ = self._executar_djen(cap, p)
                    all_results.extend(results)

        # Converter para dicts
        return [
            pub.to_dict() if hasattr(pub, "to_dict") else pub
            for pub in all_results
        ]

    def diff(self, captacao_id: int) -> Dict[str, Any]:
        """
        Compara resultados atuais vs anteriores para identificar novos.

        Returns:
            Dict com novos, total_novos, total_mantidos, resumo
        """
        db = self._get_db()

        # Pegar ultimas 2 execucoes completed
        execucoes = db.listar_execucoes_captacao(captacao_id, limite=10)
        completed = [e for e in execucoes if e["status"] == "completed"]

        if not completed:
            return {
                "captacao_id": captacao_id,
                "execucao_atual_id": None,
                "execucao_anterior_id": None,
                "novos": [],
                "total_novos": 0,
                "total_mantidos": 0,
                "total_atual": 0,
                "resumo": "Nenhuma execucao encontrada",
            }

        # Pegar publicacoes atuais
        pubs = db.buscar_publicacoes_captacao(captacao_id, limite=500)
        total_atual = len(pubs)

        # Calcular novos baseado na ultima execucao
        ultima = completed[0]
        novos_count = ultima.get("novos_resultados", 0)

        # Os "novos" sao as publicacoes mais recentes
        novos_pubs = pubs[:novos_count] if novos_count > 0 else []

        data_exec = ultima.get("inicio", "")[:16].replace("T", " ")
        resumo = (
            f"{novos_count} nova(s) publicacao(oes) encontrada(s) na ultima execucao "
            f"em {data_exec}" if novos_count > 0
            else f"Nenhuma nova publicacao na ultima execucao em {data_exec}"
        )

        return {
            "captacao_id": captacao_id,
            "execucao_atual_id": ultima.get("id"),
            "execucao_anterior_id": completed[1]["id"] if len(completed) > 1 else None,
            "novos": novos_pubs,
            "total_novos": novos_count,
            "total_mantidos": total_atual - novos_count,
            "total_atual": total_atual,
            "resumo": resumo,
        }

    @staticmethod
    def _dentro_do_horario(cap: Dict, agora: datetime) -> bool:
        """Verifica se a hora atual esta dentro da janela permitida."""
        try:
            h_ini = cap.get("horario_inicio", "06:00")
            h_fim = cap.get("horario_fim", "23:00")
            hi = int(h_ini.split(":")[0]) * 60 + int(h_ini.split(":")[1])
            hf = int(h_fim.split(":")[0]) * 60 + int(h_fim.split(":")[1])
            agora_min = agora.hour * 60 + agora.minute

            if agora_min < hi or agora_min > hf:
                return False

            # Verificar dia da semana (1=seg..7=dom, isoweekday)
            dias = cap.get("dias_semana", "1,2,3,4,5")
            dias_permitidos = [int(d.strip()) for d in dias.split(",") if d.strip()]
            if agora.isoweekday() not in dias_permitidos:
                return False

            return True
        except (ValueError, AttributeError):
            return True  # Se nao conseguir parsear, permite


# Singleton
_service: Optional[CaptacaoService] = None


def get_captacao_service() -> CaptacaoService:
    global _service
    if _service is None:
        _service = CaptacaoService()
    return _service
