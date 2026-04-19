"""
Agentes Especializados - Sistema Multi-Agentes Juridico.

Cada agente e responsavel por um aspecto especifico do enriquecimento
de dados processuais. Todos herdam de BaseAgent e sao registrados
automaticamente via decorator @register_agent.

Camadas de execucao (automatico via dependencias):
  Camada 1: validador, coletor_datajud, coletor_djen (paralelo)
  Camada 2: extrator_entidades, analisador_movimentacoes (paralelo)
  Camada 3: classificador_causa, extrator_valores, analisador_cronologia (paralelo)
  Camada 4: calculador_prazos, analisador_risco (paralelo)
  Camada 5: gerador_resumo (depende de tudo)
"""

import re
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from djen.agents.canonical_model import (
    ProcessoCanonical, Advogado, ParteProcessual, Movimentacao,
    Comunicacao, ValorPecuniario, Prazo, EventoTimeline,
    IndicadorRisco, StatusProcesso, NivelRisco, PoloProcessual,
    TipoParte, FaseProcessual,
)
from djen.agents.orchestrator import BaseAgent, register_agent

log = logging.getLogger("captacao.agents.specialized")


# =========================================================================
# Camada 1: Coleta de dados brutos
# =========================================================================

@register_agent
class ValidadorProcessual(BaseAgent):
    """Valida e normaliza o numero do processo CNJ."""

    name = "validador"
    description = "Validacao e normalizacao do numero do processo"
    depends_on = []
    priority = 1

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        num = p.numero_processo.strip()
        # Remover formatacao
        num_limpo = re.sub(r"[.\-/]", "", num)

        # Se ja esta formatado (NNNNNNN-DD.AAAA.J.TR.OOOO)
        match = re.match(r"^(\d{7})-?(\d{2})\.?(\d{4})\.?(\d{1,2})\.?(\d{2})\.?(\d{4})$", num)
        if match:
            p.numero_formatado = f"{match.group(1)}-{match.group(2)}.{match.group(3)}.{match.group(4)}.{match.group(5)}.{match.group(6)}"
            num_limpo = "".join(match.groups())

        # Se tem 20 digitos puros
        if re.match(r"^\d{20}$", num_limpo):
            n = num_limpo
            p.numero_formatado = p.numero_formatado or f"{n[:7]}-{n[7:9]}.{n[9:13]}.{n[13]}.{n[14:16]}.{n[16:20]}"

            # Extrair justica do digito J (posicao 13)
            justica_map = {"1": "stj", "2": "stm", "3": "tse", "4": "trt",
                           "5": "federal", "6": "militar_estadual",
                           "7": "militar_federal", "8": "estadual", "9": "trabalho"}
            j = n[13]
            p.justica = justica_map.get(j, "desconhecida")

            # Extrair tribunal (posicoes 14-15)
            tr = n[14:16]
            p.numero_processo = num_limpo

        if not p.numero_formatado:
            p.numero_formatado = num

        p.fontes_consultadas = []
        return p


@register_agent
class ColetorDatajud(BaseAgent):
    """Coleta metadados do processo via API DataJud."""

    name = "coletor_datajud"
    description = "Coleta metadados processuais do DataJud (CNJ)"
    depends_on = ["validador"]
    priority = 1

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        from djen.sources.datajud import DatajudSource

        source = DatajudSource()
        tribunal = p.tribunal

        # Se tribunal nao definido, tentar detectar pelo numero
        if not tribunal:
            tribunal = self._detect_tribunal(p.numero_processo)

        if not tribunal:
            self.log.warning("Tribunal nao identificado para %s", p.numero_processo)
            return p

        resultados = source.buscar(
            termo=re.sub(r"[.\-]", "", p.numero_processo),
            tribunal=tribunal.lower(),
        )

        if resultados:
            pub = resultados[0]
            raw = pub.raw_data or {}
            p.raw_datajud = raw

            # Preencher dados basicos
            p.tribunal = p.tribunal or raw.get("tribunal", tribunal.upper())
            p.classe_processual = raw.get("classe", {}).get("nome")
            p.classe_codigo = raw.get("classe", {}).get("codigo")
            p.orgao_julgador = raw.get("orgaoJulgador", {}).get("nome")
            p.orgao_codigo = raw.get("orgaoJulgador", {}).get("codigo")
            p.municipio_ibge = raw.get("orgaoJulgador", {}).get("codigoMunicipioIBGE")
            p.grau = raw.get("grau")
            p.data_ajuizamento = raw.get("dataAjuizamento")
            p.formato_origem = raw.get("formato", {}).get("nome")
            p.sistema_origem = raw.get("sistema", {}).get("nome")
            p.nivel_sigilo = raw.get("nivelSigilo", 0)

            # Assuntos
            for assunto in raw.get("assuntos", []):
                nome = assunto.get("nome", "")
                codigo = assunto.get("codigo")
                if nome and nome not in p.assuntos:
                    p.assuntos.append(nome)
                if codigo and codigo not in p.assuntos_codigos:
                    p.assuntos_codigos.append(codigo)

            # Movimentacoes
            for mov in raw.get("movimentos", []):
                p.movimentacoes.append(Movimentacao(
                    codigo=mov.get("codigo"),
                    nome=mov.get("nome", ""),
                    data=mov.get("dataHora", ""),
                    complemento="; ".join(
                        f"{c.get('nome', '')}: {c.get('valor', '')}"
                        for c in mov.get("complementosTabelados", [])
                    ) or None,
                ))

            p.total_movimentacoes = len(p.movimentacoes)
            if p.movimentacoes:
                p.ultima_movimentacao = p.movimentacoes[0]
                p.data_ultima_movimentacao = p.movimentacoes[0].data

            p.fontes_consultadas.append("datajud")

        return p

    def _detect_tribunal(self, numero: str) -> Optional[str]:
        """Detecta tribunal pelo numero do processo."""
        num = re.sub(r"[.\-]", "", numero)
        if len(num) >= 16:
            j = num[13]  # Justica
            tr = num[14:16]  # Tribunal
            if j == "8":  # Estadual
                tj_map = {"26": "tjsp", "19": "tjrj", "13": "tjmg", "21": "tjrs",
                           "16": "tjpr", "24": "tjsc", "05": "tjba", "17": "tjpe",
                           "06": "tjce", "09": "tjgo", "07": "tjdft", "12": "tjes",
                           "14": "tjpa", "10": "tjma", "11": "tjmt", "12": "tjms",
                           "02": "tjal", "20": "tjrn", "15": "tjpb", "25": "tjse",
                           "18": "tjpi", "04": "tjam", "22": "tjro", "01": "tjac",
                           "03": "tjap", "23": "tjrr", "27": "tjto"}
                return tj_map.get(tr, f"tj{tr}")
            elif j == "5" or j == "4":  # Federal
                return f"trf{tr}" if int(tr) <= 6 else f"trt{tr}"
        return None


