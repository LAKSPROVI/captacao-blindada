import { test, expect, mockLoginSuccess, mockLoginFailure, setAuthState, clearAuthState } from './fixtures';

test.describe('Autenticação', () => {
  test('página de login renderiza corretamente', async ({ page }) => {
    await page.goto('/login');

    // Verificar elementos do formulário
    await expect(page.getByPlaceholder(/usuário|username|email/i)).toBeVisible();
    await expect(page.getByPlaceholder(/senha|password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /entrar|login|acessar/i })).toBeVisible();
  });

  test('login com credenciais válidas redireciona para o dashboard', async ({ page }) => {
    await mockLoginSuccess(page);
    await page.goto('/login');

    await page.getByPlaceholder(/usuário|username|email/i).fill('admin');
    await page.getByPlaceholder(/senha|password/i).fill('admin123');
    await page.getByRole('button', { name: /entrar|login|acessar/i }).click();

    // Aguardar redirecionamento para dashboard
    await expect(page).toHaveURL('/', { timeout: 10_000 });
  });

  test('login com credenciais inválidas exibe mensagem de erro', async ({ page }) => {
    await mockLoginFailure(page);
    await page.goto('/login');

    await page.getByPlaceholder(/usuário|username|email/i).fill('usuario_invalido');
    await page.getByPlaceholder(/senha|password/i).fill('senha_errada');
    await page.getByRole('button', { name: /entrar|login|acessar/i }).click();

    // Verificar mensagem de erro
    await expect(
      page.getByText(/credenciais inválidas|erro|falha|incorret/i)
    ).toBeVisible({ timeout: 5_000 });

    // Deve permanecer na página de login
    await expect(page).toHaveURL(/\/login/);
  });

  test('logout limpa a sessão do usuário', async ({ page }) => {
    // Configurar estado autenticado
    await setAuthState(page);
    await mockLoginSuccess(page);
    await page.goto('/');

    // Clicar no botão de logout
    const logoutButton = page.getByRole('button', { name: /sair|logout|desconectar/i });
    if (await logoutButton.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await logoutButton.click();
    } else {
      // Tentar menu de usuário primeiro
      const userMenu = page.getByRole('button', { name: /perfil|usuário|menu/i });
      if (await userMenu.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await userMenu.click();
        await page.getByRole('menuitem', { name: /sair|logout/i }).click();
      }
    }

    // Verificar redirecionamento para login
    await expect(page).toHaveURL(/\/login/, { timeout: 5_000 });
  });

  test('páginas protegidas redirecionam para login quando não autenticado', async ({ page }) => {
    await clearAuthState(page);

    const protectedRoutes = ['/', '/processo', '/monitor', '/busca'];

    for (const route of protectedRoutes) {
      await page.goto(route);
      // Deve redirecionar para login
      await expect(page).toHaveURL(/\/login/, { timeout: 5_000 });
    }
  });
});
