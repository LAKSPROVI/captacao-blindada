#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste dos endpoints da API
Executar: python test_api.py
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ["IS_PRODUCTION"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-key-12345678901234567890123456789012"

print("=" * 50)
print("TESTE DOS ENDPOINTS DA API")
print("=" * 50)

print("\n[1] Testando Imports dos Routers:")

try:
    from djen.api.routers import captacao
    print("    [OK] captacao.py importado")
    print("         DEFAULT_LIMIT: " + str(captacao.DEFAULT_LIMIT))
    print("         MAX_LIMIT: " + str(captacao.MAX_LIMIT))
    print("         CACHE_TTL_SECONDS: " + str(captacao.CACHE_TTL_SECONDS))
except Exception as e:
    print("    [ERRO] captacao: " + str(e))

try:
    from djen.api.routers import datajud
    print("    [OK] datajud.py importado")
except Exception as e:
    print("    [ERRO] datajud: " + str(e))

try:
    from djen.api.routers import processo
    print("    [OK] processo.py importado")
    print("         DEFAULT_LIMIT: " + str(processo.DEFAULT_LIMIT))
    print("         MAX_LIMIT: " + str(processo.MAX_LIMIT))
except Exception as e:
    print("    [ERRO] processo: " + str(e))

try:
    from djen.api.routers import monitor
    print("    [OK] monitor.py importado")
    print("         DEFAULT_LIMIT: " + str(monitor.DEFAULT_LIMIT))
    print("         MAX_LIMIT: " + str(monitor.DEFAULT_LIMIT))
except Exception as e:
    print("    [ERRO] monitor: " + str(e))

try:
    from djen.api.routers import processos_monitor
    print("    [OK] processos_monitor.py importado")
    print("         DEFAULT_LIMIT: " + str(processos_monitor.DEFAULT_LIMIT))
    print("         MAX_LIMIT: " + str(processos_monitor.MAX_LIMIT))
except Exception as e:
    print("    [ERRO] processos_monitor: " + str(e))

try:
    from djen.api.routers import users
    print("    [OK] users.py importado")
except Exception as e:
    print("    [ERRO] users: " + str(e))

print("\n[2] Testando Database:")
try:
    from djen.api.database import Database
    db = Database(":memory:")
    print("    [OK] Database inicializada")
    
    stats = db.obter_stats()
    print("         Keys em stats: " + str(len(stats)))
except Exception as e:
    print("    [ERRO]: " + str(e)[:60])

print("\n[3] Verificando Novos Endpoints:")

captacao_attrs = [a for a in dir(captacao) if not a.startswith('_')]
endpoints = [a for a in captacao_attrs if a in ['listar_captacoes', 'relatorio_sistema', 'historico_captacao']]
print("    Endpoints captacao: " + str(endpoints))

print("\n" + "=" * 50)
print("TESTES CONCLUIDOS!")
print("=" * 50)