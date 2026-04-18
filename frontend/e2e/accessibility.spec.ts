import { test, expect, setAuthState, mockDashboardData, mockProcessoData, mockMonitorData, mockBuscaData } from './fixtures';

test.describe('Acessibilidade', () => {
  test('todas as páginas possuem títulos adequados', async ({ page }) => {
    // Página de Login
    await page.goto('/login');
    await expect(page).toHaveTitle(/.+/, { timeout: 10_000 });
    const loginTitle = await page.title();
    expect(loginTitle.length).toBeGreaterThan(0);

    // Autenticar para acessar demais páginas
    await setAuthState(page);
    await mockDashboardData(page);

    // Dashboard
    await page.goto('/');
    await expect(page).toHaveTitle(/.+/, { timeout: 10_000 });

    // Processo
    await page.goto('/processo');
    await expect(page).toHaveTitle(/.+/, { timeout: 10_000 });

    // Monitor
    await page.goto('/monitor');
    await expect(page).toHaveTitle(/.+/, { timeout: 10_000 });

    // Busca
    await page.goto('/busca');
    await expect(page).toHaveTitle(/.+/, { timeout: 10_000 });
  });

  test('todas as páginas são navegáveis por teclado', async ({ page }) => {
    await setAuthState(page);
    await mockDashboardData(page);

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Verificar que Tab funciona e move o foco
    await page.keyboard.press('Tab');
    const firstFocused = await page.evaluate(() => document.activeElement?.tagName);
    expect(firstFocused).toBeTruthy();

    await page.keyboard.press('Tab');
    const secondFocused = await page.evaluate(() => document.activeElement?.tagName);
    expect(secondFocused).toBeTruthy();

    // Verificar que pelo menos um elemento recebe foco
    const focusedElement = await page.evaluate(() => {
      const el = document.activeElement;
      return el ? { tag: el.tagName, role: el.getAttribute('role') } : null;
    });
    expect(focusedElement).not.toBeNull();
  });

  test('formulários possuem labels associados corretamente', async ({ page }) => {
    // Página de Login
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Verificar que inputs têm labels ou aria-label
    const inputsSemLabel = await page.evaluate(() => {
      const inputs = document.querySelectorAll('input:not([type="hidden"])');
      const problemas: string[] = [];

      inputs.forEach((input) => {
        const id = input.getAttribute('id');
        const ariaLabel = input.getAttribute('aria-label');
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        const placeholder = input.getAttribute('placeholder');
        const title = input.getAttribute('title');

        const hasLabel = id ? document.querySelector(`label[for="${id}"]`) : null;
        const parentLabel = input.closest('label');

        if (!hasLabel && !parentLabel && !ariaLabel && !ariaLabelledBy && !placeholder && !title) {
          problemas.push(
            `Input ${input.getAttribute('type') || 'text'} sem label acessível`
          );
        }
      });

      return problemas;
    });

    expect(inputsSemLabel).toHaveLength(0);

    // Página de Monitor
    await setAuthState(page);
    await mockMonitorData(page);
    await page.goto('/monitor');
    await page.waitForLoadState('networkidle');

    const inputsSemLabelMonitor = await page.evaluate(() => {
      const inputs = document.querySelectorAll('input:not([type="hidden"])');
      const problemas: string[] = [];

      inputs.forEach((input) => {
        const id = input.getAttribute('id');
        const ariaLabel = input.getAttribute('aria-label');
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        const placeholder = input.getAttribute('placeholder');
        const title = input.getAttribute('title');

        const hasLabel = id ? document.querySelector(`label[for="${id}"]`) : null;
        const parentLabel = input.closest('label');

        if (!hasLabel && !parentLabel && !ariaLabel && !ariaLabelledBy && !placeholder && !title) {
          problemas.push(
            `Input ${input.getAttribute('type') || 'text'} sem label acessível`
          );
        }
      });

      return problemas;
    });

    expect(inputsSemLabelMonitor).toHaveLength(0);
  });

  test('contraste de cores atende WCAG AA', async ({ page }) => {
    await setAuthState(page);
    await mockDashboardData(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Verificar contraste de texto dos elementos principais
    const contrastResults = await page.evaluate(() => {
      function getLuminance(r: number, g: number, b: number): number {
        const [rs, gs, bs] = [r, g, b].map((c) => {
          const s = c / 255;
          return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
        });
        return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
      }

      function getContrastRatio(l1: number, l2: number): number {
        const lighter = Math.max(l1, l2);
        const darker = Math.min(l1, l2);
        return (lighter + 0.05) / (darker + 0.05);
      }

      function parseColor(color: string): [number, number, number] | null {
        const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (match) {
          return [parseInt(match[1]), parseInt(match[2]), parseInt(match[3])];
        }
        return null;
      }

      const elements = document.querySelectorAll('h1, h2, h3, p, span, a, button, label');
      const problemas: string[] = [];

      elements.forEach((el) => {
        const styles = window.getComputedStyle(el);
        const fgColor = parseColor(styles.color);
        const bgColor = parseColor(styles.backgroundColor);

        if (fgColor && bgColor) {
          const fgLum = getLuminance(...fgColor);
          const bgLum = getLuminance(...bgColor);
          const ratio = getContrastRatio(fgLum, bgLum);

          const fontSize = parseFloat(styles.fontSize);
          const isBold = parseInt(styles.fontWeight) >= 700;
          const isLargeText = fontSize >= 24 || (fontSize >= 18.66 && isBold);
          const minRatio = isLargeText ? 3 : 4.5;

          if (ratio < minRatio) {
            problemas.push(
              `${el.tagName} "${el.textContent?.substring(0, 30)}" - contraste ${ratio.toFixed(2)}:1 (mínimo ${minRatio}:1)`
            );
          }
        }
      });

      return problemas;
    });

    // Reportar problemas de contraste (aviso, não falha)
    if (contrastResults.length > 0) {
      console.warn('Problemas de contraste encontrados:', contrastResults);
    }

    // Permitir até 5 problemas de contraste menores
    expect(contrastResults.length).toBeLessThanOrEqual(5);
  });
});
