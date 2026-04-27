# Guia do Usuario — Captacao Peticao Blindada

> Versao: 3.0.0 | Atualizado: 2026-04-26 | Para: Usuarios finais (advogados, equipe juridica) | 231 implementações

---

## 1. Introducao

O **Captacao Peticao Blindada** e uma plataforma de automacao juridica que permite:

- **Analisar processos** judiciais com inteligencia artificial (14 agentes especializados)
- **Buscar publicacoes** em multiplas fontes (DataJud, DJEN, TJSP DJe, DEJT, JusBrasil)
- **Monitorar** processos, OABs, advogados e partes 24/7
- **Captar automaticamente** publicacoes com regras personalizadas
- Receber **notificacoes** por WhatsApp ou e-mail quando novas publicacoes sao encontradas

Acesso: **https://captacao.jurislaw.com.br**

---

## 2. Login

### Como acessar

1. Abra o navegador e acesse `https://captacao.jurislaw.com.br`
2. O sistema redireciona automaticamente para a tela de login
3. Preencha os campos:
   - **Usuario**: seu nome de usuario
   - **Senha**: sua senha
4. Clique em **Entrar**

### Informacoes importantes

- A sessao expira apos **60 minutos** de inatividade — faca login novamente se necessario
- Se as credenciais estiverem incorretas, uma mensagem de erro aparecera abaixo do formulario
- O sistema possui tema claro e escuro — voce pode alternar apos o login

### Problemas no login?

| Problema | Solucao |
|----------|---------|
| "Credenciais invalidas" | Verifique usuario e senha. Letras maiusculas/minusculas importam |
| Tela nao carrega | Verifique sua conexao com a internet |
| Erro 500 / 502 | O servidor pode estar reiniciando. Aguarde 1 minuto e tente novamente |

---

## 3. Painel (Dashboard)

Apos o login, voce e direcionado ao **Painel**, que oferece uma visao geral do sistema.

### O que voce encontra no Painel

1. **Barra de busca rapida** — Digite um numero de processo CNJ e clique "Buscar" para ir direto a analise
2. **Cards de estatisticas** — Mostram:
   - Total de processos analisados
   - Itens monitorados ativos
   - Publicacoes encontradas
   - Status geral do sistema
3. **Processos recentes** — Lista dos ultimos 6 processos analisados com seus detalhes

### Links inteligentes

Os cards do Dashboard agora levam diretamente para os resultados relevantes:
- **"Novos resultados de captação"** → abre a aba Captação já filtrada nos novos resultados
- **"Movimentações recentes"** → abre Processos já filtrado por movimentações recentes

### Navegacao

O menu lateral (Sidebar) esta sempre disponivel com os seguintes itens:

| Item | Funcao |
|------|--------|
| **Painel** | Visao geral do sistema (pagina inicial) |
| **Processos** | Analise detalhada de processos com IA |
| **Busca Unificada** | Busca em todas as fontes judiciais |
| **Monitor** | Monitoramento automatico de processos e OABs |
| **Captacao** | Captacao automatizada de publicacoes |

Voce pode **colapsar o menu** clicando no icone de seta no canto inferior para ganhar mais espaco de tela.

### Tema claro/escuro

Clique no icone de sol/lua no rodape do menu lateral para alternar entre tema claro e escuro.

---

## 4. Analise de Processos

**Caminho:** Menu lateral → **Processos** (ou `/processo`)

### O que e?

A analise de processos usa **14 agentes de inteligencia artificial** para extrair, enriquecer e avaliar informacoes de um processo judicial. O sistema busca dados em multiplas fontes e gera:

- Resumo automatico do processo
- Timeline de movimentacoes
- Analise de risco com score (0-100)
- Dados das partes, advogados, valores envolvidos

### Como analisar um processo

1. No campo de busca, digite o **numero do processo** no formato CNJ (ex: `0001234-56.2023.8.26.0100`)
2. Opcionalmente, selecione o **tribunal** para direcionar a busca
3. Clique em **Analisar**
4. Aguarde o processamento (pode levar de 10 a 60 segundos dependendo da complexidade)

### Entendendo os resultados

