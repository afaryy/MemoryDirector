import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProductionWizard } from "./ProductionWizard";

describe("ProductionWizard", () => {
  it("keeps video creation disabled until the user approves the plan", () => {
    render(<ProductionWizard />);

    const createButton = screen.getByRole("button", { name: "Make this video" });
    expect(createButton).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Approve plan" }));

    expect(createButton).toBeEnabled();
  });
});
