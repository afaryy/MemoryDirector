"use client";

import { useState } from "react";

export function ProductionWizard() {
  const [approved, setApproved] = useState(false);

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

      <button className="button button--primary" disabled={!approved} type="button">
        Make this video
      </button>
    </section>
  );
}