Apos a analise, o sistema exibe abas com diferentes visoes:

#### Aba "Resumo"
- Resumo em linguagem natural do processo gerado pela IA
- Informacoes basicas: numero, classe, tribunal, orgao julgador, data de distribuicao

#### Aba "Timeline"
- Linha do tempo visual com todos os movimentos processuais
- Cada evento mostra data, tipo e descricao
- Eventos sao ordenados cronologicamente

#### Aba "Riscos"
- **Score de risco** de 0 a 100 representado por um gauge visual:
  - 0-30: Risco **baixo** (verde)
  - 31-60: Risco **medio** (amarelo)
  - 61-100: Risco **alto** (vermelho)
- Lista de fatores de risco identificados pela IA
- Recomendacoes baseadas na analise

#### Aba "Detalhes"
- Dados completos do processo: partes, advogados, valores
- Dados brutos retornados pelas fontes

### Processos analisados anteriormente

Abaixo do formulario de analise, o sistema exibe uma lista dos **ultimos processos analisados**. Clique em qualquer card para ver os detalhes completos.

### Processos Monitorados (novidade v2.1)

Além da análise com IA, a aba Processos agora inclui o modo **Processos Monitorados**:

#### O que é?
O sistema verifica automaticamente (a cada 6 horas) se há novas movimentações nos processos que você está acompanhando, consultando tanto o DataJud quanto o DJEN.

#### Timeline Unificada
- Ao clicar em um processo monitorado, uma **timeline unificada** mostra todas as movimentações
- Itens do **DataJud** aparecem em azul, itens do **DJEN** em âmbar
- Itens sem data mostram um indicador visual "Data indisponível"
- Paginação: carrega 30 eventos por vez

#### Exportação
- Botões **CSV** e **JSON** permitem exportar a lista de processos monitorados
- O CSV inclui: processo, tribunal, classe, movimentações, última movimentação, status

#### Validação CNJ
- Ao adicionar um processo, o sistema valida o formato CNJ em tempo real
- Formato esperado: `0000000-00.0000.0.00.0000` (20 dígitos)

#### Filtros
- Filtrar por tribunal, status, movimentações (com/sem/recentes/novas)
- 10 opções de ordenação
- Link direto do Dashboard: "Movimentações recentes" já abre filtrado

---

## 5. Busca Unificada

**Caminho:** Menu lateral → **Busca Unificada** (ou `/busca`)

### O que e?

A Busca Unificada consulta **multiplas fontes judiciais simultaneamente** e retorna publicacoes encontradas em todas elas.

### Fontes disponiveis

| Fonte | Descricao |
|-------|-----------|
| **DataJud** | API oficial do CNJ com dados de 60+ tribunais |
| **DJEN** | Diario da Justica Eletronico Nacional |
| **Unificada** | Busca em todas as fontes ao mesmo tempo (padrao) |

### Como buscar

1. Digite o **termo de busca** no campo principal (pode ser numero de processo, nome de parte, OAB, etc.)
2. Selecione a **fonte** desejada (Unificada, DataJud ou DJEN)
3. Opcionalmente, clique em **Filtros** para refinar:
   - **Tribunal** — filtrar por sigla do tribunal (ex: TJSP, TJRJ)
   - **Data inicio** — publicacoes a partir desta data
   - **Data fim** — publicacoes ate esta data
4. Clique em **Buscar**

### Entendendo os resultados

Cada resultado exibe:

- **Fonte** e **Tribunal** — de onde veio a publicacao
- **Data** — data da publicacao
- **Numero do processo** — quando disponivel
- **Classe processual** — tipo do processo (ex: Acao Civil Publica)
- **Orgao julgador** — vara ou turma responsavel
- **Assuntos** — temas do processo
- **Conteudo** — texto completo ou parcial da publicacao
- **Movimentacoes** — quando disponiveis, lista de movimentos

Clique em qualquer resultado para expandir e ver todos os detalhes.

### Novidades da versão 2.1

#### Seleção de fontes
- Os checkboxes **DataJud** e **DJEN** agora são respeitados na busca
- Desmarque uma fonte para buscar apenas na outra
- Se ambas estiverem marcadas, a busca unificada é usada