@register_agent
class ColetorDjen(BaseAgent):
    """Coleta comunicacoes processuais via API DJEN."""

    name = "coletor_djen"
    description = "Coleta comunicacoes processuais do DJEN (intimacoes, citacoes)"
    depends_on = ["validador"]
    priority = 1

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        from djen.sources.djen_source import DjenSource

        source = DjenSource()
        resultados = source.buscar_por_processo(p.numero_formatado or p.numero_processo)

        if resultados:
            p.raw_djen = [r.raw_data for r in resultados]
            for pub in resultados:
                raw = pub.raw_data or {}

                # Extrair advogados destinatarios
                advs = []
                for dest_adv in raw.get("destinatarioadvogados", []):
                    adv_data = dest_adv.get("advogado", {})
                    advs.append(Advogado(
                        nome=adv_data.get("nome", ""),
                        oab=adv_data.get("numero_oab"),
                        uf_oab=adv_data.get("uf_oab"),
                    ))

                p.comunicacoes.append(Comunicacao(
                    id=raw.get("id"),
                    tipo=raw.get("tipoComunicacao", "Intimacao"),
                    data_disponibilizacao=raw.get("data_disponibilizacao", ""),
                    texto=raw.get("texto"),
                    meio=raw.get("meiocompleto", raw.get("meio")),
                    orgao=raw.get("nomeOrgao"),
                    destinatarios=[d.get("nome", "") for d in raw.get("destinatarios", [])],
                    advogados_destinatarios=advs,
                ))

            p.total_comunicacoes = len(p.comunicacoes)
            p.tribunal = p.tribunal or (resultados[0].raw_data or {}).get("siglaTribunal")
            p.fontes_consultadas.append("djen_api")

        return p


@register_agent
class ColetorLocal(BaseAgent):
    """Coleta dados ja capturados e armazenados localmente na tabela publicacoes."""

    name = "coletor_local"
    description = "Recupera publicacoes e movimentacoes ja capturadas localmente no banco de dados"
    depends_on = ["validador"]
    priority = 1

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        from djen.api.app import get_database
        try:
            db = get_database()
        except Exception as e:
            self.log.warning("Banco de dados indisponivel para ColetorLocal: %s", e)
            return p

        # Buscar publicacoes locais pelo numero do processo
        numero = p.numero_processo
        numero_fmt = p.numero_formatado

        # Query buscando por numero limpo ou formatado
        sql = "SELECT id, fonte, data_publicacao, conteudo, movimentos, advogados FROM publicacoes WHERE numero_processo = ? OR numero_processo = ?"
        rows = db.conn.execute(sql, (numero, numero_fmt)).fetchall()

        if not rows:
            return p

        import json
        # Deduplicacao basica para evitar re-adicionar o que ja foi coletado pelas APIs
        com_ids = {c.id for c in p.comunicacoes if c.id}
        mov_hashes = {f"{m.data}_{m.nome[:50]}" for m in p.movimentacoes}

        for row in rows:
            fonte = row["fonte"]
            data_pub = row["data_publicacao"]

            if fonte == "datajud":
                # Mapear para Movimentacao
                nome_mov = row["movimentos"] or row["conteudo"][:200]
                mov_key = f"{data_pub}_{nome_mov[:50]}"

                if mov_key not in mov_hashes:
                    p.movimentacoes.append(Movimentacao(
                        nome=nome_mov,
                        data=data_pub,
                        complemento=row["conteudo"],
                        tipo="local_datajud"
                    ))
                    mov_hashes.add(mov_key)

            elif fonte == "djen_api":
                # Mapear para Comunicacao
                local_id = row["id"]
                if local_id not in com_ids:
                    advs = []
                    try:
                        advs_raw = json.loads(row["advogados"]) if row["advogados"] else []
                        for a in advs_raw:
                            if isinstance(a, dict):
                                advs.append(Advogado(
                                    nome=a.get("nome", ""),
                                    oab=a.get("oab"),
                                    uf_oab=a.get("uf")
                                ))
                    except Exception:
                        pass

                    p.comunicacoes.append(Comunicacao(
                        id=local_id,
                        tipo="Publicação Local",
                        data_disponibilizacao=data_pub,
                        texto=row["conteudo"],
                        advogados_destinatarios=advs
                    ))
                    com_ids.add(local_id)

        p.total_movimentacoes = len(p.movimentacoes)
        p.total_comunicacoes = len(p.comunicacoes)
        p.fontes_consultadas.append("db_local")

        return p


