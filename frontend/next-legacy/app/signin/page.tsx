"use client";

import Link from "next/link";
import { useState } from "react";

import { UploadPanel } from "@/components/upload-panel";

export default function SignInPage() {
  const [signedIn, setSignedIn] = useState(false);

  return (
    <main className="site-shell workspace-shell">
      <nav className="site-nav" aria-label="Workspace navigation">
        <Link href="/" className="brand-lockup" aria-label="RateDrop home">
          <span className="brand-mark">R</span>
          <span>
            <strong>RateDrop</strong>
            <small>Agent workspace</small>
          </span>
        </Link>
        <div className="nav-links">
          <Link href="/">Home</Link>
          <Link href="/signin" className="nav-cta">Workspace</Link>
        </div>
      </nav>

      {!signedIn ? (
        <section className="auth-section">
          <div className="auth-copy">
            <span className="section-tag">Demo sign in</span>
            <h1>Start from a workspace.</h1>
            <p className="hero-lede">
              In the real product this is where Clerk, Auth.js, or Cognito would protect the agent launcher. For the hackathon demo, continue with a local demo identity.
            </p>
          </div>
          <div className="auth-card">
            <span className="mini-label">RateDrop account</span>
            <div className="auth-identity">
              <strong>Demo operator</strong>
              <span>Can upload bills, define support missions, and start verified Twilio trial calls.</span>
            </div>
            <button className="primary-button" type="button" onClick={() => setSignedIn(true)}>
              Continue with demo account
            </button>
            <p>
              This does not add real auth. It gives the judges the correct product flow without adding another external dependency.
            </p>
          </div>
        </section>
      ) : (
        <section className="workspace-section">
          <div className="deploy-heading">
            <span className="section-tag">Agent launcher</span>
            <h1>Give the agent a job.</h1>
            <p>
              Upload a statement, describe the issue, and RateDrop will create a bounded phone mission before starting the voice flow.
            </p>
          </div>
          <UploadPanel />
        </section>
      )}
    </main>
  );
}
