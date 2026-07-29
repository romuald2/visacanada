import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { CriticalBadge } from "./CriticalBadge";
import type { UpcomingAlert } from "@/lib/types";

function alert(overrides: Partial<UpcomingAlert> = {}): UpcomingAlert {
  return {
    id: 1,
    dossier_id: 10,
    alert_type: "passport_expiring",
    severity: "critical",
    title: "T",
    message: "",
    days_left: 1,
    is_notified: false,
    created_at: null,
    ...overrides,
  };
}

describe("CriticalBadge", () => {
  it("renders nothing when there are no critical items", () => {
    const { container } = render(
      <CriticalBadge items={[alert({ severity: "warning" })]} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("counts critical items and pluralizes", () => {
    render(
      <CriticalBadge
        items={[alert({ id: 1 }), alert({ id: 2 }), alert({ id: 3, severity: "info" })]}
      />,
    );
    const badge = screen.getByRole("status");
    expect(badge).toHaveTextContent("2 critiques");
  });

  it("uses the singular for a single critical item", () => {
    render(<CriticalBadge items={[alert()]} />);
    expect(screen.getByRole("status")).toHaveTextContent("1 critique");
  });
});
