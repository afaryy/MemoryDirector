import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { Blob as NodeBlob } from "node:buffer";
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
  return new NodeBlob([zipSync({ "garden.mp4": strToU8("fixture-mp4") })], { type: "application/zip" });
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
    const selectionCall = fetchMock.mock.calls.find(([url]) => url === "http://localhost:8000/media/sha256:garden/decision");
    expect(selectionCall?.[1]).toMatchObject({ method: "POST" });
    expect(JSON.parse(selectionCall?.[1]?.body as string)).toEqual({ status: "selected", reason: "Chosen for this film" });
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

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Instrumental music is not configured; choose original song or no sound.",
    );
    expect(screen.getByRole("button", { name: "Try again" })).toBeEnabled();
  });

  it("keeps network failure details behind the generic recovery message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new TypeError("Failed to fetch")));
    render(<ProductionWizard />);

    completeReadyState();
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    expect(await screen.findByRole("status")).toHaveTextContent("We could not make your film. Please try again.");
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

    expect(await screen.findByRole("status")).toHaveTextContent("We could not make your film. Please try again.");
    expect(screen.queryByText("upstream gateway failure")).not.toBeInTheDocument();
  });

  it("keeps typing available when the browser cannot start voice input", async () => {
    render(<ProductionWizard />);
    fireEvent.click(screen.getByRole("button", { name: "Voice input" }));

    expect(await screen.findByText("Voice input is not available. You can type your request instead.")).toBeVisible();
  });
});
