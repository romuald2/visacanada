import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DossierList } from "./DossierList";
import { dossierStatusLabel, dossierStatusClasses } from "@/lib/dossiers";
import type { Dossier } from "@/lib/types";

function dossier(overrides: Partial<Dossier> = {}): Dossier {
  return {
    id: 1,
    candidate_id: 5,
    program_id: 2,
    assigned_to: 7,
    status: "en_cours",
    compliance_score: 82.4,
    reference_number: "EE-2026-001",
    notes: null,
    submitted_at: null,
    decision_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("dossiers helpers", () => {
  it("labels statuses in French", () => {
    expect(dossierStatusLabel("documents_manquants")).toBe("Documents manquants");
    expect(dossierStatusLabel("approuve")).toBe("Approuvé");
  });

  it("styles approved vs refused differently", () => {
    expect(dossierStatusClasses("approuve")).toContain("emerald");
    expect(dossierStatusClasses("refuse")).toContain("destructive");
  });
});

describe("DossierList", () => {
  it("renders rows with reference, status and compliance", () => {
    render(
      <DossierList items={[dossier()]} total={1} page={1} pages={1} />,
    );
    expect(screen.getByText("EE-2026-001")).toBeInTheDocument();
    expect(screen.getByText("En cours")).toBeInTheDocument();
    expect(screen.getByText("82 %")).toBeInTheDocument();
  });

  it("falls back to #id and dashes for missing fields", () => {
    render(
      <DossierList
        items={[dossier({ reference_number: null, compliance_score: null, assigned_to: null })]}
        total={1}
        page={1}
        pages={1}
      />,
    );
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText("Non assigné")).toBeInTheDocument();
  });

  it("shows the loading state", () => {
    render(<DossierList items={[]} total={0} page={1} pages={0} loading />);
    expect(screen.getByText("Chargement…")).toBeInTheDocument();
  });

  it("shows the error state", () => {
    render(
      <DossierList items={[]} total={0} page={1} pages={0} error="Boom" />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Boom");
  });

  it("shows the empty state", () => {
    render(<DossierList items={[]} total={0} page={1} pages={0} />);
    expect(screen.getByText("Aucun dossier.")).toBeInTheDocument();
  });

  it("paginates via the callback", () => {
    const onPageChange = vi.fn();
    render(
      <DossierList
        items={[dossier()]}
        total={30}
        page={2}
        pages={3}
        onPageChange={onPageChange}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Suivant" }));
    expect(onPageChange).toHaveBeenCalledWith(3);
    fireEvent.click(screen.getByRole("button", { name: "Précédent" }));
    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("disables previous on the first page", () => {
    render(
      <DossierList items={[dossier()]} total={30} page={1} pages={3} />,
    );
    expect(screen.getByRole("button", { name: "Précédent" })).toBeDisabled();
  });
});