#### Resultados clicáveis
- O número do processo em cada resultado é um **link clicável**
- Clique para ir direto à análise do processo

#### Contagem por fonte
- Os resultados mostram badges com a contagem por fonte (ex: "DataJud: 5" / "DJEN: 3")

#### Salvar como captação inteligente
- Ao salvar uma pesquisa como captação, o sistema **detecta automaticamente** o tipo:
  - Formato CNJ → tipo "processo"
  - Formato OAB (123456/SP) → tipo "oab"
  - Texto livre → tipo "nome_parte"

---

## 6. Monitor

**Caminho:** Menu lateral → **Monitor** (ou `/monitor`)

### O que e?

O Monitor permite acompanhar automaticamente processos, OABs, advogados ou partes. O sistema faz buscas periodicas (configuradas pelo scheduler) e armazena novas publicacoes encontradas.

### Como criar um monitoramento

1. Clique em **Adicionar Monitor** (botao com icone +)
2. Preencha o formulario:
   - **Tipo**: Processo, OAB, Nome, Parte, ou Advogado
   - **Valor**: O que monitorar (ex: numero do processo, "12345/SP" para OAB)
   - **Tribunal** (opcional): Filtrar por tribunal especifico
   - **Nome amigavel** (opcional): Um nome para facilitar a identificacao (ex: "Caso Silva vs. Empresa X")
3. Clique em **Adicionar**

### Tipos de monitoramento

| Tipo | O que monitorar | Exemplo de valor |
|------|----------------|------------------|
| Processo | Numero CNJ do processo | 0001234-56.2023.8.26.0100 |
| OAB | Numero de registro OAB | 123456/SP |
| Nome | Nome de pessoa/empresa | Maria Silva Santos |
| Parte | Nome de parte processual | Banco do Brasil S.A. |
| Advogado | Nome do advogado | Dr. Joao da Silva |

### Gerenciando monitores

- **Ativar/Desativar**: Clique no toggle ao lado de cada monitor para pausar/retomar
- **Remover**: Clique no icone de lixeira para excluir permanentemente
- **Ver publicacoes**: Clique em "Publicacoes Recentes" para ver todas as publicacoes encontradas

### Publicacoes encontradas

Clique em **Publicacoes Recentes** para ver as publicacoes que o sistema encontrou:

- A lista mostra as 50 mais recentes por padrao
- Clique em **Carregar mais** para ver publicacoes anteriores
- Cada publicacao mostra: fonte, tribunal, data, classe processual, conteudo

### Cards de estatisticas (topo)

O Monitor exibe cards com resumo:
- Total de monitorados
- Monitorados ativos
- Total de publicacoes encontradas
- Status de saude do sistema

### Novidades da versão 2.1

#### Processo clicável
- O número do processo em cada publicação agora é um **link clicável**
- Clique para ir direto à página de análise do processo

#### Botão "Ver Processo Completo"
- Ao expandir uma publicação, um botão azul **"Ver Processo Completo"** aparece no final
- Clique para navegar à análise completa do processo

#### Paginação
- Publicações são carregadas em blocos de 30
- Clique em **"Carregar mais 30"** para ver mais publicações
- Evita lentidão quando há centenas de publicações

---

## 7. Captacao Automatizada

**Caminho:** Menu lateral → **Captacao** (ou `/captacao`)

### O que e?

A Captacao Automatizada permite criar **regras de busca recorrentes** que o sistema executa automaticamente em intervalos definidos. E ideal para:

- Varrer publicacoes de um tribunal inteiro periodicamente
- Monitorar termos especificos sem intervencao manual
- Captar leads juridicos automaticamente

### Cards de estatisticas (topo)

| Card | Significado |
|------|-------------|
| Total Captacoes | Numero total de regras criadas |
| Ativas | Regras em execucao ativa |
| Resultados | Total de publicacoes captadas |
| Execucoes | Total de vezes que as regras foram executadas |

### Como criar uma regra de captacao

1. Clique em **Nova Captacao** (botao com icone +)
2. Preencha o formulario:

#### Campos obrigatorios

