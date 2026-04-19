"""
Agentes ML/NLP - Versoes aprimoradas dos agentes heuristicos.

Utilizam LLM (via API Gameron, compativel com OpenAI) para analise
mais sofisticada de processos judiciais. Cada agente ML possui fallback
automatico para a versao heuristica caso a API esteja indisponivel.

Ativacao via variavel de ambiente USE_ML_AGENTS=true.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests

from djen.agents.canonical_model import (
    FaseProcessual,
    IndicadorRisco,
    NivelRisco,
    ProcessoCanonical,
    StatusProcesso,
)
from djen.agents.orchestrator import BaseAgent, register_agent
from djen.api.database import Database
from djen.agents.specialized import (
    AnalisadorJurisprudencia,
    ClassificadorCausa,
    GeradorResumo,
    PrevisorResultado,
)

log = logging.getLogger("captacao.agents.ml")


# =========================================================================
# LLM Client
# =========================================================================

class LLMClient:
    """
    Wrapper para chamadas a API Gameron (OpenAI-compatible).

    Utiliza requests para chamar o endpoint de chat completions.
    Retorna None em caso de falha para permitir fallback heuristico.
    """

    BASE_URL = "https://api.gameron.io/v1/chat/completions"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    TIMEOUT = 30

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GAMERON_API_KEY")
        self.base_url = base_url or self.BASE_URL

        if not self.api_key:
            log.warning("GAMERON_API_KEY nao configurada - agentes ML usarao fallback heuristico")

    @property
    def available(self) -> bool:
        """Verifica se a API esta configurada."""
        return bool(self.api_key)

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        function_key: Optional[str] = None,
    ) -> Optional[str]:
        """
        Envia mensagem para o LLM e retorna a resposta como texto.
        Pode carregar configuracoes dinamicas do banco de dados se function_key for fornecido.
        """
        # Configuracoes padrao
        current_api_key = self.api_key
        current_base_url = self.base_url
        current_model = model or self.DEFAULT_MODEL
        current_enabled = True

        # Tentar carregar configuracao customizada do banco
        if function_key:
            try:
                db = Database()
                config = db.obter_ai_config(function_key)
                if config:
                    current_enabled = bool(config.get("enabled", True))
                    if not current_enabled:
                        log.info("[%s] IA desativada via configuracao", function_key)
                        return None
                    
                    if config.get("model_name"):
                        current_model = config["model_name"]
                    if config.get("api_key"):
                        current_api_key = config["api_key"]
                    if config.get("base_url"):
                        current_base_url = config["base_url"]
                    
                    # Logica de provedores
                    provider = config.get("provider", "").lower()
                    if provider and not config.get("base_url"):
                        PROVIDER_BASE_URLS = {
                            "openai": "https://api.openai.com/v1/chat/completions",
                            "anthropic": "https://api.anthropic.com/v1/messages",
                            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                            "google": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                            "ollama": "http://localhost:11434/v1/chat/completions",
                            "deepseek": "https://api.deepseek.com/chat/completions"
                        }
                        if provider in PROVIDER_BASE_URLS:
                            current_base_url = PROVIDER_BASE_URLS[provider]
            except Exception as e:
                log.warning("Erro ao carregar ai_config para %s: %s", function_key, e)

        if not current_api_key or not current_enabled:
            log.warning("[%s] IA desabilitada ou sem chave", function_key)
            return None

        # OpenAI-compatible payload
        payload = {
            "model": current_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

        headers = {
            "Authorization": f"Bearer {current_api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(
                current_base_url,
                json=payload,
                headers=headers,
                timeout=self.TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            elif "content" in data and isinstance(data["content"], list):
                return data["content"][0].get("text", "")
            return str(data)
        except requests.exceptions.Timeout:
            log.warning("LLM timeout apos %ds (%s)", self.TIMEOUT, current_base_url)
            return None
        except requests.exceptions.RequestException as exc:
            log.warning("LLM request falhou (%s): %s", current_base_url, exc)
            return None
        except Exception as exc:
            log.warning("Erro inesperado no LLM: %s", exc)
            return None


# Instancia global reutilizavel
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Retorna instancia singleton do LLMClient."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


# =========================================================================
# Helpers
# =========================================================================

def _parse_json_response(text: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Extrai JSON de uma resposta LLM, tolerando markdown code fences.

    Returns:
        Dicionario parseado ou None.
    """
    if not text:
        return None

    # Tentar parse direto
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Tentar extrair de code fence ```json ... ```
    import re
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Tentar encontrar primeiro { ... } ou [ ... ]
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

    return None


