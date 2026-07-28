/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    // Les tests E2E Playwright (dossier e2e/) sont exécutés séparément via
    // `npm run test:e2e` et ne doivent pas être ramassés par Vitest.
    exclude: ["e2e/**", "node_modules/**", "dist/**", ".next/**"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
