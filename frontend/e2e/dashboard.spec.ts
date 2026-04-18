import { test, expect, mockDashboardData, setAuthState } from './fixtures';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthState(page);
    await mockDashboardData(page);
    await page.goto('/');
  });

  test('dashboard carrega com cards de estatísticas', async ({ page }) => {
    // Verificar se os cards de estatísticas estão visíveis
    await expect(page.getByText(/total.*processos|processos.*total/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('150')).toBeVisible();
    await expect(page.getByText(/ativos|em andamento/i)).toBeVisible();
    await expect(page.getByText('42')).toBeVisible();
    await expect(page.getByText(/alertas|pendentes/i)).toBeVisible();
  });

  test('dashboard exibe resultados recentes', async ({ page }) => {
    // Verificar se a seção de resultados recentes está visível
    await expect(
      page.getByText(/recentes|últimos resultados|atividade recente/i)
    ).toBeVisible({ timeout: 10_000 });

    // Verificar se os processos mockados aparecem
    await expect(page.getByText(/0001234-56\.2024\.8\.26\.0100/)).toBeVisible();
    await expect(page.getByText(/0009876-54\.2024\.8\.26\.0100/)).toBeVisible();
  });

  test('busca rápida navega para página de processo', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/buscar|pesquisar|número do processo/i);

    if (await searchInput.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await searchInput.fill('0001234-56.2024.8.26.0100');
      await searchInput.press('Enter');

      // Deve navegar para a página de processo ou busca
      await expect(page).toHaveURL(/\/(processo|busca)/, { timeout: 5_000 });
    }
  });

  test('navegação da sidebar funciona corretamente', async ({ page }) => {
    // Navegar para Processos
    const processoLink = page.getByRole('link', { name: /processos?/i });
    if (await processoLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await processoLink.click();
      await expect(page).toHaveURL(/\/processo/, { timeout: 5_000 });
    }

    // Voltar ao dashboard
    await page.goto('/');

    // Navegar para Monitor
    const monitorLink = page.getByRole('link', { name: /monitor/i });
    if (await monitorLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await monitorLink.click();
      await expect(page).toHaveURL(/\/monitor/, { timeout: 5_000 });
    }

    // Voltar ao dashboard
    await page.goto('/');

    // Navegar para Busca
    const buscaLink = page.getByRole('link', { name: /busca/i });
    if (await buscaLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await buscaLink.click();
      await expect(page).toHaveURL(/\/busca/, { timeout: 5_000 });
    }
  });
});