def _build_process_context(p: ProcessoCanonical) -> str:
    """Monta contexto textual do processo para envio ao LLM."""
    parts = [
        f"Numero: {p.numero_formatado or p.numero_processo}",
        f"Tribunal: {p.tribunal or 'N/A'}",
        f"Classe Processual: {p.classe_processual or 'N/A'}",
        f"Orgao Julgador: {p.orgao_julgador or 'N/A'}",
        f"Grau: {p.grau or 'N/A'}",
        f"Area: {p.area or 'N/A'}",
        f"Fase: {p.fase.value if p.fase else 'N/A'}",
        f"Status: {p.status.value if p.status else 'N/A'}",
        f"Data Ajuizamento: {p.data_ajuizamento or 'N/A'}",
        f"Duracao (dias): {p.duracao_dias or 'N/A'}",
        f"Valor da Causa: R$ {p.valor_causa:,.2f}" if p.valor_causa else "Valor da Causa: N/A",
        f"Assuntos: {', '.join(p.assuntos) if p.assuntos else 'N/A'}",
    ]

    if p.partes:
        partes_desc = []
        for parte in p.partes[:10]:
            polo = parte.polo.value if parte.polo else "desconhecido"
            partes_desc.append(f"  - {parte.nome} (polo: {polo}, tipo: {parte.tipo.value if parte.tipo else 'N/A'})")
        parts.append("Partes:\n" + "\n".join(partes_desc))

    if p.movimentacoes:
        movs_desc = []
        for mov in p.movimentacoes[:15]:
            movs_desc.append(f"  - [{mov.data[:10] if mov.data else 'N/A'}] {mov.nome} (tipo: {mov.tipo or 'N/A'})")
        parts.append(f"Movimentacoes ({p.total_movimentacoes} total, ultimas 15):\n" + "\n".join(movs_desc))

    if p.comunicacoes:
        coms_desc = []
        for com in p.comunicacoes[:5]:
            texto_resumo = (com.texto or "")[:300]
            coms_desc.append(
                f"  - [{com.data_disponibilizacao[:10] if com.data_disponibilizacao else 'N/A'}] "
                f"{com.tipo}: {texto_resumo}..."
            )
        parts.append(f"Comunicacoes ({p.total_comunicacoes} total, ultimas 5):\n" + "\n".join(coms_desc))

    if p.indicadores_risco:
        riscos_desc = []
        for ind in p.indicadores_risco:
            riscos_desc.append(f"  - [{ind.categoria}] {ind.nivel.value}: {ind.descricao}")
        parts.append("Indicadores de Risco:\n" + "\n".join(riscos_desc))

    if p.prazos:
        prazos_desc = []
        for prazo in p.prazos[:5]:
            prazos_desc.append(
                f"  - {prazo.tipo}: vence em {prazo.data_fim} "
                f"({prazo.dias_restantes} dias restantes, urgente: {prazo.urgente})"
            )
        parts.append("Prazos:\n" + "\n".join(prazos_desc))

    if p.valores:
        vals_desc = []
        for v in p.valores[:10]:
            vals_desc.append(f"  - {v.tipo}: R$ {v.valor:,.2f}")
        parts.append("Valores:\n" + "\n".join(vals_desc))

    return "\n".join(parts)


# =========================================================================
# Agente 1: ClassificadorCausaML
# =========================================================================