# =========================================================================
# Camada 2: Extracao e analise primaria
# =========================================================================

@register_agent
class ExtratorEntidades(BaseAgent):
    """Extrai partes, advogados e entidades das comunicacoes."""

    name = "extrator_entidades"
    description = "Extracao de partes, advogados e entidades juridicas"
    depends_on = ["coletor_djen", "coletor_datajud"]
    priority = 2

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        partes_map = {}  # nome -> ParteProcessual
        advogados_map = {}  # oab -> Advogado

        # Extrair de comunicacoes DJEN
        for com in p.comunicacoes:
            for dest in com.destinatarios:
                if dest and dest not in partes_map:
                    partes_map[dest] = ParteProcessual(
                        nome=dest,
                        tipo=self._detect_tipo_parte(dest),
                    )
            for adv in com.advogados_destinatarios:
                key = f"{adv.oab}/{adv.uf_oab}" if adv.oab else adv.nome
                if key not in advogados_map:
                    advogados_map[key] = adv

        # Extrair de texto das comunicacoes (regex)
        for com in p.comunicacoes:
            if not com.texto:
                continue
            # Extrair padroes de OAB
            oab_pattern = r"OAB[:/]?\s*([A-Z]{2})\s*(\d{3,6})|(\d{3,6})[/-]([A-Z]{2})"
            for m in re.finditer(oab_pattern, com.texto):
                uf = m.group(1) or m.group(4)
                num = m.group(2) or m.group(3)
                key = f"{num}/{uf}"
                if key not in advogados_map:
                    advogados_map[key] = Advogado(nome="", oab=num, uf_oab=uf)

            # Detectar polo pelas palavras-chave
            texto_upper = com.texto.upper()
            for nome, parte in partes_map.items():
                if parte.polo == PoloProcessual.desconhecido:
                    idx = texto_upper.find(nome.upper())
                    if idx > 0:
                        context = texto_upper[max(0, idx-50):idx]
                        if any(w in context for w in ["AUTOR", "REQUERENTE", "IMPETRANTE", "RECLAMANTE"]):
                            parte.polo = PoloProcessual.ativo
                        elif any(w in context for w in ["REU", "RÉU", "REQUERIDO", "IMPETRADO", "RECLAMADO"]):
                            parte.polo = PoloProcessual.passivo

        p.partes = list(partes_map.values())
        p.advogados = list(advogados_map.values())
        p.total_partes = len(p.partes)
        return p

    def _detect_tipo_parte(self, nome: str) -> TipoParte:
        nome_upper = nome.upper()
        # Entes publicos
        if any(w in nome_upper for w in ["ESTADO ", "MUNICIPIO ", "MUNICÍPIO ", "UNIAO",
                                          "FAZENDA", "INSS", "IBAMA", "ANVISA", "DETRAN"]):
            return TipoParte.ente_publico
        # PJ
        if any(w in nome_upper for w in ["LTDA", "S/A", "S.A.", "EIRELI", "LTDA.",
                                          "BANCO ", "SEGURADORA", "TELECOM", "ENERGI"]):
            return TipoParte.pessoa_juridica
        return TipoParte.pessoa_fisica


@register_agent
class AnalisadorMovimentacoes(BaseAgent):
    """Analisa movimentacoes e classifica tipos."""

    name = "analisador_movimentacoes"
    description = "Analise e classificacao de movimentacoes processuais"
    depends_on = ["coletor_datajud"]
    priority = 2

    # Mapeamento de codigos CNJ para tipos
    TIPOS_MOV = {
        26: "distribuicao", 36: "distribuicao",
        11: "despacho", 12: "despacho",
        3: "decisao", 7: "decisao",
        22: "sentenca", 210: "sentenca", 220: "sentenca",
        193: "recurso", 194: "recurso", 195: "recurso",
        848: "transito_julgado",
        246: "arquivamento", 245: "arquivamento",
        981: "publicacao", 60: "publicacao",
        51: "peticao", 85: "juntada",
    }

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        for mov in p.movimentacoes:
            if mov.codigo and mov.codigo in self.TIPOS_MOV:
                mov.tipo = self.TIPOS_MOV[mov.codigo]
            elif mov.nome:
                nome_lower = mov.nome.lower()
                if "sentença" in nome_lower or "sentenca" in nome_lower:
                    mov.tipo = "sentenca"
                elif "despacho" in nome_lower:
                    mov.tipo = "despacho"
                elif "decisão" in nome_lower or "decisao" in nome_lower:
                    mov.tipo = "decisao"
                elif "recurso" in nome_lower or "apelação" in nome_lower:
                    mov.tipo = "recurso"
                elif "distribuí" in nome_lower or "distribui" in nome_lower:
                    mov.tipo = "distribuicao"
                elif "arquiv" in nome_lower:
                    mov.tipo = "arquivamento"
                elif "publicação" in nome_lower or "publicacao" in nome_lower:
                    mov.tipo = "publicacao"
                elif "trânsito" in nome_lower or "transito" in nome_lower:
                    mov.tipo = "transito_julgado"
                else:
                    mov.tipo = "outro"

        # Detectar status do processo pela ultima movimentacao
        if p.movimentacoes:
            ultima = p.movimentacoes[0]
            if ultima.tipo == "arquivamento":
                p.status = StatusProcesso.arquivado
            elif ultima.tipo == "transito_julgado":
                p.status = StatusProcesso.extinto
            else:
                p.status = StatusProcesso.ativo

            # Detectar data de sentenca
            for mov in p.movimentacoes:
                if mov.tipo == "sentenca" and not p.data_sentenca:
                    p.data_sentenca = mov.data
                if mov.tipo == "transito_julgado" and not p.data_transito_julgado:
                    p.data_transito_julgado = mov.data
                if mov.tipo == "distribuicao" and not p.data_distribuicao:
                    p.data_distribuicao = mov.data

        return p


