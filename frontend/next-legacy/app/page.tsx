import { LandingTranscript } from "@/components/landing-transcript";
import { UploadPanel } from "@/components/upload-panel";

export default function HomePage() {
  return (
    <main className="page-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">R</div>
          <div>
            <strong>RateDrop</strong>
            <small>Autonomous Negotiation</small>
          </div>
        </div>
        <div className="topbar-status">
          <span className="status-dot" />
          Deterministic Savings Active
        </div>
      </header>

      <section className="hero-grid">
        <div className="hero-copy">
          <span className="eyebrow">The Voice Sandbox</span>
          <h1>Drop your rate without the hold music.</h1>
          <p className="lede">
            RateDrop identifies leverage in your service bill and executes a controlled negotiation to prove your savings.
          </p>
          
          <div className="hero-points">
            <div className="mini-card">
              <strong>Structured Extraction</strong>
              <span>Line items and promos parsed with precision.</span>
            </div>
            <div className="mini-card">
              <strong>Policy-Driven</strong>
              <span>Deterministic logic, not open-ended chat.</span>
            </div>
            <div className="mini-card">
              <strong>Verified Proof</strong>
              <span>Savings calculated in code, backed by transcripts.</span>
            </div>
          </div>
        </div>
        
        <div className="hero-stack" style={{ marginTop: '120px' }}>
          <UploadPanel />
          <LandingTranscript />
        </div>
      </section>

      <section className="manifesto-section">
        <div>
          <span className="section-tag">Mechanism</span>
          <p style={{ color: 'var(--foreground-muted)', fontSize: '1.4rem', lineHeight: '1.3', letterSpacing: '-0.02em', marginTop: '12px' }}>
            A transparent loop from bill evidence to financial proof.
          </p>
        </div>
        <div className="editorial-list">
          <div className="editorial-item">
            <span className="feature-number">01</span>
            <strong>Bill-Aware Intelligence</strong>
            <p style={{ fontSize: '0.95rem', color: 'var(--foreground-muted)' }}>Every negotiation starts with the raw facts extracted from your actual statement.</p>
          </div>
          <div className="editorial-item">
            <span className="feature-number">02</span>
            <strong>Sandbox Execution</strong>
            <p style={{ fontSize: '0.95rem', color: 'var(--foreground-muted)' }}>We launch a controlled voice session using a deterministic concession ladder.</p>
          </div>
          <div className="editorial-item">
            <span className="feature-number">03</span>
            <strong>Deterministic Math</strong>
            <p style={{ fontSize: '0.95rem', color: 'var(--foreground-muted)' }}>The final result is calculated by our engine, providing a clear before-and-after breakdown.</p>
          </div>
        </div>
      </section>

      <section className="proof-tape">
        <div className="proof-tape-item">
          <span>Input</span>
          <strong>Bill PDF / Image</strong>
        </div>
        <div className="proof-tape-item">
          <span>Engine</span>
          <strong>Negotiation Policy</strong>
        </div>
        <div className="proof-tape-item">
          <span>Channel</span>
          <strong>Voice Sandbox</strong>
        </div>
        <div className="proof-tape-item">
          <span>Outcome</span>
          <strong>Verified Savings</strong>
        </div>
      </section>

      <footer className="site-footer">
        <div className="footer-brand">
          <strong>RateDrop</strong>
          <span style={{ fontSize: '0.85rem', color: 'var(--foreground-subtle)' }}>High-signal telecom automation.</span>
        </div>
        <div className="footer-col">
          <span className="footer-label">Stack</span>
          <span style={{ fontSize: '0.85rem', color: 'var(--foreground-subtle)' }}>Next.js · FastAPI · Gemini · Twilio</span>
        </div>
        <div className="footer-col">
          <span className="footer-label">Agency</span>
          <span style={{ fontSize: '0.85rem', color: 'var(--foreground-subtle)' }}>Built for consumer autonomy.</span>
        </div>
      </footer>
    </main>
  );
}