@register_agent
class ClassificadorCausaML(BaseAgent):
    """
    Classifica area juridica e fase processual usando LLM.
    Fallback: ClassificadorCausa (heuristico).
    """

    name = "classificador_causa_ml"
    description = "Classificacao de area juridica e fase processual via LLM"
    depends_on = ["analisador_movimentacoes", "extrator_entidades"]
    priority = 3

    use_llm = True

    SYSTEM_PROMPT = (
        "Voce e um especialista em direito processual brasileiro. "
        "Sua tarefa e classificar um processo judicial com base nos dados fornecidos.\n\n"
        "Classifique:\n"
        "1. **area**: a area juridica do processo. Opcoes: criminal, trabalhista, tributaria, "
        "familia, consumidor, civel, ambiental, administrativo, previdenciario, empresarial.\n"
        "2. **fase**: a fase processual atual. Opcoes: conhecimento, recursal, execucao, "
        "cumprimento, liquidacao, cautelar, desconhecida.\n\n"
        "Retorne SOMENTE um JSON valido no formato:\n"
        '{"area": "...", "fase": "...", "justificativa": "..."}\n\n'
        "Analise cuidadosamente a classe processual, os assuntos, as movimentacoes "
        "e o texto das comunicacoes para determinar a classificacao correta."
    )

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        if not self.use_llm:
            return self._fallback(p)

        llm = get_llm_client()
        if not llm.available:
            return self._fallback(p)

        context = _build_process_context(p)
        response = llm.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=f"Classifique o seguinte processo:\n\n{context}",
            max_tokens=500,
            function_key="classificacao"
        )

        parsed = _parse_json_response(response)
        if not parsed:
            self.log.info("[%s] LLM indisponivel ou resposta invalida, usando fallback heuristico", self.name)
            return self._fallback(p)

        try:
            area = parsed.get("area", "").lower().strip()
            fase_str = parsed.get("fase", "").lower().strip()

            areas_validas = {
                "criminal", "trabalhista", "tributaria", "familia", "consumidor",
                "civel", "ambiental", "administrativo", "previdenciario", "empresarial",
            }
            if area in areas_validas:
                p.area = area
            else:
                self.log.warning("[%s] Area invalida do LLM: '%s'", self.name, area)

            fase_map = {
                "conhecimento": FaseProcessual.conhecimento,
                "recursal": FaseProcessual.recursal,
                "execucao": FaseProcessual.execucao,
                "cumprimento": FaseProcessual.cumprimento,
                "liquidacao": FaseProcessual.liquidacao,
                "cautelar": FaseProcessual.cautelar,
                "desconhecida": FaseProcessual.desconhecida,
            }
            if fase_str in fase_map:
                p.fase = fase_map[fase_str]

            self.log.info("[%s] Classificacao via LLM: area=%s, fase=%s", self.name, p.area, p.fase)
        except Exception as exc:
            self.log.warning("[%s] Erro ao processar resposta LLM: %s", self.name, exc)
            return self._fallback(p)

        return p

    def _fallback(self, p: ProcessoCanonical) -> ProcessoCanonical:
        """Executa classificador heuristico como fallback."""
        self.log.info("[%s] Fallback para ClassificadorCausa heuristico", self.name)
        fallback = ClassificadorCausa()
        return fallback.execute(p)


# =========================================================================
# Agente 2: PrevisorResultadoML
# =========================================================================

