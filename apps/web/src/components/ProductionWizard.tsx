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

type MediaMode = "manual" | "auto";
type SoundtrackMode = "original_song" | "instrumental" | "no_sound";

type FindFilters = {
  dateFrom: string;
  dateTo: string;
  place: string;
  people: string;
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
  const [mediaMode, setMediaMode] = useState<MediaMode>("manual");
  const [soundtrackMode, setSoundtrackMode] = useState<SoundtrackMode>("instrumental");
  const [findFilters, setFindFilters] = useState<FindFilters>({ dateFrom: "", dateTo: "", place: "", people: "" });
  const [findStatus, setFindStatus] = useState("");
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
  const mediaInputRef = useRef<HTMLInputElement>(null);

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

  function removeMediaFile(index: number) {
    requestGeneration.current += 1;
    setMediaFiles((current) => current.filter((_, currentIndex) => currentIndex !== index));
    consentRef.current = false;
    setHasMediaPermission(false);
    resetDerivedState();
  }

  function changeMediaMode(mode: MediaMode) {
    setMediaMode(mode);
    setFindStatus("");
    setApproved(false);
    setRenderStatus("idle");
    clearExport();
  }

  function findMoments() {
    if (mediaFiles.length === 0) {
      setFindStatus("Choose photos and videos first, then we can find moments within them.");
      return;
    }
    const criteria = [
      findFilters.dateFrom && `from ${findFilters.dateFrom}`,
      findFilters.dateTo && `to ${findFilters.dateTo}`,
      findFilters.place && `around ${findFilters.place}`,
      findFilters.people && `with ${findFilters.people}`,
    ].filter(Boolean).join(", ");
    setFindStatus(
      criteria
        ? `Search scope set: ${mediaFiles.length} selected ${mediaFiles.length === 1 ? "item" : "items"}. We will look ${criteria}.`
        : `Search scope set: ${mediaFiles.length} selected ${mediaFiles.length === 1 ? "item" : "items"}.`,
    );
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
          occasion: [
            memoryRequest,
            mediaMode === "auto" && findFilters.dateFrom ? `Date from: ${findFilters.dateFrom}` : "",
            mediaMode === "auto" && findFilters.dateTo ? `Date to: ${findFilters.dateTo}` : "",
            mediaMode === "auto" && findFilters.place ? `Place or scenery: ${findFilters.place}` : "",
            mediaMode === "auto" && findFilters.people ? `People: ${findFilters.people}` : "",
          ].filter(Boolean).join("\n"),
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
      exportForm.append("soundtrack_mode", soundtrackMode);
      if (soundtrackMode === "original_song") {
        [memoryRequest, storyboard.title, storyboard.caption].forEach((detail) => exportForm.append("memory_details", detail));
        exportForm.append("requested_style", storyboard.music_direction ?? "warm acoustic");
      }
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

  const currentStage = storyboard ? (approved ? 4 : 3) : mediaReviews.length > 0 || isPlanning ? 2 : 1;

  return (
    <section aria-labelledby="production-title" className="wizard">
      <div className="wizard__progress" aria-label="Production progress">
        <span className="wizard__progress-count">{currentStage} / 4</span>
        <ol>
          <li className={currentStage === 1 ? "is-active" : "is-complete"}>Request</li>
          <li className={currentStage === 2 ? "is-active" : currentStage > 2 ? "is-complete" : ""}>Media</li>
          <li className={currentStage === 3 ? "is-active" : currentStage > 3 ? "is-complete" : ""}>Plan</li>
          <li className={currentStage === 4 ? "is-active" : ""}>Save</li>
        </ol>
      </div>

      <header className="wizard__header">
        <p className="wizard__step">01 / REQUEST</p>
        <h2 id="production-title">What would you like to remember?</h2>
        <p>Tell us the occasion. We will find the story in your media.</p>
      </header>

      <section className="wizard__stage wizard__stage--request" aria-label="Your request">
        <label className="wizard__request" htmlFor="memory-request">
          <span>Your memory request</span>
          <div className="wizard__input-wrap">
            <textarea
              id="memory-request"
              placeholder="For example: a happy afternoon with the grandchildren."
              rows={3}
              value={memoryRequest}
              onChange={(event) => updateMemoryRequest(event.target.value)}
            />
            <button
              aria-label="Voice input"
              aria-pressed={isListening}
              className={`button button--voice${isListening ? " is-listening" : ""}`}
              onClick={startVoiceRequest}
              title="Voice input"
              type="button"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 14.5a3.5 3.5 0 0 0 3.5-3.5V6a3.5 3.5 0 1 0-7 0v5a3.5 3.5 0 0 0 3.5 3.5Zm6-3.5a1 1 0 0 0-2 0 4 4 0 0 1-8 0 1 1 0 0 0-2 0 6 6 0 0 0 5 5.91V19H8a1 1 0 0 0 0 2h8a1 1 0 0 0 0-2h-3v-2.09A6 6 0 0 0 18 11Z" /></svg>
            </button>
          </div>
        </label>

        <div aria-label="How to choose media" className="wizard__media-mode" role="radiogroup">
          <button
            aria-checked={mediaMode === "manual"}
            className={`wizard__mode${mediaMode === "manual" ? " is-active" : ""}`}
            onClick={() => changeMediaMode("manual")}
            role="radio"
            type="button"
          >
            I’ll choose
          </button>
          <button
            aria-checked={mediaMode === "auto"}
            className={`wizard__mode${mediaMode === "auto" ? " is-active" : ""}`}
            onClick={() => changeMediaMode("auto")}
            role="radio"
            type="button"
          >
            Find for me
          </button>
        </div>

        {mediaMode === "manual" ? (
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
                setFindStatus("");
                resetDerivedState();
              }}
              ref={mediaInputRef}
              type="file"
            />
          </label>
        ) : (
          <div className="wizard__library-access">
            <div>
              <strong>Find moments in your photo library</strong>
              <span>Select a batch once. We will search only what you allow us to see.</span>
            </div>
            <button
              className="button button--secondary"
              onClick={() => mediaInputRef.current?.click()}
              type="button"
            >
              Allow access to photos
            </button>
            <input
              accept="image/*,video/*"
              aria-hidden="true"
              className="wizard__hidden-file-input"
              data-testid="photo-access-input"
              id="memory-media"
              multiple
              onChange={(event) => {
                requestGeneration.current += 1;
                setMediaFiles(Array.from(event.target.files ?? []));
                consentRef.current = false;
                setHasMediaPermission(false);
                setFindStatus("");
                resetDerivedState();
              }}
              ref={mediaInputRef}
              type="file"
            />
          </div>
        )}

        {mediaMode === "auto" && (
          <fieldset className="wizard__find-fields">
            <legend>Find moments in the photos you choose</legend>
            <div className="wizard__find-grid">
              <label htmlFor="find-date-from">Date from<input id="find-date-from" onChange={(event) => setFindFilters((current) => ({ ...current, dateFrom: event.target.value }))} type="date" value={findFilters.dateFrom} /></label>
              <label htmlFor="find-date-to">Date to<input id="find-date-to" onChange={(event) => setFindFilters((current) => ({ ...current, dateTo: event.target.value }))} type="date" value={findFilters.dateTo} /></label>
              <label htmlFor="find-place">Place or scenery<input id="find-place" onChange={(event) => setFindFilters((current) => ({ ...current, place: event.target.value }))} placeholder="Beach, garden, city" type="text" value={findFilters.place} /></label>
              <label htmlFor="find-people">People<input id="find-people" onChange={(event) => setFindFilters((current) => ({ ...current, people: event.target.value }))} placeholder="Family, children" type="text" value={findFilters.people} /></label>
            </div>
            <button className="button button--secondary" disabled={mediaFiles.length === 0} onClick={findMoments} type="button">Find moments</button>
          </fieldset>
        )}
        {mediaFiles.length > 0 && (
          <>
            <p className="wizard__media-count">
              {mediaFiles.length} {mediaFiles.length === 1 ? "item" : "items"} selected from your device.
            </p>
            <ul aria-label="Selected media" className="wizard__selected-files">
              {mediaFiles.map((file, index) => (
                <li key={`${file.name}-${index}`}>
                  <span>{file.name}</span>
                  <button className="button button--remove" onClick={() => removeMediaFile(index)} type="button">Remove {file.name}</button>
                </li>
              ))}
            </ul>
          </>
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
      </section>

      {mediaReviews.length > 0 && (
        <section aria-label="Media review" className="wizard__media-review">
          <p className="wizard__step">02 / MEDIA</p>
          <h3>Check the moments Memory Director found.</h3>
          <p className="wizard__section-note">Keep the moments you want in the story. Nothing is deleted.</p>
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

      {isPlanning && (
        <section aria-label="Creating your plan" className="wizard__stage wizard__stage--waiting">
          <p className="wizard__step">03 / PLAN</p>
          <h3>Making a simple plan from your memories…</h3>
          <p>We are reviewing your selected media now.</p>
        </section>
      )}

      {storyboard && (
        <section aria-label="Generated plan" className="wizard__plan">
          <p className="wizard__step">03 / PLAN</p>
          <h3>{storyboard.title}</h3>
          <p>{storyboard.caption}</p>
          {storyboard.music_direction && (
            <div className="wizard__recommendation" aria-label="Music recommendation">
              <strong>Suggested sound: {storyboard.music_direction}</strong>
              {storyboard.preference_explanation && <p>{storyboard.preference_explanation}</p>}
            </div>
          )}
          <fieldset className="wizard__soundtrack">
            <legend>Sound for your film</legend>
            <label>
              <input
                checked={soundtrackMode === "original_song"}
                name="soundtrack"
                onChange={() => setSoundtrackMode("original_song")}
                type="radio"
                value="original_song"
              />
              Original AI song
            </label>
            <label>
              <input
                checked={soundtrackMode === "instrumental"}
                name="soundtrack"
                onChange={() => setSoundtrackMode("instrumental")}
                type="radio"
                value="instrumental"
              />
              Gentle instrumental
            </label>
            <label>
              <input
                checked={soundtrackMode === "no_sound"}
                name="soundtrack"
                onChange={() => setSoundtrackMode("no_sound")}
                type="radio"
                value="no_sound"
              />
              No music
            </label>
            {soundtrackMode === "original_song" && <p>We will create an original AI song from this memory. No artist imitation or voice cloning.</p>}
          </fieldset>
        </section>
      )}

      {storyboard && (
        <section aria-label="Approval" className="wizard__approval">
          <div>
            <p className="wizard__step">04 / SAVE</p>
            <h3>Your plan stays in your control.</h3>
            <p>Review the plan, then save the finished video to your device.</p>
          </div>
          {!approved ? (
            <button
              className="button button--secondary"
              disabled={!allMediaReviewed || selectedMediaCount === 0}
              onClick={() => setApproved(true)}
              type="button"
            >
              Approve plan
            </button>
          ) : (
            <button
              className="button button--primary"
              disabled={renderStatus === "submitting"}
              onClick={submitRenderRequest}
              type="button"
            >
              {renderStatus === "submitting" ? "Saving your video…" : "Make this video"}
            </button>
          )}
        </section>
      )}

      <p aria-live="polite" className="wizard__status" id="voice-input-status" role="status">
        {planError && "We could not create your plan. Please try again."}
        {voiceError && "Voice input is not available. You can type your request instead."}
        {renderStatus === "submitting" && "Preparing your approved video request…"}
        {renderStatus === "ready" && "Your approved video request is ready."}
        {renderStatus === "error" && "We could not prepare your video request. Please try again."}
        {findStatus}
      </p>
      {exportHref && (
        <a className="button button--secondary wizard__download" download="memory-director-export.zip" href={exportHref}>
          Download your video package
        </a>
      )}
    </section>
  );
}
