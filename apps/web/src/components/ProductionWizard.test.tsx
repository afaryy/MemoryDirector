import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { strToU8, zipSync } from "fflate";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductionWizard } from "./ProductionWizard";

function selectOnePhoto() {
  fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
    target: { files: [new File(["photo"], "garden.jpg", { type: "image/jpeg" })] },
  });
}

function completeReadyState() {
  fireEvent.change(screen.getByLabelText("Your memory request"), {
    target: { value: "Make a gentle film from our garden afternoon." },
  });
  selectOnePhoto();
  fireEvent.click(screen.getByLabelText("I have permission to use these media."));
}

function exportZip() {
  return new Blob([zipSync({ "garden.mp4": strToU8("fixture-mp4") })], { type: "application/zip" });
}

describe("ProductionWizard", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("enables Make my film only after a request, selected media, and permission", () => {
    render(<ProductionWizard />);

    expect(screen.getByRole("button", { name: "Make my film" })).toBeDisabled();
    completeReadyState();
    expect(screen.getByRole("button", { name: "Make my film" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Approve plan" })).not.toBeInTheDocument();
  });

  it("removes one selected item without deleting the other selection", () => {
    render(<ProductionWizard />);
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: {
        files: [
          new File(["first"], "first.jpg", { type: "image/jpeg" }),
          new File(["second"], "second.jpg", { type: "image/jpeg" }),
        ],
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "Remove first.jpg" }));
    expect(screen.queryByText("first.jpg")).not.toBeInTheDocument();
    expect(screen.getByText("second.jpg")).toBeVisible();
  });

  it("creates a preview without a blocking plan review", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          media_id: "sha256:garden",
          description: "a sunny garden",
          privacy_flags: [],
          decision_status: "unselected",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ title: "Garden afternoon", caption: "A warm moment together.", music_direction: "gentle acoustic" }),
      })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true, blob: async () => exportZip() });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:memory-director-preview"),
      revokeObjectURL: vi.fn(),
    });
    render(<ProductionWizard />);

    completeReadyState();
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));
    expect(screen.getByRole("status")).toHaveTextContent("Making your film…");

    expect(await screen.findByRole("button", { name: "Save & share" })).toBeEnabled();
    expect(screen.getByLabelText("Your memory film preview")).toBeVisible();
    expect(screen.getByText("Garden afternoon")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Approve plan" })).not.toBeInTheDocument();

    const exportCall = fetchMock.mock.calls.find(([url]) => url === "http://localhost:8000/renders/export");
    expect(exportCall?.[1]?.body.get("media_ids")).toBe("sha256:garden");
  });

  it("keeps the request and selected media when generation fails and offers Try again", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: false }));
    render(<ProductionWizard />);

    completeReadyState();
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    expect(await screen.findByRole("button", { name: "Try again" })).toBeEnabled();
    expect(screen.getByDisplayValue("Make a gentle film from our garden afternoon.")).toBeVisible();
    expect(screen.getByText("garden.jpg")).toBeVisible();
  });

  it("keeps typing available when the browser cannot start voice input", async () => {
    render(<ProductionWizard />);
    fireEvent.click(screen.getByRole("button", { name: "Voice input" }));

    expect(await screen.findByText("Voice input is not available. You can type your request instead.")).toBeVisible();
  });
});
