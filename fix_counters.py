"""Script para corrigir contadores inflados nas captacoes.
Recalcula total_resultados, total_novos e total_execucoes baseado nos dados reais."""
import sqlite3

db_path = "/app/data/captacao_blindada.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=== ANTES da correcao ===")
c.execute("SELECT id, nome, total_resultados, total_novos, total_execucoes FROM captacoes ORDER BY id")
for r in c.fetchall():
    print("  ID=%s %s: resultados=%s novos=%s execucoes=%s" % (r[0], r[1], r[2], r[3], r[4]))

# Corrigir cada captacao
c.execute("SELECT id FROM captacoes ORDER BY id")
cap_ids = [r[0] for r in c.fetchall()]

for cap_id in cap_ids:
    # Contar publicacoes reais vinculadas a esta captacao
    c.execute("SELECT COUNT(*) FROM publicacoes WHERE captacao_id=?", (cap_id,))
    real_pub = c.fetchone()[0]

    # Contar execucoes reais
    c.execute("SELECT COUNT(*) FROM execucoes_captacao WHERE captacao_id=?", (cap_id,))
    real_exec = c.fetchone()[0]

    # Atualizar contadores para valores reais
    # total_resultados = total de publicacoes reais (nao o tamanho da resposta da API)
    # total_novos = total de publicacoes reais (cada uma foi "nova" quando inserida)
    c.execute("""
        UPDATE captacoes SET
            total_resultados=?,
            total_novos=?,
            total_execucoes=?,
            atualizado_em=datetime('now', 'localtime')
        WHERE id=?
    """, (real_pub, real_pub, real_exec, cap_id))

    print("  Corrigido ID=%s: resultados=%s novos=%s execucoes=%s" % (cap_id, real_pub, real_pub, real_exec))

# Tambem corrigir os registros de execucoes_captacao
# Zerar os contadores inflados nas execucoes passadas (opcional, mas mantem consistencia)
# Nao vamos alterar execucoes passadas pois sao historico

conn.commit()

print("")
print("=== DEPOIS da correcao ===")
c.execute("SELECT id, nome, total_resultados, total_novos, total_execucoes FROM captacoes ORDER BY id")
for r in c.fetchall():
    print("  ID=%s %s: resultados=%s novos=%s execucoes=%s" % (r[0], r[1], r[2], r[3], r[4]))

conn.close()
print("")
print("Correcao concluida com sucesso!")
