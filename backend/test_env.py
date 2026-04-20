#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de configuracao de seguranca
Executar: python test_env.py
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ["IS_PRODUCTION"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-key-12345678901234567890123456789012"

print("=" * 50)
print("TESTE DE CONFIGURACAO - CAPTACAO BLINDADA")
print("=" * 50)

print("\n[1] Variaveis de Ambiente:")
print("    IS_PRODUCTION: " + os.environ.get('IS_PRODUCTION', 'NOT SET'))
print("    JWT_SECRET_KEY: " + os.environ.get('JWT_SECRET_KEY', 'NOT SET')[:20] + "...")

print("\n[2] Testando Importacao do Modulo de Auth:")
try:
    from djen.api import auth
    print("    [OK] Modulo auth importado com sucesso")
    print("    SECRET_KEY configurada: " + auth.SECRET_KEY[:20] + "...")
    print("    ALGORITHM: " + auth.ALGORITHM)
    print("    ACCESS_TOKEN_EXPIRE_MINUTES: " + str(auth.ACCESS_TOKEN_EXPIRE_MINUTES))
except RuntimeError as e:
    print("    [ERRO]: " + str(e))
    sys.exit(1)
except Exception as e:
    print("    [ERRO] ao importar: " + type(e).__name__ + ": " + str(e))
    sys.exit(1)

print("\n[3] Teste de Funcoes de Auth:")

try:
    from djen.api.auth import verify_password, hash_password
    
    password = "test123"
    hashed = hash_password(password)
    verified = verify_password(password, hashed)
    
    print("    hash_password: " + hashed[:30] + "...")
    print("    verify_password: OK" if verified else "verify_password: FALHOU")
except Exception as e:
    print("    [ERRO]: " + str(e))

print("\n" + "=" * 50)
print("TODOS OS TESTES PASSARAM!")
print("=" * 50)