@register_agent
class PrevisorResultadoML(BaseAgent):
    """
    Gera previsao de resultado processual usando LLM.
    Fallback: PrevisorResultado (heuristico).
    """

    name = "previsor_resultado_ml"
    description = "Previsao de resultado processual via LLM"
    depends_on = ["analisador_risco", "analisador_jurisprudencia", "classificador_causa"]
    priority = 5

    use_llm = True

    SYSTEM_PROMPT = (
        "Voce e um analista juridico senior especializado em previsao de resultados "
        "de processos judiciais brasileiros. Com base nos dados processuais fornecidos, "
        "faca uma analise preditiva do resultado.\n\n"
        "Considere: area do direito, fase processual, status, indicadores de risco, "
        "duracao do processo, tipos de partes envolvidas, valores em discussao, "
        "jurisprudencia aplicavel e historico de movimentacoes.\n\n"
        "Retorne SOMENTE um JSON valido no formato:\n"
        "{\n"
        '  "previsao": "favoravel" | "moderado" | "desfavoravel",\n'
        '  "confianca": 0.0 a 1.0,\n'
        '  "fundamentacao": "texto explicativo da analise",\n'
        '  "fatores_positivos": ["fator 1", "fator 2"],\n'
        '  "fatores_negativos": ["fator 1", "fator 2"]\n'
        "}"
    )

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        if not self.use_llm:
            return self._fallback(p)

        llm = get_llm_client()
        if not llm.available:
            return self._fallback(p)

        context = _build_process_context(p)
        response = llm.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=f"Analise e preveja o resultado deste processo:\n\n{context}",
            max_tokens=1500,
            function_key="previsao"
        )

        parsed = _parse_json_response(response)
        if not parsed:
            self.log.info("[%s] LLM indisponivel ou resposta invalida, usando fallback heuristico", self.name)
            return self._fallback(p)

        try:
            previsao = parsed.get("previsao", "moderado").lower().strip()
            confianca = float(parsed.get("confianca", 0.5))
            confianca = max(0.0, min(1.0, confianca))
            fundamentacao = parsed.get("fundamentacao", "")
            fatores_positivos = parsed.get("fatores_positivos", [])
            fatores_negativos = parsed.get("fatores_negativos", [])

            # Mapear previsao para nivel de risco
            previsao_map = {
                "favoravel": (NivelRisco.baixo, 0.3),
                "moderado": (NivelRisco.medio, 0.5),
                "desfavoravel": (NivelRisco.alto, 0.7),
            }
            nivel, score_default = previsao_map.get(previsao, (NivelRisco.medio, 0.5))
            score = round(1.0 - confianca if previsao == "favoravel" else confianca, 2)

            # Montar descricao detalhada
            descricao_parts = [
                f"Previsao via LLM: {previsao.title()} (confianca: {confianca:.0%}).",
            ]
            if fundamentacao:
                descricao_parts.append(f"Fundamentacao: {fundamentacao[:300]}")
            if fatores_positivos:
                descricao_parts.append(f"Fatores positivos: {'; '.join(fatores_positivos[:5])}")
            if fatores_negativos:
                descricao_parts.append(f"Fatores negativos: {'; '.join(fatores_negativos[:5])}")

            p.indicadores_risco.append(IndicadorRisco(
                categoria="previsao_resultado",
                nivel=nivel,
                score=score,
                descricao=" | ".join(descricao_parts),
                recomendacao=(
                    "Resultado favoravel previsto - manter estrategia"
                    if previsao == "favoravel"
                    else "Considerar acordo ou revisao de estrategia processual"
                ),
            ))

            p.pontos_atencao.append(
                f"[PREVISAO ML] Resultado {previsao.title()} (confianca: {confianca:.0%})"
            )

            self.log.info(
                "[%s] Previsao via LLM: %s (confianca: %.0f%%)",
                self.name, previsao, confianca * 100,
            )
        except Exception as exc:
            self.log.warning("[%s] Erro ao processar resposta LLM: %s", self.name, exc)
            return self._fallback(p)

        return p

    def _fallback(self, p: ProcessoCanonical) -> ProcessoCanonical:
        """Executa previsor heuristico como fallback."""
        self.log.info("[%s] Fallback para PrevisorResultado heuristico", self.name)
        fallback = PrevisorResultado()
        return fallback.execute(p)


# =========================================================================
# Agente 3: GeradorResumoML
# =========================================================================

