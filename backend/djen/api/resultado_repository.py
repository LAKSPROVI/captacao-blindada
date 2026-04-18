"""
Resultado Repository - Persistencia SQLite para resultados de analise de processos.

Armazena ProcessoCanonical serializado como JSON no banco de dados,
com colunas indexadas para consultas rapidas e filtros.
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from djen.agents.canonical_model import ProcessoCanonical
from djen.api.database import Database

log = logging.getLogger("captacao.resultado_repository")


class ResultadoRepository:
    """Repositorio SQLite para resultados de analise de processos."""

    def __init__(self, db: Database):
        self.db = db
        self._init_table()

    def _init_table(self):
        """Cria a tabela resultados_analise se nao existir."""
        conn = sqlite3.connect(self.db.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS resultados_analise (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_processo TEXT UNIQUE NOT NULL,
                tribunal TEXT,
                dados_json TEXT NOT NULL,
                resumo_executivo TEXT,
                risco_geral TEXT,
                risco_score REAL,
                status_processo TEXT,
                fase TEXT,
                area TEXT,
                valor_causa REAL,
                total_movimentacoes INTEGER,
                total_comunicacoes INTEGER,
                processing_time_ms INTEGER,
                criado_em TEXT DEFAULT (datetime('now')),
                atualizado_em TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_resultados_numero
                ON resultados_analise(numero_processo);
            CREATE INDEX IF NOT EXISTS idx_resultados_tribunal
                ON resultados_analise(tribunal);
            CREATE INDEX IF NOT EXISTS idx_resultados_area
                ON resultados_analise(area);
            CREATE INDEX IF NOT EXISTS idx_resultados_risco
                ON resultados_analise(risco_geral);
        """)
        conn.commit()
        conn.close()
        log.info("[ResultadoRepository] Tabela resultados_analise inicializada")

    def salvar(self, processo: ProcessoCanonical) -> int:
        """
        Salva ou atualiza (upsert) um resultado de analise.

        Args:
            processo: ProcessoCanonical completo.

        Returns:
            ID do registro inserido/atualizado.
        """
        dados_json = processo.model_dump_json()

        try:
            cur = self.db.conn.execute("""
                INSERT INTO resultados_analise
                    (numero_processo, tribunal, dados_json, resumo_executivo,
                     risco_geral, risco_score, status_processo, fase, area,
                     valor_causa, total_movimentacoes, total_comunicacoes,
                     processing_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(numero_processo) DO UPDATE SET
                    tribunal = excluded.tribunal,
                    dados_json = excluded.dados_json,
                    resumo_executivo = excluded.resumo_executivo,
                    risco_geral = excluded.risco_geral,
                    risco_score = excluded.risco_score,
                    status_processo = excluded.status_processo,
                    fase = excluded.fase,
                    area = excluded.area,
                    valor_causa = excluded.valor_causa,
                    total_movimentacoes = excluded.total_movimentacoes,
                    total_comunicacoes = excluded.total_comunicacoes,
                    processing_time_ms = excluded.processing_time_ms,
                    atualizado_em = datetime('now')
            """, (
                processo.numero_processo,
                processo.tribunal,
                dados_json,
                processo.resumo_executivo,
                processo.risco_geral.value if processo.risco_geral else None,
                processo.risco_score,
                processo.status.value if processo.status else None,
                processo.fase.value if processo.fase else None,
                processo.area,
                processo.valor_causa,
                processo.total_movimentacoes,
                processo.total_comunicacoes,
                processo.processing_time_ms,
            ))
            self.db.conn.commit()
            row_id = cur.lastrowid

            # Se lastrowid is 0 (update case), fetch the actual id
            if not row_id:
                row = self.db.conn.execute(
                    "SELECT id FROM resultados_analise WHERE numero_processo=?",
                    (processo.numero_processo,),
                ).fetchone()
                row_id = row["id"] if row else 0

            log.info("[ResultadoRepository] Salvo processo %s (id=%d)",
                     processo.numero_processo, row_id)
            return row_id

        except Exception as e:
            log.error("[ResultadoRepository] Erro ao salvar %s: %s",
                      processo.numero_processo, e)
            raise

    def obter(self, numero_processo: str) -> Optional[ProcessoCanonical]:
        """
        Recupera um ProcessoCanonical pelo numero do processo.

        Args:
            numero_processo: Numero CNJ do processo.

        Returns:
            ProcessoCanonical ou None se nao encontrado.
        """
        row = self.db.conn.execute(
            "SELECT dados_json FROM resultados_analise WHERE numero_processo=?",
            (numero_processo,),
        ).fetchone()

        if not row:
            return None

        try:
            return ProcessoCanonical.model_validate_json(row["dados_json"])
        except Exception as e:
            log.error("[ResultadoRepository] Erro ao deserializar %s: %s",
                      numero_processo, e)
            return None

    def listar(self, limit: int = 50, offset: int = 0,
               tribunal: Optional[str] = None,
               area: Optional[str] = None,
               risco: Optional[str] = None) -> List[Dict]:
        """
        Lista resultados com filtros, retornando resumo (sem dados_json completo).

        Args:
            limit: Maximo de resultados.
            offset: Deslocamento para paginacao.
            tribunal: Filtrar por tribunal.
            area: Filtrar por area juridica.
            risco: Filtrar por nivel de risco.

        Returns:
            Lista de dicts com resumo de cada resultado.
        """
        conditions: List[str] = []
        params: List[Any] = []

        if tribunal:
            conditions.append("tribunal = ?")
            params.append(tribunal.upper())
        if area:
            conditions.append("area = ?")
            params.append(area)
        if risco:
            conditions.append("risco_geral = ?")
            params.append(risco)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT id, numero_processo, tribunal, resumo_executivo,
                   risco_geral, risco_score, status_processo, fase, area,
                   valor_causa, total_movimentacoes, total_comunicacoes,
                   processing_time_ms, criado_em, atualizado_em
            FROM resultados_analise
            {where}
            ORDER BY atualizado_em DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = self.db.conn.execute(sql, params).fetchall()

        # Total count for pagination
        count_sql = f"SELECT COUNT(*) as total FROM resultados_analise {where}"
        count_params = params[:-2]  # exclude limit/offset
        total = self.db.conn.execute(count_sql, count_params).fetchone()["total"]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "resultados": [dict(row) for row in rows],
        }

    def deletar(self, numero_processo: str) -> bool:
        """
        Deleta um resultado pelo numero do processo.

        Returns:
            True se deletou, False se nao encontrado.
        """
        cur = self.db.conn.execute(
            "DELETE FROM resultados_analise WHERE numero_processo=?",
            (numero_processo,),
        )
        self.db.conn.commit()
        deleted = cur.rowcount > 0
        if deleted:
            log.info("[ResultadoRepository] Deletado processo %s", numero_processo)
        return deleted

    def stats(self) -> Dict:
        """
        Estatisticas sobre resultados armazenados.

        Returns:
            Dict com contagens, distribuicoes e datas.
        """
        conn = self.db.conn

        total = conn.execute(
            "SELECT COUNT(*) as c FROM resultados_analise"
        ).fetchone()["c"]

        # Distribuicao por risco
        risco_rows = conn.execute(
            "SELECT risco_geral, COUNT(*) as c FROM resultados_analise GROUP BY risco_geral"
        ).fetchall()
        por_risco = {row["risco_geral"]: row["c"] for row in risco_rows}

        # Distribuicao por tribunal
        tribunal_rows = conn.execute(
            "SELECT tribunal, COUNT(*) as c FROM resultados_analise "
            "WHERE tribunal IS NOT NULL GROUP BY tribunal ORDER BY c DESC LIMIT 10"
        ).fetchall()
        por_tribunal = {row["tribunal"]: row["c"] for row in tribunal_rows}

        # Distribuicao por area
        area_rows = conn.execute(
            "SELECT area, COUNT(*) as c FROM resultados_analise "
            "WHERE area IS NOT NULL GROUP BY area ORDER BY c DESC"
        ).fetchall()
        por_area = {row["area"]: row["c"] for row in area_rows}

        # Score medio
        avg_row = conn.execute(
            "SELECT AVG(risco_score) as avg_score FROM resultados_analise"
        ).fetchone()
        avg_score = round(avg_row["avg_score"], 3) if avg_row["avg_score"] else 0.0

        # Datas
        ultima = conn.execute(
            "SELECT MAX(atualizado_em) as t FROM resultados_analise"
        ).fetchone()
        primeira = conn.execute(
            "SELECT MIN(criado_em) as t FROM resultados_analise"
        ).fetchone()

        return {
            "total_resultados": total,
            "risco_score_medio": avg_score,
            "por_risco": por_risco,
            "por_tribunal": por_tribunal,
            "por_area": por_area,
            "primeiro_registro": primeira["t"] if primeira else None,
            "ultimo_registro": ultima["t"] if ultima else None,
        }

    def buscar_texto(self, termo: str) -> List[Dict]:
        """
        Busca full-text no resumo_executivo.

        Args:
            termo: Texto para buscar.

        Returns:
            Lista de dicts com resultados que contem o termo.
        """
        rows = self.db.conn.execute("""
            SELECT id, numero_processo, tribunal, resumo_executivo,
                   risco_geral, risco_score, status_processo, fase, area,
                   valor_causa, criado_em, atualizado_em
            FROM resultados_analise
            WHERE resumo_executivo LIKE ?
            ORDER BY atualizado_em DESC
            LIMIT 50
        """, (f"%{termo}%",)).fetchall()

        return [dict(row) for row in rows]
