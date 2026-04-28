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

from djen.api.crypto import encrypt_value, decrypt_value

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
                captacao_id INTEGER,
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (monitorado_id) REFERENCES monitorados(id),
                FOREIGN KEY (captacao_id) REFERENCES captacoes(id)
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
            CREATE INDEX IF NOT EXISTS idx_publicacoes_monitorado ON publicacoes(monitorado_id);
            CREATE INDEX IF NOT EXISTS idx_publicacoes_criado ON publicacoes(criado_em);
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

            -- =========================================================
            -- Automacoes (regras)
            -- =========================================================
            CREATE TABLE IF NOT EXISTS automacao_regras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL,
                condicao TEXT NOT NULL,
                acao TEXT NOT NULL,
                ativo INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- =========================================================
            -- Kanban
            -- =========================================================
            CREATE TABLE IF NOT EXISTS kanban_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descricao TEXT,
                numero_processo TEXT,
                coluna TEXT DEFAULT 'novo',
                prioridade TEXT DEFAULT 'normal',
                responsavel TEXT,
                cor TEXT DEFAULT '#3b82f6',
                ordem INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                atualizado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- =========================================================
            -- Prazos Processuais
            -- =========================================================
            CREATE TABLE IF NOT EXISTS prazos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_processo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                tipo TEXT DEFAULT 'prazo',
                data_inicio TEXT NOT NULL,
                dias_uteis INTEGER NOT NULL,
                data_fim TEXT NOT NULL,
                status TEXT DEFAULT 'ativo',
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- =========================================================
            -- Agenda / Compromissos
            -- =========================================================
            CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descricao TEXT,
                tipo TEXT DEFAULT 'compromisso',
                numero_processo TEXT,
                data_evento TEXT NOT NULL,
                hora_evento TEXT,
                local TEXT,
                status TEXT DEFAULT 'pendente',
                lembrete_dias INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- =========================================================
            -- Favoritos e Tags
            -- =========================================================
            CREATE TABLE IF NOT EXISTS favoritos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                referencia_id INTEGER NOT NULL,
                titulo TEXT,
                descricao TEXT,
                cor TEXT DEFAULT '#3b82f6',
                criado_em TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(tipo, referencia_id)
            );

            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                cor TEXT DEFAULT '#6b7280',
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS tag_associacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                referencia_id INTEGER NOT NULL,
                UNIQUE(tag_id, tipo, referencia_id)
            );

            -- =========================================================
            -- Notas Globais
            -- =========================================================
            CREATE TABLE IF NOT EXISTS notas_globais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT,
                conteudo TEXT,
                cor TEXT DEFAULT '#3b82f6',
                fixada INTEGER DEFAULT 0,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- =========================================================
            -- Processo Anotacoes
            -- =========================================================
            CREATE TABLE IF NOT EXISTS processo_anotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_processo TEXT NOT NULL,
                texto TEXT NOT NULL,
                tipo TEXT DEFAULT 'nota',
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- =========================================================
            -- Webhook Received (integracoes)
            -- =========================================================
            CREATE TABLE IF NOT EXISTS webhook_received (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                payload TEXT,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- =========================================================
            -- Captacao Agendamentos
            -- =========================================================
            CREATE TABLE IF NOT EXISTS captacao_agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captacao_id INTEGER NOT NULL,
                data_execucao TEXT NOT NULL,
                status TEXT DEFAULT 'pendente',
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- =========================================================
            -- Automacao Historico
            -- =========================================================
            CREATE TABLE IF NOT EXISTS automacao_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regra_id INTEGER,
                tipo TEXT,
                resultado TEXT,
                detalhes TEXT,
                criado_em TEXT DEFAULT (datetime('now', 'localtime'))
            );

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
        
        # --- Migration: adicionar captacao_id na tabela publicacoes ---
        try:
            conn.execute("ALTER TABLE publicacoes ADD COLUMN captacao_id INTEGER")
        except Exception:
            pass
        # Create index for captacao_id (after migration ensures column exists)
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_publicacoes_captacao ON publicacoes(captacao_id)")
            conn.commit()
        except Exception:
            pass

        # --- Migration: adicionar bloqueado na tabela users (from users.py) ---
        try:
            conn.execute("ALTER TABLE users ADD COLUMN bloqueado INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass

        # --- Migration: adicionar lida/favorita na tabela publicacoes (from monitor.py) ---
        for col in ("lida", "favorita"):
            try:
                conn.execute(f"ALTER TABLE publicacoes ADD COLUMN {col} INTEGER DEFAULT 0")
                conn.commit()
            except Exception:
                pass

        # --- Migration: adicionar max_resultados/max_paginas na tabela captacoes (from captacao.py) ---
        for col, default in [("max_resultados", "1000"), ("max_paginas", "10")]:
            try:
                conn.execute(f"ALTER TABLE captacoes ADD COLUMN {col} INTEGER DEFAULT {default}")
                conn.commit()
            except Exception:
                pass

        # --- Migration: adicionar suspenso na tabela tenants (from users.py) ---
        try:
            conn.execute("ALTER TABLE tenants ADD COLUMN suspenso INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass

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
                              horario_fim: str = "23:00", dias_semana: str = "1,2,3,4,5",
                              tenant_id: Optional[int] = None) -> int:
        try:
            cur = self.conn.execute(
                """INSERT INTO monitorados
                   (tipo, valor, nome_amigavel, tribunal, fontes,
                    intervalo_minutos, horario_inicio, horario_fim, dias_semana, tenant_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tipo, valor, nome_amigavel, tribunal, fontes,
                 intervalo_minutos, horario_inicio, horario_fim, dias_semana, tenant_id),
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # Ja existe, reativar
            params = [intervalo_minutos, horario_inicio, horario_fim, dias_semana, tipo, valor]
            tenant_clause = ""
            if tenant_id is not None:
                tenant_clause = " AND tenant_id=?"
                params.append(tenant_id)
            self.conn.execute(
                f"""UPDATE monitorados SET ativo=1, atualizado_em=datetime('now', 'localtime'),
                   intervalo_minutos=?, horario_inicio=?, horario_fim=?, dias_semana=?
                   WHERE tipo=? AND valor=?{tenant_clause}""",
                params,
            )
            self.conn.commit()
            params2 = [tipo, valor]
            if tenant_id is not None:
                params2.append(tenant_id)
            row = self.conn.execute(f"SELECT id FROM monitorados WHERE tipo=? AND valor=?{tenant_clause}", params2).fetchone()
            return row["id"] if row else 0

    def listar_monitorados(self, apenas_ativos: bool = True, tenant_id: Optional[int] = None) -> List[Dict]:
        conditions = []
        params = []
        if apenas_ativos:
            conditions.append("m.ativo=1")
        if tenant_id is not None:
            conditions.append("m.tenant_id=?")
            params.append(tenant_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT m.*, COALESCE(p.cnt, 0) as total_publicacoes
            FROM monitorados m
            LEFT JOIN (SELECT monitorado_id, COUNT(*) as cnt FROM publicacoes GROUP BY monitorado_id) p
            ON m.id = p.monitorado_id
            {where}
            ORDER BY m.criado_em DESC
        """
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def obter_monitorado(self, monitorado_id: int, tenant_id: Optional[int] = None) -> Optional[Dict]:
        if tenant_id is not None:
            row = self.conn.execute("SELECT * FROM monitorados WHERE id=? AND tenant_id=?", (monitorado_id, tenant_id)).fetchone()
        else:
            row = self.conn.execute("SELECT * FROM monitorados WHERE id=?", (monitorado_id,)).fetchone()
        return dict(row) if row else None

    def atualizar_monitorado(self, monitorado_id: int, tenant_id: Optional[int] = None, **kwargs) -> bool:
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
        where = "WHERE id=?"
        if tenant_id is not None:
            where += " AND tenant_id=?"
            vals.append(tenant_id)
        self.conn.execute(f"UPDATE monitorados SET {', '.join(sets)} {where}", vals)
        self.conn.commit()
        return True

    def desativar_monitorado(self, monitorado_id: int, tenant_id: Optional[int] = None) -> bool:
        params = [monitorado_id]
        where = "WHERE id=?"
        if tenant_id is not None:
            where += " AND tenant_id=?"
            params.append(tenant_id)
        self.conn.execute(f"UPDATE monitorados SET ativo=0, atualizado_em=datetime('now', 'localtime') {where}", params)
        self.conn.commit()
        return True

    # === Publicacoes ===

    def salvar_publicacao(self, pub_dict: Dict, monitorado_id: Optional[int] = None,
                          tenant_id: Optional[int] = None) -> Optional[int]:
        import json
        try:
            cur = self.conn.execute("""
                INSERT OR IGNORE INTO publicacoes
                (hash, fonte, tribunal, data_publicacao, conteudo, numero_processo,
                 classe_processual, orgao_julgador, assuntos, movimentos, url_origem,
                 caderno, pagina, oab_encontradas, advogados, partes, monitorado_id, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                tenant_id,
            ))
            self.conn.commit()
            foi_inserido = cur.rowcount > 0
            return cur.lastrowid if foi_inserido else None
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
            # Suporta valores separados por vírgula: "djen_api,djen"
            fontes = [f.strip() for f in fonte.split(",") if f.strip()]
            if len(fontes) == 1:
                conditions.append("fonte=?")
                params.append(fontes[0])
            else:
                placeholders = ",".join(["?"] * len(fontes))
                conditions.append(f"fonte IN ({placeholders})")
                params.extend(fontes)
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

    def listar_monitorados_pendentes(self, agora_iso: str, tenant_id: Optional[int] = None) -> List[Dict]:
        """Retorna monitorados ativos que precisam de busca agora."""
        params = [agora_iso]
        tenant_clause = ""
        if tenant_id is not None:
            tenant_clause = " AND tenant_id = ?"
            params.append(tenant_id)
        query = f"""
            SELECT * FROM monitorados
            WHERE ativo = 1
            AND (proxima_busca IS NULL OR proxima_busca <= ?){tenant_clause}
        """
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def atualizar_monitorado_pos_execucao(self, monitorado_id: int, total: int, novos: int, proxima_busca: str,
                                          tenant_id: Optional[int] = None):
        """Atualiza estatisticas e agenda proxima execucao."""
        params = [proxima_busca, monitorado_id]
        where = "WHERE id = ?"
        if tenant_id is not None:
            where += " AND tenant_id = ?"
            params.append(tenant_id)
        self.conn.execute(
            f"""UPDATE monitorados SET
               ultima_busca = datetime('now', 'localtime'),
               proxima_busca = ?
               {where}""",
            params,
        )
        self.conn.commit()

    def registrar_busca(self, tipo: str, fonte: str, tribunal: Optional[str],
                         termos: str, resultados: int, status: str = "ok",
                         duracao_ms: int = 0, erro: Optional[str] = None,
                         tenant_id: Optional[int] = None) -> int:
        cur = self.conn.execute("""
            INSERT INTO buscas (tipo, fonte, tribunal, termos, resultados, status, duracao_ms, erro, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tipo, fonte, tribunal, termos, resultados, status, duracao_ms, erro, tenant_id))
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

    def obter_stats(self, tenant_id: Optional[int] = None) -> Dict[str, Any]:
        stats = {}
        tenant_clause = ""
        tenant_params = []
        if tenant_id is not None:
            tenant_clause = " WHERE tenant_id=?"
            tenant_params = [tenant_id]

        stats["total_monitorados"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM monitorados{tenant_clause}", tenant_params
        ).fetchone()["c"]
        stats["monitorados_ativos"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM monitorados WHERE ativo=1{' AND tenant_id=?' if tenant_id is not None else ''}",
            tenant_params
        ).fetchone()["c"]
        stats["total_publicacoes"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM publicacoes{tenant_clause}", tenant_params
        ).fetchone()["c"]
        stats["publicacoes_hoje"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM publicacoes WHERE date(criado_em)=date('now'){' AND tenant_id=?' if tenant_id is not None else ''}",
            tenant_params
        ).fetchone()["c"]
        stats["publicacoes_semana"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM publicacoes WHERE criado_em >= datetime('now', '-7 days'){' AND tenant_id=?' if tenant_id is not None else ''}",
            tenant_params
        ).fetchone()["c"]
        stats["total_buscas"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM buscas{tenant_clause}", tenant_params
        ).fetchone()["c"]

        # Fontes ativas (com busca nos ultimos 7 dias)
        stats["fontes_ativas"] = self.conn.execute(
            f"SELECT COUNT(DISTINCT fonte) as c FROM buscas WHERE criado_em >= datetime('now', '-7 days') AND status='ok'{' AND tenant_id=?' if tenant_id is not None else ''}",
            tenant_params
        ).fetchone()["c"]

        # Ultima busca
        row = self.conn.execute(
            f"SELECT MAX(criado_em) as t FROM buscas{tenant_clause}", tenant_params
        ).fetchone()
        stats["ultima_busca"] = row["t"] if row else None

        return stats

    # === Captacoes Automatizadas ===

    def criar_captacao(self, nome: str, tipo_busca: str = "processo", tenant_id: Optional[int] = None, **kwargs) -> int:
        """Cria nova captacao automatizada."""
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        BRASILIA_TZ = ZoneInfo("America/Sao_Paulo")
        intervalo = kwargs.get("intervalo_minutos", 120)
        proxima = (datetime.now(tz=BRASILIA_TZ) + timedelta(minutes=intervalo)).isoformat()

        cols = ["nome", "tipo_busca", "proxima_execucao", "tenant_id"]
        vals = [nome, tipo_busca, proxima, tenant_id]

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

    def obter_captacao(self, captacao_id: int, tenant_id: Optional[int] = None) -> Optional[Dict]:
        """Obtem uma captacao por ID."""
        if tenant_id is not None:
            row = self.conn.execute("SELECT * FROM captacoes WHERE id=? AND tenant_id=?", (captacao_id, tenant_id)).fetchone()
        else:
            row = self.conn.execute("SELECT * FROM captacoes WHERE id=?", (captacao_id,)).fetchone()
        return dict(row) if row else None

    def listar_captacoes(self, ativo: Optional[bool] = None, tipo_busca: Optional[str] = None,
                          prioridade: Optional[str] = None, tenant_id: Optional[int] = None) -> List[Dict]:
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
        if tenant_id is not None:
            conditions.append("tenant_id=?")
            params.append(tenant_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM captacoes {where} ORDER BY criado_em DESC"
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def atualizar_captacao(self, captacao_id: int, tenant_id: Optional[int] = None, **kwargs) -> bool:
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
        where = "WHERE id=?"
        if tenant_id is not None:
            where += " AND tenant_id=?"
            vals.append(tenant_id)
        self.conn.execute(f"UPDATE captacoes SET {', '.join(sets)} {where}", vals)
        self.conn.commit()
        return True

    def atualizar_captacao_pos_execucao(self, captacao_id: int, total: int, novos: int,
                                         intervalo_minutos: int, tenant_id: Optional[int] = None):
        """Atualiza captacao apos execucao: contadores e proxima_execucao."""
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        BRASILIA_TZ = ZoneInfo("America/Sao_Paulo")
        proxima = (datetime.now(tz=BRASILIA_TZ) + timedelta(minutes=intervalo_minutos)).isoformat()
        params = [total, novos, proxima, captacao_id]
        where = "WHERE id=?"
        if tenant_id is not None:
            where += " AND tenant_id=?"
            params.append(tenant_id)
        self.conn.execute(f"""
            UPDATE captacoes SET
                ultima_execucao=datetime('now', 'localtime'),
                total_execucoes=total_execucoes+1,
                total_resultados=total_resultados+?,
                total_novos=total_novos+?,
                proxima_execucao=?,
                atualizado_em=datetime('now', 'localtime')
            {where}
        """, params)
        self.conn.commit()

    def listar_captacoes_pendentes(self, agora_iso: str, tenant_id: Optional[int] = None) -> List[Dict]:
        """Lista captacoes ativas nao pausadas com proxima_execucao <= agora."""
        params = [agora_iso]
        tenant_clause = ""
        if tenant_id is not None:
            tenant_clause = " AND tenant_id=?"
            params.append(tenant_id)
        rows = self.conn.execute(f"""
            SELECT * FROM captacoes
            WHERE ativo=1 AND pausado=0
              AND (proxima_execucao IS NULL OR proxima_execucao <= ?){tenant_clause}
            ORDER BY
                CASE prioridade WHEN 'urgente' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,
                proxima_execucao ASC
        """, params).fetchall()
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
                                   offset: int = 0, tenant_id: Optional[int] = None) -> List[Dict]:
        """Lista execucoes de uma captacao."""
        conditions = ["captacao_id=?"]
        params = [captacao_id]
        if tenant_id is not None:
            conditions.append("""captacao_id IN (SELECT id FROM captacoes WHERE tenant_id=?)""")
            params.append(tenant_id)
        where = f"WHERE {' AND '.join(conditions)}"
        rows = self.conn.execute(f"""
            SELECT * FROM execucoes_captacao
            {where}
            ORDER BY inicio DESC
            LIMIT ? OFFSET ?
        """, params + [limite, offset]).fetchall()
        return [dict(r) for r in rows]

    # === Publicacoes vinculadas a captacao ===

    def salvar_publicacao_captacao(self, pub_dict: Dict, captacao_id: int,
                                    tenant_id: Optional[int] = None) -> Optional[int]:
        """Salva publicacao vinculada a uma captacao (sem FK para monitorados)."""
        import json
        from djen.api.webhook import trigger_webhook, WebhookEvent
        try:
            pub_hash = pub_dict.get("hash", "")

            cur = self.conn.execute("""
                INSERT OR IGNORE INTO publicacoes
                (hash, fonte, tribunal, data_publicacao, conteudo, numero_processo,
                 classe_processual, orgao_julgador, assuntos, movimentos, url_origem,
                 caderno, pagina, oab_encontradas, advogados, partes, captacao_id, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                tenant_id,
            ))
            self.conn.commit()
            
            # Verificar se foi realmente inserido (rowcount=1) ou ignorado (rowcount=0)
            foi_inserido = cur.rowcount > 0
            pub_id = cur.lastrowid if foi_inserido else None
            
            # Se INSERT foi ignorado (hash ja existe), atualizar captacao_id
            if not foi_inserido and pub_hash:
                self.conn.execute(
                    "UPDATE publicacoes SET captacao_id=? WHERE hash=? AND (captacao_id IS NULL OR captacao_id != ?)",
                    (captacao_id, pub_hash, captacao_id)
                )
                self.conn.commit()
            
            # Dispara webhook se nova publicacao
            if foi_inserido and pub_id:
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
            
            return pub_id
        except Exception as e:
            log.error("[Database] Erro ao salvar publicacao captacao: %s", e)
            return None

    def buscar_publicacoes_captacao(self, captacao_id: int, limite: int = 50,
                                     offset: int = 0, fonte: Optional[str] = None,
                                     tenant_id: Optional[int] = None) -> List[Dict]:
        """Busca publicacoes vinculadas a uma captacao."""
        import json
        conditions = ["captacao_id=?"]
        params: list = [captacao_id]
        if fonte:
            conditions.append("fonte=?")
            params.append(fonte)
        if tenant_id is not None:
            conditions.append("tenant_id=?")
            params.append(tenant_id)
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

    def obter_stats_captacao(self, tenant_id: Optional[int] = None) -> Dict[str, Any]:
        """Estatisticas das captacoes."""
        stats: Dict[str, Any] = {}
        tenant_clause = ""
        tenant_params = []
        if tenant_id is not None:
            tenant_clause = " WHERE tenant_id=?"
            tenant_params = [tenant_id]

        stats["total_captacoes"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM captacoes{tenant_clause}", tenant_params
        ).fetchone()["c"]
        stats["captacoes_ativas"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM captacoes WHERE ativo=1{' AND tenant_id=?' if tenant_id is not None else ''}",
            tenant_params
        ).fetchone()["c"]
        stats["captacoes_pausadas"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM captacoes WHERE ativo=1 AND pausado=1{' AND tenant_id=?' if tenant_id is not None else ''}",
            tenant_params
        ).fetchone()["c"]

        # execucoes_captacao: filtrar via subquery nas captacoes do tenant
        if tenant_id is not None:
            exec_clause = " WHERE captacao_id IN (SELECT id FROM captacoes WHERE tenant_id=?)"
            exec_params = [tenant_id]
        else:
            exec_clause = ""
            exec_params = []

        stats["total_execucoes"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM execucoes_captacao{exec_clause}", exec_params
        ).fetchone()["c"]
        stats["execucoes_hoje"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM execucoes_captacao WHERE date(inicio)=date('now'){' AND captacao_id IN (SELECT id FROM captacoes WHERE tenant_id=?)' if tenant_id is not None else ''}",
            exec_params
        ).fetchone()["c"]
        stats["total_novos_encontrados"] = self.conn.execute(
            f"SELECT COALESCE(SUM(novos_resultados),0) as c FROM execucoes_captacao{exec_clause}", exec_params
        ).fetchone()["c"]

        row = self.conn.execute(
            f"SELECT MAX(inicio) as t FROM execucoes_captacao{exec_clause}", exec_params
        ).fetchone()
        stats["ultima_execucao"] = row["t"] if row else None

        # Por tipo
        rows = self.conn.execute(
            f"SELECT tipo_busca, COUNT(*) as c FROM captacoes WHERE ativo=1{' AND tenant_id=?' if tenant_id is not None else ''} GROUP BY tipo_busca",
            tenant_params
        ).fetchall()
        stats["por_tipo"] = {r["tipo_busca"]: r["c"] for r in rows}

        # Por prioridade
        rows = self.conn.execute(
            f"SELECT prioridade, COUNT(*) as c FROM captacoes WHERE ativo=1{' AND tenant_id=?' if tenant_id is not None else ''} GROUP BY prioridade",
            tenant_params
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
                                       origem_id: int = None,
                                       tenant_id: Optional[int] = None) -> Optional[int]:
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
                 assuntos, origem, origem_id, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (numero_processo.strip(), tribunal, classe_processual,
                  orgao_julgador, assuntos_str, origem, origem_id, tenant_id))
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
                                       offset: int = 0,
                                       tenant_id: Optional[int] = None) -> List[Dict]:
        """Lista processos monitorados."""
        import json as _json
        conditions = []
        params: list = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if tenant_id is not None:
            conditions.append("tenant_id = ?")
            params.append(tenant_id)
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

    def obter_processo_monitorado(self, numero_processo: str, tenant_id: Optional[int] = None) -> Optional[Dict]:
        """Obtem processo monitorado pelo numero."""
        import json as _json
        if tenant_id is not None:
            row = self.conn.execute(
                "SELECT * FROM processos_monitorados WHERE numero_processo = ? AND tenant_id = ?",
                (numero_processo.strip(), tenant_id)
            ).fetchone()
        else:
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
                                          orgao_julgador: str = None,
                                          tenant_id: Optional[int] = None) -> bool:
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
            where = "WHERE numero_processo = ?"
            if tenant_id is not None:
                where += " AND tenant_id = ?"
                params.append(tenant_id)
            sql = f"UPDATE processos_monitorados SET {', '.join(sets)} {where}"
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            log.error("[Database] Erro ao atualizar movimentacoes: %s", e)
            return False

    def processos_para_verificar(self, limite: int = 30,
                                   horas_intervalo: int = 6,
                                   tenant_id: Optional[int] = None) -> List[Dict]:
        """Retorna processos que precisam de verificacao DataJud."""
        import json as _json
        params = [f'-{horas_intervalo} hours']
        tenant_clause = ""
        if tenant_id is not None:
            tenant_clause = " AND tenant_id = ?"
            params.append(tenant_id)
        params.append(limite)
        rows = self.conn.execute(f"""
            SELECT * FROM processos_monitorados
            WHERE status = 'ativo'
            AND (ultima_verificacao IS NULL
                 OR ultima_verificacao < datetime('now', ?)){tenant_clause}
            ORDER BY ultima_verificacao ASC NULLS FIRST
            LIMIT ?
        """, params).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["movimentacoes"] = _json.loads(d["movimentacoes"]) if d["movimentacoes"] else []
            except (_json.JSONDecodeError, TypeError):
                d["movimentacoes"] = []
            result.append(d)
        return result

    def stats_processos_monitorados(self, tenant_id: Optional[int] = None) -> Dict[str, Any]:
        """Estatisticas dos processos monitorados."""
        stats: Dict[str, Any] = {}
        tenant_clause = ""
        tenant_and = ""
        tenant_params = []
        if tenant_id is not None:
            tenant_clause = " WHERE tenant_id=?"
            tenant_and = " AND tenant_id=?"
            tenant_params = [tenant_id]

        stats["total"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM processos_monitorados{tenant_clause}", tenant_params
        ).fetchone()["c"]
        stats["ativos"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM processos_monitorados WHERE status='ativo'{tenant_and}", tenant_params
        ).fetchone()["c"]
        stats["com_movimentacoes"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM processos_monitorados WHERE total_movimentacoes > 0{tenant_and}", tenant_params
        ).fetchone()["c"]
        stats["verificados_hoje"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM processos_monitorados WHERE date(ultima_verificacao)=date('now'){tenant_and}", tenant_params
        ).fetchone()["c"]
        stats["nunca_verificados"] = self.conn.execute(
            f"SELECT COUNT(*) as c FROM processos_monitorados WHERE ultima_verificacao IS NULL{tenant_and}", tenant_params
        ).fetchone()["c"]
        row = self.conn.execute(
            f"SELECT MAX(ultima_verificacao) as t FROM processos_monitorados{tenant_clause}", tenant_params
        ).fetchone()
        stats["ultima_verificacao"] = row["t"] if row else None
        # Por origem
        rows = self.conn.execute(
            f"SELECT origem, COUNT(*) as c FROM processos_monitorados{tenant_clause} GROUP BY origem", tenant_params
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

    def deletar_processo_monitorado(self, numero_processo: str, tenant_id: Optional[int] = None) -> bool:
        """Remove processo monitorado (soft delete - muda status para inativo)."""
        params = [numero_processo.strip()]
        where = "WHERE numero_processo=?"
        if tenant_id is not None:
            where += " AND tenant_id=?"
            params.append(tenant_id)
        cur = self.conn.execute(
            f"UPDATE processos_monitorados SET status='inativo', atualizado_em=datetime('now', 'localtime') {where}",
            params
        )
        self.conn.commit()
        return cur.rowcount > 0

    # === AI Config ===

    def obter_ai_config(self, function_key: str) -> Optional[Dict]:
        """Obtem configuracao de IA para uma funcao especifica."""
        row = self.conn.execute("SELECT * FROM ai_config WHERE function_key=?", (function_key,)).fetchone()
        if not row:
            return None
        config = dict(row)
        config["api_key"] = decrypt_value(config.get("api_key", ""))
        return config

    def listar_ai_configs(self) -> List[Dict]:
        """Lista todas as configuracoes de IA."""
        rows = self.conn.execute("SELECT * FROM ai_config").fetchall()
        configs = []
        for r in rows:
            config = dict(r)
            config["api_key"] = decrypt_value(config.get("api_key", ""))
            configs.append(config)
        return configs

    def salvar_ai_config(self, function_key: str, provider: str, model_name: str, 
                         api_key: Optional[str] = None, base_url: Optional[str] = None, 
                         enabled: bool = True) -> bool:
        """Salva ou atualiza uma configuracao de IA."""
        encrypted_key = encrypt_value(api_key) if api_key else None
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
        """, (function_key, provider, model_name, encrypted_key, base_url, 1 if enabled else 0))
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
_db_lock = threading.Lock()


def get_database() -> Database:
    """
    Retorna a instancia singleton do banco de dados.
    Centralizado aqui para evitar circular imports entre app.py e audit.py.
    """
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = Database()
    return _db_instance