| Campo | Descricao |
|-------|-----------|
| **Nome** | Nome identificador da captacao (ex: "Varredura TJSP Criminal") |
| **Descricao** | Descricao detalhada do objetivo |
| **Fonte** | DataJud ou DJEN |
| **Tipo de busca** | Processo, OAB, Nome da Parte, etc. |
| **Termos** | Termos de busca separados por virgula (ex: "homicidio, roubo, furto") |

#### Campos de agendamento

| Campo | Descricao | Padrao |
|-------|-----------|--------|
| **Intervalo** | Frequencia de execucao (15min a 24h) | 2 horas |
| **Horario inicio** | Hora permitida para iniciar buscas | 06:00 |
| **Horario fim** | Hora limite para buscas | 22:00 |
| **Dias da semana** | Dias em que a captacao roda | Seg a Sex |
| **Prioridade** | Urgente, Normal ou Baixa | Normal |

#### Campos de filtro (opcionais)

| Campo | Descricao |
|-------|-----------|
| **Tribunal** | Filtrar por tribunal especifico (ex: TJSP) |
| **Max. resultados** | Limite de resultados por execucao (padrao: 100) |
| **Filtro classe** | Classe processual especifica |
| **Filtro orgao** | Orgao julgador especifico |

#### Notificacoes (opcionais)

| Campo | Descricao |
|-------|-----------|
| **WhatsApp** | Ativar notificacao via WhatsApp + numero destino |
| **E-mail** | Ativar notificacao via e-mail + endereco destino |

3. Clique em **Criar Captacao**

### Gerenciando captacoes existentes

Cada captacao na lista exibe:

- **Nome** e **descricao**
- **Status**: Ativa (verde), Pausada (amarelo), Concluida (cinza), Erro (vermelho)
- **Fonte** e **tipo de busca**
- **Intervalo** de execucao
- **Proxima execucao** agendada
- **Contadores**: total de execucoes e resultados encontrados

#### Acoes disponiveis

| Botao | Acao |
|-------|------|
| **Play** | Executar a captacao imediatamente (fora do agendamento) |
| **Pause/Resume** | Pausar ou retomar a captacao |
| **Lixeira** | Excluir permanentemente a captacao e todo seu historico |

### Detalhes expandidos

Clique em uma captacao para expandir e ver dois paineis:

#### Aba "Historico"
- Lista de todas as execucoes passadas
- Cada execucao mostra: data, status (sucesso/erro), duracao, resultados encontrados
- Mensagens de erro quando aplicavel

#### Aba "Resultados"
- Publicacoes encontradas por esta captacao
- Cada resultado mostra: fonte, tribunal, data, conteudo

### Novidades da versão 2.1

#### Badges de fonte
Cada resultado agora mostra claramente de qual fonte veio:
- **Azul** = DataJud (metadados processuais)
- **Âmbar** = DJEN (texto de publicações)

#### Resultados clicáveis
- Clique no **número do processo** em qualquer resultado para ir direto à página de análise
- Clique em um resultado para **expandir** e ver detalhes completos (classe, órgão, advogados, partes, OABs)
- Botão **"Ver Processo Completo"** no resultado expandido

#### Filtro por fonte
- Botões **DataJud / DJEN / Todas** acima dos resultados
- Cada botão mostra a contagem de resultados daquela fonte

#### Indicador de novos
- Badge vermelho pulsante mostra quantos resultados você ainda não viu
- Ao clicar em uma captação, os resultados são marcados como "vistos"

#### Paginação
- Resultados são carregados em blocos de 20
- Clique em **"Carregar mais 20"** para ver mais resultados

---

## 8. Funcionalidades Gerais

### Logout

Clique em **Sair** no rodape do menu lateral para desconectar do sistema.

### Responsividade

O sistema funciona em desktops e tablets. Em telas menores, o menu lateral pode ser colapsado para ganhar espaco.

### Tratamento de erros

Mensagens de erro aparecem em paineis vermelhos no topo da pagina ou proximo ao componente afetado. Mensagens de sucesso aparecem em paineis verdes. Ambas desaparecem automaticamente apos alguns segundos ou podem ser fechadas manualmente.

### Dados em tempo real

