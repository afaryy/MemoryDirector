"use client";

import { unzipSync } from "fflate";
import { useRef, useState } from "react";

type Storyboard = {
  title: string;
  caption: string;
  music_direction?: string;
};

type MediaReview = { media_id: string };
type ProductionState = "ready" | "preparing" | "preview" | "error" | "saved";
type SoundtrackMode = "original_song" | "instrumental" | "no_sound";

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

async function extractPreview(blob: Blob, title: string) {
  const archive = unzipSync(new Uint8Array(await blob.arrayBuffer()));
  const mp4Name = Object.keys(archive).find((name) => name.replace(/\/+$/, "").toLowerCase().endsWith(".mp4"));
  if (!mp4Name) {
    throw new Error("The film preview was not included in the export.");
  }
  const videoFile = new File([new Uint8Array(archive[mp4Name])], `${title || "memory-film"}.mp4`, { type: "video/mp4" });
  return { file: videoFile, url: URL.createObjectURL(videoFile) };
}

export function ProductionWizard() {
  const [memoryRequest, setMemoryRequest] = useState("");
  const [mediaFiles, setMediaFiles] = useState<File[]>([]);
  const [hasMediaPermission, setHasMediaPermission] = useState(false);
  const [soundtrackMode, setSoundtrackMode] = useState<SoundtrackMode>("instrumental");
  const [productionState, setProductionState] = useState<ProductionState>("ready");
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [voiceError, setVoiceError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [selectionNotice, setSelectionNotice] = useState("");
  const generationRef = useRef(0);
  const consentRef = useRef(false);

  const canMakeFilm = memoryRequest.trim().length > 0 && mediaFiles.length > 0 && hasMediaPermission && productionState !== "preparing";

  function clearPreview() {
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });
    setPreviewFile(null);
  }

  function returnToReady() {
    generationRef.current += 1;
    clearPreview();
    setStoryboard(null);
    setErrorMessage("");
    setProductionState("ready");
  }

  function updateRequest(value: string) {
    setMemoryRequest(value);
    if (productionState !== "ready") returnToReady();
  }

  function selectMedia(files: FileList | null) {
    const nextFiles = Array.from(files ?? []);
    if (nextFiles.length > 15) {
      setSelectionNotice("Choose up to 15 photos and videos for one film.");
      return;
    }
    generationRef.current += 1;
    clearPreview();
    setMediaFiles(nextFiles);
    consentRef.current = false;
    setHasMediaPermission(false);
    setStoryboard(null);
    setErrorMessage("");
    setSelectionNotice("");
    setProductionState("ready");
  }

  function removeMediaFile(index: number) {
    generationRef.current += 1;
    clearPreview();
    setMediaFiles((current) => current.filter((_, currentIndex) => currentIndex !== index));
    consentRef.current = false;
    setHasMediaPermission(false);
    setStoryboard(null);
    setErrorMessage("");
    setProductionState("ready");
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

  async function analyzeMedia(generation: number): Promise<MediaReview[] | null> {
    if (!consentRef.current) throw new Error("Permission is required before making a film.");
    const responses = await Promise.all(
      mediaFiles.map(async (file) => {
        const formData = new FormData();
        formData.append("consent", "true");
        formData.append("media", file);
        return fetch(`${apiBaseUrl}/media/analyze`, { method: "POST", body: formData });
      }),
    );
    if (responses.some((response) => !response.ok)) throw new Error("We could not use those photos and videos.");
    const reviews = (await Promise.all(responses.map((response) => response.json()))) as MediaReview[];
    return generation === generationRef.current ? reviews : null;
  }

  async function makeFilm() {
    if (!canMakeFilm) return;
    const generation = ++generationRef.current;
    clearPreview();
    setStoryboard(null);
    setErrorMessage("");
    setProductionState("preparing");

    try {
      const reviews = await analyzeMedia(generation);
      if (!reviews || !consentRef.current || generation !== generationRef.current) return;
      const storyboardResponse = await fetch(`${apiBaseUrl}/storyboards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
        body: JSON.stringify({ storyboard: nextStoryboard, approved: true }),
      });
      if (!renderResponse.ok) throw new Error("We could not make your film.");

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
      const exportResponse = await fetch(`${apiBaseUrl}/renders/export`, { method: "POST", body: exportForm });
      if (!exportResponse.ok) throw new Error("We could not make your film.");
      const preview = await extractPreview(await exportResponse.blob(), nextStoryboard.title);
      if (!consentRef.current || generation !== generationRef.current) {
        URL.revokeObjectURL(preview.url);
        return;
      }
      setStoryboard(nextStoryboard);
      setPreviewFile(preview.file);
      setPreviewUrl(preview.url);
      setProductionState("preview");
    } catch {
      if (generation === generationRef.current) {
        setErrorMessage("We could not make your film. Please try again.");
        setProductionState("error");
      }
    }
  }

  async function saveAndShare() {
    if (!previewFile || !previewUrl) return;
    try {
      if (navigator.share && (!navigator.canShare || navigator.canShare({ files: [previewFile] }))) {
        await navigator.share({ files: [previewFile], title: storyboard?.title ?? "Memory film" });
      } else {
        const link = document.createElement("a");
        link.href = previewUrl;
        link.download = previewFile.name;
        link.click();
      }
      setProductionState("saved");
    } catch {
      // A dismissed native share sheet leaves the completed preview available.
    }
  }

  return (
    <section aria-labelledby="production-title" className="wizard">
      <header className="wizard__header">
        <h2 id="production-title">Make a memory film</h2>
        <p>Describe the moment, choose photos and videos, then save your film.</p>
      </header>

      {(productionState === "ready" || productionState === "error") && (
        <section aria-label="Make your film" className="wizard__stage wizard__stage--request">
          <label className="wizard__request" htmlFor="memory-request">
            <span>Your memory request</span>
            <div className="wizard__input-wrap">
              <textarea id="memory-request" onChange={(event) => updateRequest(event.target.value)} placeholder="For example: a happy afternoon with the grandchildren." rows={2} value={memoryRequest} />
              <button aria-label="Voice input" aria-pressed={isListening} className={`button button--voice${isListening ? " is-listening" : ""}`} onClick={startVoiceRequest} type="button">
                <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 14.5a3.5 3.5 0 0 0 3.5-3.5V6a3.5 3.5 0 1 0-7 0v5a3.5 3.5 0 0 0 3.5 3.5Zm6-3.5a1 1 0 0 0-2 0 4 4 0 0 1-8 0 1 1 0 0 0-2 0 6 6 0 0 0 5 5.91V19H8a1 1 0 0 0 0 2h8a1 1 0 0 0 0-2h-3v-2.09A6 6 0 0 0 18 11Z" /></svg>
              </button>
            </div>
          </label>

          <label className="wizard__media" htmlFor="memory-media">
            <span>Choose photos and videos</span>
            <input accept="image/*,video/*" id="memory-media" multiple onChange={(event) => selectMedia(event.target.files)} type="file" />
          </label>
          <p className="wizard__media-help">Choose up to 15 items from this device. You can remove anything before making the film.</p>

          {mediaFiles.length > 0 && (
            <ul aria-label="Selected media" className="wizard__selected-files">
              {mediaFiles.map((file, index) => (
                <li key={`${file.name}-${index}`}><span>{file.name}</span><button className="button button--remove" onClick={() => removeMediaFile(index)} type="button">Remove {file.name}</button></li>
              ))}
            </ul>
          )}

          <fieldset className="wizard__soundtrack">
            <legend>Sound</legend>
            <label><input checked={soundtrackMode === "original_song"} name="soundtrack" onChange={() => setSoundtrackMode("original_song")} type="radio" />Original AI song</label>
            <label><input checked={soundtrackMode === "instrumental"} name="soundtrack" onChange={() => setSoundtrackMode("instrumental")} type="radio" />Gentle instrumental</label>
            <label><input checked={soundtrackMode === "no_sound"} name="soundtrack" onChange={() => setSoundtrackMode("no_sound")} type="radio" />No music</label>
          </fieldset>

          <label className="wizard__consent" htmlFor="media-permission">
            <input checked={hasMediaPermission} id="media-permission" onChange={(event) => { consentRef.current = event.target.checked; setHasMediaPermission(event.target.checked); }} type="checkbox" />
            <span>I have permission to use these media.</span>
          </label>
          {productionState === "error" ? (
            <button className="button button--primary" onClick={makeFilm} type="button">Try again</button>
          ) : (
            <button className="button button--primary" disabled={!canMakeFilm} onClick={makeFilm} type="button">Make my film</button>
          )}
        </section>
      )}

      {productionState === "preparing" && (
        <section aria-label="Making your film" className="wizard__stage wizard__stage--waiting">
          <h3>Making your film…</h3><p>We are choosing the best moments and preparing your sound.</p>
        </section>
      )}

      {(productionState === "preview" || productionState === "saved") && storyboard && previewUrl && (
        <section aria-label="Your film preview" className="wizard__preview">
          <h3>Your memory film</h3>
          <video aria-label="Your memory film preview" controls playsInline src={previewUrl} />
          <h4>{storyboard.title}</h4><p>{storyboard.caption}</p>
          <button className="button button--primary" onClick={saveAndShare} type="button">Save &amp; share</button>
          {productionState === "saved" && <p className="wizard__saved">Your film is ready. You choose where it goes next.</p>}
        </section>
      )}

      <p aria-live="polite" className="wizard__status" role="status">
        {productionState === "preparing" && "Making your film…"}
        {errorMessage}
        {selectionNotice}
        {voiceError && "Voice input is not available. You can type your request instead."}
      </p>
    </section>
  );
}
