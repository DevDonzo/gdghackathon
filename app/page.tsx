import { UploadPanel } from "@/components/upload-panel";

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="hero-grid">
        <div className="hero-copy">
          <span className="eyebrow">Telecom bill negotiation</span>
          <h1>Drop your rate before you waste another hour on hold.</h1>
          <p className="lede">
            RateDrop reads your mobile bill, finds the leverage, launches a controlled sandbox carrier call, and tracks the savings in
            one place.
          </p>
          <div className="hero-points">
            <div className="mini-card">
              <strong>Bill-aware</strong>
              <span>Provider, line items, fees, and promo signals extracted from the actual bill.</span>
            </div>
            <div className="mini-card">
              <strong>Controlled call flow</strong>
              <span>Deterministic policy engine with a live transcript and a Twilio-backed sandbox call.</span>
            </div>
            <div className="mini-card">
              <strong>Hard numbers</strong>
              <span>Before/after monthly cost, one-time credits, and first-year value calculated in code.</span>
            </div>
          </div>
        </div>
        <UploadPanel />
      </section>
    </main>
  );
}
