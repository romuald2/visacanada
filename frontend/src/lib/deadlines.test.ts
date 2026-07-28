import { describe, it, expect } from "vitest";
import {
  alertTypeLabel,
  countBySeverity,
  formatDaysLeft,
  severityBadgeClasses,
  sortByUrgency,
} from "./deadlines";
import type { UpcomingAlert } from "./types";

function alert(overrides: Partial<UpcomingAlert> = {}): UpcomingAlert {
  return {
    id: 1,
    dossier_id: 10,
    alert_type: "passport_expiring",
    severity: "info",
    title: "Test",
    message: "",
    days_left: 5,
    is_notified: false,
    created_at: null,
    ...overrides,
  };
}

describe("alertTypeLabel", () => {
  it("maps known types to French labels", () => {
    expect(alertTypeLabel("passport_expiring")).toBe("Passeport");
    expect(alertTypeLabel("ita_response")).toBe("Reponse ITA");
    expect(alertTypeLabel("permit_expiring")).toBe("Permis");
  });

  it("falls back to the raw type when unknown", () => {
    // @ts-expect-error deliberately passing an unknown type
    expect(alertTypeLabel("something_new")).toBe("something_new");
  });
});

describe("severityBadgeClasses", () => {
  it("uses the destructive token for critical", () => {
    expect(severityBadgeClasses("critical")).toContain("bg-destructive");
  });

  it("uses amber for warning and secondary for info", () => {
    expect(severityBadgeClasses("warning")).toContain("amber");
    expect(severityBadgeClasses("info")).toContain("secondary");
  });
});

describe("formatDaysLeft", () => {
  it("handles null/undefined as empty", () => {
    expect(formatDaysLeft(null)).toBe("");
  });

  it("says today for zero", () => {
    expect(formatDaysLeft(0)).toBe("Aujourd'hui");
  });

  it("pluralizes future days", () => {
    expect(formatDaysLeft(1)).toBe("Dans 1 jour");
    expect(formatDaysLeft(3)).toBe("Dans 3 jours");
  });

  it("describes overdue items", () => {
    expect(formatDaysLeft(-1)).toBe("En retard de 1 jour");
    expect(formatDaysLeft(-4)).toBe("En retard de 4 jours");
  });
});

describe("countBySeverity", () => {
  it("counts each bucket", () => {
    const items = [
      alert({ id: 1, severity: "critical" }),
      alert({ id: 2, severity: "critical" }),
      alert({ id: 3, severity: "warning" }),
      alert({ id: 4, severity: "info" }),
    ];
    expect(countBySeverity(items)).toEqual({
      critical: 2,
      warning: 1,
      info: 1,
    });
  });

  it("returns zeros for an empty list", () => {
    expect(countBySeverity([])).toEqual({ critical: 0, warning: 0, info: 0 });
  });
});

describe("sortByUrgency", () => {
  it("orders critical first, then by days_left ascending", () => {
    const items = [
      alert({ id: 1, severity: "info", days_left: 2 }),
      alert({ id: 2, severity: "critical", days_left: 10 }),
      alert({ id: 3, severity: "warning", days_left: 1 }),
      alert({ id: 4, severity: "critical", days_left: 3 }),
    ];
    expect(sortByUrgency(items).map((a) => a.id)).toEqual([4, 2, 3, 1]);
  });

  it("treats null days_left as last within a severity", () => {
    const items = [
      alert({ id: 1, severity: "info", days_left: null }),
      alert({ id: 2, severity: "info", days_left: 5 }),
    ];
    expect(sortByUrgency(items).map((a) => a.id)).toEqual([2, 1]);
  });

  it("does not mutate the input", () => {
    const items = [
      alert({ id: 1, severity: "info" }),
      alert({ id: 2, severity: "critical" }),
    ];
    const original = items.map((a) => a.id);
    sortByUrgency(items);
    expect(items.map((a) => a.id)).toEqual(original);
  });
});
