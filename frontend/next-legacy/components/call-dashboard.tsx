"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { eventsUrl, fetchNegotiation, fetchTranscript, money } from "@/lib/api";
import { Negotiation, TranscriptTurn } from "@/lib/types";

type Props = {
  negotiationId: string;
};

export function CallDashboard({ negotiationId }: Props) {
  const router = useRouter();
  const [negotiation, setNegotiation] = useState<Negotiation | null>(null);
  const [turns, setTurns] = useState<TranscriptTurn[]>([]);
  const [error, setError] = useState<string | null>(null);

  const displayCallStatus = useMemo(() => {
    if (!negotiation) {
      return "loading";
    }
    if (negotiation.status === "failed") {
      return "failed";
    }
    if (negotiation.status === "completed" && negotiation.call.status !== "failed") {
      return "completed";
    }
    return negotiation.call.mode === "sandbox" ? negotiation.call.status : "simulation running";
  }, [negotiation]);

  const pageTitle = useMemo(() => {
    if (!negotiation) {
      return "Negotiation";
    }
    if (negotiation.status === "failed") {
      return `${negotiation.provider} negotiation failed`;
    }
    if (negotiation.status === "completed") {
      return `${negotiation.provider} negotiation complete`;
    }
    return `${negotiation.provider} negotiation in progress`;
  }, [negotiation]);

  const progress = useMemo(() => {
    const totalSteps = 8;
    return Math.min(100, Math.round((turns.length / totalSteps) * 100));
  }, [turns.length]);

  useEffect(() => {
    let active = true;
    const source = new EventSource(eventsUrl(negotiationId));

    async function loadSnapshot() {
      try {
        const [negotiationData, transcriptData] = await Promise.all([
          fetchNegotiation(negotiationId),
          fetchTranscript(negotiationId)
        ]);
        if (!active) {
          return;
        }
        setNegotiation(negotiationData);
        setTurns(transcriptData);
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Could not load negotiation.");
      }
    }

    loadSnapshot();

    source.addEventListener("snapshot", (event) => {
      const payload = JSON.parse(event.data) as { negotiation: Negotiation; turns: TranscriptTurn[] };
      if (!active) {
        return;
      }
      setNegotiation(payload.negotiation);
      setTurns(payload.turns);
    });

    source.addEventListener("turn", (event) => {
      const payload = JSON.parse(event.data) as { negotiation: Negotiation; turn: TranscriptTurn };
      if (!active) {
        return;
      }
      setNegotiation(payload.negotiation);
      setTurns((current) => [...current, payload.turn]);
    });

    source.addEventListener("status", (event) => {
      const payload = JSON.parse(event.data) as { negotiation: Negotiation };
      if (!active) {
        return;
      }
      setNegotiation(payload.negotiation);
    });

    source.onerror = () => {
      if (!active) {
        return;
      }
      setError("Live updates dropped. Refresh to reconnect.");
    };

    return () => {
      active = false;
      source.close();
    };
  }, [negotiationId]);

  useEffect(() => {
    if (!negotiation || negotiation.status !== "completed") {
      return;
    }
    const timeout = window.setTimeout(() => {
      router.push(`/result/${negotiation.id}`);
    }, 1600);
    return () => window.clearTimeout(timeout);
  }, [negotiation, router]);

  if (!negotiation) {
    return (
      <main className="page-shell">
        <section className="single-column">
          <div className="card loading-card">Loading negotiation...</div>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <header className="subpage-topbar">
        <Link className="brand-lockup" href="/">
          <div className="brand-mark">R</div>
          <div>
            <strong>RateDrop</strong>
            <small>Voice Sandbox</small>
          </div>
        </Link>
        <div className="topbar-status">
          <span className="status-dot" />
          Live Transcript Active
        </div>
      </header>

      <section className="call-layout">
        <div className="call-stage card">
          <div className="call-stage-header">
            <div>
              <span className="section-tag">Sandbox Stream</span>
              <h2>{pageTitle}</h2>
            </div>
            <div className={`status-pill status-${negotiation.status}`}>{negotiation.status.replace("-", " ")}</div>
          </div>

          <div className="progress-block">
            <div className="progress-meta">
              <strong>{turns.length} Turns Captured</strong>
              <span>{progress}% Path Complete</span>
            </div>
            <div className="progress-track" aria-hidden="true">
              <span style={{ width: `${progress}%` }} />
            </div>
          </div>

          <div className="call-meta-grid">
            <div className="stat-card">
              <span>Objective</span>
              <strong>{negotiation.currentObjective}</strong>
            </div>
            <div className="stat-card">
              <span>Best Offer</span>
              <strong>{negotiation.bestOfferMonthly ? `${money(negotiation.bestOfferMonthly)}/mo` : "Pending"}</strong>
            </div>
          </div>

          {negotiation.status === "in-progress" && !negotiation.call.error ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '16px', background: 'var(--bg-subtle)', borderRadius: '8px', marginBottom: '32px' }}>
              <div className="voice-wave" aria-hidden="true">
                {[0, 1, 2, 3, 4, 5, 6].map((index) => (
                  <span className="voice-wave-bar" key={`left-${index}`} />
                ))}
              </div>
              <span style={{ fontSize: '0.85rem', fontWeight: '600', letterSpacing: '0.05em' }}>NEGOTIATION ACTIVE</span>
            </div>
          ) : null}

          <div className="transcript-stream">
            {turns.length === 0 ? (
              <div className="empty-state">Dialing...</div>
            ) : null}
            {turns.map((turn, index) => (
              <article className={`transcript-card role-${turn.role}`} key={`${turn.createdAt}-${index}`}>
                <div className="transcript-head">
                  <strong>{turn.role === "negotiator" ? "RateDrop" : "Carrier Rep"}</strong>
                  <span>{turn.intent.replaceAll("_", " ")}</span>
                </div>
                <p>{turn.text}</p>
                {turn.proposedMonthly || turn.credit ? (
                  <div style={{ marginTop: '12px', padding: '8px', background: 'var(--bg)', borderRadius: '4px', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>
                    {turn.proposedMonthly ? <div>Offer: {money(turn.proposedMonthly)}/mo</div> : null}
                    {turn.credit ? <div>Credit: {money(turn.credit)}</div> : null}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </div>

        <aside className="sidebar-stack">
          <div className="card sidebar-panel" style={{ background: 'var(--bg-subtle)' }}>
            <span className="section-tag">Scenario</span>
            <h3>{negotiation.scenarioLabel}</h3>
            <div className="sidebar-stats">
              <div>
                <span>Current Bill</span>
                <strong>{money(negotiation.currentMonthly)}</strong>
              </div>
              <div>
                <span>Target</span>
                <strong>{money(negotiation.targetMonthly)}</strong>
              </div>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--foreground-muted)', marginTop: '16px' }}>
              Deterministic path selected based on extracted bill facts.
            </p>
          </div>

          <div className="card sidebar-panel" style={{ border: '1px solid var(--paper-border)' }}>
            <span className="section-tag">Session Info</span>
            <div className="sidebar-stats">
              <div>
                <span>Duration</span>
                <strong>Live</strong>
              </div>
              <div>
                <span>Mode</span>
                <strong>{negotiation.call.mode}</strong>
              </div>
            </div>
            {negotiation.status === "completed" ? (
              <Link className="primary-button" href={`/result/${negotiation.id}`}>
                View Results
              </Link>
            ) : null}
          </div>
        </aside>
      </section>
    </main>
  );
}