# =========================================================================
# Camada 3: Analise secundaria
# =========================================================================

@register_agent
class ClassificadorCausa(BaseAgent):
    """Classifica area e fase do processo."""

    name = "classificador_causa"
    description = "Classificacao de area juridica e fase processual"
    depends_on = ["analisador_movimentacoes", "extrator_entidades"]
    priority = 3

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        # Classificar area pela classe e assuntos
        classe = (p.classe_processual or "").lower()
        assuntos_str = " ".join(p.assuntos).lower()
        texto = f"{classe} {assuntos_str}"

        if any(w in texto for w in ["criminal", "penal", "habeas corpus", "crime", "furto", "roubo", "homicidio"]):
            p.area = "criminal"
        elif any(w in texto for w in ["trabalh", "reclamação trabalhist", "clt", "fgts", "rescisão"]):
            p.area = "trabalhista"
        elif any(w in texto for w in ["fiscal", "tributár", "imposto", "icms", "issqn", "execução fiscal"]):
            p.area = "tributaria"
        elif any(w in texto for w in ["família", "divórcio", "aliment", "guarda", "inventário"]):
            p.area = "familia"
        elif any(w in texto for w in ["consumidor", "cdc", "produto", "serviço"]):
            p.area = "consumidor"
        else:
            p.area = "civel"

        # Classificar fase
        tipos_presentes = {m.tipo for m in p.movimentacoes if m.tipo}
        if "transito_julgado" in tipos_presentes:
            p.fase = FaseProcessual.execucao
        elif "recurso" in tipos_presentes:
            p.fase = FaseProcessual.recursal
        elif "sentenca" in tipos_presentes:
            p.fase = FaseProcessual.recursal
        elif p.movimentacoes:
            p.fase = FaseProcessual.conhecimento
        else:
            p.fase = FaseProcessual.desconhecida

        return p


@register_agent
class ExtratorValores(BaseAgent):
    """Extrai valores pecuniarios das comunicacoes."""

    name = "extrator_valores"
    description = "Extracao de valores monetarios (causa, condenacao, honorarios)"
    depends_on = ["coletor_djen"]
    priority = 3

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        # Regex para valores monetarios
        valor_pattern = r"R\$\s*([\d.,]+(?:\.\d{3})*(?:,\d{2})?)"

        for com in p.comunicacoes:
            if not com.texto:
                continue

            for m in re.finditer(valor_pattern, com.texto):
                valor_str = m.group(1).replace(".", "").replace(",", ".")
                try:
                    valor = float(valor_str)
                    if valor > 0.01:
                        # Detectar tipo pelo contexto
                        start = max(0, m.start() - 100)
                        context = com.texto[start:m.start()].lower()

                        tipo = "outros"
                        if "causa" in context or "valor da causa" in context:
                            tipo = "causa"
                            p.valor_causa = p.valor_causa or valor
                        elif "condenação" in context or "condenacao" in context:
                            tipo = "condenacao"
                        elif "honorári" in context or "honorari" in context:
                            tipo = "honorarios"
                        elif "custas" in context:
                            tipo = "custas"
                        elif "multa" in context:
                            tipo = "multa"
                        elif "indenização" in context or "indenizacao" in context:
                            tipo = "indenizacao"

                        p.valores.append(ValorPecuniario(
                            tipo=tipo,
                            valor=valor,
                            data_referencia=com.data_disponibilizacao,
                        ))
                except (ValueError, TypeError):
                    pass
        return p


@register_agent
class AnalisadorCronologia(BaseAgent):
    """Gera timeline interativa do processo."""

    name = "analisador_cronologia"
    description = "Geracao de timeline interativa com eventos processuais"
    depends_on = ["analisador_movimentacoes", "coletor_djen"]
    priority = 3

    # Relevancia por tipo de movimentacao
    RELEVANCIA = {
        "distribuicao": 9, "sentenca": 10, "decisao": 8, "recurso": 9,
        "transito_julgado": 10, "despacho": 4, "publicacao": 5,
        "peticao": 3, "juntada": 2, "arquivamento": 9, "outro": 3,
    }

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        # Eventos de movimentacoes
        for mov in p.movimentacoes:
            relevancia = self.RELEVANCIA.get(mov.tipo or "outro", 3)
            if relevancia >= 4:  # Filtrar eventos menores
                p.timeline.append(EventoTimeline(
                    data=mov.data,
                    titulo=mov.nome,
                    descricao=mov.complemento,
                    tipo=mov.tipo or "outro",
                    relevancia=relevancia,
                    agente_origem="analisador_cronologia",
                ))

        # Eventos de comunicacoes
        for com in p.comunicacoes:
            p.timeline.append(EventoTimeline(
                data=com.data_disponibilizacao,
                titulo=f"{com.tipo} - {com.orgao or 'N/A'}",
                descricao=(com.texto or "")[:200],
                tipo="comunicacao",
                relevancia=6,
                agente_origem="analisador_cronologia",
            ))

        # Ordenar por data (mais recente primeiro)
        p.timeline.sort(key=lambda e: e.data, reverse=True)

        # Calcular duracao
        if p.data_ajuizamento:
            try:
                dt_inicio = datetime.strptime(p.data_ajuizamento[:10], "%Y-%m-%d")
                p.duracao_dias = (datetime.now() - dt_inicio).days
            except (ValueError, TypeError):
                pass

        return p


