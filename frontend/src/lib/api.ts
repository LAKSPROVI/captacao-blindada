import axios, { AxiosInstance, AxiosError } from "axios";

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  username: string;
  email?: string;
  full_name?: string;
  roles?: string[];
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
