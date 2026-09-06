import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "./page";

describe("HomePage", () => {
  it("introduces Memory Director with a concise purpose", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { name: "Memory Director" })).toBeVisible();
    expect(screen.getByText("Your moments, made simply.")).toBeVisible();
    expect(screen.queryByText(/turn phone moments into a short film/i)).not.toBeInTheDocument();
  });
});
