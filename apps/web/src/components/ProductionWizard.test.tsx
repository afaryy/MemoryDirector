import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { Blob as NodeBlob } from "node:buffer";
import { strToU8, zipSync } from "fflate";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

function statusWithText(text: string) {
  const status = screen.getAllByRole("status").find((element) => element.textContent?.includes(text));
  expect(status).toBeDefined();
  return status as HTMLElement;
}

function exportZip() {
  return new NodeBlob(
    [zipSync({ "garden.mp4": strToU8("fixture-mp4"), "garden.jpg": strToU8("fixture-cover") })],
    { type: "application/zip" },
  );
}

function renderSuccessfulProduction() {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ media_id: "sha256:garden" }) })
    .mockResolvedValueOnce({ ok: true })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ title: "Garden afternoon", caption: "A warm moment together.", music_direction: "gentle acoustic" }),
    })
    .mockResolvedValueOnce({ ok: true })
    .mockResolvedValueOnce({ ok: true, blob: async () => exportZip() });
  const createObjectURL = vi.fn((file: File) => {
    if (file.name.endsWith("-cover.jpg")) return "blob:memory-director-cover";
    if (file.type === "video/mp4") return "blob:memory-director-video";
    return `blob:selected-${file.name}`;
  });
  vi.stubGlobal("fetch", fetchMock);
  const revokeObjectURL = vi.fn();
  vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
  const view = render(<ProductionWizard />);
  completeReadyState();
  fireEvent.click(screen.getByRole("button", { name: "Make my film" }));
  return { createObjectURL, fetchMock, revokeObjectURL, view };
}

