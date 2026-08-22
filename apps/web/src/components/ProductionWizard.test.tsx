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
    expect(screen.queryByRole("button", { name: "Make this video" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Your plan stays in your control." })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create a plan" })).toBeDisabled();
  });

  it("shows one clear active stage before any media is submitted", () => {
    render(<ProductionWizard />);

    expect(screen.getByRole("heading", { name: "Start with what you want to remember." })).toBeVisible();
    expect(screen.getByText("1 / 4")).toBeVisible();
    expect(screen.queryByText("04 / REVIEW")).not.toBeInTheDocument();
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

  it("exposes the listening state to assistive technology", () => {
    class WorkingRecognition {
      lang = "";
      onend: (() => void) | null = null;
      onerror: (() => void) | null = null;
      onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null = null;

      start() {}
    }

    vi.stubGlobal("SpeechRecognition", WorkingRecognition);
    render(<ProductionWizard />);

    const voiceButton = screen.getByRole("button", { name: "Speak your request" });
    expect(voiceButton).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(voiceButton);

    expect(screen.getByRole("button", { name: "Listening…" })).toHaveAttribute("aria-pressed", "true");
  });

  it("submits an approved render request and confirms it to the user", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          media_id: "sha256:beach",
          description: "a bright beach",
          quality_score: 0.9,
          privacy_flags: [],
          orientation: "landscape",
          duration_seconds: null,
          decision_status: "unselected",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ title: "A Family Day by the Sea", caption: "Small moments, held close." }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "selected" }) })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true, blob: async () => new Blob(["zip"]) });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:memory-director-export") });
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
    fireEvent.click(screen.getByRole("button", { name: "Keep this item" }));
    expect(await screen.findByRole("button", { name: "Kept" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Approve plan" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Make this video" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Make this video" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/storyboards",
        expect.objectContaining({ method: "POST" }),
      );
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/renders",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText("Your approved video request is ready.")).toBeVisible();
  });

  it("shows the explainable music preference used by the plan", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          media_id: "sha256:beach",
          description: "a bright beach",
          quality_score: 0.9,
          privacy_flags: [],
          orientation: "landscape",
          duration_seconds: null,
          decision_status: "unselected",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          title: "A Family Day by the Sea",
          caption: "Small moments, held close.",
          music_direction: "gentle festive instrumental",
          preference_explanation: "You chose gentle festive twice before for similar memories.",
          preference_evidence_count: 2,
        }),
      });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    fireEvent.change(screen.getByLabelText("What would you like to make?"), {
      target: { value: "Make a cheerful travel video." },
    });
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: { files: [new File(["photo"], "beach.jpg", { type: "image/jpeg" })] },
    });
    fireEvent.click(screen.getByLabelText("I have permission to use these media."));
    fireEvent.click(screen.getByRole("button", { name: "Create a plan" }));

    expect(await screen.findByText("Suggested sound: gentle festive instrumental")).toBeVisible();
    expect(screen.getByText("You chose gentle festive twice before for similar memories.")).toBeVisible();
  });

  it("reviews privacy flags before exporting the selected media package", async () => {
    const exportBlob = new Blob(["zip-bytes"], { type: "application/zip" });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          media_id: "sha256:photo",
          description: "a family garden",
          quality_score: 0.9,
          privacy_flags: ["contains_face"],
          orientation: "landscape",
          duration_seconds: null,
          decision_status: "unselected",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ title: "A Family Day", caption: "Small moments together." }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "selected" }) })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true, blob: async () => exportBlob });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:memory-director-export") });
    render(<ProductionWizard />);

    fireEvent.change(screen.getByLabelText("What would you like to make?"), {
      target: { value: "Make a cheerful family video." },
    });
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: { files: [new File(["photo"], "garden.jpg", { type: "image/jpeg" })] },
    });
    fireEvent.click(screen.getByLabelText("I have permission to use these media."));
    fireEvent.click(screen.getByRole("button", { name: "Create a plan" }));

    expect(await screen.findByText("a family garden")).toBeVisible();
    expect(screen.getByText("Face visible")).toBeVisible();
    expect(screen.getByRole("button", { name: "Approve plan" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Keep this item" }));
    expect(await screen.findByRole("button", { name: "Kept" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Approve plan" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Make this video" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Make this video" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/renders/export",
        expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
      );
    });
    expect(await screen.findByRole("link", { name: "Download your video package" })).toHaveAttribute(
      "href",
      "blob:memory-director-export",
    );
  });

  it("revokes review and approval when media permission is withdrawn", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          media_id: "sha256:photo",
          description: "a family garden",
          quality_score: 0.9,
          privacy_flags: [],
          orientation: "landscape",
          duration_seconds: null,
          decision_status: "unselected",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ title: "A Family Day", caption: "Small moments together." }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "selected" }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    fireEvent.change(screen.getByLabelText("What would you like to make?"), {
      target: { value: "Make a family video." },
    });
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: { files: [new File(["photo"], "garden.jpg", { type: "image/jpeg" })] },
    });
    const permission = screen.getByLabelText("I have permission to use these media.");
    fireEvent.click(permission);
    fireEvent.click(screen.getByRole("button", { name: "Create a plan" }));
    expect(await screen.findByText("a family garden")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Keep this item" }));
    expect(await screen.findByRole("button", { name: "Kept" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Approve plan" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Make this video" })).toBeEnabled());

    fireEvent.click(permission);

    expect(screen.queryByText("a family garden")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve plan" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Make this video" })).not.toBeInTheDocument();
  });

  it("allows multiple selected items to form one memory video", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          media_id: "sha256:first",
          description: "the first moment",
          quality_score: 0.9,
          privacy_flags: [],
          orientation: "landscape",
          duration_seconds: null,
          decision_status: "unselected",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          media_id: "sha256:second",
          description: "the second moment",
          quality_score: 0.9,
          privacy_flags: [],
          orientation: "landscape",
          duration_seconds: null,
          decision_status: "unselected",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ title: "Two Moments", caption: "Together." }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "selected" }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "selected" }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "held_back" }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    fireEvent.change(screen.getByLabelText("What would you like to make?"), {
      target: { value: "Make a family video." },
    });
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: {
        files: [
          new File(["first"], "first.jpg", { type: "image/jpeg" }),
          new File(["second"], "second.jpg", { type: "image/jpeg" }),
        ],
      },
    });
    fireEvent.click(screen.getByLabelText("I have permission to use these media."));
    fireEvent.click(screen.getByRole("button", { name: "Create a plan" }));
    expect(await screen.findByText("the first moment")).toBeVisible();
    expect(screen.getByText("the second moment")).toBeVisible();

    const keepButtons = screen.getAllByRole("button", { name: "Keep this item" });
    fireEvent.click(keepButtons[0]);
    expect(await screen.findByRole("button", { name: "Kept" })).toBeEnabled();
    expect(keepButtons[1]).toBeEnabled();
    fireEvent.click(keepButtons[1]);
    await waitFor(() => expect(screen.getAllByRole("button", { name: "Kept" })).toHaveLength(2));
    expect(screen.getByRole("button", { name: "Approve plan" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Approve plan" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Make this video" })).toBeEnabled());
    fireEvent.click(screen.getAllByRole("button", { name: "Hold this item back" })[0]);
    await waitFor(() => expect(screen.getAllByRole("button", { name: "Held back" })).toHaveLength(1));
    expect(screen.getByRole("button", { name: "Approve plan" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Make this video" })).not.toBeInTheDocument();
  });

  it("does not export when consent is withdrawn during rendering", async () => {
    let resolveRender: ((response: { ok: boolean }) => void) | undefined;
    const renderResponse = new Promise<{ ok: boolean }>((resolve) => {
      resolveRender = resolve;
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          media_id: "sha256:photo",
          description: "a family garden",
          quality_score: 0.9,
          privacy_flags: [],
          orientation: "landscape",
          duration_seconds: null,
          decision_status: "unselected",
        }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ title: "A Family Day", caption: "Together." }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: "selected" }) })
      .mockReturnValueOnce(renderResponse);
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    fireEvent.change(screen.getByLabelText("What would you like to make?"), {
      target: { value: "Make a family video." },
    });
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: { files: [new File(["photo"], "garden.jpg", { type: "image/jpeg" })] },
    });
    const permission = screen.getByLabelText("I have permission to use these media.");
    fireEvent.click(permission);
    fireEvent.click(screen.getByRole("button", { name: "Create a plan" }));
    expect(await screen.findByText("a family garden")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Keep this item" }));
    expect(await screen.findByRole("button", { name: "Kept" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Approve plan" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Make this video" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Make this video" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/renders", expect.anything()));

    fireEvent.click(permission);
    resolveRender?.({ ok: true });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Make this video" })).not.toBeInTheDocument());
    expect(fetchMock).not.toHaveBeenCalledWith("http://localhost:8000/renders/export", expect.anything());
  });

  it("locks other keep actions while a media decision is pending", async () => {
    let resolveDecision: ((response: { ok: boolean; json: () => Promise<{ status: string }> }) => void) | undefined;
    const decisionResponse = new Promise<{ ok: boolean; json: () => Promise<{ status: string }> }>((resolve) => {
      resolveDecision = resolve;
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ media_id: "sha256:first", description: "first", privacy_flags: [], decision_status: "unselected" }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ media_id: "sha256:second", description: "second", privacy_flags: [], decision_status: "unselected" }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ title: "Two", caption: "Together." }) })
      .mockReturnValueOnce(decisionResponse);
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    fireEvent.change(screen.getByLabelText("What would you like to make?"), { target: { value: "Make a family video." } });
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: { files: [new File(["first"], "first.jpg", { type: "image/jpeg" }), new File(["second"], "second.jpg", { type: "image/jpeg" })] },
    });
    fireEvent.click(screen.getByLabelText("I have permission to use these media."));
    fireEvent.click(screen.getByRole("button", { name: "Create a plan" }));
    expect(await screen.findByText("first")).toBeVisible();
    const keepButtons = screen.getAllByRole("button", { name: "Keep this item" });
    fireEvent.click(keepButtons[0]);
    expect(keepButtons[1]).toBeDisabled();
    resolveDecision?.({ ok: true, json: async () => ({ status: "selected" }) });
    expect(await screen.findByRole("button", { name: "Kept" })).toBeEnabled();
  });
});
