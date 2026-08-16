import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "./page";

describe("HomePage", () => {
  it("introduces Memory Director as a voice-led producer", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { name: "Memory Director" })).toBeVisible();
    expect(screen.getByText(/voice-led memory film producer/i)).toBeVisible();
  });
});
