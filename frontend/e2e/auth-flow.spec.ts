import { test, expect } from "@playwright/test";

/**
 * Smoke tests E2E du parcours interne.
 *
 * Les appels au backend sont interceptés (page.route) pour que la suite reste
 * autonome — pas besoin d'un backend en marche. On valide le routage, la
 * redirection d'entrée et le parcours de connexion jusqu'au tableau de bord.
 */

test.describe("Entrée de l'application", () => {
  test("la racine redirige vers /login quand on n'est pas connecté", async ({
    page,
  }) => {
    await page.goto("/");
    // Generous timeout: the dev server compiles routes on first hit, so the
    // client-side redirect can land after the default 5s expectation window.
    await expect(page).toHaveURL(/\/login$/, { timeout: 20_000 });
    await expect(
      page.getByRole("heading", { name: /VisaCanada/i }),
    ).toBeVisible();
  });

  test("affiche une erreur sur identifiants invalides", async ({ page }) => {
    await page.route("**/auth/login", (route) =>
      route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Email ou mot de passe incorrect" }),
      }),
    );

    await page.goto("/login");
    await page.getByLabel("Email").fill("mauvais@cabinet.ca");
    await page.getByLabel("Mot de passe").fill("mauvaispass");
    await page.getByRole("button", { name: /se connecter/i }).click();

    await expect(
      page.getByText("Email ou mot de passe incorrect"),
    ).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);
  });

  test("connexion réussie → tableau de bord", async ({ page }) => {
    await page.route("**/auth/login", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: "tok",
          refresh_token: "reftok",
          token_type: "bearer",
        }),
      }),
    );
    await page.route("**/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 1,
          email: "consultant@cabinet.ca",
          full_name: "Consultant Test",
          role: "consultant",
          is_active: true,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }),
      }),
    );
    await page.route("**/alerts/upcoming**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ count: 0, window_days: 30, items: [] }),
      }),
    );
    await page.route("**/dossiers/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          size: 10,
          pages: 0,
        }),
      }),
    );

    await page.goto("/login");
    await page.getByLabel("Email").fill("consultant@cabinet.ca");
    await page.getByLabel("Mot de passe").fill("bonmotdepasse");
    await page.getByRole("button", { name: /se connecter/i }).click();

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(
      page.getByRole("heading", { name: "Tableau de bord" }),
    ).toBeVisible();
    await expect(page.getByText("Consultant Test")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "30 prochains jours" }),
    ).toBeVisible();
  });
});
