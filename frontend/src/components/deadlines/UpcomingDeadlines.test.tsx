import { render, screen, within } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { UpcomingDeadlines } from "./UpcomingDeadlines";
import { DeadlineCard } from "./DeadlineCard";
import { SeverityCounters } from "./SeverityCounters";
import type { UpcomingAlert } from "@/lib/types";

function alert(overrides: Partial<UpcomingAlert> = {}): UpcomingAlert {
  return {
    id: 1,
    dossier_id: 10,
    alert_type: "passport_expiring",
    severity: "info",
    title: "Passeport de Jean",
    message: "Expire bientot",
    days_left: 5,
    is_notified: false,
    created_at: null,
    ...overrides,
  };
}

describe("SeverityCounters", () => {
  it("renders a count per severity", () => {
    const items = [
      alert({ id: 1, severity: "critical" }),
      alert({ id: 2, severity: "critical" }),
      alert({ id: 3, severity: "warning" }),
    ];
    render(<SeverityCounters items={items} />);
    const group = screen.getByRole("group", { name: /severite/i });
    expect(within(group).getByText("2")).toBeInTheDocument();
    expect(within(group).getByText("Critique")).toBeInTheDocument();
    expect(within(group).getByText("Avertissement")).toBeInTheDocument();
  });
});

describe("DeadlineCard", () => {
  it("shows title, type label and severity", () => {
    render(<DeadlineCard alert={alert({ severity: "critical" })} />);
    expect(screen.getByText("Passeport de Jean")).toBeInTheDocument();
    expect(screen.getByText("Passeport")).toBeInTheDocument();
    expect(screen.getByText("Critique")).toBeInTheDocument();
  });

  it("renders the days-left phrase", () => {
    render(<DeadlineCard alert={alert({ days_left: 3 })} />);
    expect(screen.getByText("Dans 3 jours")).toBeInTheDocument();
  });

  it("flags overdue items", () => {
    render(<DeadlineCard alert={alert({ days_left: -2 })} />);
    expect(screen.getByText("En retard de 2 jours")).toBeInTheDocument();
  });
});

describe("UpcomingDeadlines", () => {
  it("renders the window heading and count", () => {
    render(<UpcomingDeadlines items={[alert(), alert({ id: 2 })]} windowDays={30} />);
    expect(screen.getByText("30 prochains jours")).toBeInTheDocument();
    expect(screen.getByText(/2 echeances a suivre/i)).toBeInTheDocument();
  });

  it("orders items by urgency", () => {
    const items = [
      alert({ id: 1, severity: "info", title: "Info item", days_left: 2 }),
      alert({ id: 2, severity: "critical", title: "Critical item", days_left: 9 }),
    ];
    render(<UpcomingDeadlines items={items} />);
    const headings = screen.getAllByRole("article");
    expect(within(headings[0]).getByText("Critical item")).toBeInTheDocument();
  });

  it("shows an empty state when there is nothing", () => {
    render(<UpcomingDeadlines items={[]} />);
    expect(screen.getByText(/Aucune echeance a venir/i)).toBeInTheDocument();
    expect(screen.getByText(/Rien a signaler/i)).toBeInTheDocument();
  });
});
