import sqlite3, json

conn = sqlite3.connect("/app/data/captacao_blindada.db")
c = conn.cursor()

# List all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in c.fetchall()]
print("TABLES:", tables)
print("")

# 1. Captacoes stored counters
print("=== CAPTACOES stored counters ===")
c.execute("SELECT id, nome, total_resultados, total_novos, total_execucoes FROM captacoes ORDER BY id")
for r in c.fetchall():
    print("  ID=%s nome=%s total_resultados=%s total_novos=%s total_execucoes=%s" % (r[0], r[1], r[2], r[3], r[4]))

# 2. Real count of publicacoes per captacao
print("")
print("=== PUBLICACOES real count per captacao ===")
c.execute("SELECT captacao_id, COUNT(*) as total FROM publicacoes WHERE captacao_id IS NOT NULL GROUP BY captacao_id ORDER BY captacao_id")
for r in c.fetchall():
    print("  captacao_id=%s real_count=%s" % (r[0], r[1]))

# 3. Total publicacoes without captacao_id
c.execute("SELECT COUNT(*) FROM publicacoes WHERE captacao_id IS NULL")
print("  publicacoes sem captacao_id: %s" % c.fetchone()[0])

# 4. Execucoes per captacao - sum of total_resultados and novos_resultados
print("")
print("=== EXECUCOES sum per captacao ===")
c.execute("SELECT captacao_id, COUNT(*) as num_exec, SUM(total_resultados) as sum_total, SUM(novos_resultados) as sum_novos FROM execucoes_captacao GROUP BY captacao_id ORDER BY captacao_id")
for r in c.fetchall():
    print("  captacao_id=%s num_exec=%s sum_total_resultados=%s sum_novos_resultados=%s" % (r[0], r[1], r[2], r[3]))

# 5. Last 15 execucoes detail
print("")
print("=== LAST 15 EXECUCOES ===")
c.execute("SELECT id, captacao_id, fonte, status, total_resultados, novos_resultados, inicio, fim FROM execucoes_captacao ORDER BY id DESC LIMIT 15")
for r in c.fetchall():
    print("  exec_id=%s cap_id=%s fonte=%s status=%s total=%s novos=%s inicio=%s fim=%s" % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]))

# 6. Compare stored vs real
print("")
print("=== COMPARISON: stored vs real ===")
c.execute("SELECT id, nome, total_resultados, total_novos, total_execucoes FROM captacoes ORDER BY id")
caps = c.fetchall()
for cap in caps:
    cap_id, nome, stored_total, stored_novos, stored_exec = cap
    c.execute("SELECT COUNT(*) FROM publicacoes WHERE captacao_id=?", (cap_id,))
    real_pub = c.fetchone()[0]
    c.execute("SELECT COUNT(*), COALESCE(SUM(total_resultados),0), COALESCE(SUM(novos_resultados),0) FROM execucoes_captacao WHERE captacao_id=?", (cap_id,))
    real_exec, sum_total, sum_novos = c.fetchone()
    match_total = "OK" if stored_total == sum_total else "MISMATCH"
    match_novos = "OK" if stored_novos == sum_novos else "MISMATCH"
    match_exec = "OK" if stored_exec == real_exec else "MISMATCH"
    match_pub = "OK" if stored_total == real_pub or stored_novos == real_pub else "CHECK"
    print("  ID=%s %s" % (cap_id, nome))
    print("    stored total_resultados=%s vs exec_sum=%s [%s]" % (stored_total, sum_total, match_total))
    print("    stored total_novos=%s vs exec_sum_novos=%s [%s]" % (stored_novos, sum_novos, match_novos))
    print("    stored total_execucoes=%s vs real_exec_count=%s [%s]" % (stored_exec, real_exec, match_exec))
    print("    real publicacoes count=%s [%s]" % (real_pub, match_pub))

conn.close()
