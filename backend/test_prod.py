#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de seguranca em modoProducao
Executar: python test_prod.py
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ["IS_PRODUCTION"] = "true"
os.environ.pop("JWT_SECRET_KEY", None)

print("=" * 50)
print("TESTE MODO PRODUCAO (DEVE FALHAR)")
print("=" * 50)

print("\n[1] Variaveis Configuradas:")
print("    IS_PRODUCTION: true")
print("    JWT_SECRET_KEY: (nao configurado)")

print("\n[2] Tentando Importar Modulo Auth:")
try:
    from djen.api import auth
    print("    [ERRO] Modulo deveria ter falhado!")
    sys.exit(1)
except RuntimeError as e:
    expected_msg = "JWT_SECRET_KEY is required in production"
    if expected_msg in str(e):
        print("    [OK] ERRO ESPERADO DETECTADO!")
        print("    Mensagem: " + str(e)[:80])
        print("\n" + "=" * 50)
        print("SISTEMA BLOQUEOU COMO ESPERADO!")
        print("=" * 50)
    else:
        print("    [AVISO] Erro diferente: " + str(e)[:80])
except Exception as e:
    print("    [ERRO]: " + type(e).__name__ + ": " + str(e)[:80])