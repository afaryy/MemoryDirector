"use client";

import { useState } from "react";

type Storyboard = {
  title: string;
  caption: string;
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

export function ProductionWizard() {
  const [approved, setApproved] = useState(false);
  const [memoryRequest, setMemoryRequest] = useState("");
  const [mediaFiles, setMediaFiles] = useState<File[]>([]);
  const [hasMediaPermission, setHasMediaPermission] = useState(false);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [isPlanning, setIsPlanning] = useState(false);
  const [planError, setPlanError] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [voiceError, setVoiceError] = useState(false);
  const [renderStatus, setRenderStatus] = useState<"idle" | "submitting" | "ready" | "error">("idle");

  function updateMemoryRequest(value: string) {
    setMemoryRequest(value);
    setStoryboard(null);
    setApproved(false);
    setPlanError(false);
    setRenderStatus("idle");
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

  async function createPlan() {
    setIsPlanning(true);
    setPlanError(false);
    setApproved(false);

    try {
      const response = await fetch(`${apiBaseUrl}/storyboards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ occasion: memoryRequest, moods: ["warm", "cheerful"] }),
      });

      if (!response.ok) {
        throw new Error("Storyboard request was not accepted.");
      }

      setStoryboard((await response.json()) as Storyboard);
    } catch {
      setStoryboard(null);
      setPlanError(true);
    } finally {
      setIsPlanning(false);
    }
  }

  async function submitRenderRequest() {
    if (!storyboard) {
      return;
    }

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

      setRenderStatus("ready");
    } catch {
      setRenderStatus("error");
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
      <button className="button button--secondary" onClick={startVoiceRequest} type="button">
        {isListening ? "Listening…" : "Speak your request"}
      </button>

      <label className="wizard__media" htmlFor="memory-media">
        <span>Choose photos and videos</span>
        <input
          accept="image/*,video/*"
          id="memory-media"
          multiple
          onChange={(event) => {
            setMediaFiles(Array.from(event.target.files ?? []));
            setHasMediaPermission(false);
            setStoryboard(null);
            setApproved(false);
            setPlanError(false);
            setRenderStatus("idle");
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
          onChange={(event) => setHasMediaPermission(event.target.checked)}
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
        {isPlanning ? "Creating your plan…" : "Create a plan"}
      </button>

      {storyboard && (
        <section aria-label="Generated plan" className="wizard__plan">
          <p className="wizard__step">02 / YOUR PLAN</p>
          <h3>{storyboard.title}</h3>
          <p>{storyboard.caption}</p>
        </section>
      )}

      <section aria-label="Approval" className="wizard__approval">
        <div>
          <p className="wizard__step">03 / REVIEW</p>
          <h3>Your plan stays in your control.</h3>
          <p>Nothing is exported until you approve the plan.</p>
        </div>
        <button
          className="button button--secondary"
          disabled={!storyboard}
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
      <p aria-live="polite" className="wizard__status">
        {planError && "We could not create your plan. Please try again."}
        {voiceError && "Voice input is not available. You can type your request instead."}
        {renderStatus === "submitting" && "Preparing your approved video request…"}
        {renderStatus === "ready" && "Your approved video request is ready."}
        {renderStatus === "error" && "We could not prepare your video request. Please try again."}
      </p>
    </section>
  );
}
