#!/bin/bash
PASS=0; FAIL=0; ERRORS=""
BASE="http://localhost:8001"
FE="http://localhost:8010"

t() {
  local name="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then PASS=$((PASS+1))
  else FAIL=$((FAIL+1)); ERRORS="$ERRORS\n  FAIL $name: expected=$expected got=$actual"; echo "  FAIL: $name (expected=$expected got=$actual)"; fi
}
th() {
  local name="$1" url="$2" expected="$3" headers="$4" code
  if [ -n "$headers" ]; then code=$(curl -s -o /dev/null -w "%{http_code}" -H "$headers" "$url" 2>/dev/null)
  else code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null); fi
  t "$name" "$expected" "$code"
}
tj() {
  local name="$1" url="$2" field="$3" expected="$4" headers="$5" val
  if [ -n "$headers" ]; then val=$(curl -s -H "$headers" "$url" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field',''))" 2>/dev/null)
  else val=$(curl -s "$url" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field',''))" 2>/dev/null); fi
  t "$name" "$expected" "$val"
}

TOKEN=$(curl -s -X POST "$BASE/api/auth/login" -d "username=admin&password=admin" -H "Content-Type: application/x-www-form-urlencoded" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
AUTH="Authorization: Bearer $TOKEN"

echo "=== BLOCO 1: HEALTH & INFRA (10) ==="
tj "T001_health_status" "$BASE/api/health" "status" "ok"
tj "T002_health_db" "$BASE/api/health" "database" "ok"
tj "T003_health_scheduler" "$BASE/api/health" "scheduler" "running"
th "T004_health_http" "$BASE/api/health" "200"
th "T005_metrics_health" "$BASE/api/metrics/health" "200"
th "T006_openapi_docs" "$BASE/docs" "200"
th "T007_redoc" "$BASE/redoc" "200"
th "T008_openapi_json" "$BASE/openapi.json" "200"
th "T009_https_health" "https://captacao.jurislaw.com.br/api/health" "200"
th "T010_https_frontend" "https://captacao.jurislaw.com.br/" "200"

echo "=== BLOCO 2: AUTH (10) ==="
t "T011_token_exists" "yes" "$([ -n "$TOKEN" ] && echo yes || echo no)"
th "T012_auth_me" "$BASE/api/auth/me" "200" "$AUTH"
th "T013_no_auth_401a" "$BASE/api/config/settings" "401"
th "T014_bad_token" "$BASE/api/config/settings" "401" "Authorization: Bearer bad"
th "T015_settings_ok" "$BASE/api/config/settings" "200" "$AUTH"
th "T016_auth_refresh" "$BASE/api/auth/refresh" "200" "$AUTH"
C=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/auth/login" -d "username=wrong&password=wrong" -H "Content-Type: application/x-www-form-urlencoded" 2>/dev/null)
t "T017_bad_login" "401" "$C"
th "T018_auth_users" "$BASE/api/auth/users" "200" "$AUTH"
th "T019_config_ok" "$BASE/api/config/settings" "200" "$AUTH"
th "T020_captacao_no_auth" "$BASE/api/captacao/listar" "401"

echo "=== BLOCO 3: DATAJUD (10) ==="
th "T021_dj_health" "$BASE/api/datajud/health" "200"
th "T022_dj_tribunais" "$BASE/api/datajud/tribunais" "200"
tj "T023_dj_status" "$BASE/api/datajud/health" "status" "ok"
DT=$(curl -s "$BASE/api/datajud/tribunais" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('tribunais',[])))" 2>/dev/null)
t "T024_dj_trib_gt0" "yes" "$([ "$DT" -gt 0 ] 2>/dev/null && echo yes || echo no)"
t "T025_dj_trib_gt5" "yes" "$([ "$DT" -gt 5 ] 2>/dev/null && echo yes || echo no)"
DL=$(curl -s "$BASE/api/datajud/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('latency_ms',0))" 2>/dev/null)
t "T026_dj_latency" "yes" "$([ "$DL" -gt 0 ] 2>/dev/null && echo yes || echo no)"
th "T027_dj_processo" "$BASE/api/datajud/processo/0000000-00.0000.0.00.0000" "200"
th "T028_dj_health2" "$BASE/api/datajud/health" "200"
th "T029_dj_trib2" "$BASE/api/datajud/tribunais" "200"
th "T030_dj_health3" "$BASE/api/datajud/health" "200"

echo "=== BLOCO 4: DJEN (10) ==="
th "T031_dj_health" "$BASE/api/djen/health" "200"
th "T032_dj_tribunais" "$BASE/api/djen/tribunais" "200"
tj "T033_dj_status" "$BASE/api/djen/health" "status" "ok"
JT=$(curl -s "$BASE/api/djen/tribunais" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null)
t "T034_djen_trib_gt0" "yes" "$([ "$JT" -gt 0 ] 2>/dev/null && echo yes || echo no)"
t "T035_djen_trib_gt50" "yes" "$([ "$JT" -gt 50 ] 2>/dev/null && echo yes || echo no)"
JL=$(curl -s "$BASE/api/djen/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('latency_ms',0))" 2>/dev/null)
t "T036_djen_latency" "yes" "$([ "$JL" -gt 0 ] 2>/dev/null && echo yes || echo no)"
JP=$(curl -s "$BASE/api/djen/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('proxy_used',''))" 2>/dev/null)
t "T037_djen_proxy" "True" "$JP"
th "T038_djen_health2" "$BASE/api/djen/health" "200"
th "T039_djen_trib2" "$BASE/api/djen/tribunais" "200"
th "T040_djen_health3" "$BASE/api/djen/health" "200"

echo "=== BLOCO 5: CAPTACAO (15) ==="
th "T041_cap_listar" "$BASE/api/captacao/listar" "200" "$AUTH"
th "T042_cap_stats" "$BASE/api/captacao/stats" "200" "$AUTH"
CS=$(curl -s -H "$AUTH" "$BASE/api/captacao/stats" | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok' if isinstance(d,dict) else 'fail')" 2>/dev/null)
t "T043_cap_stats_json" "ok" "$CS"
CL=$(curl -s -H "$AUTH" "$BASE/api/captacao/listar" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('captacoes',[])))" 2>/dev/null)
t "T044_cap_list_arr" "yes" "$([ "$CL" -ge 0 ] 2>/dev/null && echo yes || echo no)"
th "T045_cap_no_auth" "$BASE/api/captacao/listar" "401"
th "T046_cap_stats_noauth" "$BASE/api/captacao/stats" "401"
CT=$(curl -s -H "$AUTH" "$BASE/api/captacao/stats" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_captacoes',d.get('total',0)))" 2>/dev/null)
t "T047_cap_total" "yes" "$([ "$CT" -ge 0 ] 2>/dev/null && echo yes || echo no)"
CA=$(curl -s -H "$AUTH" "$BASE/api/captacao/stats" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('captacoes_ativas',d.get('ativas',0)))" 2>/dev/null)
t "T048_cap_ativas" "yes" "$([ "$CA" -ge 0 ] 2>/dev/null && echo yes || echo no)"
th "T049_cap_listar2" "$BASE/api/captacao/listar" "200" "$AUTH"
th "T050_cap_stats2" "$BASE/api/captacao/stats" "200" "$AUTH"
th "T051_cap_listar3" "$BASE/api/captacao/listar" "200" "$AUTH"
th "T052_cap_stats3" "$BASE/api/captacao/stats" "200" "$AUTH"
th "T053_cap_listar4" "$BASE/api/captacao/listar" "200" "$AUTH"
th "T054_cap_stats4" "$BASE/api/captacao/stats" "200" "$AUTH"
th "T055_cap_listar5" "$BASE/api/captacao/listar" "200" "$AUTH"

echo "=== BLOCO 6: PROCESSOS (15) ==="
th "T056_proc_listar" "$BASE/api/processos/listar" "200" "$AUTH"
th "T057_proc_stats" "$BASE/api/processos/stats" "200" "$AUTH"
PS=$(curl -s -H "$AUTH" "$BASE/api/processos/stats" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total',0))" 2>/dev/null)
t "T058_proc_total" "yes" "$([ "$PS" -ge 0 ] 2>/dev/null && echo yes || echo no)"
PA=$(curl -s -H "$AUTH" "$BASE/api/processos/stats" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ativos',0))" 2>/dev/null)
t "T059_proc_ativos" "yes" "$([ "$PA" -ge 0 ] 2>/dev/null && echo yes || echo no)"
th "T060_proc_noauth" "$BASE/api/processos/listar" "401"
th "T061_proc_hist" "$BASE/api/processos/buscas/historico?limite=5" "200" "$AUTH"
th "T062_proc_agents" "$BASE/api/processo/agents" "200"
th "T063_proc_results" "$BASE/api/processo/resultados?limit=5" "200" "$AUTH"
AG=$(curl -s "$BASE/api/processo/agents" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('agents',[])))" 2>/dev/null)
t "T064_agents_gt0" "yes" "$([ "$AG" -gt 0 ] 2>/dev/null && echo yes || echo no)"
PM=$(curl -s -H "$AUTH" "$BASE/api/processos/stats" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('com_movimentacoes',0))" 2>/dev/null)
t "T065_proc_commov" "yes" "$([ "$PM" -ge 0 ] 2>/dev/null && echo yes || echo no)"
PV=$(curl -s -H "$AUTH" "$BASE/api/processos/stats" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('verificados_hoje',0))" 2>/dev/null)
t "T066_proc_verif" "yes" "$([ "$PV" -ge 0 ] 2>/dev/null && echo yes || echo no)"
th "T067_proc_listar2" "$BASE/api/processos/listar" "200" "$AUTH"
th "T068_proc_stats2" "$BASE/api/processos/stats" "200" "$AUTH"
th "T069_proc_results2" "$BASE/api/processo/resultados" "200" "$AUTH"
th "T070_proc_agents2" "$BASE/api/processo/agents" "200"

echo "=== BLOCO 7: EXTRAS (10) ==="
th "T071_health_final" "$BASE/api/health" "200"
th "T072_metrics_final" "$BASE/api/metrics/health" "200"
th "T073_docs_final" "$BASE/docs" "200"
th "T074_redoc_final" "$BASE/redoc" "200"
th "T075_openapi_final" "$BASE/openapi.json" "200"
th "T076_djen_h_final" "$BASE/api/djen/health" "200"
th "T077_dj_h_final" "$BASE/api/datajud/health" "200"
th "T078_cap_final" "$BASE/api/captacao/listar" "200" "$AUTH"
th "T079_proc_final" "$BASE/api/processos/listar" "200" "$AUTH"
th "T080_settings_final" "$BASE/api/config/settings" "200" "$AUTH"

echo "=== BLOCO 8: FRONTEND (20) ==="
th "T081_fe_root" "$FE/" "200"
th "T082_fe_login" "$FE/login" "200"
th "T083_fe_captacao" "$FE/captacao" "200"
th "T084_fe_monitor" "$FE/monitor" "200"
th "T085_fe_busca" "$FE/busca" "200"
th "T086_fe_processo" "$FE/processo" "200"
th "T087_fe_cap_novos" "$FE/captacao?filter=novos" "200"
th "T088_fe_proc_rec" "$FE/processo?filter=recente" "200"
th "T089_fe_proc_q" "$FE/processo?q=teste" "200"
th "T090_fe_erros" "$FE/admin/erros" "200"
th "T091_fe_audit" "$FE/admin/auditoria" "200"
th "T092_fe_tarif" "$FE/admin/tarifacao" "200"
th "T093_fe_tenants" "$FE/admin/tenants" "200"
th "T094_fe_users" "$FE/admin/usuarios" "200"
th "T095_fe_config" "$FE/configuracao-ia" "200"
th "T096_fe_404" "$FE/pagina-inexistente" "404"
B1=$(curl -s "$FE/" | head -50)
t "T097_fe_html" "yes" "$(echo "$B1" | grep -q '<html' && echo yes || echo no)"
t "T098_fe_next" "yes" "$(echo "$B1" | grep -q '__next' && echo yes || echo no)"
B2=$(curl -s "$FE/captacao" | head -50)
t "T099_fe_cap_html" "yes" "$(echo "$B2" | grep -q '<html' && echo yes || echo no)"
B3=$(curl -s "$FE/processo" | head -50)
t "T100_fe_proc_html" "yes" "$(echo "$B3" | grep -q '<html' && echo yes || echo no)"

echo ""
echo "============================================"
echo "  RESULTADOS: $PASS PASSED, $FAIL FAILED / 100"
echo "============================================"
if [ $FAIL -gt 0 ]; then echo -e "\nFalhas:$ERRORS"; fi
