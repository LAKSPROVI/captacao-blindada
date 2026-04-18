"""
Legal Parser - Extracao estruturada de dados juridicos de publicacoes.

Extrai de textos de publicacoes judiciais:
- Numeros de processo (formato CNJ)
- Numeros de OAB
- Nomes de advogados
- Nomes de partes
- Tribunal
- Data
- Tipo de acao/classe processual
"""

import re
import logging
from typing import List, Dict, Optional, Tuple

log = logging.getLogger("djen.parser")

# ============================================================
# REGEX PATTERNS
# ============================================================

# Numero de processo CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
RE_PROCESSO_CNJ = re.compile(
    r"\b(\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4})\b"
)

# Numero de processo antigo (varios formatos)
RE_PROCESSO_ANTIGO = re.compile(
    r"\b(\d{3,7}[./]\d{4}[./]?\d{0,7})\b"
)

# OAB: OAB/UF NNNNNN ou OAB NNNNNN/UF
RE_OAB = re.compile(
    r"\bOAB[/:\s]*([A-Z]{2})[\s./]*([\d.]+)\b|"
    r"\bOAB[/:\s]*([\d.]+)[/\s]*([A-Z]{2})\b|"
    r"\b(\d{3,6})[/\s]*OAB[/\s]*([A-Z]{2})\b",
    re.IGNORECASE
)

# Advogado: Dr., Dra., Adv., "advogado(a)", apos OAB
RE_ADVOGADO = re.compile(
    r"(?:Dr[a]?\.?|Adv[a]?\.?|[Aa]dvogad[oa])\s+([A-Z][A-Za-záàâãéèêíïóôõúüçÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ\s]+?)(?:\s*[-,;(]|\s+OAB|\s*$)",
    re.UNICODE
)

# Nomes em CAPS (possiveis partes ou advogados)
RE_NOME_CAPS = re.compile(
    r"\b([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ][A-ZÁÀÂÃÉÈÊÍÏÓÔÕÚÜÇ\s]{5,50})\b"
)

