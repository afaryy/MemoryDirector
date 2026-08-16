import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductionWizard } from "./ProductionWizard";

describe("ProductionWizard", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("keeps video creation disabled until the user approves a generated plan", () => {
    render(<ProductionWizard />);

    expect(screen.getByRole("button", { name: "Speak your request" })).toBeVisible();
    const createButton = screen.getByRole("button", { name: "Make this video" });
    expect(createButton).toBeDisabled();
    expect(screen.getByRole("button", { name: "Approve plan" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Create a plan" })).toBeDisabled();
  });

  it("offers typing when the browser cannot start voice input", async () => {
    class FailingRecognition {
      lang = "";
      onend: (() => void) | null = null;
      onerror: (() => void) | null = null;
      onresult: (() => void) | null = null;

      start() {
        throw new Error("Microphone permission denied");
      }
    }

    vi.stubGlobal("SpeechRecognition", FailingRecognition);
    render(<ProductionWizard />);

    fireEvent.click(screen.getByRole("button", { name: "Speak your request" }));

    expect(await screen.findByText("Voice input is not available. You can type your request instead.")).toBeVisible();
  });

  it("submits an approved render request and confirms it to the user", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ title: "A Family Day by the Sea", caption: "Small moments, held close." }),
      })
      .mockResolvedValueOnce({ ok: true });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    fireEvent.change(screen.getByLabelText("What would you like to make?"), {
      target: { value: "Make a cheerful travel video." },
    });
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: {
        files: [new File(["photo"], "beach.jpg", { type: "image/jpeg" })],
      },
    });
    expect(screen.getByText("1 item selected from your device.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Create a plan" })).toBeDisabled();
    fireEvent.click(screen.getByLabelText("I have permission to use these media."));
    fireEvent.click(screen.getByRole("button", { name: "Create a plan" }));
    expect(await screen.findByText("A Family Day by the Sea")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Approve plan" }));
    fireEvent.click(screen.getByRole("button", { name: "Make this video" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/storyboards",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/renders",
      expect.objectContaining({ method: "POST" }),
    );
    expect(await screen.findByText("Your approved video request is ready.")).toBeVisible();
  });
});
