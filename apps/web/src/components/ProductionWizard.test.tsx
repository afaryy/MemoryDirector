import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Blob as NodeBlob } from "node:buffer";
import { strToU8, zipSync } from "fflate";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductionWizard } from "./ProductionWizard";

function selectOnePhoto() {
  fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
    target: { files: [new File(["photo"], "garden.jpg", { type: "image/jpeg" })] },
  });
}

function selectPhotos(count: number) {
  fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
    target: {
      files: Array.from(
        { length: count },
        (_, index) => new File([`photo-${index}`], `garden-${index}.jpg`, { type: "image/jpeg" }),
      ),
    },
  });
}

function completeReadyStateWithPhotos(count: number) {
  fireEvent.change(screen.getByLabelText("Your memory request"), {
    target: { value: "Make a gentle film from our garden afternoon." },
  });
  selectPhotos(count);
  fireEvent.click(screen.getByLabelText("I have permission to use these media."));
}

function completeReadyState() {
  fireEvent.change(screen.getByLabelText("Your memory request"), {
    target: { value: "Make a gentle film from our garden afternoon." },
  });
  selectOnePhoto();
  fireEvent.click(screen.getByLabelText("I have permission to use these media."));
}

function exportZip() {
  return new NodeBlob([zipSync({ "garden.mp4": strToU8("fixture-mp4") })], { type: "application/zip" });
}

