"use client";

import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  horizontalListSortingStrategy,
  SortableContext,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { unzipSync } from "fflate";
import {
  CircleCheck,
  Download,
  GripVertical,
  ImageIcon,
  Images,
  Mic,
  Play,
  Share2,
  Sparkles,
  Video,
  X,
} from "lucide-react";
import { type KeyboardEvent as ReactKeyboardEvent, useEffect, useRef, useState } from "react";

type Storyboard = {
  title: string;
  caption: string;
  music_direction?: string;
};

type MediaReview = { media_id: string };
type SelectedMedia = {
  file: File;
  id: number;
  kind: "photo" | "video";
  previewUrl: string;
};
type ProductionState = "ready" | "preparing" | "preview" | "error" | "saved";
type SoundtrackMode = "original_song" | "instrumental" | "no_sound";

type SortableMediaCardProps = {
  isPreparing: boolean;
  isKeyboardGrabbed: boolean;
  item: SelectedMedia;
  onKeyboardReorder: (event: ReactKeyboardEvent<HTMLButtonElement>, itemId: number) => void;
  onRemove: () => void;
  position: number;
  registerRemoveButton: (element: HTMLButtonElement | null) => void;
  total: number;
};

function SortableMediaCard({
  isPreparing,
  isKeyboardGrabbed,
  item,
  onKeyboardReorder,
  onRemove,
  position,
  registerRemoveButton,
  total,
}: SortableMediaCardProps) {
  const { attributes, isDragging, listeners, setNodeRef, transform, transition } = useSortable({
    disabled: isPreparing,
    id: item.id,
  });

  return (
    <li
      className={`wizard__media-card${isDragging ? " is-dragging" : ""}`}
      aria-disabled={isPreparing}
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...listeners}
    >
      <div className="wizard__thumbnail">
        {item.kind === "photo" ? (
          // Local blob URLs are browser-owned previews and cannot use the Next image optimizer.
          // eslint-disable-next-line @next/next/no-img-element
          <img alt={`Preview ${item.file.name}`} src={item.previewUrl} />
        ) : (
          <video aria-label={`Preview ${item.file.name}`} muted playsInline preload="metadata" src={item.previewUrl} />
        )}
        <span className="wizard__media-kind">
          {item.kind === "photo" ? <ImageIcon aria-hidden="true" /> : <Video aria-hidden="true" />}
          {item.kind === "photo" ? "Photo" : "Video"}
        </span>
        <button
          aria-label={`Remove ${item.file.name}`}
          className="button wizard__thumbnail-remove"
          onClick={onRemove}
          onMouseDown={(event) => event.stopPropagation()}
          onPointerDown={(event) => event.stopPropagation()}
          onTouchStart={(event) => event.stopPropagation()}
          ref={registerRemoveButton}
          type="button"
        >
          <X aria-hidden="true" />
        </button>
      </div>
      <div className="wizard__media-meta">
        <span className="wizard__media-name" title={item.file.name}>{item.file.name}</span>
        <button
          {...attributes}
          aria-label={`Reorder ${item.file.name}`}
          aria-pressed={isKeyboardGrabbed}
          className="button wizard__drag-handle"
          disabled={isPreparing}
          onKeyDown={(event) => onKeyboardReorder(event, item.id)}
          title={`Drag to reorder. Position ${position} of ${total}.`}
          type="button"
        >
          <GripVertical aria-hidden="true" />
          <span>{position}</span>
        </button>
      </div>
    </li>
  );
}

const phoneVideoExtension = /\.(?:3g2|3gp|avi|m4v|mkv|mov|mp4|mpeg|mpg|webm)$/i;

function selectedMediaKind(file: File): SelectedMedia["kind"] {
  return file.type.startsWith("video/") || (!file.type && phoneVideoExtension.test(file.name))
    ? "video"
    : "photo";
}

class UserFacingExportError extends Error {}

type SpeechResultEvent = { results: ArrayLike<ArrayLike<{ transcript: string }>> };
type SpeechRecognitionInstance = {
  lang: string;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  onresult: ((event: SpeechResultEvent) => void) | null;
  start: () => void;
};
type SpeechRecognitionWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognitionInstance;
  webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const mediaAnalysisConcurrency = 2;