@register_agent
class GeradorResumoML(BaseAgent):
    """
    Gera resumo executivo em linguagem natural usando LLM.
    Fallback: GeradorResumo (heuristico).
    """

    name = "gerador_resumo_ml"
    description = "Geracao de resumo executivo via LLM com linguagem natural"
    depends_on = ["analisador_risco", "analisador_cronologia"]
    priority = 5

    use_llm = True

    SYSTEM_PROMPT = (
        "Voce e um analista juridico senior. Sua tarefa e gerar um resumo executivo "
        "claro, conciso e profissional de um processo judicial brasileiro.\n\n"
        "O resumo deve ser escrito em portugues brasileiro formal, adequado para "
        "apresentacao a gestores e advogados.\n\n"
        "Retorne SOMENTE um JSON valido no formato:\n"
        "{\n"
        '  "resumo_executivo": "Paragrafo com resumo geral do processo",\n'
        '  "situacao_atual": "Descricao da situacao atual do processo",\n'
        '  "pontos_atencao": ["ponto 1", "ponto 2", "..."],\n'
        '  "proximos_passos": ["passo 1", "passo 2", "..."]\n'
        "}\n\n"
        "Seja preciso, factual e baseie-se exclusivamente nos dados fornecidos. "
        "Nao invente informacoes. Destaque riscos, prazos urgentes e valores relevantes."
    )

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        if not self.use_llm:
            return self._fallback(p)

        llm = get_llm_client()
        if not llm.available:
            return self._fallback(p)

        context = _build_process_context(p)
        response = llm.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=f"Gere o resumo executivo para este processo:\n\n{context}",
            max_tokens=2000,
            function_key="resumo"
        )

        parsed = _parse_json_response(response)
        if not parsed:
            self.log.info("[%s] LLM indisponivel ou resposta invalida, usando fallback heuristico", self.name)
            return self._fallback(p)

        try:
            resumo = parsed.get("resumo_executivo")
            situacao = parsed.get("situacao_atual")
            pontos = parsed.get("pontos_atencao", [])
            passos = parsed.get("proximos_passos", [])

            if resumo:
                p.resumo_executivo = resumo
            if situacao:
                p.resumo_situacao_atual = situacao
            if pontos and isinstance(pontos, list):
                # Preservar pontos existentes de outros agentes e adicionar os do LLM
                pontos_ml = [f"[ML] {pt}" for pt in pontos if isinstance(pt, str)]
                p.pontos_atencao = pontos_ml + p.pontos_atencao
            if passos and isinstance(passos, list):
                p.proximos_passos = [pt for pt in passos if isinstance(pt, str)]

            self.log.info("[%s] Resumo gerado via LLM (%d chars)", self.name, len(resumo or ""))
        except Exception as exc:
            self.log.warning("[%s] Erro ao processar resposta LLM: %s", self.name, exc)
            return self._fallback(p)

        return p

    def _fallback(self, p: ProcessoCanonical) -> ProcessoCanonical:
        """Executa gerador de resumo heuristico como fallback."""
        self.log.info("[%s] Fallback para GeradorResumo heuristico", self.name)
        fallback = GeradorResumo()
        return fallback.execute(p)


# =========================================================================
# Agente 4: AnalisadorJurisprudenciaML
# =========================================================================

