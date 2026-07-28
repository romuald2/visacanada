import { test, expect } from "@playwright/test";

/**
 * Smoke tests E2E de la page d'accueil.
 *
 * Ces tests valident le rendu de base et servent de fondation à la suite E2E.
 * À étendre au fur et à mesure de l'ajout des parcours (connexion, tableau de
 * bord, portail candidat, etc.).
 */
test.describe("Page d'accueil", () => {
  test("affiche le titre et la description", async ({ page }) => {
    await page.goto("/");

    await expect(
      page.getByRole("heading", { name: /VisaCanada/i })
    ).toBeVisible();

    await expect(
      page.getByText(/Plateforme IA de gestion d'immigration/i)
    ).toBeVisible();
  });

  test("propose les liens Documentation API et GitHub", async ({ page }) => {
    await page.goto("/");

    const apiLink = page.getByRole("link", { name: /API Documentation/i });
    await expect(apiLink).toBeVisible();
    await expect(apiLink).toHaveAttribute("href", "/docs");

    const githubLink = page.getByRole("link", { name: /GitHub/i });
    await expect(githubLink).toHaveAttribute(
      "href",
      "https://github.com/romuald2/visacanada"
    );
  });

  test("n'a pas d'erreur console critique au chargement", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await page.goto("/");
    await expect(page.getByRole("heading", { name: /VisaCanada/i })).toBeVisible();

    expect(errors).toEqual([]);
  });
});