# =========================================================================
# Camada 4: Analise avancada
# =========================================================================

@register_agent
class CalculadorPrazos(BaseAgent):
    """Calcula prazos remanescentes baseado nas comunicacoes."""

    name = "calculador_prazos"
    description = "Calculo de prazos processuais e alertas de urgencia"
    depends_on = ["coletor_djen", "analisador_movimentacoes"]
    priority = 4

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        hoje = datetime.now()

        for com in p.comunicacoes:
            if not com.texto:
                continue

            texto = com.texto.lower()

            # Detectar prazos no texto
            prazo_patterns = [
                (r"prazo de (\d+)\s*(?:\([\w\s]+\))?\s*dias?\s*(?:úteis|uteis)?", "manifestacao"),
                (r"no prazo de (\d+)\s*dias", "manifestacao"),
                (r"(\d+)\s*dias?\s*para\s*(?:se )?manifestar", "manifestacao"),
                (r"(\d+)\s*dias?\s*para\s*(?:cum\w+|pagar)", "cumprimento"),
                (r"(\d+)\s*dias?\s*para\s*(?:recorrer|recurso)", "recurso"),
            ]

            for pattern, tipo in prazo_patterns:
                m = re.search(pattern, texto)
                if m:
                    dias = int(m.group(1))
                    try:
                        dt_pub = datetime.strptime(com.data_disponibilizacao[:10], "%Y-%m-%d")
                        dt_fim = dt_pub + timedelta(days=dias)
                        dias_restantes = (dt_fim - hoje).days

                        p.prazos.append(Prazo(
                            tipo=tipo,
                            data_inicio=com.data_disponibilizacao,
                            data_fim=dt_fim.strftime("%Y-%m-%d"),
                            dias_restantes=dias_restantes,
                            descricao=f"Prazo de {dias} dias ({tipo})",
                            urgente=dias_restantes <= 5,
                        ))
                    except (ValueError, TypeError):
                        pass

        # Ordenar por urgencia
        p.prazos.sort(key=lambda pr: pr.dias_restantes if pr.dias_restantes is not None else 9999)
        if p.prazos:
            p.prazo_mais_urgente = p.prazos[0]

        return p


@register_agent
class AnalisadorRisco(BaseAgent):
    """Analisa indicadores de risco processual."""

    name = "analisador_risco"
    description = "Avaliacao de riscos processuais multidimensional"
    depends_on = ["classificador_causa", "calculador_prazos", "extrator_valores"]
    priority = 4

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        indicadores = []
        scores = []

        # 1. Risco de prazo
        if p.prazos:
            prazo_urgente = p.prazo_mais_urgente
            if prazo_urgente and prazo_urgente.dias_restantes is not None:
                if prazo_urgente.dias_restantes <= 0:
                    indicadores.append(IndicadorRisco(
                        categoria="prazo", nivel=NivelRisco.critico, score=1.0,
                        descricao=f"Prazo VENCIDO ha {abs(prazo_urgente.dias_restantes)} dias",
                        recomendacao="Verificar possibilidade de justificativa ou recurso",
                    ))
                    scores.append(1.0)
                elif prazo_urgente.dias_restantes <= 3:
                    indicadores.append(IndicadorRisco(
                        categoria="prazo", nivel=NivelRisco.alto, score=0.8,
                        descricao=f"Prazo vence em {prazo_urgente.dias_restantes} dia(s)",
                        recomendacao="Acao imediata necessaria",
                    ))
                    scores.append(0.8)
                elif prazo_urgente.dias_restantes <= 10:
                    indicadores.append(IndicadorRisco(
                        categoria="prazo", nivel=NivelRisco.medio, score=0.5,
                        descricao=f"Prazo vence em {prazo_urgente.dias_restantes} dias",
                    ))
                    scores.append(0.5)
                else:
                    scores.append(0.2)
        else:
            scores.append(0.3)

        # 2. Risco procedimental (duracao)
        if p.duracao_dias:
            if p.duracao_dias > 1825:  # 5 anos
                indicadores.append(IndicadorRisco(
                    categoria="procedimental", nivel=NivelRisco.alto, score=0.7,
                    descricao=f"Processo com {p.duracao_dias} dias ({p.duracao_dias//365} anos)",
                    recomendacao="Avaliar morosidade e possibilidade de peticao de urgencia",
                ))
                scores.append(0.7)
            elif p.duracao_dias > 730:  # 2 anos
                scores.append(0.4)
            else:
                scores.append(0.2)

        # 3. Risco de merito (fase)
        if p.fase == FaseProcessual.recursal:
            indicadores.append(IndicadorRisco(
                categoria="merito", nivel=NivelRisco.medio, score=0.5,
                descricao="Processo em fase recursal - resultado incerto",
            ))
            scores.append(0.5)
        elif p.fase == FaseProcessual.execucao:
            indicadores.append(IndicadorRisco(
                categoria="merito", nivel=NivelRisco.baixo, score=0.3,
                descricao="Processo em fase de execucao - merito ja decidido",
            ))
            scores.append(0.3)

        # 4. Risco financeiro
        if p.valor_causa and p.valor_causa > 100000:
            indicadores.append(IndicadorRisco(
                categoria="financeiro", nivel=NivelRisco.alto, score=0.7,
                descricao=f"Valor da causa elevado: R$ {p.valor_causa:,.2f}",
                recomendacao="Monitorar de perto e preparar provisao",
            ))
            scores.append(0.7)

        # Score geral
        p.indicadores_risco = indicadores
        if scores:
            p.risco_score = round(sum(scores) / len(scores), 2)
        else:
            p.risco_score = 0.3

        # Nivel geral
        if p.risco_score >= 0.8:
            p.risco_geral = NivelRisco.critico
        elif p.risco_score >= 0.6:
            p.risco_geral = NivelRisco.alto
        elif p.risco_score >= 0.4:
            p.risco_geral = NivelRisco.medio
        elif p.risco_score >= 0.2:
            p.risco_geral = NivelRisco.baixo
        else:
            p.risco_geral = NivelRisco.muito_baixo

        return p