const mediaAnalysisAttempts = 2;
const mediaAnalysisRetryDelayMs = 250;
const visitorStorageKey = "memory-director-visitor";
const maximumMediaItems = 15;

function selectedMediaFingerprint(file: File): string {
  return [file.name, file.size, file.type, file.lastModified, file.webkitRelativePath].join("\u0000");
}

function memoryDirectorVisitorId(): string {
  const existing = window.localStorage.getItem(visitorStorageKey);
  if (existing) return existing;
  const generated = globalThis.crypto?.randomUUID?.() ?? `visitor-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem(visitorStorageKey, generated);
  return generated;
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function mapWithConcurrency<Item, Result>(
  items: Item[],
  concurrency: number,
  operation: (item: Item, index: number) => Promise<Result>,
  stopActiveOperations?: () => void,
): Promise<Result[]> {
  const results = new Array<Result>(items.length);
  let nextIndex = 0;
  let firstError: unknown;
  async function worker() {
    while (nextIndex < items.length && firstError === undefined) {
      const index = nextIndex++;
      try {
        results[index] = await operation(items[index], index);
      } catch (error) {
        if (firstError === undefined) {
          firstError = error;
          stopActiveOperations?.();
        }
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, worker));
  if (firstError !== undefined) throw firstError;
  return results;
}

async function analyzeMediaFile(file: File, signal: AbortSignal, headers: Record<string, string>): Promise<MediaReview> {
  for (let attempt = 1; attempt <= mediaAnalysisAttempts; attempt += 1) {
    const formData = new FormData();
    formData.append("consent", "true");
    formData.append("media", file);
    const response = await fetch(`${apiBaseUrl}/media/analyze`, { method: "POST", body: formData, headers, signal });
    if (response.ok) return (await response.json()) as MediaReview;
    const isTransient = typeof response.status === "number" && response.status >= 500 && response.status <= 599;
    if (!isTransient || attempt === mediaAnalysisAttempts) {
      throw new Error("We could not use those photos and videos.");
    }
    await wait(mediaAnalysisRetryDelayMs);
  }
  throw new Error("We could not use those photos and videos.");
}

async function extractPreview(blob: Blob, title: string) {
  const archive = unzipSync(new Uint8Array(await blob.arrayBuffer()));
  const mp4Name = Object.keys(archive).find((name) => name.replace(/\/+$/, "").toLowerCase().endsWith(".mp4"));
  if (!mp4Name) {
    throw new Error("The film preview was not included in the export.");
  }
  const videoFile = new File([new Uint8Array(archive[mp4Name])], `${title || "memory-film"}.mp4`, { type: "video/mp4" });
  const coverName = Object.keys(archive).find((name) => /\.(jpe?g)$/i.test(name.replace(/\/+$/, "")));
  const coverFile = coverName
    ? new File([new Uint8Array(archive[coverName])], `${title || "memory-film"}-cover.jpg`, { type: "image/jpeg" })
    : null;
  const videoUrl = URL.createObjectURL(videoFile);
  return {
    file: videoFile,
    posterUrl: coverFile ? URL.createObjectURL(coverFile) : null,
    url: videoUrl,
  };
}

export function ProductionWizard() {
  const [memoryRequest, setMemoryRequest] = useState("");
  const [mediaItems, setMediaItems] = useState<SelectedMedia[]>([]);
  const [hasMediaPermission, setHasMediaPermission] = useState(false);
  const [soundtrackMode, setSoundtrackMode] = useState<SoundtrackMode>("original_song");
  const [productionState, setProductionState] = useState<ProductionState>("ready");
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [posterUrl, setPosterUrl] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [voiceError, setVoiceError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [selectionNotice, setSelectionNotice] = useState("");
  const [progressMessage, setProgressMessage] = useState("");
  const [completionMessage, setCompletionMessage] = useState("");
  const [mediaUpdateMessage, setMediaUpdateMessage] = useState("");
  const [keyboardDragId, setKeyboardDragId] = useState<number | null>(null);
  const generationRef = useRef(0);
  const consentRef = useRef(false);
  const activeRequestRef = useRef<AbortController | null>(null);
  const productionStateRef = useRef<ProductionState>("ready");
  const previewUrlRef = useRef<string | null>(null);
  const posterUrlRef = useRef<string | null>(null);
  const mediaItemsRef = useRef<SelectedMedia[]>([]);
  const nextMediaIdRef = useRef(1);
  const previewSectionRef = useRef<HTMLElement | null>(null);
  const removeButtonRefs = useRef(new Map<number, HTMLButtonElement>());
  const keyboardDragOriginRef = useRef<SelectedMedia[] | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 250, tolerance: 8 } }),
  );

  const mediaFiles = mediaItems.map((item) => item.file);
  const canMakeFilm = memoryRequest.trim().length > 0 && mediaFiles.length > 0 && hasMediaPermission && productionState !== "preparing";
  const isPreparing = productionState === "preparing";

  useEffect(
    () => () => {
      generationRef.current += 1;
      activeRequestRef.current?.abort();
      activeRequestRef.current = null;
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
      if (posterUrlRef.current) URL.revokeObjectURL(posterUrlRef.current);
      mediaItemsRef.current.forEach((item) => URL.revokeObjectURL(item.previewUrl));
      previewUrlRef.current = null;
      posterUrlRef.current = null;
      mediaItemsRef.current = [];
    },
    [],
  );

  useEffect(() => {
    if (!previewUrl) return;
    const previewSection = previewSectionRef.current;
    if (previewSection && typeof previewSection.scrollIntoView === "function") {
      const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
      previewSection.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    }
  }, [previewUrl]);

  function invalidateGeneration() {
    generationRef.current += 1;
    activeRequestRef.current?.abort();
    activeRequestRef.current = null;
  }

  function changeProductionState(nextState: ProductionState) {
    productionStateRef.current = nextState;
    setProductionState(nextState);
  }

  function clearPreview() {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    if (posterUrlRef.current) URL.revokeObjectURL(posterUrlRef.current);
    previewUrlRef.current = null;
    posterUrlRef.current = null;
    setPreviewUrl(null);
    setPosterUrl(null);
    setPreviewFile(null);
    setCompletionMessage("");
  }

  function markRevision() {
    invalidateGeneration();
    setErrorMessage("");
    setCompletionMessage("");
    changeProductionState(previewUrlRef.current ? "preview" : "ready");
  }

  function updateRequest(value: string) {
    setMemoryRequest(value);
    markRevision();
  }

  function selectMedia(files: FileList | null) {
    const nextFiles = Array.from(files ?? []);
    if (nextFiles.length === 0) return;

    const existingFingerprints = new Set(mediaItemsRef.current.map((item) => selectedMediaFingerprint(item.file)));
    const uniqueFiles: File[] = [];
    let duplicateCount = 0;
    for (const file of nextFiles) {
      const fingerprint = selectedMediaFingerprint(file);
      if (existingFingerprints.has(fingerprint)) {
        duplicateCount += 1;
        continue;
      }
      existingFingerprints.add(fingerprint);
      uniqueFiles.push(file);
    }

    if (mediaItemsRef.current.length + uniqueFiles.length > maximumMediaItems) {
      const remaining = maximumMediaItems - mediaItemsRef.current.length;
      setSelectionNotice(
        mediaItemsRef.current.length === 0
          ? "Choose up to 15 photos and videos for one film."
          : `You already selected ${mediaItemsRef.current.length} moments. Choose ${remaining} more at most.`,
      );
      return;
    }
    if (uniqueFiles.length === 0) {
      setSelectionNotice("");
      setMediaUpdateMessage(
        duplicateCount === 1
          ? "That moment is already selected."
          : `${duplicateCount} duplicates were already selected.`,
      );
      return;
    }

    invalidateGeneration();
    const addedItems = uniqueFiles.map((file) => ({
      file,
      id: nextMediaIdRef.current++,
      kind: selectedMediaKind(file),
      previewUrl: URL.createObjectURL(file),
    }));
    const nextItems = [...mediaItemsRef.current, ...addedItems];
    mediaItemsRef.current = nextItems;
    setMediaItems(nextItems);
    setKeyboardDragId(null);
    keyboardDragOriginRef.current = null;
    consentRef.current = false;
    setHasMediaPermission(false);
    setErrorMessage("");
    setCompletionMessage("");
    setSelectionNotice("");
    setMediaUpdateMessage(
      duplicateCount > 0
        ? `Added ${addedItems.length} ${addedItems.length === 1 ? "moment" : "moments"}; ${duplicateCount} ${duplicateCount === 1 ? "duplicate was" : "duplicates were"} already selected.`
        : `Added ${addedItems.length} ${addedItems.length === 1 ? "moment" : "moments"}; ${nextItems.length} selected.`,
    );
    changeProductionState(previewUrlRef.current ? "preview" : "ready");
  }

  function clearSelectedMedia() {
    if (!window.confirm("Clear all selected photos and videos?")) return;
    invalidateGeneration();
    mediaItemsRef.current.forEach((item) => URL.revokeObjectURL(item.previewUrl));
    mediaItemsRef.current = [];
    setMediaItems([]);
    setKeyboardDragId(null);
    keyboardDragOriginRef.current = null;
    consentRef.current = false;
    setHasMediaPermission(false);
    setErrorMessage("");
    setCompletionMessage("");
    setSelectionNotice("");
    setMediaUpdateMessage("All selected photos and videos were cleared.");
    if (uploadInputRef.current) uploadInputRef.current.value = "";
    changeProductionState(previewUrlRef.current ? "preview" : "ready");
    window.setTimeout(() => uploadInputRef.current?.focus(), 0);
  }

  function removeMediaFile(index: number) {
    const removed = mediaItemsRef.current[index];
    if (!removed) return;
    URL.revokeObjectURL(removed.previewUrl);
    const nextItems = mediaItemsRef.current.filter((_, currentIndex) => currentIndex !== index);
    const nextFocusItem = nextItems[Math.min(index, nextItems.length - 1)];
    mediaItemsRef.current = nextItems;
    setMediaItems(nextItems);
    setKeyboardDragId(null);
    keyboardDragOriginRef.current = null;
    setMediaUpdateMessage(`Removed ${removed.file.name}; ${nextItems.length} ${nextItems.length === 1 ? "item remains" : "items remain"}.`);
    markRevision();
    window.setTimeout(() => {
      if (nextFocusItem) removeButtonRefs.current.get(nextFocusItem.id)?.focus();
      else uploadInputRef.current?.focus();
    }, 0);
  }

  function reorderMediaFile(itemId: number, destination: number) {
    const source = mediaItemsRef.current.findIndex((item) => item.id === itemId);
    if (source < 0 || destination < 0 || destination >= mediaItemsRef.current.length || source === destination) return;
    const nextItems = arrayMove(mediaItemsRef.current, source, destination);
    mediaItemsRef.current = nextItems;
    setMediaItems(nextItems);
    setMediaUpdateMessage(`Moved ${nextItems[destination].file.name} to position ${destination + 1} of ${nextItems.length}.`);
    markRevision();
  }

  function finishPointerReorder(event: DragEndEvent) {
    if (productionStateRef.current === "preparing") return;
    if (event.over && event.active.id !== event.over.id) {
      const destination = mediaItemsRef.current.findIndex((item) => item.id === event.over?.id);
      reorderMediaFile(Number(event.active.id), destination);
    }
  }

  function handleKeyboardReorder(event: ReactKeyboardEvent<HTMLButtonElement>, itemId: number) {
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      if (keyboardDragId === itemId) {
        const position = mediaItemsRef.current.findIndex((item) => item.id === itemId) + 1;
        setKeyboardDragId(null);
        keyboardDragOriginRef.current = null;
        setMediaUpdateMessage(`Placed ${mediaItemsRef.current[position - 1].file.name} at position ${position} of ${mediaItemsRef.current.length}.`);
      } else {
        keyboardDragOriginRef.current = [...mediaItemsRef.current];
        setKeyboardDragId(itemId);
        const position = mediaItemsRef.current.findIndex((item) => item.id === itemId) + 1;
        setMediaUpdateMessage(`Picked up ${mediaItemsRef.current[position - 1].file.name} at position ${position} of ${mediaItemsRef.current.length}. Use left and right arrow keys to move it.`);
      }
      return;
    }

    if (event.key === "Escape" && keyboardDragId === itemId) {
      event.preventDefault();
      const originalItems = keyboardDragOriginRef.current;
      if (originalItems) {
        mediaItemsRef.current = originalItems;
        setMediaItems(originalItems);
      }
      setKeyboardDragId(null);
      keyboardDragOriginRef.current = null;
      setMediaUpdateMessage("Reordering canceled.");
      return;
    }

    if (keyboardDragId !== itemId || (event.key !== "ArrowLeft" && event.key !== "ArrowRight")) return;
    event.preventDefault();
    const source = mediaItemsRef.current.findIndex((item) => item.id === itemId);
    const destination = source + (event.key === "ArrowLeft" ? -1 : 1);
    if (destination < 0 || destination >= mediaItemsRef.current.length) {
      setMediaUpdateMessage(`${mediaItemsRef.current[source].file.name} is already ${destination < 0 ? "first" : "last"}.`);
      return;
    }
    reorderMediaFile(itemId, destination);
  }

  function updateSoundtrackMode(mode: SoundtrackMode) {
    setSoundtrackMode(mode);
    markRevision();
  }

  function startVoiceRequest() {
    const speechWindow = window as SpeechRecognitionWindow;
    const SpeechRecognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceError(true);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = navigator.language;
    recognition.onresult = (event) => updateRequest(event.results[0][0].transcript);
    recognition.onerror = () => setVoiceError(true);
    recognition.onend = () => setIsListening(false);
    setVoiceError(false);
    setIsListening(true);
    try {
      recognition.start();
    } catch {
      setIsListening(false);
      setVoiceError(true);
    }
  }

  async function analyzeMedia(
    generation: number,
    signal: AbortSignal,
    headers: Record<string, string>,
    stopActiveOperations: () => void,
  ): Promise<MediaReview[] | null> {
    if (!consentRef.current) throw new Error("Permission is required before making a film.");
    let completed = 0;
    const reviews = await mapWithConcurrency(mediaFiles, mediaAnalysisConcurrency, async (file) => {
      if (generation !== generationRef.current || !consentRef.current || signal.aborted) {
        throw new DOMException("Generation cancelled", "AbortError");
      }
      const review = await analyzeMediaFile(file, signal, headers);
      completed += 1;
      if (generation === generationRef.current) {
        setProgressMessage(`Checked ${completed} of ${mediaFiles.length} moments…`);
      }
      return review;
    }, stopActiveOperations);
    if (generation !== generationRef.current || !consentRef.current) return null;
    const selectionResponses = await mapWithConcurrency(
      reviews,
      mediaAnalysisConcurrency,
      (review) => {
        if (generation !== generationRef.current || !consentRef.current || signal.aborted) {
          throw new DOMException("Generation cancelled", "AbortError");
        }
        return fetch(`${apiBaseUrl}/media/${review.media_id}/decision`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "selected", reason: "Chosen for this film" }),
          signal,
        });
      },
      stopActiveOperations,
    );
    if (selectionResponses.some((response) => !response.ok)) throw new Error("We could not select those photos and videos.");
    return generation === generationRef.current ? reviews : null;
  }

  async function makeFilm() {
    if (!canMakeFilm) return;
    activeRequestRef.current?.abort();
    const generation = ++generationRef.current;
    const requestController = new AbortController();
    activeRequestRef.current = requestController;
    setErrorMessage("");
    setCompletionMessage("");
    setProgressMessage(`Checking ${mediaFiles.length} moments…`);
    changeProductionState("preparing");
    const visitorId = memoryDirectorVisitorId();
    let admissionId: string | null = null;

    try {
      const admissionResponse = await fetch(`${apiBaseUrl}/usage/admissions`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Memory-Director-Visitor": visitorId },
        body: JSON.stringify({ soundtrack_mode: soundtrackMode }),
        signal: requestController.signal,
      });
      if (!admissionResponse.ok) {
        const errorBody = (await admissionResponse.json().catch(() => null)) as { detail?: unknown } | null;
        throw new UserFacingExportError(typeof errorBody?.detail === "string" ? errorBody.detail : "Please try again later.");
      }
      admissionId = ((await admissionResponse.json()) as { admission_id: string }).admission_id;
      const admissionHeaders = {
        "X-Memory-Director-Visitor": visitorId,
        "X-Memory-Director-Admission": admissionId,
      };
      const reviews = await analyzeMedia(generation, requestController.signal, admissionHeaders, () => requestController.abort());
      if (!reviews || !consentRef.current || generation !== generationRef.current) return;
      setProgressMessage("Choosing the best moments…");
      const storyboardResponse = await fetch(`${apiBaseUrl}/storyboards`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...admissionHeaders },
        signal: requestController.signal,
        body: JSON.stringify({
          occasion: memoryRequest,
          moods: ["warm", "cheerful"],
          media_count: mediaFiles.length,
          media_consent: hasMediaPermission,
        }),
      });
      if (!storyboardResponse.ok) throw new Error("We could not make your film.");
      const nextStoryboard = (await storyboardResponse.json()) as Storyboard;
      if (!consentRef.current || generation !== generationRef.current) return;

      const renderResponse = await fetch(`${apiBaseUrl}/renders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: requestController.signal,
        body: JSON.stringify({ storyboard: nextStoryboard, approved: true }),
      });
      if (!renderResponse.ok) throw new Error("We could not make your film.");

      setProgressMessage("Making your video and sound…");
      const exportForm = new FormData();
      exportForm.append("title", nextStoryboard.title);
      exportForm.append("caption", nextStoryboard.caption);
      exportForm.append("approved", "true");
      exportForm.append("soundtrack_mode", soundtrackMode);
      reviews.forEach((media) => exportForm.append("media_ids", media.media_id));
      if (soundtrackMode === "original_song") {
        [memoryRequest, nextStoryboard.title, nextStoryboard.caption].forEach((detail) => exportForm.append("memory_details", detail));
        exportForm.append("requested_style", nextStoryboard.music_direction ?? "warm acoustic");
      }
      const exportResponse = await fetch(`${apiBaseUrl}/renders/export`, {
        method: "POST",
        headers: admissionHeaders,
        body: exportForm,
        signal: requestController.signal,
      });
      if (!exportResponse.ok) {
        const errorBody = (await exportResponse.json().catch(() => null)) as { detail?: unknown } | null;
        const detail = typeof errorBody?.detail === "string" ? errorBody.detail.trim() : "";
        if (detail) throw new UserFacingExportError(detail);
        throw new Error("We could not make your film.");
      }
      const preview = await extractPreview(await exportResponse.blob(), nextStoryboard.title);
      if (!consentRef.current || generation !== generationRef.current) {
        URL.revokeObjectURL(preview.url);
        if (preview.posterUrl) URL.revokeObjectURL(preview.posterUrl);
        return;
      }
      clearPreview();
      setStoryboard(nextStoryboard);
      setPreviewFile(preview.file);
      previewUrlRef.current = preview.url;
      posterUrlRef.current = preview.posterUrl;
      setPreviewUrl(preview.url);
      setPosterUrl(preview.posterUrl);
      if (activeRequestRef.current === requestController) activeRequestRef.current = null;
      changeProductionState("preview");
    } catch (error) {
      requestController.abort();
      if (generation === generationRef.current) {
        generationRef.current += 1;
        if (activeRequestRef.current === requestController) activeRequestRef.current = null;
        setErrorMessage(
          error instanceof UserFacingExportError ? error.message : "We could not make your film. Please try again.",
        );
        changeProductionState("error");
      }
    } finally {
      if (admissionId) {
        void fetch(`${apiBaseUrl}/usage/admissions/${admissionId}/release`, {
          method: "POST",
          headers: {
            "X-Memory-Director-Visitor": visitorId,
            "X-Memory-Director-Admission": admissionId,
          },
          keepalive: true,
        }).catch(() => undefined);
      }
    }
  }

  function saveVideo() {
    if (!previewFile || !previewUrl) return;
    const link = document.createElement("a");
    link.href = previewUrl;
    link.download = previewFile.name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setCompletionMessage("Video saved to this device.");
    changeProductionState("saved");
  }

  async function shareVideo() {
    if (!previewFile) return;
    if (!navigator.share || (navigator.canShare && !navigator.canShare({ files: [previewFile] }))) {
      setCompletionMessage("Save the video first, then send it from WhatsApp or WeChat.");
      return;
    }
    try {
      await navigator.share({ files: [previewFile], title: storyboard?.title ?? "Memory film" });
      setCompletionMessage("Your video is still here if you want to save or share it again.");
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setCompletionMessage("Save the video first, then send it from WhatsApp or WeChat.");
      }
    }
  }

  return (
    <section aria-label="Memory film creator" className="wizard">
      <fieldset aria-label="Make your memory film" className={`wizard__stage wizard__stage--request${isPreparing ? " is-preparing" : ""}`} disabled={isPreparing}>
            <header className="wizard__header">
              <div>
                <p className="wizard__eyebrow">A short film, made for you</p>
                <h2 id="production-title">Start with the moments you love.</h2>
              </div>
              <p>Choose photos or videos from your phone.</p>
            </header>

            <section className="wizard__step" aria-labelledby="choose-title">
              <div className="wizard__step-heading">
                <h3 id="choose-title">1. Choose photos and videos</h3>
                <span>Up to 15</span>
              </div>
              <label className="wizard__media" htmlFor="memory-media">
                <span className="wizard__media-icon" aria-hidden="true"><Images /></span>
                <strong>Choose from this device</strong>
                <small>Photos and videos stay under your control.</small>
                <input accept="image/*,video/*" aria-label="Choose photos and videos" id="memory-media" multiple onChange={(event) => { selectMedia(event.target.files); event.currentTarget.value = ""; }} ref={uploadInputRef} type="file" />
              </label>

              {mediaItems.length > 0 ? (
                <>
                  <DndContext collisionDetection={closestCenter} onDragEnd={finishPointerReorder} sensors={sensors}>
                    <SortableContext items={mediaItems.map((item) => item.id)} strategy={horizontalListSortingStrategy}>
                      <div className="wizard__media-scroll">
                        <ul aria-describedby="media-reorder-help" aria-label="Selected media" className="wizard__media-strip">
                          {mediaItems.map((item, index) => (
                            <SortableMediaCard
                              isPreparing={isPreparing}
                              isKeyboardGrabbed={keyboardDragId === item.id}
                              item={item}
                              key={item.id}
                              onKeyboardReorder={handleKeyboardReorder}
                              onRemove={() => removeMediaFile(index)}
                              position={index + 1}
                              registerRemoveButton={(element) => {
                                if (element) removeButtonRefs.current.set(item.id, element);
                                else removeButtonRefs.current.delete(item.id);
                              }}
                              total={mediaItems.length}
                            />
                          ))}
                        </ul>
                      </div>
                    </SortableContext>
                  </DndContext>
                  <div className="wizard__media-tools">
                    <p className="wizard__media-reorder-help" id="media-reorder-help">Drag to change the order. On a phone, press and hold, then move.</p>
                    <button aria-label="Clear all selected media" className="button wizard__clear-media" onClick={clearSelectedMedia} type="button"><X aria-hidden="true" />Clear all</button>
                  </div>
                </>
              ) : (
                <div className="wizard__media-help"><CircleCheck aria-hidden="true" /><span>Your selected moments will appear here. Remove any one before you make the film.</span></div>
              )}
              {mediaUpdateMessage && <p aria-live="polite" className="sr-only" role="status">{mediaUpdateMessage}</p>}
            </section>

            <section className="wizard__step" aria-labelledby="story-title">
              <div className="wizard__step-heading"><h3 id="story-title">2. Tell us about it</h3><span className="wizard__step-note">Type or speak</span></div>
              <label className="wizard__request" htmlFor="memory-request">
                <span className="sr-only">Your memory request</span>
                <div className="wizard__input-wrap">
                  <textarea aria-label="Your memory request" id="memory-request" onChange={(event) => updateRequest(event.target.value)} placeholder="For example: a happy afternoon with the grandchildren." rows={2} value={memoryRequest} />
                  <div className="wizard__input-actions">
                    <button aria-label="Clear request" className="button button--clear" onClick={() => updateRequest("")} type="button"><X aria-hidden="true" />Clear</button>
                    <button aria-label="Voice input" aria-pressed={isListening} className={`button button--voice${isListening ? " is-listening" : ""}`} onClick={startVoiceRequest} type="button"><Mic aria-hidden="true" /></button>
                  </div>
                </div>
              </label>
              <p className="wizard__request-help">Please check your words before making the film.</p>
            </section>

            <section className="wizard__step" aria-labelledby="music-title">
              <div className="wizard__step-heading"><h3 id="music-title">3. Choose the sound</h3><span className="wizard__music-note">Part of the story</span></div>
              <p className="wizard__music-intro">We can make a new little song for this memory, or choose a gentle background sound.</p>
              <fieldset className="wizard__soundtrack">
                <legend className="sr-only">Sound</legend>
                <label className={soundtrackMode === "original_song" ? "is-selected" : ""}><span><input aria-label="Original AI song" checked={soundtrackMode === "original_song"} name="soundtrack" onChange={() => updateSoundtrackMode("original_song")} type="radio" /><strong>Original AI song</strong></span><small>A new song for this memory</small></label>
                <label className={soundtrackMode === "instrumental" ? "is-selected" : ""}><span><input aria-label="Gentle instrumental" checked={soundtrackMode === "instrumental"} name="soundtrack" onChange={() => updateSoundtrackMode("instrumental")} type="radio" /><strong>Gentle instrumental</strong></span><small>Warm background music</small></label>
                <label className={soundtrackMode === "no_sound" ? "is-selected" : ""}><span><input aria-label="No music" checked={soundtrackMode === "no_sound"} name="soundtrack" onChange={() => updateSoundtrackMode("no_sound")} type="radio" /><strong>No music</strong></span><small>Silent film</small></label>
              </fieldset>
            </section>

            <label className="wizard__consent" htmlFor="media-permission">
              <input aria-label="I have permission to use these media." checked={hasMediaPermission} id="media-permission" onChange={(event) => { consentRef.current = event.target.checked; setHasMediaPermission(event.target.checked); }} type="checkbox" />
              <span>I have permission to use these photos and videos.</span>
            </label>
      </fieldset>

      <section aria-label={isPreparing ? "Making your film" : "Preview information"} aria-live={isPreparing ? "polite" : undefined} className={`wizard__preview-callout${isPreparing ? " is-preparing" : ""}`} role={isPreparing ? "status" : undefined}>
        <div className="wizard__preview-copy"><span aria-hidden="true"><Play /></span><div><h3>{isPreparing ? "Making your film…" : previewUrl ? "Your film is below" : "Watch before you save"}</h3><p>{isPreparing ? progressMessage : previewUrl ? "Change anything above, then choose Make again." : "Your 60-second film appears here after it is made."}</p></div></div>
        <span className="wizard__preview-badge">{isPreparing ? `${mediaFiles.length} moments` : previewUrl ? "Ready to watch" : "Preview first"}</span>
      </section>

      <div className="wizard__action-bar">
        <div>
          <button className="button button--primary" disabled={!canMakeFilm} onClick={makeFilm} type="button">{isPreparing ? "Please wait…" : productionState === "error" ? "Try again" : previewUrl ? "Make again" : "Make my film"}<Sparkles aria-hidden="true" /></button>
        </div>
      </div>

      {storyboard && previewUrl && (
        <section aria-label="Your film preview" className="wizard__preview" ref={previewSectionRef}>
          <h3>Your memory film</h3>
          <video
            aria-label="Your memory film preview"
            controls
            onEnded={(event) => event.currentTarget.load()}
            playsInline
            poster={posterUrl ?? undefined}
            src={previewUrl}
          />
          <h4>{storyboard.title}</h4><p>{storyboard.caption}</p>
          <div className="wizard__preview-actions">
            <button className="button button--primary" onClick={saveVideo} type="button"><Download aria-hidden="true" />Save video</button>
            <button className="button button--secondary" onClick={shareVideo} type="button"><Share2 aria-hidden="true" />Share video</button>
          </div>
          <p className="wizard__share-help">Choose WhatsApp, WeChat, or another app from your phone&apos;s share menu.</p>
          {completionMessage && <p aria-live="polite" className="wizard__saved" role="status">{completionMessage}</p>}
        </section>
      )}

      {(errorMessage || selectionNotice || voiceError) && (
        <p aria-live="polite" className="wizard__status" role="status">
          {errorMessage}
          {selectionNotice}
          {voiceError && "Voice input is not available. You can type your request instead."}
        </p>
      )}
    </section>
  );
}
