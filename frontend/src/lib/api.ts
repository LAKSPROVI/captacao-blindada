import axios, { AxiosInstance, AxiosError } from "axios";

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  id?: number;
  username: string;
  email?: string;
  full_name?: string;
  role?: string;
  tenant_id?: number;
}

export interface ProcessoAnalise {
  numero_processo: string;
  tribunal?: string;
  force_refresh?: boolean;
}

export interface ProcessoResult {
  numero_processo: string;
  tribunal?: string;
  classe?: string;
  assunto?: string;
  data_ajuizamento?: string;
  status?: string;
  partes?: Parte[];
  movimentacoes?: Movimentacao[];
  resumo?: string;
  riscos?: RiscoAnalise;
  timeline?: TimelineEvent[];
  [key: string]: unknown;
}

export interface Parte {
  nome: string;
  tipo: string;
  cpf_cnpj?: string;
  advogados?: string[];
}

export interface Movimentacao {
  data: string;
  descricao: string;
  tipo?: string;
}

export interface IndicadorRisco {
  tipo: string;
  nivel: string;
  descricao: string;
  detalhes?: string;
  recomendacao?: string;
}

export interface RiscoAnalise {
  nivel: "baixo" | "medio" | "alto" | "critico";
  score?: number;
  fatores?: string[];
  recomendacoes?: string[];
}

export interface TimelineEvent {
  data: string;
  titulo: string;
  descricao?: string;
  tipo?: string;
}

export interface MonitorItem {
  id: number;
  tipo: string;
  valor: string;
  nome_amigavel?: string;
  ativo: boolean;
  tribunal?: string;
  fontes: string;
  criado_em?: string;
  ultima_busca?: string;
  total_publicacoes: number;
  // Agendamento
  intervalo_minutos: number;
  horario_inicio: string;
  horario_fim: string;
  dias_semana: string;
  proxima_busca?: string;
}

export interface PublicacaoItem {
  id?: number;
  hash?: string;
  fonte: string;
  tribunal: string;
  data_publicacao: string;
  conteudo: string;
  numero_processo?: string;
  classe_processual?: string;
  orgao_julgador?: string;
  assuntos?: string[];
  movimentos?: Record<string, unknown>[];
  url_origem?: string;
  caderno?: string;
  pagina?: string;
  oab_encontradas?: string[];
  advogados?: string[];
  partes?: string[];
}

