"use client";

import { useState } from "react";

export function ProductionWizard() {
  const [approved, setApproved] = useState(false);
  const [memoryRequest, setMemoryRequest] = useState("");
  const [renderStatus, setRenderStatus] = useState<"idle" | "submitting" | "ready" | "error">("idle");

  async function submitRenderRequest() {
    setRenderStatus("submitting");

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/renders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          storyboard: {
            title: "Your memory film",
            caption: memoryRequest || "A memory worth sharing.",
          },
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
            setApproved(false);
            setRenderStatus("idle");
          }}
        />
      </label>

      <section aria-label="Approval" className="wizard__approval">
        <div>
          <p className="wizard__step">02 / REVIEW</p>
          <h3>Your plan stays in your control.</h3>
          <p>Nothing is exported until you approve the plan.</p>
        </div>
        <button className="button button--secondary" onClick={() => setApproved(true)} type="button">
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
        {renderStatus === "submitting" && "Preparing your approved video request…"}
        {renderStatus === "ready" && "Your approved video request is ready."}
        {renderStatus === "error" && "We could not prepare your video request. Please try again."}
      </p>
    </section>
  );
}
