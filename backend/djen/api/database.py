"""
Captacao Peticao Blindada - Database Layer.
SQLite com schema para monitorados, publicacoes, buscas e health checks.
"""

import logging
import os
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any

log = logging.getLogger("captacao.database")

# Path padrao do banco
DEFAULT_DB_PATH = os.environ.get(
    "CAPTACAO_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "captacao_blindada.db"),
)


class Database:
    """Gerenciador SQLite thread-safe para Captacao Peticao Blindada."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._local = threading.local()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn.execute("PRAGMA cache_size=-20000")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
            self._local.conn.execute("PRAGMA mmap_size=268435456")
        return self._local.conn

    def _init_schema(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS monitorados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                valor TEXT NOT NULL,
                nome_amigavel TEXT,
                ativo INTEGER DEFAULT 1,
                tribunal TEXT,
                fontes TEXT DEFAULT 'datajud,djen_api',
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                atualizado_em TEXT DEFAULT (datetime('now', 'localtime')),
                ultima_busca TEXT,
                UNIQUE(tipo, valor)
            );

            CREATE TABLE IF NOT EXISTS publicacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                fonte TEXT NOT NULL,
                tribunal TEXT,
                data_publicacao TEXT,
                conteudo TEXT,
                numero_processo TEXT,
                classe_processual TEXT,
                orgao_julgador TEXT,
                assuntos TEXT,
                movimentos TEXT,
                url_origem TEXT,
                caderno TEXT,
                pagina TEXT,
                oab_encontradas TEXT,
                advogados TEXT,
                partes TEXT,
                notificado INTEGER DEFAULT 0,
                monitorado_id INTEGER,
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (monitorado_id) REFERENCES monitorados(id)
            );

            CREATE TABLE IF NOT EXISTS buscas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                fonte TEXT,
                tribunal TEXT,
                termos TEXT,
                resultados INTEGER DEFAULT 0,
                status TEXT DEFAULT 'ok',
                duracao_ms INTEGER,
                erro TEXT,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                latency_ms INTEGER,
                message TEXT,
                proxy_used INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- =========================================================
            -- Multi-Tenant & Identidade Estrutura (v2.0)
            -- =========================================================

            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                ativo INTEGER DEFAULT 1,
                saldo_tokens INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                atualizado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NULL,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            );

            CREATE TABLE IF NOT EXISTS function_costs (
                function_name TEXT PRIMARY KEY,
                description TEXT,
                cost_tokens INTEGER DEFAULT 0,
                atualizado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                user_id INTEGER,
                function_name TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                metadata TEXT,
                data_uso TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            -- Indexes for the new tables
            CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_usage_logs_tenant_id ON usage_logs(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_usage_logs_function_name ON usage_logs(function_name);

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NULL,
                user_id INTEGER NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                details TEXT,
                ip_address TEXT,
                data_hash TEXT NOT NULL,
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS system_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NULL,
                user_id INTEGER NULL,
                function_name TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                stack_trace TEXT,
                status TEXT DEFAULT 'aberto',
                resolvido_em TEXT,
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_criado ON audit_logs(criado_em);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_system_errors_status ON system_errors(status);
            CREATE INDEX IF NOT EXISTS idx_system_errors_criado ON system_errors(criado_em);



            CREATE INDEX IF NOT EXISTS idx_publicacoes_fonte ON publicacoes(fonte);
            CREATE INDEX IF NOT EXISTS idx_publicacoes_tribunal ON publicacoes(tribunal);
            CREATE INDEX IF NOT EXISTS idx_publicacoes_processo ON publicacoes(numero_processo);
            CREATE INDEX IF NOT EXISTS idx_publicacoes_data ON publicacoes(data_publicacao);
            CREATE INDEX IF NOT EXISTS idx_publicacoes_hash ON publicacoes(hash);
            CREATE INDEX IF NOT EXISTS idx_monitorados_ativo ON monitorados(ativo);
            CREATE INDEX IF NOT EXISTS idx_buscas_fonte ON buscas(fonte);

            -- =========================================================
            -- Captacao Automatizada (v1.1)
            -- =========================================================

            CREATE TABLE IF NOT EXISTS captacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT,
                ativo INTEGER DEFAULT 1,

                -- Parametros de busca
                tipo_busca TEXT NOT NULL,
                numero_processo TEXT,
                numero_oab TEXT,
                uf_oab TEXT,
                nome_parte TEXT,
                nome_advogado TEXT,
                tribunal TEXT,
                tribunais TEXT,
                classe_codigo INTEGER,
                assunto_codigo INTEGER,
                orgao_id INTEGER,
                tipo_comunicacao TEXT,
                data_inicio TEXT,
                data_fim TEXT,

                -- Fontes
                fontes TEXT DEFAULT 'datajud,djen_api',

                -- Scheduler
                intervalo_minutos INTEGER DEFAULT 120,
                horario_inicio TEXT DEFAULT '06:00',
                horario_fim TEXT DEFAULT '23:00',
                dias_semana TEXT DEFAULT '1,2,3,4,5',
                proxima_execucao TEXT,
                pausado INTEGER DEFAULT 0,

                -- Enriquecimento
                auto_enriquecer INTEGER DEFAULT 0,

                -- Notificacao
                notificar_whatsapp INTEGER DEFAULT 0,
                notificar_email INTEGER DEFAULT 0,
                prioridade TEXT DEFAULT 'normal',
                modalidade TEXT DEFAULT 'recorrente',

                -- Meta
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                atualizado_em TEXT DEFAULT (datetime('now', 'localtime')),
                ultima_execucao TEXT,
                total_execucoes INTEGER DEFAULT 0,
                total_resultados INTEGER DEFAULT 0,
                total_novos INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS execucoes_captacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captacao_id INTEGER NOT NULL,
                inicio TEXT NOT NULL,
                fim TEXT,
                status TEXT DEFAULT 'running',
                fonte TEXT NOT NULL,
                parametros_json TEXT,
                total_resultados INTEGER DEFAULT 0,
                novos_resultados INTEGER DEFAULT 0,
                duracao_ms INTEGER,
                erro TEXT,
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (captacao_id) REFERENCES captacoes(id)
            );

            CREATE INDEX IF NOT EXISTS idx_captacoes_ativo ON captacoes(ativo);
            CREATE INDEX IF NOT EXISTS idx_captacoes_proxima ON captacoes(proxima_execucao);
            CREATE INDEX IF NOT EXISTS idx_captacoes_prioridade ON captacoes(prioridade);
            CREATE INDEX IF NOT EXISTS idx_execucoes_captacao_id ON execucoes_captacao(captacao_id);
            CREATE INDEX IF NOT EXISTS idx_execucoes_status ON execucoes_captacao(status);
            CREATE INDEX IF NOT EXISTS idx_execucoes_inicio ON execucoes_captacao(inicio);

            -- =========================================================
            -- Processos Monitorados (v1.2)
            -- =========================================================

            CREATE TABLE IF NOT EXISTS processos_monitorados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_processo TEXT NOT NULL UNIQUE,
                tribunal TEXT,
                classe_processual TEXT,
                orgao_julgador TEXT,
                assuntos TEXT,
                status TEXT DEFAULT 'ativo',
                origem TEXT DEFAULT 'monitor',
                origem_id INTEGER,
                ultima_verificacao TEXT,
                total_movimentacoes INTEGER DEFAULT 0,
                movimentacoes TEXT,
                data_ultima_movimentacao TEXT,
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                atualizado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_proc_mon_numero ON processos_monitorados(numero_processo);
            CREATE INDEX IF NOT EXISTS idx_proc_mon_status ON processos_monitorados(status);
            CREATE INDEX IF NOT EXISTS idx_proc_mon_verificacao ON processos_monitorados(ultima_verificacao);

            -- =========================================================
            -- Configuracao de IA (v1.3)
            -- =========================================================

            CREATE TABLE IF NOT EXISTS ai_config (
                function_key TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model_name TEXT NOT NULL,
                api_key TEXT,
                base_url TEXT,
                enabled INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- Inserir defaults se nao existirem
            INSERT OR IGNORE INTO ai_config (function_key, provider, model_name, enabled)
            VALUES 
                ('classificacao', 'gemini', 'gemini-2.5-flash', 1),
                ('previsao', 'gemini', 'gemini-3-flash-preview', 1),
                ('resumo', 'gemini', 'gemini-2.5-flash', 1),
                ('jurisprudencia', 'gemini', 'gemini-3-flash-preview', 1);

            -- =========================================================
            -- Configuracoes Globais (v1.4)
            -- =========================================================

            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- =========================================================
            -- Historico de Verificacoes (v1.5)
            -- =========================================================

            CREATE TABLE IF NOT EXISTS processos_monitorados_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_processo TEXT NOT NULL,
                data_verificacao TEXT DEFAULT (datetime('now', 'localtime')),
                status TEXT, -- ok, erro, sem_mudancas
                fonte TEXT, -- datajud, djen
                detalhes TEXT, -- JSON com o que mudou ou mensagem de erro
                total_movimentacoes INTEGER,
                novas_movimentacoes INTEGER DEFAULT 0,
                FOREIGN KEY (numero_processo) REFERENCES processos_monitorados(numero_processo)
            );

            CREATE INDEX IF NOT EXISTS idx_proc_hist_numero ON processos_monitorados_historico(numero_processo);
            CREATE INDEX IF NOT EXISTS idx_proc_hist_data ON processos_monitorados_historico(data_verificacao);

        """)
        conn.commit()

        # --- Migration: adicionar colunas de agendamento na tabela monitorados ---
        for col, default in [
            ("intervalo_minutos", "120"),
            ("horario_inicio", "'06:00'"),
            ("horario_fim", "'23:00'"),
            ("dias_semana", "'1,2,3,4,5'"),
            ("proxima_busca", "NULL"),
        ]:
            try:
                conn.execute(f"ALTER TABLE monitorados ADD COLUMN {col} TEXT DEFAULT {default}")
                conn.commit()
            except Exception:
                pass  # Coluna ja existe

        # --- Migration: adicionar tenant_id em varias tabelas (v2.0) ---
        tabelas_tenant = [
            "monitorados", "publicacoes", "buscas", "captacoes",
            "execucoes_captacao", "processos_monitorados"
        ]
        for tabela in tabelas_tenant:
            try:
                conn.execute(f"ALTER TABLE {tabela} ADD COLUMN tenant_id INTEGER")
                conn.commit()
            except Exception:
                pass  # Coluna ja existe
        
        # Opcional: Atualizar registros antigos para tenant_id = 1
        for tabela in tabelas_tenant:
            try:
                conn.execute(f"UPDATE {tabela} SET tenant_id = 1 WHERE tenant_id IS NULL")
                conn.commit()
            except Exception:
                pass
        
        # Garantir Default Tenant (Admin)
        try:
            cur = conn.execute("SELECT id FROM tenants WHERE id=1")
            if not cur.fetchone():
                conn.execute("INSERT INTO tenants (id, nome, ativo, saldo_tokens) VALUES (1, 'Sistema Root', 1, 1000000)")
                conn.commit()
        except Exception as e:
            log.error(f"Erro ao criar tenant admin: {e}")

        conn.close()
        log.info("[Database] Schema inicializado em %s", self.db_path)

    # === Monitorados ===

    def adicionar_monitorado(self, tipo: str, valor: str, nome_amigavel: Optional[str] = None,
                              tribunal: Optional[str] = None, fontes: str = "datajud,djen_api",
                              intervalo_minutos: int = 120, horario_inicio: str = "06:00",
                              horario_fim: str = "23:00", dias_semana: str = "1,2,3,4,5") -> int:
        try:
            cur = self.conn.execute(
                """INSERT INTO monitorados
                   (tipo, valor, nome_amigavel, tribunal, fontes,
                    intervalo_minutos, horario_inicio, horario_fim, dias_semana)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tipo, valor, nome_amigavel, tribunal, fontes,
                 intervalo_minutos, horario_inicio, horario_fim, dias_semana),
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # Ja existe, reativar
            self.conn.execute(
                """UPDATE monitorados SET ativo=1, atualizado_em=datetime('now', 'localtime'),
                   intervalo_minutos=?, horario_inicio=?, horario_fim=?, dias_semana=?
                   WHERE tipo=? AND valor=?""",
                (intervalo_minutos, horario_inicio, horario_fim, dias_semana, tipo, valor),
            )
            self.conn.commit()
            row = self.conn.execute("SELECT id FROM monitorados WHERE tipo=? AND valor=?", (tipo, valor)).fetchone()
            return row["id"] if row else 0

    def listar_monitorados(self, apenas_ativos: bool = True) -> List[Dict]:
        sql = "SELECT * FROM monitorados"
        if apenas_ativos:
            sql += " WHERE ativo=1"
        sql += " ORDER BY criado_em DESC"
        rows = self.conn.execute(sql).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            # Contar publicacoes
            count = self.conn.execute(
                "SELECT COUNT(*) as c FROM publicacoes WHERE monitorado_id=?", (d["id"],)
            ).fetchone()
            d["total_publicacoes"] = count["c"] if count else 0
            result.append(d)
        return result

    def obter_monitorado(self, monitorado_id: int) -> Optional[Dict]:
        row = self.conn.execute("SELECT * FROM monitorados WHERE id=?", (monitorado_id,)).fetchone()
        return dict(row) if row else None

    def atualizar_monitorado(self, monitorado_id: int, **kwargs) -> bool:
        sets = []
        vals = []
        allowed = ("nome_amigavel", "ativo", "tribunal", "fontes",
                   "intervalo_minutos", "horario_inicio", "horario_fim", "dias_semana", "proxima_busca")
        for k, v in kwargs.items():
            if v is not None and k in allowed:
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets:
            return False
        sets.append("atualizado_em=datetime('now', 'localtime')")
        vals.append(monitorado_id)
        self.conn.execute(f"UPDATE monitorados SET {', '.join(sets)} WHERE id=?", vals)
        self.conn.commit()
        return True

    def desativar_monitorado(self, monitorado_id: int) -> bool:
        self.conn.execute("UPDATE monitorados SET ativo=0, atualizado_em=datetime('now', 'localtime') WHERE id=?", (monitorado_id,))
        self.conn.commit()
        return True

    # === Publicacoes ===

    def salvar_publicacao(self, pub_dict: Dict, monitorado_id: Optional[int] = None) -> Optional[int]:
        import json
        try:
            cur = self.conn.execute("""
                INSERT OR IGNORE INTO publicacoes
                (hash, fonte, tribunal, data_publicacao, conteudo, numero_processo,
                 classe_processual, orgao_julgador, assuntos, movimentos, url_origem,
                 caderno, pagina, oab_encontradas, advogados, partes, monitorado_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pub_dict.get("hash", ""),
                pub_dict.get("fonte", ""),
                pub_dict.get("tribunal", ""),
                pub_dict.get("data_publicacao", ""),
                pub_dict.get("conteudo", ""),
                pub_dict.get("numero_processo"),
                pub_dict.get("classe_processual"),
                pub_dict.get("orgao_julgador"),
                json.dumps(pub_dict.get("assuntos", []), ensure_ascii=False),
                json.dumps(pub_dict.get("movimentos", []), ensure_ascii=False),
                pub_dict.get("url_origem"),
                pub_dict.get("caderno"),
                pub_dict.get("pagina"),
                json.dumps(pub_dict.get("oab_encontradas", []), ensure_ascii=False),
                json.dumps(pub_dict.get("advogados", []), ensure_ascii=False),
                json.dumps(pub_dict.get("partes", []), ensure_ascii=False),
                monitorado_id,
            ))
            self.conn.commit()
            return cur.lastrowid if cur.lastrowid else None
        except Exception as e:
            log.error("[Database] Erro ao salvar publicacao: %s", e)
            return None

    def buscar_publicacoes(self, fonte: Optional[str] = None, tribunal: Optional[str] = None,
                            processo: Optional[str] = None, limite: int = 50,
                            offset: int = 0) -> List[Dict]:
        import json
        conditions = []
        params = []
        if fonte:
            conditions.append("fonte=?")
            params.append(fonte)
        if tribunal:
            conditions.append("tribunal=?")
            params.append(tribunal.upper())
        if processo:
            conditions.append("numero_processo LIKE ?")
            params.append(f"%{processo}%")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM publicacoes {where} ORDER BY criado_em DESC LIMIT ? OFFSET ?"
        params.extend([limite, offset])
        rows = self.conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            for field in ("assuntos", "movimentos", "oab_encontradas", "advogados", "partes"):
                try:
                    d[field] = json.loads(d[field]) if d[field] else []
                except (json.JSONDecodeError, TypeError):
                    d[field] = []
            result.append(d)
        return result

    # === Buscas ===

    def listar_monitorados_pendentes(self, agora_iso: str) -> List[Dict]:
        """Retorna monitorados ativos que precisam de busca agora."""
        query = """
            SELECT * FROM monitorados
            WHERE ativo = 1
            AND (proxima_busca IS NULL OR proxima_busca <= ?)
        """
        rows = self.conn.execute(query, (agora_iso,)).fetchall()
        return [dict(r) for r in rows]

    def atualizar_monitorado_pos_execucao(self, monitorado_id: int, total: int, novos: int, proxima_busca: str):
        """Atualiza estatisticas e agenda proxima execucao."""
        self.conn.execute(
            """UPDATE monitorados SET
               ultima_busca = datetime('now', 'localtime'),
               total_publicacoes = total_publicacoes + ?,
               proxima_busca = ?
               WHERE id = ?""",
            (novos, proxima_busca, monitorado_id),
        )
        self.conn.commit()

    def registrar_busca(self, tipo: str, fonte: str, tribunal: Optional[str],
                         termos: str, resultados: int, status: str = "ok",
                         duracao_ms: int = 0, erro: Optional[str] = None) -> int:
        cur = self.conn.execute("""
            INSERT INTO buscas (tipo, fonte, tribunal, termos, resultados, status, duracao_ms, erro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (tipo, fonte, tribunal, termos, resultados, status, duracao_ms, erro))
        self.conn.commit()
        return cur.lastrowid

    # === Health ===

    def registrar_health(self, source: str, status: str, latency_ms: int = 0,
                          message: str = "", proxy_used: bool = False) -> int:
        cur = self.conn.execute("""
            INSERT INTO health_checks (source, status, latency_ms, message, proxy_used)
            VALUES (?, ?, ?, ?, ?)
        """, (source, status, latency_ms, message, 1 if proxy_used else 0))
        self.conn.commit()
        return cur.lastrowid

    # === Stats ===

    def obter_stats(self) -> Dict[str, Any]:
        stats = {}
        stats["total_monitorados"] = self.conn.execute("SELECT COUNT(*) as c FROM monitorados").fetchone()["c"]
        stats["monitorados_ativos"] = self.conn.execute("SELECT COUNT(*) as c FROM monitorados WHERE ativo=1").fetchone()["c"]
        stats["total_publicacoes"] = self.conn.execute("SELECT COUNT(*) as c FROM publicacoes").fetchone()["c"]
        stats["publicacoes_hoje"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM publicacoes WHERE date(criado_em)=date('now')"
        ).fetchone()["c"]
        stats["publicacoes_semana"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM publicacoes WHERE criado_em >= datetime('now', '-7 days')"
        ).fetchone()["c"]
        stats["total_buscas"] = self.conn.execute("SELECT COUNT(*) as c FROM buscas").fetchone()["c"]

        # Fontes ativas (com busca nos ultimos 7 dias)
        stats["fontes_ativas"] = self.conn.execute(
            "SELECT COUNT(DISTINCT fonte) as c FROM buscas WHERE criado_em >= datetime('now', '-7 days') AND status='ok'"
        ).fetchone()["c"]

        # Ultima busca
        row = self.conn.execute("SELECT MAX(criado_em) as t FROM buscas").fetchone()
        stats["ultima_busca"] = row["t"] if row else None

        return stats

    # === Captacoes Automatizadas ===

    def criar_captacao(self, nome: str, tipo_busca: str = "processo", **kwargs) -> int:
        """Cria nova captacao automatizada."""
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        BRASILIA_TZ = ZoneInfo("America/Sao_Paulo")
        intervalo = kwargs.get("intervalo_minutos", 120)
        proxima = (datetime.now(tz=BRASILIA_TZ) + timedelta(minutes=intervalo)).isoformat()
        proxima = (datetime.now() + timedelta(minutes=intervalo)).isoformat()

        cols = ["nome", "tipo_busca", "proxima_execucao"]
        vals = [nome, tipo_busca, proxima]

        allowed = [
            "descricao", "numero_processo", "numero_oab", "uf_oab",
            "nome_parte", "nome_advogado", "tribunal", "tribunais",
            "classe_codigo", "assunto_codigo", "orgao_id", "tipo_comunicacao",
            "data_inicio", "data_fim", "fontes", "intervalo_minutos",
            "horario_inicio", "horario_fim", "dias_semana",
            "auto_enriquecer", "notificar_whatsapp", "notificar_email", "prioridade",
            "modalidade",
        ]
        for key in allowed:
            val = kwargs.get(key)
            if val is not None:
                cols.append(key)
                if isinstance(val, bool):
                    vals.append(1 if val else 0)
                else:
                    vals.append(val)

        placeholders = ",".join(["?"] * len(cols))
        sql = f"INSERT INTO captacoes ({','.join(cols)}) VALUES ({placeholders})"
        cur = self.conn.execute(sql, vals)
        self.conn.commit()
        return cur.lastrowid or 0

    def obter_captacao(self, captacao_id: int) -> Optional[Dict]:
        """Obtem uma captacao por ID."""
        row = self.conn.execute("SELECT * FROM captacoes WHERE id=?", (captacao_id,)).fetchone()
        return dict(row) if row else None

    def listar_captacoes(self, ativo: Optional[bool] = None, tipo_busca: Optional[str] = None,
                          prioridade: Optional[str] = None) -> List[Dict]:
        """Lista captacoes com filtros opcionais."""
        conditions = []
        params = []
        if ativo is not None:
            conditions.append("ativo=?")
            params.append(1 if ativo else 0)
        if tipo_busca:
            conditions.append("tipo_busca=?")
            params.append(tipo_busca)
        if prioridade:
            conditions.append("prioridade=?")
            params.append(prioridade)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM captacoes {where} ORDER BY criado_em DESC"
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def atualizar_captacao(self, captacao_id: int, **kwargs) -> bool:
        """Atualiza campos de uma captacao."""
        allowed = [
            "nome", "descricao", "ativo", "pausado", "tipo_busca",
            "numero_processo", "numero_oab", "uf_oab", "nome_parte",
            "nome_advogado", "tribunal", "tribunais", "classe_codigo",
            "assunto_codigo", "orgao_id", "tipo_comunicacao", "data_inicio",
            "data_fim", "fontes", "intervalo_minutos", "horario_inicio",
            "horario_fim", "dias_semana", "proxima_execucao",
            "auto_enriquecer", "notificar_whatsapp", "notificar_email", "prioridade",
            "modalidade",
        ]
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                sets.append(f"{k}=?")
                if isinstance(v, bool):
                    vals.append(1 if v else 0)
                else:
                    vals.append(v)
        if not sets:
            return False
        sets.append("atualizado_em=datetime('now', 'localtime')")
        vals.append(captacao_id)
        self.conn.execute(f"UPDATE captacoes SET {', '.join(sets)} WHERE id=?", vals)
        self.conn.commit()
        return True

    def atualizar_captacao_pos_execucao(self, captacao_id: int, total: int, novos: int,
                                         intervalo_minutos: int):
        """Atualiza captacao apos execucao: contadores e proxima_execucao."""
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        BRASILIA_TZ = ZoneInfo("America/Sao_Paulo")
        proxima = (datetime.now(tz=BRASILIA_TZ) + timedelta(minutes=intervalo_minutos)).isoformat()
        self.conn.execute("""
            UPDATE captacoes SET
                ultima_execucao=datetime('now', 'localtime'),
                total_execucoes=total_execucoes+1,
                total_resultados=total_resultados+?,
                total_novos=total_novos+?,
                proxima_execucao=?,
                atualizado_em=datetime('now', 'localtime')
            WHERE id=?
        """, (total, novos, proxima, captacao_id))
        self.conn.commit()

    def listar_captacoes_pendentes(self, agora_iso: str) -> List[Dict]:
        """Lista captacoes ativas nao pausadas com proxima_execucao <= agora."""
        rows = self.conn.execute("""
            SELECT * FROM captacoes
            WHERE ativo=1 AND pausado=0
              AND (proxima_execucao IS NULL OR proxima_execucao <= ?)
            ORDER BY
                CASE prioridade WHEN 'urgente' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,
                proxima_execucao ASC
        """, (agora_iso,)).fetchall()
        return [dict(r) for r in rows]

    # === Execucoes de Captacao ===

    def iniciar_execucao_captacao(self, captacao_id: int, fonte: str,
                                   parametros_json: str = "") -> int:
        """Registra inicio de uma execucao de captacao."""
        cur = self.conn.execute("""
            INSERT INTO execucoes_captacao (captacao_id, inicio, fonte, parametros_json)
            VALUES (?, datetime('now', 'localtime'), ?, ?)
        """, (captacao_id, fonte, parametros_json))
        self.conn.commit()
        return cur.lastrowid or 0

    def finalizar_execucao_captacao(self, exec_id: int, status: str,
                                     total: int, novos: int, duracao_ms: int,
                                     erro: Optional[str] = None):
        """Finaliza uma execucao de captacao."""
        self.conn.execute("""
            UPDATE execucoes_captacao SET
                fim=datetime('now', 'localtime'), status=?, total_resultados=?,
                novos_resultados=?, duracao_ms=?, erro=?
            WHERE id=?
        """, (status, total, novos, duracao_ms, erro, exec_id))
        self.conn.commit()

    def listar_execucoes_captacao(self, captacao_id: int, limite: int = 20,
                                   offset: int = 0) -> List[Dict]:
        """Lista execucoes de uma captacao."""
        rows = self.conn.execute("""
            SELECT * FROM execucoes_captacao
            WHERE captacao_id=?
            ORDER BY inicio DESC
            LIMIT ? OFFSET ?
        """, (captacao_id, limite, offset)).fetchall()
        return [dict(r) for r in rows]

    # === Publicacoes vinculadas a captacao ===

    def salvar_publicacao_captacao(self, pub_dict: Dict, captacao_id: int) -> Optional[int]:
        """Salva publicacao vinculada a uma captacao (sem FK para monitorados)."""
        import json
        from djen.api.webhook import trigger_webhook, WebhookEvent
        try:
            # Garantir que a coluna captacao_id existe
            try:
                self.conn.execute("ALTER TABLE publicacoes ADD COLUMN captacao_id INTEGER")
                self.conn.commit()
            except Exception:
                pass  # Coluna ja existe

            pub_hash = pub_dict.get("hash", "")

            cur = self.conn.execute("""
                INSERT OR IGNORE INTO publicacoes
                (hash, fonte, tribunal, data_publicacao, conteudo, numero_processo,
                 classe_processual, orgao_julgador, assuntos, movimentos, url_origem,
                 caderno, pagina, oab_encontradas, advogados, partes, captacao_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pub_hash,
                pub_dict.get("fonte", ""),
                pub_dict.get("tribunal", ""),
                pub_dict.get("data_publicacao", ""),
                pub_dict.get("conteudo", ""),
                pub_dict.get("numero_processo"),
                pub_dict.get("classe_processual"),
                pub_dict.get("orgao_julgador"),
                json.dumps(pub_dict.get("assuntos", []), ensure_ascii=False),
                json.dumps(pub_dict.get("movimentos", []), ensure_ascii=False),
                pub_dict.get("url_origem"),
                pub_dict.get("caderno"),
                pub_dict.get("pagina"),
                json.dumps(pub_dict.get("oab_encontradas", []), ensure_ascii=False),
                json.dumps(pub_dict.get("advogados", []), ensure_ascii=False),
                json.dumps(pub_dict.get("partes", []), ensure_ascii=False),
                captacao_id,
            ))
            self.conn.commit()
            
            # Se INSERT foi ignorado (hash ja existe), atualizar captacao_id
            if cur.rowcount == 0 and pub_hash:
                self.conn.execute(
                    "UPDATE publicacoes SET captacao_id=? WHERE hash=? AND (captacao_id IS NULL OR captacao_id != ?)",
                    (captacao_id, pub_hash, captacao_id)
                )
                self.conn.commit()
            
            # Dispara webhook se nova publicacao
            if cur.lastrowid:
                pub_id = cur.lastrowid
                # Buscar nome da captacao
                captura = self.obter_captacao(captacao_id)
                nome_captacao = captura.get("nome", "") if captura else f"Captacao {captacao_id}"
                
                # Dispara webhook
                try:
                    trigger_webhook(WebhookEvent.NEW_PUBLICATION, {
                        "id": pub_id,
                        "numero_processo": pub_dict.get("numero_processo"),
                        "tribunal": pub_dict.get("tribunal"),
                        "fonte": pub_dict.get("fonte"),
                        "tipo_comunicacao": pub_dict.get("tipo_comunicacao", "intimacao"),
                        "conteudo": pub_dict.get("conteudo", "")[:500],
                        "data_publicacao": pub_dict.get("data_publicacao"),
                        "captacao_id": captacao_id,
                        "captacao_nome": nome_captacao,
                        "oab_encontradas": pub_dict.get("oab_encontradas", []),
                    })
                except Exception as e:
                    log.error("[Webhook] Erro ao Disparar: %s", e)
            
            return cur.lastrowid if cur.lastrowid else None
        except Exception as e:
            log.error("[Database] Erro ao salvar publicacao captacao: %s", e)
            return None

    def buscar_publicacoes_captacao(self, captacao_id: int, limite: int = 50,
                                     offset: int = 0, fonte: Optional[str] = None) -> List[Dict]:
        """Busca publicacoes vinculadas a uma captacao."""
        import json
        # Garantir coluna captacao_id existe
        try:
            self.conn.execute("ALTER TABLE publicacoes ADD COLUMN captacao_id INTEGER")
            self.conn.commit()
        except Exception:
            pass

        conditions = ["captacao_id=?"]
        params: list = [captacao_id]
        if fonte:
            conditions.append("fonte=?")
            params.append(fonte)
        where = f"WHERE {' AND '.join(conditions)}"
        sql = f"SELECT * FROM publicacoes {where} ORDER BY criado_em DESC LIMIT ? OFFSET ?"
        params.extend([limite, offset])
        rows = self.conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            for field in ("assuntos", "movimentos", "oab_encontradas", "advogados", "partes"):
                try:
                    d[field] = json.loads(d[field]) if d[field] else []
                except (json.JSONDecodeError, TypeError):
                    d[field] = []
            result.append(d)
        return result

    # === Stats Captacao ===

    def obter_stats_captacao(self) -> Dict[str, Any]:
        """Estatisticas das captacoes."""
        stats: Dict[str, Any] = {}
        stats["total_captacoes"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM captacoes"
        ).fetchone()["c"]
        stats["captacoes_ativas"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM captacoes WHERE ativo=1"
        ).fetchone()["c"]
        stats["captacoes_pausadas"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM captacoes WHERE ativo=1 AND pausado=1"
        ).fetchone()["c"]
        stats["total_execucoes"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM execucoes_captacao"
        ).fetchone()["c"]
        stats["execucoes_hoje"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM execucoes_captacao WHERE date(inicio)=date('now')"
        ).fetchone()["c"]
        stats["total_novos_encontrados"] = self.conn.execute(
            "SELECT COALESCE(SUM(novos_resultados),0) as c FROM execucoes_captacao"
        ).fetchone()["c"]

        row = self.conn.execute(
            "SELECT MAX(inicio) as t FROM execucoes_captacao"
        ).fetchone()
        stats["ultima_execucao"] = row["t"] if row else None

        # Por tipo
        rows = self.conn.execute(
            "SELECT tipo_busca, COUNT(*) as c FROM captacoes WHERE ativo=1 GROUP BY tipo_busca"
        ).fetchall()
        stats["por_tipo"] = {r["tipo_busca"]: r["c"] for r in rows}

        # Por prioridade
        rows = self.conn.execute(
            "SELECT prioridade, COUNT(*) as c FROM captacoes WHERE ativo=1 GROUP BY prioridade"
        ).fetchall()
        stats["por_prioridade"] = {r["prioridade"]: r["c"] for r in rows}

        return stats

    # === Processos Monitorados ===

    def registrar_processo_monitorado(self, numero_processo: str,
                                       tribunal: str = None,
                                       classe_processual: str = None,
                                       orgao_julgador: str = None,
                                       assuntos: Any = None,
                                       origem: str = "publicacao",
                                       origem_id: int = None) -> Optional[int]:
        """Registra processo para monitoramento. Ignora duplicatas."""
        import json as _json
        try:
            assuntos_str = ""
            if assuntos:
                if isinstance(assuntos, list):
                    assuntos_str = _json.dumps(assuntos, ensure_ascii=False)
                else:
                    assuntos_str = str(assuntos)
            cur = self.conn.execute("""
                INSERT OR IGNORE INTO processos_monitorados
                (numero_processo, tribunal, classe_processual, orgao_julgador,
                 assuntos, origem, origem_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (numero_processo.strip(), tribunal, classe_processual,
                  orgao_julgador, assuntos_str, origem, origem_id))
            self.conn.commit()
            if cur.lastrowid and self.conn.execute("SELECT changes()").fetchone()[0] > 0:
                log.info("[Database] Processo registrado para monitoramento: %s", numero_processo)
                return cur.lastrowid
            return None
        except Exception as e:
            log.error("[Database] Erro ao registrar processo: %s", e)
            return None

    def listar_processos_monitorados(self, status: str = None,
                                       limite: int = 100,
                                       offset: int = 0) -> List[Dict]:
        """Lista processos monitorados."""
        import json as _json
        conditions = []
        params: list = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM processos_monitorados {where} ORDER BY CASE WHEN data_ultima_movimentacao IS NULL THEN 1 ELSE 0 END, data_ultima_movimentacao DESC, atualizado_em DESC LIMIT ? OFFSET ?"
        params.extend([limite, offset])
        rows = self.conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            for field in ("movimentacoes",):
                try:
                    d[field] = _json.loads(d[field]) if d[field] else []
                except (_json.JSONDecodeError, TypeError):
                    d[field] = []
            result.append(d)
        return result

    def obter_processo_monitorado(self, numero_processo: str) -> Optional[Dict]:
        """Obtem processo monitorado pelo numero."""
        import json as _json
        row = self.conn.execute(
            "SELECT * FROM processos_monitorados WHERE numero_processo = ?",
            (numero_processo.strip(),)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["movimentacoes"] = _json.loads(d["movimentacoes"]) if d["movimentacoes"] else []
        except (_json.JSONDecodeError, TypeError):
            d["movimentacoes"] = []
        return d

    def atualizar_movimentacoes_processo(self, numero_processo: str,
                                          movimentacoes: list,
                                          tribunal: str = None,
                                          classe_processual: str = None,
                                          orgao_julgador: str = None) -> bool:
        """Atualiza movimentacoes de um processo monitorado."""
        import json as _json
        try:
            sets = [
                "movimentacoes = ?",
                "total_movimentacoes = ?",
                "ultima_verificacao = datetime('now', 'localtime')",
                "atualizado_em = datetime('now', 'localtime')",
            ]
            params: list = [_json.dumps(movimentacoes, ensure_ascii=False), len(movimentacoes)]
            if tribunal:
                sets.append("tribunal = ?")
                params.append(tribunal)
            if classe_processual:
                sets.append("classe_processual = ?")
                params.append(classe_processual)
            if orgao_julgador:
                sets.append("orgao_julgador = ?")
                params.append(orgao_julgador)
            
            # Extrair data da movimentacao mais recente
            _data_ultima_mov = None
            if movimentacoes:
                _datas = [m.get("dataHora", "") for m in movimentacoes if isinstance(m, dict) and m.get("dataHora")]
                if _datas:
                    _data_ultima_mov = max(_datas)
            sets.append("data_ultima_movimentacao = ?")
            params.append(_data_ultima_mov)

            params.append(numero_processo.strip())
            sql = f"UPDATE processos_monitorados SET {', '.join(sets)} WHERE numero_processo = ?"
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            log.error("[Database] Erro ao atualizar movimentacoes: %s", e)
            return False

    def processos_para_verificar(self, limite: int = 30,
                                   horas_intervalo: int = 6) -> List[Dict]:
        """Retorna processos que precisam de verificacao DataJud."""
        import json as _json
        rows = self.conn.execute("""
            SELECT * FROM processos_monitorados
            WHERE status = 'ativo'
            AND (ultima_verificacao IS NULL
                 OR ultima_verificacao < datetime('now', ?))
            ORDER BY ultima_verificacao ASC NULLS FIRST
            LIMIT ?
        """, (f'-{horas_intervalo} hours', limite)).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["movimentacoes"] = _json.loads(d["movimentacoes"]) if d["movimentacoes"] else []
            except (_json.JSONDecodeError, TypeError):
                d["movimentacoes"] = []
            result.append(d)
        return result

    def stats_processos_monitorados(self) -> Dict[str, Any]:
        """Estatisticas dos processos monitorados."""
        stats: Dict[str, Any] = {}
        stats["total"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM processos_monitorados"
        ).fetchone()["c"]
        stats["ativos"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM processos_monitorados WHERE status='ativo'"
        ).fetchone()["c"]
        stats["com_movimentacoes"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM processos_monitorados WHERE total_movimentacoes > 0"
        ).fetchone()["c"]
        stats["verificados_hoje"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM processos_monitorados WHERE date(ultima_verificacao)=date('now')"
        ).fetchone()["c"]
        stats["nunca_verificados"] = self.conn.execute(
            "SELECT COUNT(*) as c FROM processos_monitorados WHERE ultima_verificacao IS NULL"
        ).fetchone()["c"]
        row = self.conn.execute(
            "SELECT MAX(ultima_verificacao) as t FROM processos_monitorados"
        ).fetchone()
        stats["ultima_verificacao"] = row["t"] if row else None
        # Por origem
        rows = self.conn.execute(
            "SELECT origem, COUNT(*) as c FROM processos_monitorados GROUP BY origem"
        ).fetchall()
        stats["por_origem"] = {r["origem"]: r["c"] for r in rows}
        return stats

    def registrar_historico_processo(self, numero_processo: str, status: str,
                                    fonte: str, total_mov: int, novas: int,
                                    detalhes: str = None) -> int:
        """Registra uma entrada no historico de verificacoes do processo."""
        cur = self.conn.execute("""
            INSERT INTO processos_monitorados_historico
            (numero_processo, status, fonte, total_movimentacoes, novas_movimentacoes, detalhes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (numero_processo, status, fonte, total_mov, novas, detalhes))
        self.conn.commit()
        return cur.lastrowid or 0

    def listar_historico_processo(self, numero_processo: str, limite: int = 50) -> List[Dict]:
        """Lista o historico de verificacoes de um processo especifico."""
        rows = self.conn.execute("""
            SELECT * FROM processos_monitorados_historico
            WHERE numero_processo = ?
            ORDER BY data_verificacao DESC
            LIMIT ?
        """, (numero_processo, limite)).fetchall()
        return [dict(r) for r in rows]

    def deletar_processo_monitorado(self, numero_processo: str) -> bool:
        """Remove processo monitorado (soft delete - muda status para inativo)."""
        cur = self.conn.execute(
            "UPDATE processos_monitorados SET status='inativo', atualizado_em=datetime('now', 'localtime') WHERE numero_processo=?",
            (numero_processo.strip(),)
        )
        self.conn.commit()
        return cur.rowcount > 0

    # === AI Config ===

    def obter_ai_config(self, function_key: str) -> Optional[Dict]:
        """Obtem configuracao de IA para uma funcao especifica."""
        row = self.conn.execute("SELECT * FROM ai_config WHERE function_key=?", (function_key,)).fetchone()
        return dict(row) if row else None

    def listar_ai_configs(self) -> List[Dict]:
        """Lista todas as configuracoes de IA."""
        rows = self.conn.execute("SELECT * FROM ai_config").fetchall()
        return [dict(r) for r in rows]

    def salvar_ai_config(self, function_key: str, provider: str, model_name: str, 
                         api_key: Optional[str] = None, base_url: Optional[str] = None, 
                         enabled: bool = True) -> bool:
        """Salva ou atualiza uma configuracao de IA."""
        self.conn.execute("""
            INSERT INTO ai_config (function_key, provider, model_name, api_key, base_url, enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(function_key) DO UPDATE SET
                provider=excluded.provider,
                model_name=excluded.model_name,
                api_key=COALESCE(excluded.api_key, ai_config.api_key),
                base_url=COALESCE(excluded.base_url, ai_config.base_url),
                enabled=excluded.enabled,
                updated_at=datetime('now', 'localtime')
        """, (function_key, provider, model_name, api_key, base_url, 1 if enabled else 0))
        self.conn.commit()
        return True

    # =========================================================================
    # System Settings
    # =========================================================================

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Busca uma configuracao no banco."""
        try:
            row = self.conn.execute(
                "SELECT value FROM system_settings WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default
        except Exception as e:
            log.error("Erro ao buscar setting %s: %s", key, e)
            return default

    def set_setting(self, key: str, value: Any):
        """Salva ou atualiza uma configuracao."""
        try:
            self.conn.execute(
                "INSERT INTO system_settings (key, value, updated_at) VALUES (?, ?, datetime('now', 'localtime')) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, str(value))
            )
            self.conn.commit()
        except Exception as e:
            log.error("Erro ao salvar setting %s: %s", key, e)
            self.conn.rollback()
            raise e

    def listar_settings(self) -> Dict[str, str]:
        """Lista todas as configuracoes."""
        try:
            rows = self.conn.execute("SELECT key, value FROM system_settings").fetchall()
            return {row["key"]: row["value"] for row in rows}
        except Exception as e:
            log.error("Erro ao listar settings: %s", e)
            return {}


# =========================================================================
# Singleton DB Accessor
# =========================================================================

_db_instance: Optional[Database] = None


def get_database() -> Database:
    """
    Retorna a instancia singleton do banco de dados.
    Centralizado aqui para evitar circular imports entre app.py e audit.py.
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