export interface BuscaParams {
  termo: string;
  tribunal?: string;
  data_inicio?: string;
  data_fim?: string;
  // Campos específicos DJEN (passados diretamente sem auto-detecção)
  numero_oab?: string;
  uf_oab?: string;
  nome_advogado?: string;
  nome_parte?: string;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface HealthStatus {
  status: string;
  version?: string;
  uptime?: number;
}

export interface MonitorStats {
  total_monitorados?: number;
  monitorados_ativos?: number;
  total_publicacoes?: number;
  publicacoes_hoje?: number;
  publicacoes_semana?: number;
  total_buscas?: number;
  fontes_ativas?: number;
  ultima_busca?: string;
}

export interface ProcessoMonitoradoStats {
  total: number;
  ativos?: number;
  com_movimentacoes?: number;
  verificados_hoje?: number;
  nunca_verificados?: number;
  ultima_verificacao?: string;
  por_origem?: Record<string, number>;
}

export interface ProcessoMonitorado {
  id?: number;
  numero_processo: string;
  tribunal?: string;
  classe_processual?: string;
  orgao_julgador?: string;
  assuntos?: any;
  status?: string;
  origem?: string;
  origem_id?: number;
  ultima_verificacao?: string;
  total_movimentacoes: number;
  movimentacoes?: any[];
  data_ultima_movimentacao?: string;
  criado_em?: string;
  atualizado_em?: string;
}

export interface ProcMonitorHistory {
  id: number;
  numero_processo: string;
  data_verificacao: string;
  status: string;
  fonte: string;
  detalhes?: string;
  total_movimentacoes: number;
  novas_movimentacoes: number;
}

export interface AIConfig {
  function_key: string;
  provider: string;
  model_name: string;
  api_key?: string;
  base_url?: string;
  enabled: boolean;
  updated_at?: string;
}

export interface AIProvider {
  id: string;
  name: string;
  models: string[];
  details?: {
    id: string;
    name: string;
    description: string;
    input_tokens: number;
    output_tokens: number;
    thinking: boolean;
    recommended_for: string[];
  }[];
  api_key_configured?: boolean;
}

export interface AIModelsResponse {
  providers: AIProvider[];
}

interface ProcessoResumoResponseRaw {
  resumo_executivo?: string;
  [key: string]: unknown;
}

interface TimelineResponseRaw {
  timeline?: TimelineEvent[];
  [key: string]: unknown;
}

interface RiscoResponseRaw {
  risco_geral?: string;
  risco_score?: number;
  indicadores?: IndicadorRisco[];
  recomendacoes?: string[];
  [key: string]: unknown;
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: "/api",
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.client.interceptors.request.use((config) => {
      if (typeof window !== "undefined") {
        const token = localStorage.getItem("access_token");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          if (typeof window !== "undefined") {
            localStorage.removeItem("access_token");
            if (!window.location.pathname.includes("/login")) {
              window.location.href = "/login";
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async login(username: string, password: string): Promise<LoginResponse> {
    const params = new URLSearchParams();
    params.append("username", username);
    params.append("password", password);
    const { data } = await this.client.post<LoginResponse>("/auth/login", params, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", data.access_token);
    }
    return data;
  }

  async me(): Promise<UserInfo> {
    const { data } = await this.client.get<UserInfo>("/auth/me");
    return data;
  }

  logout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
  }

  // Processo
  async analisarProcesso(params: ProcessoAnalise): Promise<ProcessoResult> {
    const { data } = await this.client.post<ProcessoResult>(
      "/processo/analisar",
      params
    );
    return data;
  }

  async getProcesso(numero: string): Promise<ProcessoResult> {
    const { data } = await this.client.get<ProcessoResult>(
      `/processo/${encodeURIComponent(numero)}`
    );
    return data;
  }

  async getResumo(numero: string): Promise<{ resumo: string }> {
    const { data } = await this.client.get<ProcessoResumoResponseRaw>(
      `/processo/${encodeURIComponent(numero)}/resumo`
    );
    return { resumo: data.resumo_executivo || "" };
  }

  async getTimeline(numero: string): Promise<TimelineEvent[]> {
    const { data } = await this.client.get<TimelineResponseRaw>(
      `/processo/${encodeURIComponent(numero)}/timeline`
    );
    return data.timeline || [];
  }

  async getRiscos(numero: string): Promise<RiscoAnalise> {
    const { data } = await this.client.get<RiscoResponseRaw>(
      `/processo/${encodeURIComponent(numero)}/riscos`
    );
    return {
      nivel: (data.risco_geral || "baixo") as RiscoAnalise["nivel"],
      score: data.risco_score,
      fatores: (data.indicadores || []).map((i) => i.descricao),
      recomendacoes: data.recomendacoes,
    };
  }

  async getAgents(): Promise<{ agents: string[] }> {
    const { data } = await this.client.get("/processo/agents");
    return data;
  }

  async getResultados(params?: {
    limit?: number;
    offset?: number;
    tribunal?: string;
    area?: string;
  }): Promise<PaginatedResult<ProcessoResult>> {
    const { data } = await this.client.get("/processo/resultados", { params });
    return data;
  }

  // Busca
  async buscarDataJud(params: BuscaParams) {
    // Detectar se o termo e numero de processo ou texto generico
    const termoLimpo = params.termo.trim();
    const isProcesso = /^\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4}$/.test(termoLimpo) || /^\d{20}$/.test(termoLimpo);

    const body: Record<string, unknown> = {
      tribunal: params.tribunal || "tjsp",
      data_inicio: params.data_inicio,
      data_fim: params.data_fim,
    };

    if (isProcesso) {
      body.numero_processo = termoLimpo;
    } else {
      // Busca generica — DataJud nao suporta nome de parte,
      // mas enviar como numero_processo faz a query generica funcionar
      body.numero_processo = termoLimpo;
    }

    const { data } = await this.client.post("/datajud/buscar", body);
    return data;
  }

  async buscarDJEN(params: BuscaParams) {
    // Converter data YYYY-MM-DD (HTML date input) → DD/MM/AAAA (formato DJEN)
    const toDataBR = (iso: string) => {
      const parts = iso.split("-");
      return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : iso;
    };

    const body: Record<string, unknown> = {
      tribunal: params.tribunal,
      data_inicio: params.data_inicio ? toDataBR(params.data_inicio) : undefined,
      data_fim: params.data_fim ? toDataBR(params.data_fim) : undefined,
    };

    // Se campos DJEN explícitos foram fornecidos, usá-los diretamente
    if (params.numero_oab) {
      body.numero_oab = params.numero_oab;
      if (params.uf_oab) body.uf_oab = params.uf_oab.toUpperCase();
    } else if (params.nome_advogado) {
      body.nome_advogado = params.nome_advogado;
    } else if (params.nome_parte) {
      body.nome_parte = params.nome_parte;
    } else {
      // Auto-detectar pelo termo livre
      const termoLimpo = params.termo.trim();
      if (termoLimpo) {
        const isProcesso =
          /^\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4}$/.test(termoLimpo) ||
          /^\d{20}$/.test(termoLimpo);
        // OAB: 123456/SP ou SP123456
        const isOAB =
          /^\d{3,6}\/[A-Z]{2}$/i.test(termoLimpo) ||
          /^[A-Z]{2}\d{3,6}$/i.test(termoLimpo);

        if (isProcesso) {
          body.numero_processo = termoLimpo;
        } else if (isOAB) {
          // Detectar formato: 123456/SP → group1=123456, group2=SP
          //                   SP123456  → group1=SP,     group2=123456
          const m1 = termoLimpo.match(/^(\d{3,6})\/([A-Z]{2})$/i);
          const m2 = termoLimpo.match(/^([A-Z]{2})(\d{3,6})$/i);
          if (m1) {
            body.numero_oab = m1[1];
            body.uf_oab = m1[2].toUpperCase();
          } else if (m2) {
            body.uf_oab = m2[1].toUpperCase();
            body.numero_oab = m2[2];
          } else {
            body.numero_oab = termoLimpo;
          }
        } else {
          // Texto livre → nome_parte (DJEN suporta busca por nome de parte)
          body.nome_parte = termoLimpo;
        }
      }
    }

    const { data } = await this.client.post("/djen/buscar", body);
    return data;
  }

  async buscaUnificada(params: BuscaParams) {
    const { data } = await this.client.post("/buscar/unificada", null, {
      params: {
        termo: params.termo,
        ...(params.tribunal ? { tribunal: params.tribunal } : {}),
        ...(params.data_inicio ? { data_inicio: params.data_inicio } : {}),
        ...(params.data_fim ? { data_fim: params.data_fim } : {}),
      },
    });
    return data;
  }

  // Monitor
  async addMonitor(params: {
    tipo: string;
    valor: string;
    nome_amigavel?: string;
    tribunal?: string;
    fontes?: string | string[];
    intervalo_minutos?: number;
    horario_inicio?: string;
    horario_fim?: string;
    dias_semana?: string;
  }): Promise<MonitorItem> {
    const { data } = await this.client.post<MonitorItem>(
      "/monitor/add",
      params
    );
    return data;
  }

  async listMonitors(): Promise<MonitorItem[]> {
    const { data } = await this.client.get<MonitorItem[]>("/monitor/list");
    return Array.isArray(data) ? data : [];
  }

  async getMonitorStats(): Promise<MonitorStats> {
    const { data } = await this.client.get<MonitorStats>("/monitor/stats");
    return data;
  }

  async getPublicacoesRecentes(params?: {
    fonte?: string;
    tribunal?: string;
    processo?: string;
    limite?: number;
  }): Promise<PublicacaoItem[]> {
    const { data } = await this.client.get<PublicacaoItem[]>(
      "/monitor/publicacoes/recentes",
      { params }
    );
    return Array.isArray(data) ? data : [];
  }

  async buscarLocal(params: {
    termo: string;
    fonte?: string;
    tribunal?: string;
    limite?: number;
  }): Promise<PublicacaoItem[]> {
    const { data } = await this.client.get<PublicacaoItem[]>(
      "/monitor/publicacoes/buscar",
      { params }
    );
    return Array.isArray(data) ? data : [];
  }

  async deletePublicacao(id: number): Promise<{ status: string }> {
    const { data } = await this.client.delete<{ status: string }>(`/monitor/publicacoes/${id}`);
    return data;
  }

  // Captacao Automatizada
  async listarCaptacoes(params?: {
    ativo?: boolean;
    tipo_busca?: string;
    prioridade?: string;
  }): Promise<CaptacaoListResponse> {
    const { data } = await this.client.get<CaptacaoListResponse>("/captacao/listar", { params });
    return data;
  }

  async getCaptacaoStats(): Promise<CaptacaoStats> {
    const { data } = await this.client.get<CaptacaoStats>("/captacao/stats");
    return data;
  }

  async criarCaptacao(params: CaptacaoCreateParams): Promise<CaptacaoItem> {
    const { data } = await this.client.post<CaptacaoItem>("/captacao/criar", params);
    return data;
  }

  async obterCaptacao(id: number): Promise<CaptacaoItem> {
    const { data } = await this.client.get<CaptacaoItem>(`/captacao/${id}`);
    return data;
  }

  async atualizarCaptacao(id: number, params: Partial<CaptacaoCreateParams>): Promise<CaptacaoItem> {
    const { data } = await this.client.put<CaptacaoItem>(`/captacao/${id}`, params);
    return data;
  }

  async desativarCaptacao(id: number): Promise<{ status: string; message: string }> {
    const { data } = await this.client.delete(`/captacao/${id}`);
    return data;
  }

  async executarCaptacao(id: number): Promise<CaptacaoExecResult> {
    const { data } = await this.client.post<CaptacaoExecResult>(`/captacao/${id}/executar`);
    return data;
  }

  async pausarCaptacao(id: number): Promise<{ status: string; message: string }> {
    const { data } = await this.client.post(`/captacao/${id}/pausar`);
    return data;
  }

  async retomarCaptacao(id: number): Promise<{ status: string; message: string }> {
    const { data } = await this.client.post(`/captacao/${id}/retomar`);
    return data;
  }

  async historicoCaptacao(id: number, params?: {
    limite?: number;
    offset?: number;
  }): Promise<{ status: string; total: number; execucoes: CaptacaoExecucao[] }> {
    const { data } = await this.client.get(`/captacao/${id}/historico`, { params });
    return data;
  }

  async resultadosCaptacao(id: number, params?: {
    limite?: number;
    offset?: number;
    fonte?: string;
  }): Promise<{ status: string; total: number; publicacoes: PublicacaoItem[] }> {
    const { data } = await this.client.get(`/captacao/${id}/resultados`, { params });
    return data;
  }

  async diffCaptacao(id: number): Promise<CaptacaoDiff> {
    const { data } = await this.client.get<CaptacaoDiff>(`/captacao/${id}/diff`);
    return data;
  }

  async executarTodasCaptacoes(): Promise<CaptacaoExecResult[]> {
    const { data } = await this.client.post<CaptacaoExecResult[]>("/captacao/executar-todas");
    return data;
  }

  async previewCaptacao(params: CaptacaoPreviewParams): Promise<PublicacaoItem[]> {
    const { data } = await this.client.post<PublicacaoItem[]>("/captacao/preview", params);
    return data;
  }

  // Health
  async health(): Promise<HealthStatus> {
    const { data } = await this.client.get<HealthStatus>("/health");
    return data;
  }

  async getProcessoMonitoradoStats(): Promise<ProcessoMonitoradoStats> {
    const { data } = await this.client.get<ProcessoMonitoradoStats>("/processos/stats");
    return data;
  }

  async listarProcessosMonitorados(params?: { limite?: number; offset?: number; status?: string }): Promise<{ processos: ProcessoMonitorado[]; total: number }> {
    const { data } = await this.client.get<{ status: string; processos: ProcessoMonitorado[]; total: number }>("/processos/listar", { params });
    return { processos: data.processos || [], total: data.total || 0 };
  }

  async registrarProcessoMonitorado(params: { numero_processo: string; tribunal?: string; origem?: string }): Promise<{ status: string; id?: number }> {
    const { data } = await this.client.post<{ status: string; id?: number }>("/processos/registrar", params);
    return data;
  }

  async deletarProcessoMonitorado(numero_processo: string): Promise<{ status: string }> {
    const { data } = await this.client.delete<{ status: string }>(`/processos/${encodeURIComponent(numero_processo)}`);
    return data;
  }

  // Novos endpoints v1.3.0
  async adicionarProcessoManual(params: { numero_processo: string; tribunal?: string }): Promise<any> {
    const { data } = await this.client.post("/processos/adicionar", params);
    return data;
  }

  async calcularPrazo(params: { data_inicio: string; dias_uteis: number }): Promise<any> {
    const { data } = await this.client.post("/processos/prazos/calcular", params);
    return data;
  }

  async getAnotacoes(numero_processo: string): Promise<any> {
    const { data } = await this.client.get(`/processos/${encodeURIComponent(numero_processo)}/anotacoes`);
    return data;
  }

  async addAnotacao(numero_processo: string, params: { texto: string; tipo: string }): Promise<any> {
    const { data } = await this.client.post(`/processos/${encodeURIComponent(numero_processo)}/anotacoes`, params);
    return data;
  }

  async deleteAnotacao(numero_processo: string, id: number): Promise<any> {
    const { data } = await this.client.delete(`/processos/${encodeURIComponent(numero_processo)}/anotacoes/${id}`);
    return data;
  }

  async clonarCaptacao(id: number): Promise<any> {
    const { data } = await this.client.post(`/captacao/${id}/clonar`);
    return data;
  }

  async marcarPublicacaoLida(id: number, lida: boolean = true): Promise<any> {
    const { data } = await this.client.put(`/monitor/publicacoes/${id}/lida`, lida);
    return data;
  }

  async marcarPublicacaoFavorita(id: number, favorita: boolean = true): Promise<any> {
    const { data } = await this.client.put(`/monitor/publicacoes/${id}/favorita`, favorita);
    return data;
  }

  async getHistoricoBuscas(limite: number = 50): Promise<any> {
    const { data } = await this.client.get("/processos/buscas/historico", { params: { limite } });
    return data;
  }

  async getNotificationStatus(): Promise<any> {
    const { data } = await this.client.get("/notifications/status");
    return data;
  }

  // Prazos
  async criarPrazo(params: { numero_processo: string; descricao: string; data_inicio: string; dias_uteis: number; tipo?: string }): Promise<any> {
    const { data } = await this.client.post("/prazos/criar", params);
    return data;
  }

  async listarPrazos(status: string = "ativo"): Promise<any> {
    const { data } = await this.client.get("/prazos/listar", { params: { status } });
    return data;
  }

  async proximosPrazos(dias: number = 7): Promise<any> {
    const { data } = await this.client.get("/prazos/proximos", { params: { dias } });
    return data;
  }

  async concluirPrazo(id: number): Promise<any> {
    const { data } = await this.client.put(`/prazos/${id}/concluir`);
    return data;
  }

  async removerPrazo(id: number): Promise<any> {
    const { data } = await this.client.delete(`/prazos/${id}`);
    return data;
  }

  // Favoritos e Tags
  async listarFavoritos(tipo?: string): Promise<any> {
    const { data } = await this.client.get("/favoritos", { params: tipo ? { tipo } : {} });
    return data;
  }

  async adicionarFavorito(params: { tipo: string; referencia_id: number; titulo?: string; cor?: string }): Promise<any> {
    const { data } = await this.client.post("/favoritos", params);
    return data;
  }

  async removerFavorito(tipo: string, referencia_id: number): Promise<any> {
    const { data } = await this.client.delete(`/favoritos/${tipo}/${referencia_id}`);
    return data;
  }

  async listarTags(): Promise<any> {
    const { data } = await this.client.get("/favoritos/tags");
    return data;
  }

  async criarTag(params: { nome: string; cor?: string }): Promise<any> {
    const { data } = await this.client.post("/favoritos/tags", params);
    return data;
  }

  // Agenda
  async criarCompromisso(params: { titulo: string; data_evento: string; tipo?: string; numero_processo?: string; hora_evento?: string; local?: string }): Promise<any> {
    const { data } = await this.client.post("/agenda/criar", params);
    return data;
  }

  async listarCompromissos(status: string = "pendente"): Promise<any> {
    const { data } = await this.client.get("/agenda/listar", { params: { status } });
    return data;
  }

  async compromissosHoje(): Promise<any> {
    const { data } = await this.client.get("/agenda/hoje");
    return data;
  }

  async proximosCompromissos(dias: number = 7): Promise<any> {
    const { data } = await this.client.get("/agenda/proximos", { params: { dias } });
    return data;
  }

  async concluirCompromisso(id: number): Promise<any> {
    const { data } = await this.client.put(`/agenda/${id}/concluir`);
    return data;
  }

  // Contadores
  async getContadores(): Promise<any> {
    const { data } = await this.client.get("/contadores");
    return data;
  }

  // Dashboard
  async getDashboardResumo(): Promise<any> {
    const { data } = await this.client.get("/dashboard/resumo-completo");
    return data;
  }

  async getDashboardEvolucao(dias: number = 30): Promise<any> {
    const { data } = await this.client.get("/dashboard/evolucao", { params: { dias } });
    return data;
  }

  async getDashboardTribunais(): Promise<any> {
    const { data } = await this.client.get("/dashboard/tribunais");
    return data;
  }

  async getDashboardProximas(): Promise<any> {
    const { data } = await this.client.get("/dashboard/proximas-execucoes");
    return data;
  }

  // Relatórios
  async getRelatorioSemanal(): Promise<any> {
    const { data } = await this.client.get("/relatorios/semanal");
    return data;
  }

  async getRelatorioDiario(): Promise<any> {
    const { data } = await this.client.get("/relatorios/diario");
    return data;
  }

  // Busca Global
  async buscaGlobal(q: string, limite: number = 50): Promise<any> {
    const { data } = await this.client.get("/busca-global", { params: { q, limite } });
    return data;
  }

  // Captação Estatísticas
  async getCaptacaoEstatisticas(id: number): Promise<any> {
    const { data } = await this.client.get(`/captacao/${id}/estatisticas`);
    return data;
  }

  // Captação Alertas
  async getCaptacaoAlertas(dias: number = 3): Promise<any> {
    const { data } = await this.client.get("/captacao/alertas/sem-resultados", { params: { dias } });
    return data;
  }

  // Retry Captação
  async retryCaptacao(id: number, max_tentativas: number = 3): Promise<any> {
    const { data } = await this.client.post(`/captacao/${id}/retry`, null, { params: { max_tentativas } });
    return data;
  }

  // Health detalhado
  async getHealthDatabase(): Promise<any> {
    const { data } = await this.client.get("/health/database");
    return data;
  }

  async getHealthSystem(): Promise<any> {
    const { data } = await this.client.get("/health/system");
    return data;
  }

  async verificarProcessosAgora(): Promise<{ status: string; verificados?: number; atualizados?: number }> {
    const { data } = await this.client.post<{ status: string; verificados?: number; atualizados?: number }>("/processos/verificar-agora");
    return data;
  }

  async getProcessoMonitoradoHistory(numero: string): Promise<ProcMonitorHistory[]> {
    const { data } = await this.client.get<{ status: string; historico: ProcMonitorHistory[] }>(
      `/processos/${encodeURIComponent(numero)}/historico`
    );
    return data.historico || [];
  }

  // IA Config
  async getAIConfigs(): Promise<AIConfig[]> {
    const { data } = await this.client.get<AIConfig[]>("/ai/config");
    return data;
  }

  async updateAIConfig(key: string, config: Partial<AIConfig>): Promise<{ status: string }> {
    const { data } = await this.client.put<{ status: string }>(`/ai/config/${key}`, config);
    return data;
  }

  async getAvailableAIModels(): Promise<AIProvider[]> {
    const { data } = await this.client.get<AIModelsResponse>("/ai/models");
    return data.providers;
  }

  async testAIConfig(config: Partial<AIConfig>): Promise<{ status: string; message: string; response?: string }> {
    const { data } = await this.client.post("/ai/test", config);
    return data;
  }

  // Settings
  async getSettings(): Promise<Record<string, string>> {
    const { data } = await this.client.get<Record<string, string>>("/settings");
    return data;
  }

  async updateSetting(key: string, value: any): Promise<{ status: string }> {
    const { data } = await this.client.post<{ status: string }>("/settings", { key, value });
    return data;
  }

  // ==========================================
  // Admin & Billing
  // ==========================================

  async getTenants(): Promise<any[]> {
    const { data } = await this.client.get("/admin/tenants");
    return data;
  }
  
  async createTenant(tenantData: any): Promise<any> {
    const { data } = await this.client.post("/admin/tenants", tenantData);
    return data;
  }

  async updateTenant(id: number, tenantData: any): Promise<any> {
    const { data } = await this.client.put(`/admin/tenants/${id}`, tenantData);
    return data;
  }

  async getUsers(): Promise<any[]> {
    const { data } = await this.client.get("/admin/users");
    return data;
  }

  async createUser(userData: any): Promise<any> {
    const { data } = await this.client.post("/auth/register", userData);
    return data;
  }

  async updateUser(id: number, userData: any): Promise<any> {
    const { data } = await this.client.put(`/admin/users/${id}`, userData);
    return data;
  }

  async deleteUser(id: number): Promise<void> {
    await this.client.delete(`/admin/users/${id}`);
  }

  async getBillingStats(): Promise<any> {
    const { data } = await this.client.get("/billing/stats");
    return data;
  }

  async getFunctionCosts(): Promise<any[]> {
    const { data } = await this.client.get("/billing/costs");
    return data;
  }

  async updateFunctionCost(function_name: string, costData: any): Promise<any> {
    const { data } = await this.client.put(`/billing/costs/${function_name}`, costData);
    return data;
  }

  async getUsageLogs(limit = 100, offset = 0): Promise<any[]> {
    const { data } = await this.client.get("/billing/usage", { params: { limit, offset } });
    return data;
  }

  // ==========================================
  // Custodia & Sistema
  // ==========================================

  async getAuditLogs(limit = 100, offset = 0): Promise<any[]> {
    const { data } = await this.client.get("/audit/logs", { params: { limit, offset } });
    return data;
  }

  async verifyAuditChain(): Promise<{status: string, message: string, erros?: any[]}> {
    const { data } = await this.client.get("/audit/verify");
    return data;
  }

  async getAuditStats(): Promise<any> {
    const { data } = await this.client.get("/audit/stats");
    return data;
  }

  async getSystemErrors(status: string = "aberto", limit = 100, offset = 0): Promise<any[]> {
    const { data } = await this.client.get("/errors", { params: { status, limit, offset } });
    return data;
  }

  async resolveSystemError(errorId: number): Promise<any> {
    const { data } = await this.client.post(`/errors/${errorId}/resolve`);
    return data;
  }

  // Analytics
  async getAnalyticsPubPorDia(dias: number = 30): Promise<any> {
    const { data } = await this.client.get("/analytics/publicacoes-por-dia", { params: { dias } });
    return data;
  }

  async getAnalyticsPubPorTribunal(): Promise<any> {
    const { data } = await this.client.get("/analytics/publicacoes-por-tribunal");
    return data;
  }

  async getAnalyticsExecPorStatus(): Promise<any> {
    const { data } = await this.client.get("/analytics/execucoes-por-status");
    return data;
  }

  async getAnalyticsTempoMedio(): Promise<any> {
    const { data } = await this.client.get("/analytics/tempo-medio-execucao");
    return data;
  }

  async getAnalyticsTaxaNovos(dias: number = 30): Promise<any> {
    const { data } = await this.client.get("/analytics/taxa-novos", { params: { dias } });
    return data;
  }

  async getAnalyticsHorasPico(): Promise<any> {
    const { data } = await this.client.get("/analytics/horas-pico");
    return data;
  }

  async getAnalyticsResumoMensal(): Promise<any> {
    const { data } = await this.client.get("/analytics/resumo-mensal");
    return data;
  }

  // Sidebar contadores
  async getSidebarContadores(): Promise<any> {
    const { data } = await this.client.get("/contadores");
    return data;
  }

  // Agendamentos captação
  async agendarCaptacao(id: number, data_execucao: string): Promise<any> {
    const { data } = await this.client.post(`/captacao/${id}/agendar-data`, null, { params: { data_execucao } });
    return data;
  }

  async listarAgendamentos(id: number): Promise<any> {
    const { data } = await this.client.get(`/captacao/${id}/agendamentos`);
    return data;
  }

  async configurarLimiteCaptacao(id: number, max_resultados: number, max_paginas: number): Promise<any> {
    const { data } = await this.client.put(`/captacao/${id}/limite`, null, { params: { max_resultados, max_paginas } });
    return data;
  }

  // Upload CSV processos
  async uploadCSVProcessos(processos: Array<{numero_processo: string; tribunal?: string}>): Promise<any> {
    const { data } = await this.client.post("/config/processos/upload-csv", processos);
    return data;
  }

  // Suspender/reativar tenant
  async suspenderTenant(id: number): Promise<any> {
    const { data } = await this.client.put(`/admin/tenants/${id}/suspender`);
    return data;
  }

  async reativarTenant(id: number): Promise<any> {
    const { data } = await this.client.put(`/admin/tenants/${id}/reativar`);
    return data;
  }

  // Analytics extras
  async getPublicacoesPorClasse(): Promise<any> {
    const { data } = await this.client.get("/extras/publicacoes-por-classe");
    return data;
  }

  async getPublicacoesPorOrgao(): Promise<any> {
    const { data } = await this.client.get("/extras/publicacoes-por-orgao");
    return data;
  }

  async getCaptacoesPorTipo(): Promise<any> {
    const { data } = await this.client.get("/extras/captacoes-por-tipo");
    return data;
  }

  async getErrosPorTipo(): Promise<any> {
    const { data } = await this.client.get("/extras/erros-por-tipo");
    return data;
  }

  async getSaudeCompleta(): Promise<any> {
    const { data } = await this.client.get("/extras/saude-completa");
    return data;
  }

  async limparDuplicadas(): Promise<any> {
    const { data } = await this.client.post("/extras/limpar-publicacoes-duplicadas");
    return data;
  }

  // Integrações
  async getIntegracaoStatus(): Promise<any> {
    const { data } = await this.client.get("/integracoes/status");
    return data;
  }

  async testTelegram(message: string): Promise<any> {
    const { data } = await this.client.post("/integracoes/telegram/test", message);
    return data;
  }

  // Automações
  async listarRegras(ativo?: boolean): Promise<any> {
    const { data } = await this.client.get("/automacoes/regras", { params: ativo !== undefined ? { ativo } : {} });
    return data;
  }

  async criarRegra(params: { nome: string; tipo: string; condicao: string; acao: string }): Promise<any> {
    const { data } = await this.client.post("/automacoes/regras", params);
    return data;
  }

  async toggleRegra(id: number): Promise<any> {
    const { data } = await this.client.put(`/automacoes/regras/${id}/toggle`);
    return data;
  }

  async removerRegra(id: number): Promise<any> {
    const { data } = await this.client.delete(`/automacoes/regras/${id}`);
    return data;
  }

  async getResumoAutomacoes(): Promise<any> {
    const { data } = await this.client.get("/automacoes/resumo");
    return data;
  }

  // Tools
  async formatarCNJ(numero: string): Promise<any> {
    const { data } = await this.client.post("/tools/formatar-cnj", numero);
    return data;
  }

  async calcularDiasUteis(data_inicio: string, data_fim: string): Promise<any> {
    const { data } = await this.client.post("/tools/calcular-dias-uteis", { data_inicio, data_fim });
    return data;
  }

  async getEstatisticasGerais(): Promise<any> {
    const { data } = await this.client.get("/tools/estatisticas-gerais");
    return data;
  }

  async getUptime(): Promise<any> {
    const { data } = await this.client.get("/tools/uptime");
    return data;
  }

  async vacuumDB(): Promise<any> {
    const { data } = await this.client.post("/tools/vacuum");
    return data;
  }

  async getIndicesDB(): Promise<any> {
    const { data } = await this.client.get("/tools/indices-db");
    return data;
  }

  // Fontes de Dados
  async getFontesDisponiveis(): Promise<any> {
    const { data } = await this.client.get("/fontes/disponiveis");
    return data;
  }

  async getFonteDetalhe(id: string): Promise<any> {
    const { data } = await this.client.get(`/fontes/${id}`);
    return data;
  }

  async getFontesAtivasStatus(): Promise<any> {
    const { data } = await this.client.get("/fontes/ativas/status");
    return data;
  }

  // Kanban
  async getKanbanColunas(): Promise<any> {
    const { data } = await this.client.get("/kanban/colunas");
    return data;
  }

  async getKanbanCards(coluna?: string): Promise<any> {
    const { data } = await this.client.get("/kanban/cards", { params: coluna ? { coluna } : {} });
    return data;
  }

  async criarKanbanCard(params: { titulo: string; descricao?: string; numero_processo?: string; coluna?: string; prioridade?: string }): Promise<any> {
    const { data } = await this.client.post("/kanban/cards", params);
    return data;
  }

  async moverKanbanCard(id: number, coluna: string, ordem: number = 0): Promise<any> {
    const { data } = await this.client.put(`/kanban/cards/${id}/mover`, { coluna, ordem });
    return data;
  }

  async removerKanbanCard(id: number): Promise<any> {
    const { data } = await this.client.delete(`/kanban/cards/${id}`);
    return data;
  }

  async getKanbanStats(): Promise<any> {
    const { data } = await this.client.get("/kanban/stats");
    return data;
  }

  // Automações historico
  async getHistoricoAutomacoes(limite: number = 50): Promise<any> {
    const { data } = await this.client.get("/automacoes/historico", { params: { limite } });
    return data;
  }
}

// =========================================================================
// Captacao Automatizada - Types
// =========================================================================

export interface CaptacaoItem {
  id: number;
  nome: string;
  descricao?: string;
  ativo: boolean;
  tipo_busca: string;
  modalidade: "recorrente" | "faixa_fixa";
  numero_processo?: string;
  numero_oab?: string;
  uf_oab?: string;
  nome_parte?: string;
  nome_advogado?: string;
  tribunal?: string;
  tribunais?: string;
  classe_codigo?: number;
  assunto_codigo?: number;
  orgao_id?: number;
  tipo_comunicacao?: string;
  data_inicio?: string;
  data_fim?: string;
  fontes: string;
  intervalo_minutos: number;
  horario_inicio: string;
  horario_fim: string;
  dias_semana: string;
  proxima_execucao?: string;
  pausado: boolean;
  auto_enriquecer: boolean;
  notificar_whatsapp: boolean;
  notificar_email: boolean;
  prioridade: string;
  criado_em?: string;
  atualizado_em?: string;
  ultima_execucao?: string;
  total_execucoes: number;
  total_resultados: number;
  total_novos: number;
}

export interface CaptacaoListResponse {
  status: string;
  total: number;
  captacoes: CaptacaoItem[];
}

export interface CaptacaoCreateParams {
  nome: string;
  descricao?: string;
  tipo_busca: string;
  modalidade: "recorrente" | "faixa_fixa";
  numero_processo?: string;
  numero_oab?: string;
  uf_oab?: string;
  nome_parte?: string;
  nome_advogado?: string;
  tribunal?: string;
  tribunais?: string;
  classe_codigo?: number;
  assunto_codigo?: number;
  orgao_id?: number;
  tipo_comunicacao?: string;
  data_inicio?: string;
  data_fim?: string;
  fontes?: string[];
  intervalo_minutos?: number;
  horario_inicio?: string;
  horario_fim?: string;
  dias_semana?: string;
  auto_enriquecer?: boolean;
  notificar_whatsapp?: boolean;
  notificar_email?: boolean;
  prioridade?: string;
}

export interface CaptacaoPreviewParams {
  tipo_busca: string;
  numero_processo?: string;
  numero_oab?: string;
  uf_oab?: string;
  nome_parte?: string;
  nome_advogado?: string;
  tribunal?: string;
  tribunais?: string;
  classe_codigo?: number;
  assunto_codigo?: number;
  orgao_id?: number;
  tipo_comunicacao?: string;
  data_inicio?: string;
  data_fim?: string;
  fontes?: string[];
}

export interface CaptacaoStats {
  total_captacoes: number;
  captacoes_ativas: number;
  captacoes_pausadas: number;
  total_execucoes: number;
  execucoes_hoje: number;
  total_novos_encontrados: number;
  ultima_execucao?: string;
  por_tipo: Record<string, number>;
  por_prioridade: Record<string, number>;
}

export interface CaptacaoExecucao {
  id: number;
  captacao_id: number;
  inicio: string;
  fim?: string;
  status: string;
  fonte: string;
  parametros_json?: string;
  total_resultados: number;
  novos_resultados: number;
  duracao_ms?: number;
  erro?: string;
  criado_em?: string;
}

export interface CaptacaoExecResult {
  captacao_id: number;
  status: string;
  fontes_consultadas: string[];
  total_resultados: number;
  novos_resultados: number;
  tempo_total_ms: number;
  execucoes: CaptacaoExecucao[];
  processos_enriquecidos: string[];
  erro?: string;
}

export interface CaptacaoDiff {
  captacao_id: number;
  execucao_atual_id?: number;
  execucao_anterior_id?: number;
  novos: PublicacaoItem[];
  total_novos: number;
  total_mantidos: number;
  total_atual: number;
  resumo: string;
}

export const api = new ApiClient();
