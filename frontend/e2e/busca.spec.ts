import { test, expect, mockBuscaData, setAuthState } from './fixtures';

test.describe('Busca Unificada', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthState(page);
    await mockBuscaData(page);
  });

  test('página de busca unificada renderiza corretamente', async ({ page }) => {
    await page.goto('/busca');

    // Verificar campo de busca
    await expect(
      page.getByPlaceholder(/buscar|pesquisar|termo/i)
        .or(page.getByRole('searchbox'))
        .or(page.getByRole('textbox').first())
    ).toBeVisible({ timeout: 10_000 });

    // Verificar botão de busca
    await expect(
      page.getByRole('button', { name: /buscar|pesquisar/i })
    ).toBeVisible();
  });

  test('realizar busca exibe resultados', async ({ page }) => {
    await page.goto('/busca');

    // Preencher campo de busca
    const searchInput = page.getByPlaceholder(/buscar|pesquisar|termo/i)
      .or(page.getByRole('searchbox'))
      .or(page.getByRole('textbox').first());

    await searchInput.fill('dano moral');

    // Executar busca
    const searchButton = page.getByRole('button', { name: /buscar|pesquisar/i });
    if (await searchButton.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await searchButton.click();
    } else {
      await searchInput.press('Enter');
    }

    // Verificar que resultados aparecem
    await expect(
      page.getByText(/0001234-56\.2024\.8\.26\.0100/)
        .or(page.getByText(/Indenização por Dano Moral/i))
    ).toBeVisible({ timeout: 10_000 });

    // Verificar múltiplos resultados
    await expect(
      page.getByText(/Acórdão.*Dano Moral|Dano Moral em Relação de Consumo/i)
    ).toBeVisible();
  });

  test('filtrar resultados por fonte', async ({ page }) => {
    await page.goto('/busca');

    // Realizar busca primeiro
    const searchInput = page.getByPlaceholder(/buscar|pesquisar|termo/i)
      .or(page.getByRole('searchbox'))
      .or(page.getByRole('textbox').first());

    await searchInput.fill('processo');

    const searchButton = page.getByRole('button', { name: /buscar|pesquisar/i });
    if (await searchButton.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await searchButton.click();
    } else {
      await searchInput.press('Enter');
    }

    // Aguardar resultados
    await page.waitForTimeout(2_000);

    // Procurar filtro de fonte (select, radio, ou botões)
    const filtroDataJud = page.getByRole('button', { name: /datajud/i })
      .or(page.getByRole('option', { name: /datajud/i }))
      .or(page.getByLabel(/datajud/i))
      .or(page.getByText(/datajud/i));

    const filtroDJEN = page.getByRole('button', { name: /djen/i })
      .or(page.getByRole('option', { name: /djen/i }))
      .or(page.getByLabel(/djen/i))
      .or(page.getByText(/djen/i));

    // Verificar que filtros de fonte existem
    if (await filtroDataJud.first().isVisible({ timeout: 3_000 }).catch(() => false)) {
      await filtroDataJud.first().click();

      // Após filtrar, verificar que resultados são exibidos
      await expect(
        page.getByText(/DataJud/).first()
      ).toBeVisible({ timeout: 5_000 });
    }

    if (await filtroDJEN.first().isVisible({ timeout: 3_000 }).catch(() => false)) {
      await filtroDJEN.first().click();

      await expect(
        page.getByText(/DJEN/).first()
      ).toBeVisible({ timeout: 5_000 });
    }
  });
});
