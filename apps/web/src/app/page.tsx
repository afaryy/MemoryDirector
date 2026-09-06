import { CircleHelp, Film } from "lucide-react";

import { ProductionWizard } from "../components/ProductionWizard";

export default function HomePage() {
  return (
    <main className="page-shell">
      <header className="masthead">
        <div className="masthead__brand">
          <span className="masthead__mark" aria-hidden="true"><Film /></span>
          <div>
            <h1>Memory Director</h1>
            <p className="masthead__subtitle">Your moments, made simply.</p>
          </div>
        </div>
        <span aria-hidden="true" className="masthead__help"><CircleHelp /></span>
      </header>
      <ProductionWizard />
    </main>
  );
}