O sistema atualiza os dados automaticamente em alguns cenarios:
- O **Dashboard** carrega dados frescos sempre que voce acessa
- O **Monitor** pode ser atualizado manualmente clicando nos botoes de refresh
- A **Captacao** exibe a proxima execucao agendada

---

## 9. Glossario

| Termo | Significado |
|-------|-------------|
| **CNJ** | Conselho Nacional de Justica — orgao que padroniza a numeracao de processos |
| **DataJud** | Base de dados publica do CNJ com informacoes processuais |
| **DJEN** | Diario da Justica Eletronico Nacional |
| **TJSP DJe** | Diario da Justica Eletronico do Tribunal de Justica de Sao Paulo |
| **DEJT** | Diario Eletronico da Justica do Trabalho |
| **OAB** | Ordem dos Advogados do Brasil — registro profissional do advogado |
| **Score de risco** | Pontuacao de 0 a 100 que indica o nivel de risco de um processo |
| **Classe processual** | Tipo do processo (ex: Acao Civil Publica, Mandado de Seguranca) |
| **Orgao julgador** | Vara, turma ou camara responsavel pelo julgamento |
| **Pipeline de IA** | Conjunto de agentes que processam e enriquecem os dados do processo |
| **Captacao** | Regra de busca automatizada recorrente |
| **Monitor** | Acompanhamento automatico de processo, OAB, parte ou advogado |
| **Publicacao** | Texto oficial publicado em diario de justica |
| **Busca unificada** | Consulta simultanea em todas as fontes judiciais disponiveis |

---

## 10. Perguntas Frequentes

### O sistema funciona 24 horas?

Sim, o servidor esta ativo 24/7. As captacoes automatizadas respeitam os horarios configurados (padrao: 06:00 as 22:00), mas voce pode acessar o sistema e fazer buscas manuais a qualquer momento.

### Quanto tempo leva uma analise de processo?

Depende da complexidade e das fontes consultadas. Em media, de **10 a 60 segundos**. Processos com muitas movimentacoes podem levar mais tempo.

### As buscas no DJEN precisam de proxy?

Sim, o servidor esta hospedado na Alemanha, e o DJEN bloqueia IPs nao-brasileiros. O sistema usa automaticamente um proxy residencial brasileiro (Bright Data) para acessar o DJEN. Isso e transparente para o usuario.

### Posso monitorar quantos processos?

Nao ha limite tecnico. No entanto, muitos monitorados simultaneos podem aumentar o consumo de API e o tempo de processamento do scheduler.

### Os dados ficam armazenados por quanto tempo?

Os dados permanecem no banco de dados SQLite indefinidamente. Nao ha politica de expiracao automatica. A exclusao de monitorados ou captacoes remove os registros associados.

### Recebo notificacoes automaticas?

Sim, se configuradas. Na Captacao Automatizada, voce pode ativar notificacoes por WhatsApp ou e-mail. O Monitor tambem pode notificar quando novas publicacoes sao encontradas (depende da configuracao do sistema).

### O que acontece se o servidor reiniciar?

Os containers Docker reiniciam automaticamente (politica `restart: unless-stopped`). Os dados persistem no volume Docker (`captacao-data`). Ao retornar, o scheduler retoma as captacoes ativas.

---

## 11. Suporte

Para relatar problemas ou solicitar novas funcionalidades, entre em contato com a equipe de desenvolvimento. Inclua:

1. O que voce estava tentando fazer
2. O que aconteceu (mensagem de erro, tela em branco, etc.)
3. Navegador e sistema operacional utilizados
4. Horario aproximado do problema

---

*Documento gerado em 2026-04-26 — Captacao Peticao Blindada v3.0.0*

---

## Novas Funcionalidades (v2.0.0)

### Funcionalidades Adicionadas desde v1.1.0

#### Captação Automatizada
- Clonar captação existente com 1 clique
- Salvar busca pontual como captação automática
- Retry automático com backoff exponencial
- Alertas quando captação não encontra resultados
- Comparação entre execuções (diff)
- Agendamento por data específica
- Limite configurável por captação
- Exportar publicações por captação (CSV/JSON)
- Estatísticas avançadas por captação
- Resumo formatado para WhatsApp