describe("ProductionWizard", () => {
  beforeEach(() => {
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn((file: File) => `blob:selected-${file.name}`),
      revokeObjectURL: vi.fn(),
    });
  });

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

  it("shows real photo and video previews in an ordered horizontal media strip", () => {
    render(<ProductionWizard />);
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: {
        files: [
          new File(["photo"], "birthday.jpg", { type: "image/jpeg" }),
          new File(["video"], "candles.mp4", { type: "video/mp4" }),
        ],
      },
    });

    const strip = screen.getByRole("list", { name: "Selected media" });
    expect(within(strip).getByRole("img", { name: "Preview birthday.jpg" })).toHaveAttribute(
      "src",
      "blob:selected-birthday.jpg",
    );
    expect(within(strip).getByLabelText("Preview candles.mp4")).toHaveAttribute(
      "src",
      "blob:selected-candles.mp4",
    );
    expect(within(strip).getByText("Photo")).toBeVisible();
    expect(within(strip).getByText("Video")).toBeVisible();
  });

  it("recognizes a phone video by extension when the browser omits its MIME type", () => {
    render(<ProductionWizard />);
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: { files: [new File(["video"], "IMG_3352.MOV")] },
    });

    const strip = screen.getByRole("list", { name: "Selected media" });
    expect(within(strip).getByLabelText("Preview IMG_3352.MOV")).toHaveAttribute(
      "src",
      "blob:selected-IMG_3352.MOV",
    );
    expect(within(strip).getByText("Video")).toBeVisible();
  });

  it("reorders selected media with the keyboard drag control without revoking consent", () => {
    render(<ProductionWizard />);
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: {
        files: [
          new File(["first"], "first.jpg", { type: "image/jpeg" }),
          new File(["second"], "second.mp4", { type: "video/mp4" }),
          new File(["third"], "third.jpg", { type: "image/jpeg" }),
        ],
      },
    });
    fireEvent.click(screen.getByLabelText("I have permission to use these media."));

    const reorderThird = screen.getByRole("button", { name: "Reorder third.jpg" });
    reorderThird.focus();
    fireEvent.keyDown(reorderThird, { key: " " });
    expect(reorderThird).toHaveAttribute("aria-pressed", "true");
    fireEvent.keyDown(reorderThird, { key: "ArrowLeft" });
    expect(statusWithText("Moved third.jpg to position 2 of 3.")).toHaveTextContent("Moved third.jpg to position 2 of 3.");
    fireEvent.keyDown(reorderThird, { key: " " });

    const cards = within(screen.getByRole("list", { name: "Selected media" })).getAllByRole("listitem");
    expect(cards.map((card) => within(card).getByText(/\.(?:jpg|mp4)$/).textContent)).toEqual([
      "first.jpg",
      "third.jpg",
      "second.mp4",
    ]);
    expect(screen.getByLabelText("I have permission to use these media.")).toBeChecked();
    expect(statusWithText("Placed third.jpg at position 2 of 3.")).toHaveTextContent("Placed third.jpg at position 2 of 3.");
    expect(screen.getByRole("button", { name: "Reorder third.jpg" })).toHaveFocus();
    expect(screen.queryByRole("button", { name: /Move .* (?:left|right)/ })).not.toBeInTheDocument();
  });

  it("locks mouse and touch reordering while film generation is pending", async () => {
    let analyzeSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((_url: string, options?: RequestInit) => {
      analyzeSignal = options?.signal as AbortSignal | undefined;
      return new Promise<Response>(() => undefined);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProductionWizard />);
    fireEvent.change(screen.getByLabelText("Your memory request"), {
      target: { value: "Make a gentle film from these moments." },
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
    fireEvent.click(screen.getByRole("button", { name: "Make my film" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const reorderSecond = screen.getByRole("button", { name: "Reorder second.jpg" });
    expect(reorderSecond).toBeDisabled();

    const secondCard = reorderSecond.closest("li");
    expect(secondCard).not.toBeNull();
    fireEvent.mouseDown(secondCard!, { button: 0, clientX: 240, clientY: 100 });
    fireEvent.mouseMove(document, { clientX: 40, clientY: 100 });
    fireEvent.mouseUp(document, { clientX: 40, clientY: 100 });
    fireEvent.touchStart(secondCard!, { touches: [{ clientX: 240, clientY: 100 }] });
    fireEvent.touchMove(document, { touches: [{ clientX: 40, clientY: 100 }] });
    fireEvent.touchEnd(document);

    const cards = within(screen.getByRole("list", { name: "Selected media" })).getAllByRole("listitem");
    expect(cards.map((card) => within(card).getByText(/\.jpg$/).textContent)).toEqual(["first.jpg", "second.jpg"]);
    expect(analyzeSignal?.aborted).toBe(false);
    expect(screen.getByText("Making your film…")).toBeVisible();
  });

  it("removes a selected thumbnail without asking for permission again", async () => {
    render(<ProductionWizard />);
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: {
        files: [
          new File(["first"], "first.jpg", { type: "image/jpeg" }),
          new File(["second"], "second.jpg", { type: "image/jpeg" }),
        ],
      },
    });
    fireEvent.click(screen.getByLabelText("I have permission to use these media."));

    const removeFirst = screen.getByRole("button", { name: "Remove first.jpg" });
    removeFirst.focus();
    fireEvent.click(removeFirst);

    expect(screen.queryByText("first.jpg")).not.toBeInTheDocument();
    expect(screen.getByLabelText("I have permission to use these media.")).toBeChecked();
    expect(statusWithText("Removed first.jpg; 1 item remains.")).toHaveTextContent("Removed first.jpg; 1 item remains.");
    await waitFor(() => expect(screen.getByRole("button", { name: "Remove second.jpg" })).toHaveFocus());
  });

  it("returns focus to the file chooser after removing the final item", async () => {
    render(<ProductionWizard />);
    selectOnePhoto();

    const removeOnlyItem = screen.getByRole("button", { name: "Remove garden.jpg" });
    removeOnlyItem.focus();
    fireEvent.click(removeOnlyItem);

    expect(statusWithText("Removed garden.jpg; 0 items remain.")).toHaveTextContent("Removed garden.jpg; 0 items remain.");
    await waitFor(() => expect(screen.getByLabelText("Choose photos and videos")).toHaveFocus());
  });

  it("announces keyboard drag boundaries and lets the user cancel without reordering", () => {
    render(<ProductionWizard />);
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: {
        files: [
          new File(["first"], "first.jpg", { type: "image/jpeg" }),
          new File(["second"], "second.jpg", { type: "image/jpeg" }),
        ],
      },
    });

    const reorderSecond = screen.getByRole("button", { name: "Reorder second.jpg" });
    reorderSecond.focus();
    fireEvent.keyDown(reorderSecond, { key: " " });
    fireEvent.keyDown(reorderSecond, { key: "ArrowRight" });
    expect(statusWithText("second.jpg is already last.")).toHaveTextContent("second.jpg is already last.");
    fireEvent.keyDown(reorderSecond, { key: "Escape" });

    const cards = within(screen.getByRole("list", { name: "Selected media" })).getAllByRole("listitem");
    expect(cards.map((card) => within(card).getByText(/\.jpg$/).textContent)).toEqual(["first.jpg", "second.jpg"]);
    expect(reorderSecond).toHaveAttribute("aria-pressed", "false");
    expect(statusWithText("Reordering canceled.")).toHaveTextContent("Reordering canceled.");
  });

  it("explains the 15-item limit instead of silently dropping selected media", () => {
    render(<ProductionWizard />);
    fireEvent.change(screen.getByLabelText("Choose photos and videos"), {
      target: {
        files: Array.from({ length: 16 }, (_, index) => new File([String(index)], `moment-${index}.jpg`, { type: "image/jpeg" })),
      },
    });

    expect(statusWithText("Choose up to 15 photos and videos for one film.")).toHaveTextContent("Choose up to 15 photos and videos for one film.");
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
    expect(statusWithText("Making your film…")).toHaveTextContent("Making your film…");

    expect(await screen.findByRole("button", { name: "Save video" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Share video" })).toBeEnabled();
    expect(screen.getByLabelText("Your memory film preview")).toBeVisible();
    expect(screen.getByText("Garden afternoon")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Your memory request", exact: true })).toBeVisible();
    expect(screen.getByLabelText("Choose photos and videos")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve plan" })).not.toBeInTheDocument();

    const exportCall = fetchMock.mock.calls.find(([url]) => url === "http://localhost:8000/renders/export");
    expect(exportCall?.[1]?.body.get("media_ids")).toBe("sha256:garden");
    expect(exportCall?.[1]?.body.get("soundtrack_mode")).toBe("original_song");
    const selectionCall = fetchMock.mock.calls.find(([url]) => url === "http://localhost:8000/media/sha256:garden/decision");
    expect(selectionCall?.[1]).toMatchObject({ method: "POST" });
    expect(JSON.parse(selectionCall?.[1]?.body as string)).toEqual({ status: "selected", reason: "Chosen for this film" });
  });

  it("keeps the last successful film visible while a revised film is prepared", async () => {
    const { fetchMock } = renderSuccessfulProduction();
    const firstPreview = await screen.findByLabelText("Your memory film preview");
    expect(firstPreview).toHaveAttribute("src", "blob:memory-director-video");

    fetchMock.mockImplementation(() => new Promise<Response>(() => undefined));
    fireEvent.change(screen.getByLabelText("Your memory request"), {
      target: { value: "Make the birthday version more cheerful." },
    });

    expect(screen.getByLabelText("Your memory film preview")).toHaveAttribute(
      "src",
      "blob:memory-director-video",
    );
    fireEvent.click(screen.getByRole("button", { name: "Make again" }));

    expect(screen.getByLabelText("Your memory film preview")).toHaveAttribute(
      "src",
      "blob:memory-director-video",
    );
    expect(statusWithText("Making your film…")).toHaveTextContent("Making your film…");
  });

  it("brings the completed preview into view without leaving the editor", async () => {
    const scrollIntoView = vi.fn();
    Object.defineProperty(Element.prototype, "scrollIntoView", { configurable: true, value: scrollIntoView });
    vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));

    renderSuccessfulProduction();
    await screen.findByLabelText("Your memory film preview");

    await waitFor(() => expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "auto", block: "start" }));
    expect(screen.getByRole("textbox", { name: "Your memory request", exact: true })).toBeVisible();
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
    expect(statusWithText("Making your film…")).toHaveTextContent("Making your film…");
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

    expect(await screen.findByRole("button", { name: "Save video" })).toBeEnabled();
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

  it("uses the generated cover while the finished film is not playing", async () => {
    const load = vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => undefined);
    const { createObjectURL } = renderSuccessfulProduction();

    const video = await screen.findByLabelText("Your memory film preview");

    expect(video).toHaveAttribute("poster", "blob:memory-director-cover");
    expect(createObjectURL.mock.calls.map(([file]) => file.name)).toContain("Garden afternoon-cover.jpg");
    expect(createObjectURL.mock.calls.map(([file]) => file.type)).toContain("video/mp4");
    fireEvent.ended(video);
    expect(load).toHaveBeenCalledTimes(1);
  });

  it("downloads the finished film without opening the share sheet", async () => {
    const share = vi.fn();
    let downloadedHref = "";
    let downloadedName = "";
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function () {
      downloadedHref = this.href;
      downloadedName = this.download;
    });
    vi.stubGlobal("navigator", { share, canShare: vi.fn(() => true) });
    renderSuccessfulProduction();

    fireEvent.click(await screen.findByRole("button", { name: "Save video" }));

    expect(click).toHaveBeenCalledTimes(1);
    expect(downloadedHref).toBe("blob:memory-director-video");
    expect(downloadedName).toMatch(/\.mp4$/);
    expect(share).not.toHaveBeenCalled();
    expect(screen.getByText("Video saved to this device.")).toBeVisible();
  });

  it("opens the native file share sheet for WhatsApp, WeChat, or another installed app", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { share, canShare: vi.fn(() => true) });
    renderSuccessfulProduction();

    fireEvent.click(await screen.findByRole("button", { name: "Share video" }));

    await waitFor(() => expect(share).toHaveBeenCalledTimes(1));
    expect(share.mock.calls[0][0].files[0]).toBeInstanceOf(File);
    expect(share.mock.calls[0][0].files[0].type).toBe("video/mp4");
    expect(screen.getByText("Choose WhatsApp, WeChat, or another app from your phone's share menu.")).toBeVisible();
  });

  it("explains how to share when native file sharing is unavailable", async () => {
    vi.stubGlobal("navigator", {});
    renderSuccessfulProduction();

    fireEvent.click(await screen.findByRole("button", { name: "Share video" }));

    expect(screen.getByText("Save the video first, then send it from WhatsApp or WeChat.")).toBeVisible();
  });

  it("releases the video and cover object URLs when the completed preview leaves the page", async () => {
    const { revokeObjectURL, view } = renderSuccessfulProduction();
    await screen.findByLabelText("Your memory film preview");

    view.unmount();

    expect(revokeObjectURL).toHaveBeenCalledWith("blob:memory-director-video");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:memory-director-cover");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:selected-garden.jpg");
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
