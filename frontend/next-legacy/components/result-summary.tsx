"use client";

import confetti from "canvas-confetti";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { fetchNegotiation, money } from "@/lib/api";
import { Negotiation } from "@/lib/types";
import { SavingsChart } from "@/components/savings-chart";

type Props = {
  negotiationId: string;
};

export function ResultSummary({ negotiationId }: Props) {
  const [negotiation, setNegotiation] = useState<Negotiation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [displayMonthly, setDisplayMonthly] = useState<number | null>(null);
  const [savingsVisible, setSavingsVisible] = useState(false);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchNegotiation(negotiationId);
        setNegotiation(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Could not load result.");
      }
    }

    load();
  }, [negotiationId]);

  useEffect(() => {
    if (!negotiation?.result) {
      return;
    }

    const result = negotiation.result;
    const skip = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (skip) {
      setDisplayMonthly(result.newMonthly);
      setSavingsVisible(true);
      return;
    }

    const from = result.currentMonthly;
    const to = result.newMonthly;
    const duration = 1200;
    const startTime = performance.now();

    setDisplayMonthly(from);
    setSavingsVisible(false);

    function tick(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayMonthly(from + (to - from) * eased);

      if (progress < 1) {
        rafRef.current = window.requestAnimationFrame(tick);
        return;
      }

      setDisplayMonthly(to);
      confetti({
        particleCount: 82,
        spread: 58,
        origin: { y: 0.32 },
        colors: ["#050505", "#3b3b37", "#77776f", "#fbfbf8", "#ffffff"]
      });
      window.setTimeout(() => setSavingsVisible(true), 280);
    }

    rafRef.current = window.requestAnimationFrame(tick);

    return () => {
      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current);
      }
    };
  }, [negotiation]);

  if (error) {
    return (
      <main className="page-shell">
        <section className="single-column">
          <div className="error-banner">{error}</div>
        </section>
      </main>
    );
  }

  if (!negotiation || !negotiation.result) {
    return (
      <main className="page-shell">
        <section className="single-column">
          <div className="card loading-card">Preparing result...</div>
        </section>
      </main>
    );
  }

  const result = negotiation.result;
  const callModeLabel =
    negotiation.call.mode === "conversation_relay"
      ? "Live rep mode"
      : negotiation.call.mode === "sandbox"
        ? "Guided voice demo"
        : "Simulated run";
  const callStatusLabel = negotiation.call.error ?? negotiation.call.status.replace("-", " ");
  const savingsRate =
    result.currentMonthly > 0
      ? Math.max(0, Math.min(100, Math.round((result.monthlySavings / result.currentMonthly) * 100)))
      : 0;
  const transcriptItems = result.transcriptSummary.length
    ? result.transcriptSummary
    : ["RateDrop completed the support mission and generated the final outcome."];

  return (
    <main className="result-page">
      <nav className="result-nav">
        <Link className="result-brand" href="/">
          <span>R</span>
          <div>
            <strong>RateDrop</strong>
            <small>Action report</small>
          </div>
        </Link>
        <div className="result-status-pill">
          <div className="status-dot" />
          <span>{negotiation.status === "completed" ? "Result ready" : "Run in progress"}</span>
        </div>
      </nav>

      <section className="result-shell">
        <div className="result-hero fade-in">
          <div className="result-kicker">Final outcome</div>
          <h1>{result.summary}</h1>
          <p>
            A deterministic RateDrop agent completed the call plan, captured the proof points,
            and calculated the savings in code.
          </p>
        </div>

        <div className="result-metrics" aria-label="Savings summary">
          <article>
            <span>Before</span>
            <strong>{money(result.currentMonthly)}</strong>
            <small>Original monthly bill</small>
          </article>
          <article className="is-primary">
            <span>After</span>
            <strong>{money(displayMonthly ?? result.currentMonthly)}</strong>
            <small>New monthly cost</small>
          </article>
          <article>
            <span>Saved monthly</span>
            <strong>{money(result.monthlySavings)}</strong>
            <small>{savingsRate}% reduction</small>
          </article>
          <article className="is-dark">
            <span>First year value</span>
            <strong>{money(result.effectiveFirstYearValue)}</strong>
            <small>Annual savings plus credits</small>
          </article>
        </div>

        <div className="result-grid">
           <section className="result-panel result-chart-panel">
              <div className="result-panel-head">
                <span>Cost movement</span>
                <strong>{money(result.annualSavings)} annualized</strong>
              </div>
              <SavingsChart currentMonthly={result.currentMonthly} newMonthly={result.newMonthly} />
              <div className="result-breakdown">
                 <div>
                    <span>Annual savings</span>
                    <strong>{money(result.annualSavings)}</strong>
                 </div>
                 <div>
                    <span>One-time credit</span>
                    <strong>{money(result.oneTimeCredit)}</strong>
                 </div>
                 <div>
                    <span>Reduction</span>
                    <strong>{savingsRate}%</strong>
                 </div>
              </div>
           </section>

           <aside className="result-side">
              <section className="result-panel">
                <div className="result-panel-head">
                  <span>Proof trail</span>
                  <strong>{transcriptItems.length} checkpoints</strong>
                </div>
                <ol className="proof-list">
                  {transcriptItems.map((item, i) => (
                    <li key={i}>
                       <span>{String(i + 1).padStart(2, "0")}</span>
                       <p>{item}</p>
                    </li>
                  ))}
                </ol>
              </section>

              {negotiation.issueContext && (
                <section className="result-panel result-context">
                  <div className="result-panel-head">
                    <span>Mission context</span>
                    <strong>{negotiation.issueContext.companyName}</strong>
                  </div>
                  <p>{negotiation.issueContext.problemSummary}</p>
                  {negotiation.issueContext.desiredOutcome && (
                    <div>
                      <span>Desired outcome</span>
                      <strong>{negotiation.issueContext.desiredOutcome}</strong>
                    </div>
                  )}
                </section>
              )}

              <section className="result-panel result-call">
                <div>
                  <span>Call mode</span>
                  <strong>{callModeLabel}</strong>
                </div>
                <p>{callStatusLabel}</p>
              </section>

              <div className="result-actions">
                <Link className="primary-button" href="/">Start another run</Link>
                <Link className="btn btn-outline" href={`/call/${negotiation.id}`}>Review call log</Link>
              </div>
           </aside>
        </div>
      </section>
    </main>
  );
}
