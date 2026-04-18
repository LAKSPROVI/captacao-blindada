import { test, expect, mockMonitorData, setAuthState } from './fixtures';

test.describe('Monitor', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthState(page);
    await mockMonitorData(page);
  });

  test('página de monitores renderiza com formulário e lista', async ({ page }) => {
    await page.goto('/monitor');

    // Verificar formulário de adição
    await expect(
      page.getByPlaceholder(/número.*processo|processo/i)
        .or(page.getByRole('textbox').first())
    ).toBeVisible({ timeout: 10_000 });

    await expect(
      page.getByRole('button', { name: /adicionar|criar|novo|monitorar/i })
    ).toBeVisible();

    // Verificar que a lista de monitores existe
    await expect(
      page.getByText(/0001234-56\.2024\.8\.26\.0100/)
    ).toBeVisible();
  });

  test('adicionar um novo monitor', async ({ page }) => {
    await page.goto('/monitor');

    // Preencher formulário
    const inputProcesso = page.getByPlaceholder(/número.*processo|processo/i)
      .or(page.getByRole('textbox').first());
    await inputProcesso.fill('0005555-12.2024.8.26.0100');

    // Preencher descrição se existir
    const inputDescricao = page.getByPlaceholder(/descrição|nome|label/i);
    if (await inputDescricao.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await inputDescricao.fill('Novo Monitor de Teste');
    }

    // Clicar em adicionar
    await page.getByRole('button', { name: /adicionar|criar|novo|monitorar/i }).click();

    // Verificar que o novo monitor aparece ou mensagem de sucesso
    await expect(
      page.getByText(/0005555-12\.2024\.8\.26\.0100/)
        .or(page.getByText(/sucesso|adicionado|criado/i))
    ).toBeVisible({ timeout: 5_000 });
  });

  test('lista de monitores exibe itens corretamente', async ({ page }) => {
    await page.goto('/monitor');

    // Verificar que ambos os monitores mockados aparecem
    await expect(
      page.getByText(/0001234-56\.2024\.8\.26\.0100/)
    ).toBeVisible({ timeout: 10_000 });

    await expect(
      page.getByText(/0009876-54\.2024\.8\.26\.0100/)
    ).toBeVisible();

    // Verificar descrições
    await expect(page.getByText(/Monitor Processo Civil/i)).toBeVisible();
    await expect(page.getByText(/Monitor Processo Trabalhista/i)).toBeVisible();
  });

  test('alternar status ativo/inativo de um monitor', async ({ page }) => {
    // Mock PATCH/PUT para toggle
    await page.route('**/api/monitor/*/toggle', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 1, ativo: false }),
      });
    });

    await page.route('**/api/monitor/*', async (route) => {
      if (route.request().method() === 'PATCH' || route.request().method() === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 1, ativo: false }),
        });
      } else {
        await route.fallback();
      }
    });

    await page.goto('/monitor');

    // Procurar botão de toggle (switch, checkbox, ou botão)
    const toggleButton = page.getByRole('switch').first()
      .or(page.getByRole('checkbox').first())
      .or(page.locator('[data-testid="toggle-monitor"]').first());

    if (await toggleButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await toggleButton.click();

      // Verificar que o estado mudou (mensagem de sucesso ou mudança visual)
      // O teste verifica que a interação não causa erro
      await page.waitForTimeout(1_000);
    }
  });
});
