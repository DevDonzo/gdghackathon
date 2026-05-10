"use client";

import { useEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/dist/ScrollTrigger";
import Link from "next/link";

import { Bill3D } from "@/components/bill-3d";
import { LandingTranscript } from "@/components/landing-transcript";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

export default function HomePage() {
  const containerRef = useRef<HTMLElement | null>(null);
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const ctx = gsap.context(() => {
      ScrollTrigger.create({
        trigger: ".animation-section",
        start: "top 72%",
        end: "bottom 24%",
        scrub: 0.8,
        onUpdate: (self) => setScrollProgress(self.progress)
      });

      gsap.from(".reveal-block", {
        y: 22,
        opacity: 0,
        stagger: 0.07,
        duration: 0.7,
        ease: "power2.out"
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <main className="site-shell" ref={containerRef}>
      <nav className="site-nav" aria-label="Primary navigation">
        <Link href="/" className="brand-lockup" aria-label="RateDrop home">
          <span className="brand-mark">R</span>
          <span>
            <strong>RateDrop</strong>
            <small>Consumer phone agent</small>
          </span>
        </Link>
        <div className="nav-links">
          <Link href="#use-case">Product</Link>
          <Link href="#install">Install</Link>
          <Link href="/signin" className="nav-cta">Start</Link>
        </div>
      </nav>

      <section className="hero-section">
        <div className="hero-grid">
          <div className="hero-copy">
            <span className="eyebrow reveal-block">Agentic savings infrastructure</span>
            <h1 className="reveal-block">Companies use AI on you. Use one back.</h1>
            <p className="hero-lede reveal-block">
              RateDrop gives consumers an agentic phone rep for bills, fees, and support problems. It reads the evidence, calls the company, negotiates for savings, and proves what happened.
            </p>
            <div className="hero-actions reveal-block">
              <Link className="btn" href="/signin">
                Start the agent
              </Link>
              <Link className="btn btn-ghost" href="#install">
                Install SDK
              </Link>
            </div>
            <div className="hero-proof-strip reveal-block" aria-label="RateDrop deployment proof">
              <span>Google ADK</span>
              <span>Gemini 2.5 Flash</span>
              <span>Twilio voice</span>
              <span>Deterministic policy</span>
            </div>
            <div className="hero-metrics reveal-block" aria-label="RateDrop capabilities">
              <div>
                <strong>01</strong>
                <span>Finds savings context</span>
              </div>
              <div>
                <strong>02</strong>
                <span>Calls with policy bounds</span>
              </div>
              <div>
                <strong>03</strong>
                <span>Shows proof of savings</span>
              </div>
            </div>
          </div>

          <aside className="product-surface reveal-block" aria-label="RateDrop run status">
            <div className="surface-head">
              <span>Agent stack</span>
              <span>Live</span>
            </div>
            <div className="surface-table">
              <div className="surface-row surface-row-head">
                <span>Stage</span>
                <span>Status</span>
                <span>Owner</span>
              </div>
              <div className="surface-row">
                <span>Evidence scan</span>
                <span>Complete</span>
                <span>Gemini</span>
              </div>
              <div className="surface-row">
                <span>Call policy</span>
                <span>Locked</span>
                <span>Backend</span>
              </div>
              <div className="surface-row">
                <span>Voice call</span>
                <span>Queued</span>
                <span>Twilio</span>
              </div>
              <div className="surface-row">
                <span>Agent reasoning</span>
                <span>Bounded</span>
                <span>Google ADK</span>
              </div>
            </div>
            <div className="surface-note">
              <strong>Consumer leverage</strong>
              <p>Companies automate support to save time. RateDrop gives the customer a bounded agent to push back, capture proof, and protect the math.</p>
            </div>
          </aside>
        </div>
      </section>

      <section className="animation-section">
        <Bill3D scrollProgress={scrollProgress} />
        <div className="section-copy">
          <span className="section-tag">Savings, not hold music</span>
          <h2>Your bill becomes a phone agent that fights for a lower rate.</h2>
        </div>
      </section>

      <section className="mechanism-section" id="use-case">
        <div className="mechanism-grid">
          <div>
            <span className="section-tag">Mechanism</span>
            <h2>Built for support calls with evidence.</h2>
            <p className="section-lede">
              The product stays simple: collect context, create a phone plan, run the call, and verify that the job is actually complete.
            </p>
          </div>
          <div className="steps-grid" id="example">
            <article className="step-card">
              <span>01</span>
              <h3>Read the artifact</h3>
              <p>Gemini extracts provider, plan, totals, charges, red flags, and the issue context from the uploaded bill or receipt.</p>
            </article>
            <article className="step-card">
              <span>02</span>
              <h3>Prepare the call</h3>
              <p>Tavily can locate real company contact paths while the demo safely routes calls through verified Twilio trial numbers.</p>
            </article>
            <article className="step-card">
              <span>03</span>
              <h3>Close with proof</h3>
              <p>Google ADK and Gemini phrase each response, but deterministic backend policy decides whether to push, counter, accept, or close.</p>
            </article>
          </div>
        </div>
        <LandingTranscript />
      </section>

      <section className="sdk-section" id="install">
        <div className="sdk-grid">
          <div>
            <span className="section-tag">Installable agent surface</span>
            <h2>Use RateDrop from your own product.</h2>
            <p className="section-lede">
              The hosted cloud agent stays server-side. Other apps install the client SDK, create a support run, start the call, and stream transcript/result state from RateDrop.
            </p>
            <div className="install-steps" aria-label="RateDrop install steps">
              <div>
                <strong>1</strong>
                <span>Install</span>
                <code>npm install @ratedrop/agent</code>
              </div>
              <div>
                <strong>2</strong>
                <span>Connect</span>
                <code>apiBaseUrl: "https://your-ratedrop.run.app"</code>
              </div>
              <div>
                <strong>3</strong>
                <span>Launch</span>
                <code>await agent.startVoiceCall(run.id)</code>
              </div>
            </div>
          </div>
          <div className="code-panel" aria-label="RateDrop SDK example">
            <div className="code-panel-head">
              <span>@ratedrop/agent</span>
              <span>client sdk</span>
            </div>
            <pre>{`import { RateDropAgent } from "@ratedrop/agent";

const agent = new RateDropAgent({
  apiBaseUrl: "https://your-ratedrop-api.com"
});

const run = await agent.createSupportRun({
  billId: "bill_123",
  companyName: "Air Canada",
  problemSummary: "Wrong baggage fee charged",
  desiredOutcome: "Refund the fee and capture a reference number",
  completionCriteria: ["Refund confirmed", "Reference number captured"]
});

await agent.startVoiceCall(run.id);`}</pre>
          </div>
        </div>
      </section>

      <section className="cloud-section" id="cloud">
        <div>
          <span className="section-tag">Google Cloud runtime</span>
          <h2>Built for the Google stack.</h2>
          <p className="section-lede">
            The demo runs as one Cloud Run service with server-side secrets and a public HTTPS webhook surface for Twilio.
          </p>
        </div>
        <div className="cloud-stack">
          <article>
            <span>Cloud Run</span>
            <strong>Hosts the Next.js UI and FastAPI agent runtime behind one HTTPS URL.</strong>
          </article>
          <article>
            <span>Google ADK</span>
            <strong>Wraps deterministic policy tools so Gemini can speak without controlling the math.</strong>
          </article>
          <article>
            <span>Secret Manager</span>
            <strong>Keeps Gemini, Tavily, and Twilio credentials server-side.</strong>
          </article>
          <article>
            <span>Gemini 2.5 Flash</span>
            <strong>Extracts bill context and phrases concise phone responses.</strong>
          </article>
        </div>
      </section>

      <section className="deploy-section" id="deploy">
        <div className="deploy-heading">
          <span className="section-tag">Agent workspace</span>
          <h2>Sign in before the agent calls.</h2>
          <p>
            The demo sign-in keeps the launch flow separate from the public landing page. After sign-in, you can upload a bill, describe the issue, and start the voice agent.
          </p>
        </div>
        <Link className="workspace-card" href="/signin">
          <span>Open workspace</span>
          <strong>Continue to sign in</strong>
        </Link>
      </section>

      <footer className="site-footer">
        <span>RateDrop</span>
        <span>Google ADK // Gemini // Cloud Run // Twilio trial compatible</span>
      </footer>
    </main>
  );
}