describe("ProductionWizard", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("presents the selected album-workbench journey and keeps music visible", () => {
    render(<ProductionWizard />);

    expect(screen.getByRole("heading", { name: "Start with the moments you love." })).toBeVisible();
    expect(screen.getByRole("heading", { name: "1. Choose photos and videos" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "2. Tell us about it" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "3. Choose the sound" })).toBeVisible();
    expect(screen.getByRole("radio", { name: /Original AI song/ })).toBeChecked();
    expect(screen.getByText("Watch before you save")).toBeVisible();
  });

  it("clears a spoken or typed request with one labelled action", () => {
    render(<ProductionWizard />);
    const request = screen.getByRole("textbox", { name: "Your memory request", exact: true });

    fireEvent.change(request, { target: { value: "Use the sunny garden photos." } });
    fireEvent.click(screen.getByRole("button", { name: "Clear request" }));

    expect(request).toHaveValue("");
  });

  it("enables Make my film only after a request, selected media, and permission", () => {
    render(<ProductionWizard />);

    expect(screen.getByRole("textbox", { name: "Your memory request", exact: true })).toBeVisible();
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

  it("explains the 15-item limit instead of silently dropping selected media", () => {
    render(<ProductionWizard />);
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: {
        files: Array.from({ length: 16 }, (_, index) => new File([String(index)], `moment-${index}.jpg`, { type: "image/jpeg" })),
      },
    });

    expect(screen.getByRole("status")).toHaveTextContent("Choose up to 15 photos and videos for one film.");
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
        json: async () => ({ media_id: "sha256:garden", status: "selected", reason: "Chosen for this film" }),
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
    expect(exportCall?.[1]?.body.get("soundtrack_mode")).toBe("original_song");
    const selectionCall = fetchMock.mock.calls.find(([url]) => url === "http://localhost:8000/media/sha256:garden/decision");
    expect(selectionCall?.[1]).toMatchObject({ method: "POST" });
    expect(JSON.parse(selectionCall?.[1]?.body as string)).toEqual({ status: "selected", reason: "Chosen for this film" });
  });

  it("starts no more than two media analyses at once", async () => {
    const fetchMock = vi.fn(() => new Promise<Response>(() => undefined));
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    completeReadyStateWithPhotos(4);
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls.every(([url]) => url === "http://localhost:8000/media/analyze")).toBe(true);
  });

  it("keeps the choices visible and disabled with progress in the preview area", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => undefined)));
    render(<ProductionWizard />);

    completeReadyState();
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    expect(screen.getByRole("textbox", { name: "Your memory request", exact: true })).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Your memory request", exact: true })).toBeDisabled();
    expect(screen.getByText("garden.jpg")).toBeVisible();
    expect(screen.getByRole("radio", { name: /Original AI song/ })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Making your film…");
    expect(screen.getAllByText("Making your film…")).toHaveLength(1);
  });

  it("retries one transient media-analysis failure and continues", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 500 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ media_id: "sha256:garden" }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ media_id: "sha256:garden", status: "selected" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ title: "Garden afternoon", caption: "Together.", music_direction: "gentle acoustic" }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ output_format: "vertical-mp4" }), { status: 201 }))
      .mockResolvedValueOnce({ ok: true, blob: async () => exportZip() });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:memory-director-preview"),
      revokeObjectURL: vi.fn(),
    });
    render(<ProductionWizard />);

    completeReadyState();
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    expect(await screen.findByRole("button", { name: "Save & share" })).toBeEnabled();
    const analysisCalls = fetchMock.mock.calls.filter(([url]) => url === "http://localhost:8000/media/analyze");
    expect(analysisCalls).toHaveLength(2);
  });

  it("does not retry a media-analysis validation failure", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(null, { status: 415 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    completeReadyState();
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    expect(await screen.findByRole("button", { name: "Try again" })).toBeEnabled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("cancels the failed generation before a retry starts new analysis workers", async () => {
    let analysisCalls = 0;
    let activeAnalyses = 0;
    let maximumActiveAnalyses = 0;
    const fetchMock = vi.fn((url: string, options?: RequestInit) => {
      if (url !== "http://localhost:8000/media/analyze") {
        throw new Error(`Unexpected request: ${url}`);
      }
      analysisCalls += 1;
      activeAnalyses += 1;
      maximumActiveAnalyses = Math.max(maximumActiveAnalyses, activeAnalyses);
      if (analysisCalls === 1) {
        activeAnalyses -= 1;
        return Promise.resolve(new Response(null, { status: 415 }));
      }
      return new Promise<Response>((_resolve, reject) => {
        options?.signal?.addEventListener(
          "abort",
          () => {
            activeAnalyses -= 1;
            reject(new DOMException("Aborted", "AbortError"));
          },
          { once: true },
        );
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    completeReadyStateWithPhotos(4);
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    const retry = await screen.findByRole("button", { name: "Try again" });
    await waitFor(() => expect(activeAnalyses).toBe(0));
    expect(analysisCalls).toBe(2);

    fireEvent.click(retry);
    await waitFor(() => expect(analysisCalls).toBe(4));
    expect(maximumActiveAnalyses).toBe(2);
  });

  it("cancels active media analysis when the creator leaves the page", async () => {
    let analysisCalls = 0;
    let activeAnalyses = 0;
    const fetchMock = vi.fn((_url: string, options?: RequestInit) => {
      analysisCalls += 1;
      activeAnalyses += 1;
      return new Promise<Response>((_resolve, reject) => {
        options?.signal?.addEventListener(
          "abort",
          () => {
            activeAnalyses -= 1;
            reject(new DOMException("Aborted", "AbortError"));
          },
          { once: true },
        );
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const view = render(<ProductionWizard />);

    completeReadyStateWithPhotos(4);
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));
    await waitFor(() => expect(activeAnalyses).toBe(2));

    view.unmount();
    await waitFor(() => expect(activeAnalyses).toBe(0));
    expect(analysisCalls).toBe(2);
  });

  it("cancels active generation when a delayed voice result changes the request", async () => {
    const recognition = {
      lang: "",
      onend: null as (() => void) | null,
      onerror: null as (() => void) | null,
      onresult: null as ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null,
      start: vi.fn(),
    };
    vi.stubGlobal("SpeechRecognition", vi.fn(() => recognition));
    let activeAnalyses = 0;
    const fetchMock = vi.fn((_url: string, options?: RequestInit) => {
      activeAnalyses += 1;
      return new Promise<Response>((_resolve, reject) => {
        options?.signal?.addEventListener(
          "abort",
          () => {
            activeAnalyses -= 1;
            reject(new DOMException("Aborted", "AbortError"));
          },
          { once: true },
        );
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);

    completeReadyStateWithPhotos(4);
    fireEvent.click(screen.getByRole("button", { name: "Voice input" }));
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));
    await waitFor(() => expect(activeAnalyses).toBe(2));

    act(() => recognition.onresult?.({ results: [[{ transcript: "Use the birthday moments instead." }]] }));

    await waitFor(() => expect(activeAnalyses).toBe(0));
    expect(screen.getByRole("textbox", { name: "Your memory request", exact: true })).toHaveValue(
      "Use the birthday moments instead.",
    );
    expect(screen.getByRole("button", { name: "Make my film" })).toBeEnabled();
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

  it("disables Try again when permission is revoked after a failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: false }));
    render(<ProductionWizard />);

    completeReadyState();
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));
    expect(await screen.findByRole("button", { name: "Try again" })).toBeEnabled();

    fireEvent.click(screen.getByLabelText("I have permission to use these media."));
    expect(screen.getByRole("button", { name: "Try again" })).toBeDisabled();
  });

  it("shows the API guidance when the selected soundtrack is unavailable", async () => {
    const jsonResponse = (body: unknown, status = 200) =>
      new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          jsonResponse(
            {
              media_id: "sha256:garden",
              description: "A sunny garden",
              quality_score: 0.9,
              duplicate_of: null,
              privacy_flags: [],
              orientation: "landscape",
              duration_seconds: null,
              decision_status: "unselected",
            },
            201,
          ),
        )
        .mockResolvedValueOnce(
          jsonResponse({ media_id: "sha256:garden", status: "selected", reason: "Chosen for this film" }),
        )
        .mockResolvedValueOnce(
          jsonResponse(
            { title: "Garden afternoon", caption: "A warm moment together.", music_direction: "gentle acoustic" },
            201,
          ),
        )
        .mockResolvedValueOnce(
          jsonResponse({ title: "Garden afternoon", caption: "A warm moment together.", output_format: "vertical-mp4" }, 201),
        )
        .mockResolvedValueOnce(
          jsonResponse({ detail: "Instrumental music is not configured; choose original song or no sound." }, 422),
        ),
    );
    render(<ProductionWizard />);

    completeReadyState();
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    await waitFor(() =>
      expect(screen.getByText("Instrumental music is not configured; choose original song or no sound.")).toBeVisible(),
    );
    expect(screen.getByRole("button", { name: "Try again" })).toBeEnabled();
  });

  it("keeps network failure details behind the generic recovery message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new TypeError("Failed to fetch")));
    render(<ProductionWizard />);

    completeReadyState();
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    await waitFor(() =>
      expect(screen.getByText("We could not make your film. Please try again.")).toBeVisible(),
    );
    expect(screen.queryByText("Failed to fetch")).not.toBeInTheDocument();
  });

  it("uses the generic recovery message when an export error is not JSON", async () => {
    const jsonResponse = (body: unknown, status = 200) =>
      new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          jsonResponse(
            {
              media_id: "sha256:garden",
              description: "A sunny garden",
              quality_score: 0.9,
              duplicate_of: null,
              privacy_flags: [],
              orientation: "landscape",
              duration_seconds: null,
              decision_status: "unselected",
            },
            201,
          ),
        )
        .mockResolvedValueOnce(
          jsonResponse({ media_id: "sha256:garden", status: "selected", reason: "Chosen for this film" }),
        )
        .mockResolvedValueOnce(
          jsonResponse(
            { title: "Garden afternoon", caption: "A warm moment together.", music_direction: "gentle acoustic" },
            201,
          ),
        )
        .mockResolvedValueOnce(
          jsonResponse({ title: "Garden afternoon", caption: "A warm moment together.", output_format: "vertical-mp4" }, 201),
        )
        .mockResolvedValueOnce(new Response("upstream gateway failure", { status: 502 })),
    );
    render(<ProductionWizard />);

    completeReadyState();
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    await waitFor(() =>
      expect(screen.getByText("We could not make your film. Please try again.")).toBeVisible(),
    );
    expect(screen.queryByText("upstream gateway failure")).not.toBeInTheDocument();
  });

  it("keeps typing available when the browser cannot start voice input", async () => {
    render(<ProductionWizard />);
    fireEvent.click(screen.getByRole("button", { name: "Voice input" }));

    expect(await screen.findByText("Voice input is not available. You can type your request instead.")).toBeVisible();
  });
});
