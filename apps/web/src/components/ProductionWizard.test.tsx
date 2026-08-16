import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductionWizard } from "./ProductionWizard";

describe("ProductionWizard", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("keeps video creation disabled until the user approves the plan", () => {
    render(<ProductionWizard />);

    const createButton = screen.getByRole("button", { name: "Make this video" });
    expect(createButton).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Approve plan" }));

    expect(createButton).toBeEnabled();
  });

  it("submits an approved render request and confirms it to the user", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    fireEvent.change(screen.getByLabelText("What would you like to make?"), {
      target: { value: "Make a cheerful travel video." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Approve plan" }));
    fireEvent.click(screen.getByRole("button", { name: "Make this video" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/renders",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Your approved video request is ready.")).toBeVisible();
  });
});
