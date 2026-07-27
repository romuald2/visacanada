import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Home from "./page";

describe("Home Page", () => {
  it("renders the main heading", () => {
    render(<Home />);
    expect(screen.getByText(/VisaCanada/i)).toBeInTheDocument();
  });

  it("renders the description", () => {
    render(<Home />);
    expect(
      screen.getByText(/Plateforme IA de gestion d'immigration/i)
    ).toBeInTheDocument();
  });

  it("renders the API documentation link", () => {
    render(<Home />);
    const link = screen.getByText(/API Documentation/i);
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/docs");
  });

  it("renders the GitHub link", () => {
    render(<Home />);
    const link = screen.getByText(/GitHub/i);
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute(
      "href",
      "https://github.com/romuald2/visacanada"
    );
  });
});
