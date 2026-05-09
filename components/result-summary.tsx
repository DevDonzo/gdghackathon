"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchNegotiation, money } from "@/lib/api";
import { Negotiation } from "@/lib/types";

type Props = {
  negotiationId: string;
};

export function ResultSummary({ negotiationId }: Props) {
  const [negotiation, setNegotiation] = useState<Negotiation | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <main className="page-shell">
      <section className="result-hero card">
        <span className="section-tag">Negotiation result</span>
        <h1>{result.summary}</h1>
        <p className="lede">One call flow, one transcript, one hard savings number the user can actually understand.</p>
        <div className="result-meta-row">
          <div className="confidence-pill">Scenario: {negotiation.scenarioLabel}</div>
          <div className="confidence-pill">Call status: {callStatusLabel}</div>
        </div>

        <div className="result-strip">
          <div className="result-card">
            <span>Before</span>
            <strong>{money(result.currentMonthly)}/mo</strong>
          </div>
          <div className="result-card accent-card">
            <span>After</span>
            <strong>{money(result.newMonthly)}/mo</strong>
          </div>
          <div className="result-card">
            <span>Monthly savings</span>
            <strong>{money(result.monthlySavings)}</strong>
          </div>
          <div className="result-card">
            <span>First-year value</span>
            <strong>{money(result.effectiveFirstYearValue)}</strong>
          </div>
        </div>
      </section>

      <section className="result-grid">
        <div className="card result-panel">
          <span className="section-tag">Savings math</span>
          <div className="result-metrics">
            <div>
              <span>Annual savings</span>
              <strong>{money(result.annualSavings)}</strong>
            </div>
            <div>
              <span>One-time credit</span>
              <strong>{money(result.oneTimeCredit)}</strong>
            </div>
            <div>
              <span>Scenario</span>
              <strong>{negotiation.scenarioLabel}</strong>
            </div>
          </div>
        </div>

        <div className="card result-panel">
          <span className="section-tag">What worked</span>
          <ul className="bullet-list">
            {result.transcriptSummary.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="single-column">
        <div className="card footer-actions">
          <Link className="secondary-link" href="/">
            Run another bill
          </Link>
          <Link className="primary-button link-button" href={`/call/${negotiation.id}`}>
            Reopen live transcript
          </Link>
        </div>
      </section>
    </main>
  );
}
