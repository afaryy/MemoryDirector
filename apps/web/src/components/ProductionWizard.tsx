"use client";

import { useRef, useState } from "react";

type Storyboard = {
  title: string;
  caption: string;
  music_direction?: string;
  preference_explanation?: string;
  preference_evidence_count?: number;
};

type PrivacyFlag = "contains_face" | "contains_text" | "possible_sensitive_document";

type MediaReview = {
  media_id: string;
  description: string;
  privacy_flags: PrivacyFlag[];
  decision_status: "unselected" | "selected" | "held_back";
};

type SpeechResultEvent = {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
};

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

const privacyFlagLabels: Record<PrivacyFlag, string> = {
  contains_face: "Face visible",
  contains_text: "Text visible",
  possible_sensitive_document: "Possible sensitive document",
};

export function ProductionWizard() {
  const [approved, setApproved] = useState(false);
  const [memoryRequest, setMemoryRequest] = useState("");
  const [mediaFiles, setMediaFiles] = useState<File[]>([]);
  const [mediaReviews, setMediaReviews] = useState<MediaReview[]>([]);
  const [hasMediaPermission, setHasMediaPermission] = useState(false);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [isPlanning, setIsPlanning] = useState(false);
  const [planError, setPlanError] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [voiceError, setVoiceError] = useState(false);
  const [renderStatus, setRenderStatus] = useState<"idle" | "submitting" | "ready" | "error">("idle");
  const [exportHref, setExportHref] = useState<string | null>(null);
  const [pendingDecisionMediaId, setPendingDecisionMediaId] = useState<string | null>(null);
  const requestGeneration = useRef(0);
  const consentRef = useRef(false);

  const allMediaReviewed = mediaReviews.length === mediaFiles.length && mediaReviews.every((media) => media.decision_status !== "unselected");
  const selectedMedia = mediaReviews.filter((media) => media.decision_status === "selected");
  const selectedMediaCount = selectedMedia.length;

  function clearExport() {
    setExportHref((current) => {
      if (current && typeof URL.revokeObjectURL === "function") {
        URL.revokeObjectURL(current);
      }
      return null;
    });
  }

  function resetDerivedState() {
    setIsPlanning(false);
    setStoryboard(null);
    setApproved(false);
    setPlanError(false);
    setRenderStatus("idle");
    setMediaReviews([]);
    setPendingDecisionMediaId(null);
    clearExport();
  }

  function updateMemoryRequest(value: string) {
    requestGeneration.current += 1;
    setMemoryRequest(value);
    resetDerivedState();
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
    recognition.onresult = (event) => updateMemoryRequest(event.results[0][0].transcript);
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
    if (!consentRef.current) {
      throw new Error("Explicit media consent is required.");
    }
    const responses = await Promise.all(
      mediaFiles.map(async (file) => {
        const formData = new FormData();
        formData.append("consent", String(consentRef.current));
        formData.append("media", file);
        return fetch(`${apiBaseUrl}/media/analyze`, { method: "POST", body: formData });
      }),
    );
    if (responses.some((response) => !response.ok)) {
      throw new Error("Media analysis was not accepted.");
    }
    const reviews = (await Promise.all(responses.map((response) => response.json()))) as MediaReview[];
    if (generation !== requestGeneration.current) {
      return null;
    }
    setMediaReviews(reviews);
    return reviews;
  }

  async function createPlan() {
    const generation = requestGeneration.current;
    setIsPlanning(true);
    setPlanError(false);
    setApproved(false);
    setRenderStatus("idle");
    clearExport();

    try {
      const reviews = await analyzeMedia(generation);
      if (!reviews || generation !== requestGeneration.current) {
        return;
      }
      const response = await fetch(`${apiBaseUrl}/storyboards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          occasion: memoryRequest,
          moods: ["warm", "cheerful"],
          media_count: mediaFiles.length,
          media_consent: hasMediaPermission,
        }),
      });

      if (!response.ok) {
        throw new Error("Storyboard request was not accepted.");
      }

      if (generation !== requestGeneration.current) {
        return;
      }
      setStoryboard((await response.json()) as Storyboard);
    } catch {
      if (generation === requestGeneration.current) {
        setStoryboard(null);
        setPlanError(true);
      }
    } finally {
      if (generation === requestGeneration.current) {
        setIsPlanning(false);
      }
    }
  }

  async function updateMediaDecision(mediaId: string, status: "selected" | "held_back") {
    if (pendingDecisionMediaId !== null || renderStatus === "submitting") {
      return;
    }
    const generation = ++requestGeneration.current;
    setPendingDecisionMediaId(mediaId);
    setApproved(false);
    setRenderStatus("idle");
    clearExport();
    try {
      const response = await fetch(`${apiBaseUrl}/media/${mediaId}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, reason: status === "selected" ? "User kept this item." : "User held this item back." }),
      });
      if (!response.ok) {
        throw new Error("Media decision was not accepted.");
      }
      if (generation !== requestGeneration.current) {
        return;
      }
      setMediaReviews((current) => current.map((media) => (media.media_id === mediaId ? { ...media, decision_status: status } : media)));
    } catch {
      if (generation === requestGeneration.current) {
        setPlanError(true);
      }
    } finally {
      if (generation === requestGeneration.current) {
        setPendingDecisionMediaId(null);
      }
    }
  }

  async function submitRenderRequest() {
    if (!consentRef.current || !storyboard || selectedMedia.length === 0) {
      return;
    }

    const generation = requestGeneration.current;
    clearExport();
    setRenderStatus("submitting");

    try {
      const response = await fetch(`${apiBaseUrl}/renders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          storyboard,
          approved: true,
        }),
      });

      if (!response.ok) {
        throw new Error("Render request was not accepted.");
      }
      if (generation !== requestGeneration.current || !consentRef.current) {
        return;
      }

      const exportForm = new FormData();
      exportForm.append("title", storyboard.title);
      exportForm.append("caption", storyboard.caption);
      exportForm.append("approved", "true");
      selectedMedia.forEach((media) => exportForm.append("media_ids", media.media_id));
      const exportResponse = await fetch(`${apiBaseUrl}/renders/export`, { method: "POST", body: exportForm });
      if (!exportResponse.ok) {
        throw new Error("Video export was not accepted.");
      }
      const exportBlob = await exportResponse.blob();
      if (generation !== requestGeneration.current || !consentRef.current) {
        return;
      }
      setExportHref(typeof URL.createObjectURL === "function" ? URL.createObjectURL(exportBlob) : null);

      setRenderStatus("ready");
    } catch {
      if (generation === requestGeneration.current) {
        setRenderStatus("error");
      }
    }
  }

  return (
    <section aria-labelledby="production-title" className="wizard">
      <header className="wizard__header">
        <p className="wizard__step">01 / YOUR REQUEST</p>
        <h2 id="production-title">Start with what you want to remember.</h2>
        <p>
          Tell Memory Director about the occasion, then review every suggestion before a video is made.
        </p>
      </header>

      <label className="wizard__request" htmlFor="memory-request">
        <span>What would you like to make?</span>
        <textarea
          id="memory-request"
          placeholder="For example: Make a cheerful travel video."
          rows={3}
          value={memoryRequest}
          onChange={(event) => updateMemoryRequest(event.target.value)}
        />
      </label>
      <button
        aria-pressed={isListening}
        className="button button--secondary"
        onClick={startVoiceRequest}
        type="button"
      >
        {isListening ? "Listening…" : "Speak your request"}
      </button>

      <label className="wizard__media" htmlFor="memory-media">
        <span>Choose photos and videos</span>
        <input
          accept="image/*,video/*"
          id="memory-media"
          multiple
          onChange={(event) => {
            requestGeneration.current += 1;
            setMediaFiles(Array.from(event.target.files ?? []));
            consentRef.current = false;
            setHasMediaPermission(false);
            resetDerivedState();
          }}
          type="file"
        />
      </label>
      {mediaFiles.length > 0 && (
        <p className="wizard__media-count">
          {mediaFiles.length} {mediaFiles.length === 1 ? "item" : "items"} selected from your device.
        </p>
      )}
      <label className="wizard__consent" htmlFor="media-permission">
        <input
          checked={hasMediaPermission}
          id="media-permission"
          onChange={(event) => {
            const granted = event.target.checked;
            consentRef.current = granted;
            setHasMediaPermission(granted);
            if (!granted) {
              requestGeneration.current += 1;
              resetDerivedState();
            }
          }}
          type="checkbox"
        />
        <span>I have permission to use these media.</span>
      </label>

      <button
        className="button button--secondary"
        disabled={!memoryRequest.trim() || mediaFiles.length === 0 || !hasMediaPermission || isPlanning}
        onClick={createPlan}
        type="button"
      >
        {isPlanning ? "Reviewing your media…" : "Create a plan"}
      </button>

      {mediaReviews.length > 0 && (
        <section aria-label="Media review" className="wizard__media-review">
          <p className="wizard__step">02 / MEDIA REVIEW</p>
          <h3>Check each item before your plan is approved.</h3>
          {mediaReviews.map((media) => (
            <article className="wizard__media-card" key={media.media_id}>
              <p>{media.description}</p>
              {media.privacy_flags.length > 0 && (
                <ul aria-label="Privacy flags" className="wizard__privacy-flags">
                  {media.privacy_flags.map((flag) => <li key={flag}>{privacyFlagLabels[flag]}</li>)}
                </ul>
              )}
              <div className="wizard__media-actions">
                <button
                  aria-pressed={media.decision_status === "selected"}
                  className="button button--secondary"
                  disabled={pendingDecisionMediaId !== null || renderStatus === "submitting"}
                  onClick={() => updateMediaDecision(media.media_id, "selected")}
                  type="button"
                >
                  {media.decision_status === "selected" ? "Kept" : "Keep this item"}
                </button>
                <button
                  aria-pressed={media.decision_status === "held_back"}
                  className="button button--secondary"
                  disabled={pendingDecisionMediaId !== null || renderStatus === "submitting"}
                  onClick={() => updateMediaDecision(media.media_id, "held_back")}
                  type="button"
                >
                  {media.decision_status === "held_back" ? "Held back" : "Hold this item back"}
                </button>
              </div>
            </article>
          ))}
        </section>
      )}

      {storyboard && (
        <section aria-label="Generated plan" className="wizard__plan">
          <p className="wizard__step">03 / YOUR PLAN</p>
        <h3>{storyboard.title}</h3>
        <p>{storyboard.caption}</p>
        {storyboard.music_direction && (
          <div className="wizard__recommendation" aria-label="Music recommendation">
            <strong>Suggested sound: {storyboard.music_direction}</strong>
            {storyboard.preference_explanation && <p>{storyboard.preference_explanation}</p>}
          </div>
        )}
      </section>
      )}

      <section aria-label="Approval" className="wizard__approval">
        <div>
          <p className="wizard__step">04 / REVIEW</p>
          <h3>Your plan stays in your control.</h3>
          <p>Nothing is exported until you approve the plan.</p>
        </div>
        <button
          className="button button--secondary"
          disabled={!storyboard || !allMediaReviewed || selectedMediaCount === 0}
          onClick={() => setApproved(true)}
          type="button"
        >
          Approve plan
        </button>
      </section>

      <button
        className="button button--primary"
        disabled={!approved || renderStatus === "submitting"}
        onClick={submitRenderRequest}
        type="button"
      >
        Make this video
      </button>
      <p aria-live="polite" className="wizard__status" id="voice-input-status" role="status">
        {planError && "We could not create your plan. Please try again."}
        {voiceError && "Voice input is not available. You can type your request instead."}
        {renderStatus === "submitting" && "Preparing your approved video request…"}
        {renderStatus === "ready" && "Your approved video request is ready."}
        {renderStatus === "error" && "We could not prepare your video request. Please try again."}
      </p>
      {exportHref && (
        <a className="button button--secondary wizard__download" download="memory-director-export.zip" href={exportHref}>
          Download your video package
        </a>
      )}
    </section>
  );
}
