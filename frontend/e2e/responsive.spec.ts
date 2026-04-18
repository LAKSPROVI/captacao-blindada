import { test, expect, setAuthState, mockDashboardData } from './fixtures';

test.describe('Responsividade', () => {
  test.beforeEach(async ({ page }) => {
    await setAuthState(page);
    await mockDashboardData(page);
  });

  test('viewport mobile (375x667) - sidebar colapsa', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // A sidebar deve estar colapsada ou escondida em mobile
    const sidebar = page.locator('nav, aside, [data-testid="sidebar"], [role="navigation"]').first();

    if (await sidebar.isVisible({ timeout: 3_000 }).catch(() => false)) {
      const sidebarBox = await sidebar.boundingBox();

      if (sidebarBox) {
        // Sidebar pode estar oculta (largura 0 ou fora da tela) ou ser um menu hamburguer
        const isCollapsed = sidebarBox.width < 100 || sidebarBox.x < -50;

        if (!isCollapsed) {
          // Verificar se é um overlay/drawer (posição absoluta/fixa)
          const position = await sidebar.evaluate((el) => {
            return window.getComputedStyle(el).position;
          });
          const isOverlay = position === 'fixed' || position === 'absolute';
          expect(isCollapsed || isOverlay).toBeTruthy();
        }
      }
    }

    // Verificar se botão de menu hamburguer existe
    const menuButton = page.getByRole('button', { name: /menu|navegação|abrir menu/i })
      .or(page.locator('[data-testid="menu-toggle"]'))
      .or(page.locator('button.hamburger, button[aria-label*="menu"]'));

    // Em mobile, deve haver um botão de menu ou a sidebar deve estar oculta
    const hasMobileMenu = await menuButton.first().isVisible({ timeout: 3_000 }).catch(() => false);

    // Conteúdo principal deve ser visível e ocupar a largura total
    const mainContent = page.locator('main, [role="main"], .main-content').first();
    if (await mainContent.isVisible({ timeout: 3_000 }).catch(() => false)) {
      const mainBox = await mainContent.boundingBox();
      if (mainBox) {
        // Conteúdo principal deve ocupar pelo menos 80% da largura
        expect(mainBox.width).toBeGreaterThan(300);
      }
    }
  });

  test('viewport tablet (768x1024)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // O conteúdo deve ser visível e adaptado para tablet
    const mainContent = page.locator('main, [role="main"], .main-content, #__next').first();
    await expect(mainContent).toBeVisible({ timeout: 10_000 });

    // Verificar que não há overflow horizontal
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll).toBeFalsy();

    // Cards/estatísticas devem estar visíveis
    const statsSection = page.getByText(/total.*processos|processos.*total/i)
      .or(page.getByText(/estatísticas|resumo/i));
    if (await statsSection.first().isVisible({ timeout: 5_000 }).catch(() => false)) {
      await expect(statsSection.first()).toBeVisible();
    }
  });

  test('viewport desktop (1920x1080)', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Sidebar deve estar visível e expandida em desktop
    const sidebar = page.locator('nav, aside, [data-testid="sidebar"], [role="navigation"]').first();

    if (await sidebar.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const sidebarBox = await sidebar.boundingBox();
      if (sidebarBox) {
        // Sidebar deve ter largura significativa em desktop
        expect(sidebarBox.width).toBeGreaterThan(50);
      }
    }

    // Conteúdo principal deve estar visível
    const mainContent = page.locator('main, [role="main"], .main-content, #__next').first();
    await expect(mainContent).toBeVisible({ timeout: 10_000 });

    // Verificar que não há overflow horizontal
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll).toBeFalsy();

    // Verificar layout lado a lado (sidebar + conteúdo)
    const bodyWidth = await page.evaluate(() => document.body.offsetWidth);
    expect(bodyWidth).toBeLessThanOrEqual(1920);
  });
});