# =========================================================================
# Camada 5: Consolidacao
# =========================================================================

@register_agent
class GeradorResumo(BaseAgent):
    """Gera resumo executivo e pontos de atencao."""

    name = "gerador_resumo"
    description = "Geracao de resumo executivo, pontos de atencao e proximos passos"
    depends_on = ["analisador_risco", "analisador_cronologia"]
    priority = 5

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        partes_str = []
        for parte in p.partes[:4]:
            polo = {"ativo": "Autor", "passivo": "Réu"}.get(parte.polo.value, "Parte") if parte.polo else "Parte"
            partes_str.append(f"{polo}: {parte.nome}")

        # Resumo executivo
        resumo_parts = []
        resumo_parts.append(f"Processo {p.numero_formatado or p.numero_processo}")
        if p.tribunal:
            resumo_parts.append(f"tramitando no {p.tribunal}")
        if p.classe_processual:
            resumo_parts.append(f"({p.classe_processual})")
        if p.orgao_julgador:
            resumo_parts.append(f"perante {p.orgao_julgador}")
        resumo_parts.append(".")

        if p.area:
            resumo_parts.append(f"Area: {p.area.title()}.")
        if p.fase != FaseProcessual.desconhecida:
            resumo_parts.append(f"Fase: {p.fase.value.title()}.")
        if p.status != StatusProcesso.desconhecido:
            resumo_parts.append(f"Status: {p.status.value.title()}.")

        if partes_str:
            resumo_parts.append(f"Partes: {'; '.join(partes_str)}.")

        if p.duracao_dias:
            anos = p.duracao_dias // 365
            meses = (p.duracao_dias % 365) // 30
            resumo_parts.append(f"Duracao: {anos} ano(s) e {meses} mes(es).")

        if p.valor_causa:
            resumo_parts.append(f"Valor da causa: R$ {p.valor_causa:,.2f}.")

        p.resumo_executivo = " ".join(resumo_parts)

        # Situacao atual
        sit_parts = []
        if p.ultima_movimentacao:
            sit_parts.append(f"Ultima movimentacao: {p.ultima_movimentacao.nome} em {p.ultima_movimentacao.data[:10]}")
        if p.total_comunicacoes > 0:
            sit_parts.append(f"{p.total_comunicacoes} comunicacao(es) no DJEN")
        p.resumo_situacao_atual = ". ".join(sit_parts) + "." if sit_parts else None

        # Pontos de atencao
        p.pontos_atencao = []
        for ind in p.indicadores_risco:
            if ind.nivel in (NivelRisco.alto, NivelRisco.critico):
                p.pontos_atencao.append(f"[{ind.nivel.value.upper()}] {ind.descricao}")

        if p.prazo_mais_urgente and p.prazo_mais_urgente.dias_restantes is not None:
            if p.prazo_mais_urgente.dias_restantes <= 5:
                p.pontos_atencao.insert(0,
                    f"PRAZO URGENTE: {p.prazo_mais_urgente.descricao} "
                    f"(vence em {p.prazo_mais_urgente.dias_restantes} dia(s))")

        # Proximos passos
        p.proximos_passos = []
        if p.status == StatusProcesso.ativo:
            if p.fase == FaseProcessual.conhecimento:
                p.proximos_passos.append("Acompanhar instrucao processual e prazos")
            elif p.fase == FaseProcessual.recursal:
                p.proximos_passos.append("Monitorar julgamento do recurso")
            elif p.fase == FaseProcessual.execucao:
                p.proximos_passos.append("Verificar cumprimento de obrigacao")

        if p.prazos:
            for prazo in p.prazos[:3]:
                if prazo.dias_restantes is not None and prazo.dias_restantes > 0:
                    p.proximos_passos.append(
                        f"Cumprir prazo de {prazo.tipo} ate {prazo.data_fim}"
                    )

        if p.total_comunicacoes > 0:
            p.proximos_passos.append("Verificar novas intimacoes no DJEN")

        return p


