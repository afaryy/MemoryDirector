"use client";

import { useState } from "react";

type Storyboard = {
  title: string;
  caption: string;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function ProductionWizard() {
  const [approved, setApproved] = useState(false);
  const [memoryRequest, setMemoryRequest] = useState("");
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [isPlanning, setIsPlanning] = useState(false);
  const [planError, setPlanError] = useState(false);
  const [renderStatus, setRenderStatus] = useState<"idle" | "submitting" | "ready" | "error">("idle");

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
          onChange={(event) => {
            setMemoryRequest(event.target.value);
            setStoryboard(null);
            setApproved(false);
            setPlanError(false);
            setRenderStatus("idle");
          }}
        />
      </label>

      <button
        className="button button--secondary"
        disabled={!memoryRequest.trim() || isPlanning}
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
        {renderStatus === "submitting" && "Preparing your approved video request…"}
        {renderStatus === "ready" && "Your approved video request is ready."}
        {renderStatus === "error" && "We could not prepare your video request. Please try again."}
      </p>
    </section>
  );
}
