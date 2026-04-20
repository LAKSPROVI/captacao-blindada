#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de Rate Limiting
Executar: python test_ratelimit.py
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ["IS_PRODUCTION"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-key-12345678901234567890123456789012"

print("=" * 60)
print("TESTE DE RATE LIMITING - CAPTACAO BLINDADA")
print("=" * 60)

print("\n[1] Verificando dependencias...")

try:
    from slowapi import Limiter
    print("    [OK] slowapi instalado")
except ImportError:
    print("    [ERRO] slowapi NAO instalado")
    print("    Execute: pip install slowapi")
    sys.exit(1)

print("\n[2] Testando importacao do modulo ratelimit...")

try:
    from djen.api import ratelimit
    print("    [OK] Modulo ratelimit importado")
    print("     Limites configurados:")
    for key, limit in ratelimit.RATE_LIMITS.items():
        print(f"       - {key}: {limit}")
except Exception as e:
    print(f"    [ERRO] {type(e).__name__}: {e}")
    sys.exit(1)

print("\n[3] Verificando limites padrao...")

DEFAULT = ratelimit.RATE_LIMITS.get("default", "")
EXPECTADO = "60/minute"

if DEFAULT == EXPECTADO:
    print(f"    [OK] Limite padrao: {DEFAULT}")
else:
    print(f"    [ERRO] Limite padrao: {DEFAULT} (esperado: {EXPECTADO})")

print("\n[4] Verificando limiter no app...")

try:
    from djen.api.app import app
    if hasattr(app.state, 'limiter'):
        print("    [OK] Limiter registrado no app")
    else:
        print("    [AVISO] Limiter NAO registrado no app.state")
except Exception as e:
    print(f"    [ERRO] {type(e).__name__}: {e}")

print("\n[5] Verificando decorators...")

from djen.api.ratelimit import limit_auth_login, limit_busca, limit_captacao
print(f"    [OK] limit_auth_login: {limit_auth_login}")
print(f"    [OK] limit_busca: {limit_busca}")
print(f"    [OK] limit_captacao: {limit_captacao}")

print("\n[6] Simulando rate limit (memoria)...")

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    
    test_limiter = Limiter(key_func=get_remote_address, default_limits=["3/minute"])
    
    class MockRequest:
        def __init__(self):
            self.headers = {}
            self.client = type('Client', (), {'host': '127.0.0.1'})()
    
    req = MockRequest()
    
    for i in range(4):
        key = test_limiter._check_request_limit(req)
        print(f"    Requisicao {i+1}: {'BLOQUEADO' if key is None else 'OK'}")
    
    print("    [OK] Simulacao completada")
    
except Exception as e:
    print(f"    [ERRO] {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("TESTES CONCLUIDOS!")
print("=" * 60)
print("\nPara testar com API real:")
print("  1. Inicie: uvicorn djen.api.app:app --host 0.0.0.0 --port 8000")
print("  2. Execute: for i in {1..35}; do curl -s http://localhost:8000/api/auth/login -X POST -d 'username=admin&password=admin' > /dev/null && echo OK || echo BLOQUEADO; done")
print("")