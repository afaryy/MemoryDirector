import { ProductionWizard } from "../components/ProductionWizard";

export default function HomePage() {
  return (
    <main className="page-shell">
      <header className="masthead">
        <p className="masthead__mark">MD / 01</p>
        <div>
          <h1>Memory Director</h1>
          <p className="masthead__subtitle">Turn phone moments into a short film.</p>
        </div>
      </header>
      <ProductionWizard />
    </main>
  );
}
