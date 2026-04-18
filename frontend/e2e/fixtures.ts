import { test as base, expect, type Page, type APIRequestContext } from '@playwright/test';

const TEST_USER = {
  username: process.env.TEST_USERNAME || 'admin',
  password: process.env.TEST_PASSWORD || 'admin123',
};

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

type CustomFixtures = {
  authenticatedPage: Page;
  apiContext: APIRequestContext;
};

export const test = base.extend<CustomFixtures>({
  authenticatedPage: async ({ page, context }, use) => {
    // Interceptar chamadas de API para autenticação
    await page.goto('/login');

    // Preencher formulário de login
    await page.getByPlaceholder(/usuário|username|email/i).fill(TEST_USER.username);
    await page.getByPlaceholder(/senha|password/i).fill(TEST_USER.password);
    await page.getByRole('button', { name: /entrar|login|acessar/i }).click();

    // Aguardar redirecionamento para dashboard
    await page.waitForURL('/', { timeout: 10_000 });

    await use(page);
  },

  apiContext: async ({ playwright }, use) => {
    // Criar contexto de API com autenticação
    const apiContext = await playwright.request.newContext({
      baseURL: API_BASE_URL,
    });

    // Obter token JWT
    const loginResponse = await apiContext.post('/api/auth/login', {
      data: {
        username: TEST_USER.username,
        password: TEST_USER.password,
      },
    });

    if (loginResponse.ok()) {
      const { access_token } = await loginResponse.json();
      // Recriar contexto com token
      await apiContext.dispose();
      const authenticatedContext = await playwright.request.newContext({
        baseURL: API_BASE_URL,
        extraHTTPHeaders: {
          Authorization: `Bearer ${access_token}`,
        },
      });
      await use(authenticatedContext);
      await authenticatedContext.dispose();
    } else {
      await use(apiContext);
      await apiContext.dispose();
    }
  },
});

export { expect };

// --- Helpers ---

/** Mock da resposta de login com sucesso */
export async function mockLoginSuccess(page: Page) {
  await page.route('**/api/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'fake-jwt-token-for-testing',
        token_type: 'bearer',
      }),
    });
  });
}

/** Mock da resposta de login com falha */
export async function mockLoginFailure(page: Page) {
  await page.route('**/api/auth/login', async (route) => {
    await route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: 'Credenciais inválidas',
      }),
    });
  });
}

/** Mock dos dados do dashboard */
export async function mockDashboardData(page: Page) {
  await page.route('**/api/dashboard**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_processos: 150,
        processos_ativos: 42,
        alertas_pendentes: 7,
        ultimas_atualizacoes: 23,
      }),
    });
  });

  await page.route('**/api/resultados/recentes**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 1,
          numero_processo: '0001234-56.2024.8.26.0100',
          titulo: 'Processo Teste 1',
          status: 'analisado',
          data: '2024-12-01T10:00:00',
        },
        {
          id: 2,
          numero_processo: '0009876-54.2024.8.26.0100',
          titulo: 'Processo Teste 2',
          status: 'pendente',
          data: '2024-12-02T14:30:00',
        },
      ]),
    });
  });
}

/** Mock dos dados de processo */
export async function mockProcessoData(page: Page, numero?: string) {
  const processoNumero = numero || '0001234-56.2024.8.26.0100';

  await page.route('**/api/processo/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        numero: processoNumero,
        classe: 'Procedimento Comum Cível',
        assunto: 'Indenização por Dano Moral',
        tribunal: 'TJSP',
        vara: '1ª Vara Cível',
        status: 'Em andamento',
        partes: {
          autor: 'João da Silva',
          reu: 'Empresa XYZ Ltda',
        },
        resumo: 'Ação de indenização por dano moral decorrente de falha na prestação de serviço.',
        timeline: [
          {
            data: '2024-01-15T00:00:00',
            tipo: 'Distribuição',
            descricao: 'Processo distribuído à 1ª Vara Cível',
          },
          {
            data: '2024-02-10T00:00:00',
            tipo: 'Citação',
            descricao: 'Réu citado por oficial de justiça',
          },
          {
            data: '2024-03-15T00:00:00',
            tipo: 'Contestação',
            descricao: 'Apresentação de contestação pelo réu',
          },
        ],
        riscos: [
          { nivel: 'alto', descricao: 'Prazo de recurso próximo do vencimento', cor: 'red' },
          { nivel: 'medio', descricao: 'Pendência de juntada de documentos', cor: 'yellow' },
          { nivel: 'baixo', descricao: 'Processo dentro do prazo médio', cor: 'green' },
        ],
      }),
    });
  });
}

/** Mock dos dados de monitores */
export async function mockMonitorData(page: Page) {
  await page.route('**/api/monitor**', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 1,
            numero_processo: '0001234-56.2024.8.26.0100',
            descricao: 'Monitor Processo Civil',
            ativo: true,
            criado_em: '2024-11-01T08:00:00',
          },
          {
            id: 2,
            numero_processo: '0009876-54.2024.8.26.0100',
            descricao: 'Monitor Processo Trabalhista',
            ativo: false,
            criado_em: '2024-11-15T10:00:00',
          },
        ]),
      });
    } else if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 3,
          numero_processo: '0005555-12.2024.8.26.0100',
          descricao: 'Novo Monitor',
          ativo: true,
          criado_em: new Date().toISOString(),
        }),
      });
    }
  });
}

/** Mock dos dados de busca unificada */
export async function mockBuscaData(page: Page) {
  await page.route('**/api/busca**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        resultados: [
          {
            id: 1,
            tipo: 'processo',
            fonte: 'DataJud',
            titulo: 'Processo 0001234-56.2024.8.26.0100',
            descricao: 'Indenização por Dano Moral',
            relevancia: 0.95,
          },
          {
            id: 2,
            tipo: 'jurisprudencia',
            fonte: 'DJEN',
            titulo: 'Acórdão - Dano Moral em Relação de Consumo',
            descricao: 'Recurso parcialmente provido',
            relevancia: 0.87,
          },
          {
            id: 3,
            tipo: 'processo',
            fonte: 'DataJud',
            titulo: 'Processo 0007777-88.2024.8.26.0100',
            descricao: 'Cobrança Indevida',
            relevancia: 0.72,
          },
        ],
        total: 3,
      }),
    });
  });
}

/** Simular autenticação via localStorage/cookies */
export async function setAuthState(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'fake-jwt-token-for-testing');
    localStorage.setItem('user', JSON.stringify({ username: 'admin', role: 'admin' }));
  });
}

/** Limpar estado de autenticação */
export async function clearAuthState(page: Page) {
  await page.addInitScript(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  });
}