# =========================================================================
# Camada 4b: Agentes adicionais avancados
# =========================================================================

@register_agent
class AnalisadorJurisprudencia(BaseAgent):
    """Identifica jurisprudencia correlata baseada nos assuntos e classe processual."""

    name = "analisador_jurisprudencia"
    description = "Identificacao de jurisprudencia correlata e precedentes"
    depends_on = ["classificador_causa"]
    priority = 4

    # Base simplificada de teses frequentes por area/assunto
    TESES_BASE = {
        "consumidor": [
            {"tese": "Dano moral in re ipsa em inscricao indevida em cadastro de inadimplentes",
             "referencia": "Sumula 385/STJ", "favorabilidade": 0.7},
            {"tese": "Inversao do onus da prova em relacoes de consumo",
             "referencia": "Art. 6, VIII, CDC", "favorabilidade": 0.8},
            {"tese": "Responsabilidade objetiva do fornecedor",
             "referencia": "Art. 14, CDC", "favorabilidade": 0.7},
        ],
        "trabalhista": [
            {"tese": "Onus da prova na dispensa discriminatoria",
             "referencia": "Sumula 443/TST", "favorabilidade": 0.6},
            {"tese": "Horas extras e registro de ponto",
             "referencia": "Sumula 338/TST", "favorabilidade": 0.5},
        ],
        "tributaria": [
            {"tese": "Exclusao do ICMS da base de calculo do PIS/COFINS",
             "referencia": "RE 574.706/PR (STF)", "favorabilidade": 0.8},
            {"tese": "Prescricao quinquenal de credito tributario",
             "referencia": "Art. 174, CTN", "favorabilidade": 0.6},
        ],
        "familia": [
            {"tese": "Fixacao de alimentos com base na necessidade e possibilidade",
             "referencia": "Art. 1.694, CC", "favorabilidade": 0.5},
            {"tese": "Guarda compartilhada como regra",
             "referencia": "Art. 1.584, CC", "favorabilidade": 0.6},
        ],
        "civel": [
            {"tese": "Responsabilidade civil por dano moral",
             "referencia": "Art. 186 c/c 927, CC", "favorabilidade": 0.5},
            {"tese": "Boa-fe objetiva nas relacoes contratuais",
             "referencia": "Art. 422, CC", "favorabilidade": 0.5},
        ],
        "criminal": [
            {"tese": "Principio da insignificancia",
             "referencia": "HC 84.412/SP (STF)", "favorabilidade": 0.4},
            {"tese": "Regime inicial de cumprimento de pena",
             "referencia": "Sumula 719/STF", "favorabilidade": 0.5},
        ],
    }

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        area = (p.area or "civel").lower()
        teses = self.TESES_BASE.get(area, self.TESES_BASE["civel"])

        # Adicionar teses como pontos de atencao informativos
        jurisprudencia_info = []
        for tese in teses:
            jurisprudencia_info.append(
                f"[JURISPRUDENCIA] {tese['tese']} - Ref: {tese['referencia']} "
                f"(favorabilidade: {tese['favorabilidade']*100:.0f}%)"
            )

        # Adicionar ao campo de pontos de atencao (sem duplicar)
        for info in jurisprudencia_info:
            if info not in p.pontos_atencao:
                p.pontos_atencao.append(info)

        # Adicionar indicador de risco baseado em jurisprudencia
        favorabilidade_media = sum(t["favorabilidade"] for t in teses) / len(teses) if teses else 0.5

        if favorabilidade_media < 0.4:
            nivel = NivelRisco.alto
        elif favorabilidade_media < 0.6:
            nivel = NivelRisco.medio
        else:
            nivel = NivelRisco.baixo

        p.indicadores_risco.append(IndicadorRisco(
            categoria="jurisprudencia",
            nivel=nivel,
            score=round(1 - favorabilidade_media, 2),
            descricao=f"Jurisprudencia na area '{area}' com favorabilidade media de {favorabilidade_media*100:.0f}%",
            recomendacao="Verificar teses aplicaveis ao caso concreto",
        ))

        return p


