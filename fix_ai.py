import sqlite3
c = sqlite3.connect("/app/data/captacao_blindada.db")
c.execute("UPDATE ai_config SET provider='gemini', model_name='gemini-2.5-flash' WHERE function_key='classificacao'")
c.execute("UPDATE ai_config SET provider='gemini', model_name='gemini-3-flash-preview' WHERE function_key='previsao'")
c.execute("UPDATE ai_config SET provider='gemini', model_name='gemini-2.5-flash' WHERE function_key='resumo'")
c.execute("UPDATE ai_config SET provider='gemini', model_name='gemini-3-flash-preview' WHERE function_key='jurisprudencia'")
c.commit()
print("AI configs updated to Gemini")
c.close()