@register_agent
class AnalisadorJurisprudenciaML(BaseAgent):
    """
    Identifica jurisprudencia correlata usando LLM.
    Fallback: AnalisadorJurisprudencia (base hardcoded).
    """

    name = "analisador_jurisprudencia_ml"
    description = "Identificacao de jurisprudencia correlata via LLM"
    depends_on = ["classificador_causa"]
    priority = 4

    use_llm = True

    SYSTEM_PROMPT = (
        "Voce e um pesquisador juridico especializado em jurisprudencia brasileira. "
        "Com base nos dados do processo fornecido, identifique teses juridicas, "
        "sumulas e precedentes relevantes dos tribunais superiores (STF, STJ, TST, TSE) "
        "e do tribunal de origem.\n\n"
        "Retorne SOMENTE um JSON valido no formato:\n"
        "{\n"
        '  "teses": [\n'
        "    {\n"
        '      "tese": "Descricao da tese juridica",\n'
        '      "referencia": "Sumula/Recurso/Artigo de lei",\n'
        '      "tribunal": "STF/STJ/TST/etc",\n'
        '      "favorabilidade": 0.0 a 1.0,\n'
        '      "aplicabilidade": "Breve explicacao de por que se aplica ao caso"\n'
        "    }\n"
        "  ],\n"
        '  "analise_geral": "Analise geral da jurisprudencia aplicavel",\n'
        '  "favorabilidade_geral": 0.0 a 1.0\n'
        "}\n\n"
        "Inclua apenas teses reais e conhecidas. Nao invente sumulas ou precedentes. "
        "Se nao tiver certeza, indique menor favorabilidade."
    )

    def execute(self, p: ProcessoCanonical) -> ProcessoCanonical:
        if not self.use_llm:
            return self._fallback(p)

        llm = get_llm_client()
        if not llm.available:
            return self._fallback(p)

        context = _build_process_context(p)
        response = llm.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=f"Identifique jurisprudencia relevante para este processo:\n\n{context}",
            max_tokens=2000,
            function_key="jurisprudencia"
        )

        parsed = _parse_json_response(response)
        if not parsed:
            self.log.info("[%s] LLM indisponivel ou resposta invalida, usando fallback heuristico", self.name)
            return self._fallback(p)

        try:
            teses = parsed.get("teses", [])
            analise = parsed.get("analise_geral", "")
            favorabilidade_geral = float(parsed.get("favorabilidade_geral", 0.5))
            favorabilidade_geral = max(0.0, min(1.0, favorabilidade_geral))

            # Adicionar teses como pontos de atencao
            for tese in teses:
                if not isinstance(tese, dict):
                    continue
                desc = tese.get("tese", "")
                ref = tese.get("referencia", "")
                tribunal = tese.get("tribunal", "")
                fav = tese.get("favorabilidade", 0.5)
                try:
                    fav = float(fav)
                except (ValueError, TypeError):
                    fav = 0.5

                info = (
                    f"[JURISPRUDENCIA ML] {desc} - Ref: {ref}"
                    f"{f' ({tribunal})' if tribunal else ''}"
                    f" (favorabilidade: {fav * 100:.0f}%)"
                )
                if info not in p.pontos_atencao:
                    p.pontos_atencao.append(info)

            # Indicador de risco consolidado
            if favorabilidade_geral < 0.4:
                nivel = NivelRisco.alto
            elif favorabilidade_geral < 0.6:
                nivel = NivelRisco.medio
            else:
                nivel = NivelRisco.baixo

            descricao = (
                f"Jurisprudencia (via LLM) na area '{p.area or 'N/A'}' com "
                f"favorabilidade geral de {favorabilidade_geral * 100:.0f}%"
            )
            if analise:
                descricao += f". {analise[:200]}"

            p.indicadores_risco.append(IndicadorRisco(
                categoria="jurisprudencia",
                nivel=nivel,
                score=round(1 - favorabilidade_geral, 2),
                descricao=descricao,
                recomendacao="Verificar teses identificadas pelo LLM e validar aplicabilidade ao caso concreto",
            ))

            self.log.info(
                "[%s] %d teses identificadas via LLM (favorabilidade: %.0f%%)",
                self.name, len(teses), favorabilidade_geral * 100,
            )
        except Exception as exc:
            self.log.warning("[%s] Erro ao processar resposta LLM: %s", self.name, exc)
            return self._fallback(p)

        return p

    def _fallback(self, p: ProcessoCanonical) -> ProcessoCanonical:
        """Executa analisador de jurisprudencia heuristico como fallback."""
        self.log.info("[%s] Fallback para AnalisadorJurisprudencia heuristico", self.name)
        fallback = AnalisadorJurisprudencia()
        return fallback.execute(p)


# =========================================================================
# Mapeamento de agentes heuristicos -> ML
# =========================================================================

ML_AGENT_MAP: Dict[str, str] = {
    "classificador_causa": "classificador_causa_ml",
    "previsor_resultado": "previsor_resultado_ml",
    "gerador_resumo": "gerador_resumo_ml",
    "analisador_jurisprudencia": "analisador_jurisprudencia_ml",
}


def get_ml_agent_names() -> Dict[str, str]:
    """Retorna mapeamento de agente heuristico -> agente ML."""
    return dict(ML_AGENT_MAP)