@register_agent
class ValidadorConformidade(BaseAgent):
    """Verifica conformidade legal e procedimental do processo."""

    name = "validador_conformidade"
    description = "Validacao de conformidade legal e procedimental"
    depends_on = ["analisador_movimentacoes", "calculador_prazos"]
    priority = 4

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        alertas = []

        # 1. Verificar se ha prazos vencidos sem manifestacao
        for prazo in p.prazos:
            if prazo.dias_restantes is not None and prazo.dias_restantes < 0:
                alertas.append(
                    f"[CONFORMIDADE] Prazo de {prazo.tipo} vencido ha "
                    f"{abs(prazo.dias_restantes)} dias sem manifestacao identificada"
                )

        # 2. Verificar tempo sem movimentacao
        if p.data_ultima_movimentacao:
            try:
                dt_ultima = datetime.strptime(p.data_ultima_movimentacao[:10], "%Y-%m-%d")
                dias_parado = (datetime.now() - dt_ultima).days
                if dias_parado > 365:
                    alertas.append(
                        f"[CONFORMIDADE] Processo sem movimentacao ha {dias_parado} dias "
                        f"- risco de prescricao intercorrente"
                    )
                    p.indicadores_risco.append(IndicadorRisco(
                        categoria="conformidade",
                        nivel=NivelRisco.alto,
                        score=0.8,
                        descricao=f"Processo parado ha {dias_parado} dias",
                        recomendacao="Verificar prescricao intercorrente e peticionar nos autos",
                    ))
                elif dias_parado > 180:
                    alertas.append(
                        f"[CONFORMIDADE] Processo sem movimentacao ha {dias_parado} dias"
                    )
                    p.indicadores_risco.append(IndicadorRisco(
                        categoria="conformidade",
                        nivel=NivelRisco.medio,
                        score=0.5,
                        descricao=f"Processo sem movimentacao ha {dias_parado} dias",
                        recomendacao="Acompanhar e avaliar necessidade de impulsionar o processo",
                    ))
            except (ValueError, TypeError):
                pass

        # 3. Verificar sigilo
        if p.nivel_sigilo and p.nivel_sigilo > 0:
            alertas.append(
                f"[CONFORMIDADE] Processo com nivel de sigilo {p.nivel_sigilo} - "
                "acesso restrito"
            )

        # 4. Verificar consistencia de dados
        if p.movimentacoes and not p.classe_processual:
            alertas.append(
                "[CONFORMIDADE] Classe processual nao identificada apesar de "
                "movimentacoes existentes"
            )

        if p.comunicacoes and not p.partes:
            alertas.append(
                "[CONFORMIDADE] Comunicacoes sem partes identificadas - "
                "verificar extracao de entidades"
            )

        # Adicionar alertas unicos
        for alerta in alertas:
            if alerta not in p.pontos_atencao:
                p.pontos_atencao.append(alerta)

        return p


@register_agent
class PrevisorResultado(BaseAgent):
    """Gera previsao de resultado baseada em heuristicas processuais."""

    name = "previsor_resultado"
    description = "Previsao heuristica de resultado processual"
    depends_on = ["analisador_risco", "analisador_jurisprudencia", "classificador_causa"]
    priority = 5

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        # Calcular previsao baseada em multiplos fatores
        fatores = {}

        # 1. Fase processual
        fase_scores = {
            FaseProcessual.conhecimento: 0.5,
            FaseProcessual.recursal: 0.4,  # Mais incerto
            FaseProcessual.execucao: 0.7,  # Merito ja decidido
            FaseProcessual.cumprimento: 0.8,
            FaseProcessual.liquidacao: 0.7,
            FaseProcessual.cautelar: 0.5,
            FaseProcessual.desconhecida: 0.5,
        }
        fatores["fase"] = fase_scores.get(p.fase, 0.5)

        # 2. Duracao
        if p.duracao_dias:
            if p.duracao_dias > 2555:  # 7 anos
                fatores["duracao"] = 0.3  # Muito longo, tende a ser desfavoravel
            elif p.duracao_dias > 1460:  # 4 anos
                fatores["duracao"] = 0.4
            elif p.duracao_dias > 730:  # 2 anos
                fatores["duracao"] = 0.5
            else:
                fatores["duracao"] = 0.6
        else:
            fatores["duracao"] = 0.5

        # 3. Indicadores de risco
        risco_invertido = 1.0 - p.risco_score
        fatores["risco"] = risco_invertido

        # 4. Jurisprudencia (buscar indicador)
        for ind in p.indicadores_risco:
            if ind.categoria == "jurisprudencia":
                fatores["jurisprudencia"] = 1.0 - ind.score
                break
        else:
            fatores["jurisprudencia"] = 0.5

        # 5. Complexidade (numero de partes e movimentacoes)
        if p.total_partes > 10 or p.total_movimentacoes > 100:
            fatores["complexidade"] = 0.3
        elif p.total_partes > 5 or p.total_movimentacoes > 50:
            fatores["complexidade"] = 0.4
        else:
            fatores["complexidade"] = 0.6

        # Media ponderada
        pesos = {"fase": 2.0, "duracao": 1.0, "risco": 2.0,
                 "jurisprudencia": 1.5, "complexidade": 1.0}
        score_total = sum(fatores[k] * pesos[k] for k in fatores)
        peso_total = sum(pesos[k] for k in fatores)
        previsao_score = round(score_total / peso_total, 2) if peso_total > 0 else 0.5

        # Classificar previsao
        if previsao_score >= 0.7:
            previsao_texto = "Favoravel"
            nivel = NivelRisco.baixo
        elif previsao_score >= 0.5:
            previsao_texto = "Moderado"
            nivel = NivelRisco.medio
        elif previsao_score >= 0.3:
            previsao_texto = "Desfavoravel"
            nivel = NivelRisco.alto
        else:
            previsao_texto = "Muito desfavoravel"
            nivel = NivelRisco.critico

        # Adicionar indicador de previsao
        p.indicadores_risco.append(IndicadorRisco(
            categoria="previsao_resultado",
            nivel=nivel,
            score=round(1 - previsao_score, 2),
            descricao=(
                f"Previsao heuristica: {previsao_texto} "
                f"(score {previsao_score*100:.0f}%). "
                f"Fatores: {', '.join(f'{k}={v:.0%}' for k, v in fatores.items())}"
            ),
            recomendacao=(
                "Resultado favoravel previsto - manter estrategia" if previsao_score >= 0.6
                else "Considerar acordo ou revisao de estrategia processual"
            ),
        ))

        # Adicionar ao resumo
        p.pontos_atencao.append(
            f"[PREVISAO] Resultado {previsao_texto} (confianca: {previsao_score*100:.0f}%)"
        )

        return p
