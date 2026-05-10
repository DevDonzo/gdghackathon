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
        particleCount: 110,
        spread: 70,
        origin: { y: 0.38 },
        colors: ["#cf6430", "#9b451c", "#12233d", "#2e7f67", "#fffaf2"]
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
  const callStatusLabel =
    negotiation.call.error ?? (negotiation.call.mode === "sandbox" ? negotiation.call.status.replace("-", " ") : "simulated flow");
  const savingsRate = Math.max(0, Math.min(100, Math.round((result.monthlySavings / result.currentMonthly) * 100)));

  return (
    <main className="page-shell">
      <header className="subpage-topbar">
        <Link className="brand-lockup" href="/">
          <div className="brand-mark">R</div>
          <div>
            <strong>RateDrop</strong>
            <small>Outcome Proof</small>
          </div>
        </Link>
        <div className="topbar-status">
          <span className="status-dot" />
          Result Verified
        </div>
      </header>

      <section className="result-hero card" style={{ background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)' }}>
        <span className="section-tag">Negotiation Result</span>
        <h1 className={`result-savings-reveal${savingsVisible ? "" : " result-savings-hidden"}`} style={{ fontSize: '5rem', marginBottom: '16px' }}>{result.summary}</h1>
        <p className="lede" style={{ marginBottom: '40px' }}>Deterministic savings proven through voice sandbox execution.</p>
        
        <div className="result-strip">
          <div className="result-card">
            <span>Before</span>
            <strong>{money(result.currentMonthly)}/mo</strong>
          </div>
          <div className="result-card accent-card">
            <span>After</span>
            <strong>{money(displayMonthly ?? result.currentMonthly)}/mo</strong>
          </div>
          <div className="result-card">
            <span>Monthly Savings</span>
            <strong>{money(result.monthlySavings)}</strong>
          </div>
          <div className="result-card">
            <span>12-Month Value</span>
            <strong>{money(result.effectiveFirstYearValue)}</strong>
          </div>
        </div>

        <div className="savings-meter" style={{ marginTop: '40px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', fontSize: '0.85rem' }}>
            <strong>{savingsRate}% Reduction</strong>
            <span style={{ color: 'var(--foreground-muted)' }}>Verified math</span>
          </div>
          <div className="progress-track" aria-hidden="true" style={{ height: '8px' }}>
            <span style={{ width: `${savingsRate}%` }} />
          </div>
        </div>
      </section>

      <section className="result-grid" style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '32px', marginTop: '32px' }}>
        <div className="card result-panel">
          <span className="section-tag">Comparison</span>
          <SavingsChart currentMonthly={result.currentMonthly} newMonthly={result.newMonthly} />
          
          <div className="equation-card" style={{ marginTop: '32px', padding: '24px' }}>
            <div>
              <span className="intel-label">Current</span>
              <strong>{money(result.currentMonthly)}</strong>
            </div>
            <div className="equation-divider">-</div>
            <div>
              <span className="intel-label">New</span>
              <strong>{money(result.newMonthly)}</strong>
            </div>
            <div className="equation-divider">=</div>
            <div style={{ color: 'var(--success)' }}>
              <span className="intel-label">Saved</span>
              <strong>{money(result.monthlySavings)}</strong>
            </div>
          </div>
        </div>

        <div className="card result-panel">
          <span className="section-tag">
            {negotiation.issueContext ? "Task Outcome" : "What worked"}
          </span>
          {negotiation.issueContext && (
            <div style={{ marginBottom: '32px', borderBottom: '1px solid var(--paper-border)', paddingBottom: '24px' }}>
              <h3 style={{ fontSize: '1.2rem', marginBottom: '16px' }}>{negotiation.issueContext.companyName}</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--foreground-muted)', lineHeight: '1.5' }}>{negotiation.issueContext.problemSummary}</p>
            </div>
          )}
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px' }}>
            {result.transcriptSummary.map((item) => (
              <li key={item} style={{ display: 'flex', gap: '12px', fontSize: '0.9rem', color: 'var(--foreground-muted)' }}>
                <span style={{ color: 'var(--success)' }}>✓</span>
                {item}
              </li>
            ))}
          </ul>
          {negotiation.issueContext && (
            <div style={{ marginTop: '32px', borderTop: '1px solid var(--paper-border)', paddingTop: '24px' }}>
              <label className="intel-label">Outcome Achieved</label>
              <p style={{ fontSize: '0.9rem', color: 'var(--foreground)', marginTop: '8px' }}>{negotiation.issueContext.desiredOutcome}</p>
            </div>
          )}
        </div>
      </section>

      <section style={{ marginTop: '60px', display: 'flex', justifyContent: 'center', gap: '16px' }}>
        <Link className="primary-button" href="/" style={{ width: 'auto', padding: '0 32px' }}>
          Process Another Bill
        </Link>
        <Link href={`/call/${negotiation.id}`} style={{ display: 'flex', alignItems: 'center', padding: '0 32px', border: '1px solid var(--paper-border)', borderRadius: '8px', fontSize: '0.9rem', fontWeight: '600' }}>
          Revisit Transcript
        </Link>
      </section>
    </main>
  );
}