#### Monitor DJEN
- Marcar publicação como lida/não lida
- Favoritar publicações importantes
- Exportar publicações em CSV e JSON
- Botões de exportação no painel

#### Processos
- Adicionar processo manualmente por número CNJ
- Anotações e comentários em processos
- Calculadora de prazos processuais (dias úteis)
- Busca por nome de parte
- Kanban board para gestão visual de processos

#### Pesquisa Pontual
- Busca simultânea em DataJud + DJEN
- Histórico de buscas realizadas
- Salvar busca como captação com 1 clique

#### IA & Modelos
- 3 modelos Gemini configurados (Flash, Flash Preview, Flash Lite)
- 4 funções de IA (Classificação, Previsão, Resumo, Jurisprudência)
- Log de chamadas à IA com estatísticas
- Fallback automático entre modelos

#### Administração
- Gestão de usuários com Modal (criar/editar/deletar)
- Página de Cadastros/Tenants
- Bloquear/desbloquear usuários
- Suspender/reativar tenants
- Tarifação reformulada com 20 funções do sistema

#### Segurança
- Rate Limiting (proteção contra abuso)
- Circuit Breaker (proteção contra falhas)
- Security Headers (5 headers de segurança)
- Bloqueio de login após 5 tentativas
- CORS restrito em produção

#### Cadeia de Custódia
- Auditoria automática de todas as ações
- Exportação em CSV e JSON
- Estatísticas por ação, entidade e usuário
- Verificação de integridade hash-chain

#### Novas Ferramentas
- Prazos processuais com cálculo de dias úteis
- Agenda de compromissos e audiências
- Favoritos e tags para organização
- Notas/lembretes globais
- Templates de captação
- Busca global full-text
- Contadores em tempo real
- Relatórios semanal e diário
- Score de produtividade
- Mapa de calor de atividade

#### Integrações
- Notificações por Email (SMTP)
- Notificações por WhatsApp Business
- Telegram Bot (configurável)
- Webhook receiver (Zapier/n8n/Make)
- Google Calendar (placeholder)

#### UX
- Toast notifications (substituiu alert())
- Skeleton loading
- Modal component
- Breadcrumbs em todas as páginas
- Página 404 customizada
- Modo escuro melhorado
- Atalhos de teclado (Ctrl+K, Ctrl+1-3)
- Tooltips informativos
- Indicador offline
- Sidebar com memória

#### Performance
- SQLite otimizado (WAL, cache, mmap)
- Gzip compression
- Cache em memória (5min TTL)
- Paginação automática
- Índices adicionais no banco

---

## Novas Funcionalidades (v3.0.0 — Security Hardening)

### Seguranca Aprimorada
- Login agora usa cookies seguros (httpOnly) — seu token nao fica mais exposto no navegador
- Sessao mais segura: o sistema gerencia automaticamente a autenticacao
- Conexao HTTPS automatica com certificado TLS (Caddy)
- Protecao contra abuso: limite de tentativas de login (5/min) e buscas (30/min)

### Novas Paginas de Administracao
- **Configuracao IA** (`/configuracao-ia`) — Ajuste parametros dos agentes de inteligencia artificial
- **Gestao de Usuarios** (`/admin/usuarios`) — Criar, editar, bloquear usuarios com diferentes niveis de acesso
- **Auditoria** (`/admin/auditoria`) — Visualize todas as acoes realizadas no sistema (cadeia de custodia)
- **Tarifacao** (`/admin/tarifacao`) — Acompanhe o consumo e uso do sistema
- **Cadastros/Tenants** (`/admin/tenants`) — Gerencie escritorios e organizacoes
- **Erros do Sistema** (`/admin/erros`) — Monitore erros e problemas do sistema

### Melhorias de Interface
- Notificacoes visuais (Toast) substituem alertas do navegador
- Loading states com Skeleton (carregamento mais suave)
- Modais para confirmacoes e formularios
- Breadcrumbs para navegacao
- Indicador de status online/offline
- Atalhos de teclado (Ctrl+K para busca rapida)
- Tooltips informativos em botoes e campos
