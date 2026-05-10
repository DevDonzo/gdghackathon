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
            <small>Automated Advocacy</small>
          </div>
        </div>
        <div className="topbar-status">
          <span className="status-dot" />
          Systems Online
        </div>
      </header>

      <section className="hero-grid">
        <div className="hero-copy">
          <span className="eyebrow">The Digital Advocate</span>
          <h1>We negotiate your bills so you don't have to.</h1>
          <p className="lede">
            RateDrop uses AI to analyze your statements, find hidden leverage, and fight for better rates—saving you time, stress, and money.
          </p>
          
          <div className="hero-points">
            <div className="mini-card fade-in" style={{ animationDelay: '200ms' }}>
              <strong>Forensic Extraction</strong>
              <span>We parse complex statements into actionable leverage points.</span>
            </div>
            <div className="mini-card fade-in" style={{ animationDelay: '400ms' }}>
              <strong>Autonomous Execution</strong>
              <span>Our AI agent handles the hold music and the negotiation.</span>
            </div>
            <div className="mini-card fade-in" style={{ animationDelay: '600ms' }}>
              <strong>Mathematical Proof</strong>
              <span>Get verified proof of savings on every successful run.</span>
            </div>
          </div>
        </div>
        
        <div className="hero-stack fade-in" style={{ animationDelay: '300ms' }}>
          <UploadPanel />
          <LandingTranscript />
        </div>
      </section>

      <section className="manifesto-section">
        <div className="fade-in" style={{ animationDelay: '200ms' }}>
          <span className="section-tag">How it works</span>
          <p style={{ fontSize: '2rem', lineHeight: '1.3', letterSpacing: '-0.03em', marginTop: '24px', color: '#fff', fontWeight: 600 }}>
            A closed-loop system from evidence to financial proof.
          </p>
        </div>
        <div className="editorial-list">
          <div className="editorial-item fade-in" style={{ animationDelay: '300ms' }}>
            <span className="feature-number">01</span>
            <strong>Evidence-Based Starting</strong>
            <p style={{ fontSize: '1.1rem', color: 'var(--foreground-muted)' }}>Every run begins with the raw facts from your statement—no guesswork, just data.</p>
          </div>
          <div className="editorial-item fade-in" style={{ animationDelay: '400ms' }}>
            <span className="feature-number">02</span>
            <strong>Policy-Driven Strategy</strong>
            <p style={{ fontSize: '1.1rem', color: 'var(--foreground-muted)' }}>We launch a controlled session using a deterministic concession ladder to maximize results.</p>
          </div>
          <div className="editorial-item fade-in" style={{ animationDelay: '500ms' }}>
            <span className="feature-number">03</span>
            <strong>Verified Outcomes</strong>
            <p style={{ fontSize: '1.1rem', color: 'var(--foreground-muted)' }}>Final savings are calculated by our engine, providing a clear breakdown you can rely on.</p>
          </div>
        </div>
      </section>

      <section className="proof-tape fade-in" style={{ animationDelay: '600ms' }}>
        <div className="proof-tape-item">
          <span className="intel-label">Source</span>
          <strong>Statement PDF</strong>
        </div>
        <div className="proof-tape-item">
          <span className="intel-label">Brain</span>
          <strong>Policy Engine</strong>
        </div>
        <div className="proof-tape-item">
          <span className="intel-label">Channel</span>
          <strong>Voice Sandbox</strong>
        </div>
        <div className="proof-tape-item">
          <span className="intel-label">Result</span>
          <strong>Verified Delta</strong>
        </div>
      </section>

      <footer className="site-footer fade-in" style={{ animationDelay: '700ms' }}>
        <div className="footer-brand">
          <strong>RateDrop</strong>
          <span style={{ fontSize: '0.9rem', color: 'var(--foreground-subtle)' }}>High-signal consumer automation.</span>
        </div>
        <div className="footer-col">
          <span className="footer-label">Stack</span>
          <span style={{ fontSize: '0.9rem', color: 'var(--foreground-subtle)' }}>Next.js · Gemini · Twilio</span>
        </div>
        <div className="footer-col">
          <span className="footer-label">Mission</span>
          <span style={{ fontSize: '0.9rem', color: 'var(--foreground-subtle)' }}>Scaling consumer agency with AI.</span>
        </div>
      </footer>
    </main>
  );
}