# CPF: NNN.NNN.NNN-NN
RE_CPF = re.compile(r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b")

# CNPJ: NN.NNN.NNN/NNNN-NN
RE_CNPJ = re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b")

# Varas e orgaos julgadores
RE_VARA = re.compile(
    r"\b(\d+[aª]\s+(?:Vara|Turma|Camara|Secao|Plenario)[\w\s]*?)(?:\s*[-,;.]|$)",
    re.IGNORECASE | re.UNICODE
)

# Classe processual
RE_CLASSE = re.compile(
    r"\b(Acao\s+\w+|Habeas\s+Corpus|Mandado\s+de\s+Seguranca|Agravo\s+\w+|"
    r"Apelacao(?:\s+\w+)?|Recurso\s+\w+|Embargos\s+\w+|"
    r"Execucao(?:\s+\w+)?|Cumprimento\s+de\s+Sentenca|"
    r"Procedimento\s+\w+|Medida\s+Cautelar|Tutela\s+\w+|"
    r"Acao\s+Civil\s+Publica|Acao\s+Popular|Reclamacao\s+\w+)",
    re.IGNORECASE | re.UNICODE
)

# Tribunais
TRIBUNAIS_REGEX = re.compile(
    r"\b(STF|STJ|TST|TSE|STM|"
    r"TJ[A-Z]{2}|TJDFT|"
    r"TRF[1-6]|"
    r"TRT\s*(?:da)?\s*\d{1,2}[aª]?(?:\s*Regiao)?|"
    r"TRE[-/]?[A-Z]{2})\b",
    re.IGNORECASE
)


# ============================================================
# PARSER
# ============================================================

class LegalParser:
    """Parser de dados juridicos de publicacoes judiciais."""

    def __init__(self):
        self.log = logging.getLogger("djen.parser")

    def extrair_tudo(self, texto: str) -> Dict:
        """
        Extrai todos os dados juridicos de um texto.

        Returns:
            Dict com chaves: processos, oabs, advogados, partes,
            tribunais, varas, classes, cpfs, cnpjs
        """
        return {
            "processos": self.extrair_processos(texto),
            "oabs": self.extrair_oabs(texto),
            "advogados": self.extrair_advogados(texto),
            "tribunais": self.extrair_tribunais(texto),
            "varas": self.extrair_varas(texto),
            "classes": self.extrair_classes(texto),
            "cpfs": self.extrair_cpfs(texto),
            "cnpjs": self.extrair_cnpjs(texto),
            "nomes_caps": self.extrair_nomes_caps(texto),
        }

    def extrair_processos(self, texto: str) -> List[str]:
        """Extrai numeros de processo no formato CNJ."""
        return list(set(RE_PROCESSO_CNJ.findall(texto)))

    def extrair_oabs(self, texto: str) -> List[Dict[str, str]]:
        """
        Extrai numeros de OAB.
        Returns: [{"uf": "SP", "numero": "123456"}, ...]
        """
        oabs = []
        for match in RE_OAB.finditer(texto):
            groups = match.groups()
            # Normalizar os diferentes formatos de match
            if groups[0] and groups[1]:  # OAB/UF NUMERO
                oabs.append({"uf": groups[0].upper(), "numero": groups[1].replace(".", "")})
            elif groups[2] and groups[3]:  # OAB NUMERO/UF
                oabs.append({"uf": groups[3].upper(), "numero": groups[2].replace(".", "")})
            elif groups[4] and groups[5]:  # NUMERO OAB/UF
                oabs.append({"uf": groups[5].upper(), "numero": groups[4].replace(".", "")})

        # Deduplicar
        seen = set()
        unique = []
        for oab in oabs:
            key = f"{oab['uf']}/{oab['numero']}"
            if key not in seen:
                seen.add(key)
                unique.append(oab)
        return unique

    def extrair_advogados(self, texto: str) -> List[str]:
        """Extrai nomes de advogados."""
        nomes = []
        for match in RE_ADVOGADO.finditer(texto):
            nome = match.group(1).strip()
            if len(nome) > 5 and not nome.isupper():
                nomes.append(nome)

        # Tambem buscar nomes antes/depois de OAB
        for match in RE_OAB.finditer(texto):
            start = max(0, match.start() - 100)
            end = min(len(texto), match.end() + 50)
            contexto = texto[start:end]

            # Buscar nome em CAPS antes da OAB
            nomes_contexto = RE_NOME_CAPS.findall(contexto)
            for n in nomes_contexto:
                n_limpo = n.strip()
                if 5 < len(n_limpo) < 60 and " " in n_limpo:
                    nomes.append(n_limpo)

        return list(set(nomes))

    def extrair_tribunais(self, texto: str) -> List[str]:
        """Extrai siglas de tribunais."""
        return list(set(m.upper() for m in TRIBUNAIS_REGEX.findall(texto)))

    def extrair_varas(self, texto: str) -> List[str]:
        """Extrai varas e orgaos julgadores."""
        return list(set(RE_VARA.findall(texto)))

    def extrair_classes(self, texto: str) -> List[str]:
        """Extrai classes processuais."""
        return list(set(RE_CLASSE.findall(texto)))

    def extrair_cpfs(self, texto: str) -> List[str]:
        """Extrai CPFs."""
        return list(set(RE_CPF.findall(texto)))

    def extrair_cnpjs(self, texto: str) -> List[str]:
        """Extrai CNPJs."""
        return list(set(RE_CNPJ.findall(texto)))

    def extrair_nomes_caps(self, texto: str) -> List[str]:
        """
        Extrai nomes escritos em MAIUSCULAS (possiveis partes).
        Filtra palavras comuns e siglas.
        """
        STOP_WORDS = {
            "PODER", "JUDICIARIO", "TRIBUNAL", "JUSTICA", "FEDERAL",
            "ESTADUAL", "TRABALHO", "ELEITORAL", "MILITAR",
            "DIARIO", "OFICIAL", "ELETRONICO", "PUBLICACAO",
            "PROCESSO", "RECURSO", "APELACAO", "AGRAVO", "DECISAO",
            "DESPACHO", "SENTENCA", "ACORDAO", "EMBARGOS",
            "AUTOR", "REU", "REQUERENTE", "REQUERIDO",
            "IMPETRANTE", "IMPETRADO", "AGRAVANTE", "AGRAVADO",
            "APELANTE", "APELADO", "RECORRENTE", "RECORRIDO",
            "EXEQUENTE", "EXECUTADO", "RELATOR", "REVISOR",
            "MINISTERIO", "PUBLICO", "UNIAO", "ESTADO",
            "REPUBLICA", "FEDERATIVA", "BRASIL",
            "SECAO", "TURMA", "CAMARA", "VARA", "COMARCA",
        }

        nomes = []
        for match in RE_NOME_CAPS.findall(texto):
            nome = match.strip()
            palavras = nome.split()
            # Filtrar: deve ter pelo menos 2 palavras, nao ser stop word
            if len(palavras) >= 2 and all(p not in STOP_WORDS for p in palavras):
                nomes.append(nome)

        return list(set(nomes))[:20]  # Limitar a 20

    def classificar_tipo_busca(self, termo: str) -> str:
        """
        Classifica o tipo de busca pelo formato do termo.

        Returns:
            'processo' | 'oab' | 'cpf' | 'cnpj' | 'nome'
        """
        termo = termo.strip()

        if RE_PROCESSO_CNJ.match(termo):
            return "processo"

        if re.match(r"^\d{3,6}[/\s][A-Z]{2}$", termo, re.I):
            return "oab"

        if RE_CPF.match(termo):
            return "cpf"

        if RE_CNPJ.match(termo):
            return "cnpj"

        return "nome"

    def formatar_processo_cnj(self, numero: str) -> Optional[str]:
        """
        Formata um numero de processo para o padrao CNJ.
        Aceita: 12345678901234567890 ou parcialmente formatado.
        Returns: NNNNNNN-DD.AAAA.J.TR.OOOO
        """
        # Remover tudo que nao e digito
        digits = re.sub(r"\D", "", numero)

        if len(digits) == 20:
            return (
                f"{digits[0:7]}-{digits[7:9]}."
                f"{digits[9:13]}.{digits[13]}.{digits[14:16]}.{digits[16:20]}"
            )
        return None

    def extrair_contexto(self, texto: str, termo: str, janela: int = 500) -> List[str]:
        """
        Extrai trechos do texto ao redor de cada ocorrencia do termo.

        Args:
            texto: Texto completo
            termo: Termo a buscar
            janela: Numero de caracteres antes/depois

        Returns:
            Lista de trechos contextuais
        """
        trechos = []
        texto_lower = texto.lower()
        termo_lower = termo.lower()
        idx = 0

        while True:
            pos = texto_lower.find(termo_lower, idx)
            if pos == -1:
                break

            start = max(0, pos - janela)
            end = min(len(texto), pos + len(termo) + janela)
            trecho = texto[start:end].strip()
            trechos.append(trecho)
            idx = pos + len(termo) + 100  # Pular para frente

        return trechos
