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
    if (negotiation.status === "completed" && negotiation.call.status !== "failed") {
      return "completed";
    }
    return negotiation.call.mode === "sandbox" ? negotiation.call.status : "simulation running";
  }, [negotiation]);

  const pageTitle = useMemo(() => {
    if (!negotiation) {
      return "Negotiation";
    }
    if (negotiation.status === "completed") {
      return `${negotiation.provider} negotiation complete`;
    }
    return `${negotiation.provider} negotiation in progress`;
  }, [negotiation]);

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
      <section className="call-layout">
        <div className="call-stage card">
          <div className="call-stage-header">
            <div>
              <span className="section-tag">Live sandbox call</span>
              <h1>{pageTitle}</h1>
            </div>
            <div className={`status-pill status-${negotiation.status}`}>{negotiation.status.replace("-", " ")}</div>
          </div>

          <div className="call-meta-grid">
            <div className="stat-card">
              <span>Current objective</span>
              <strong>{negotiation.currentObjective}</strong>
            </div>
            <div className="stat-card">
              <span>Sandbox call</span>
              <strong>{displayCallStatus}</strong>
            </div>
            <div className="stat-card">
              <span>Best live offer</span>
              <strong>{negotiation.bestOfferMonthly ? `${money(negotiation.bestOfferMonthly)}/mo` : "Waiting for rep offer"}</strong>
            </div>
          </div>

          {negotiation.call.error ? <div className="error-banner">{negotiation.call.error}</div> : null}
          {negotiation.status === "completed" ? <div className="callout-banner">Negotiation finished. Redirecting to the result page.</div> : null}
          {error ? <div className="error-banner">{error}</div> : null}

          <div className="transcript-stream">
            {turns.length === 0 ? (
              <div className="empty-state">The call is dialing. Transcript turns will appear here as the negotiation advances.</div>
            ) : null}
            {turns.map((turn, index) => (
              <article className={`transcript-card role-${turn.role}`} key={`${turn.createdAt}-${index}`}>
                <div className="transcript-head">
                  <strong>{turn.role === "negotiator" ? "RateDrop" : "Carrier rep"}</strong>
                  <span>{turn.objective}</span>
                </div>
                <p>{turn.text}</p>
                {turn.proposedMonthly ? <small>Offer on table: {money(turn.proposedMonthly)}/mo</small> : null}
                {turn.credit ? <small>Credit offered: {money(turn.credit)}</small> : null}
              </article>
            ))}
          </div>
        </div>

        <aside className="sidebar-stack">
          <div className="card sidebar-panel">
            <span className="section-tag">Negotiation frame</span>
            <h2>{negotiation.scenarioLabel}</h2>
            <div className="sidebar-stats">
              <div>
                <span>Current bill</span>
                <strong>{money(negotiation.currentMonthly)}/mo</strong>
              </div>
              <div>
                <span>Target</span>
                <strong>{money(negotiation.targetMonthly)}/mo</strong>
              </div>
              <div>
                <span>Walk-away</span>
                <strong>{money(negotiation.walkAwayMonthly)}/mo</strong>
              </div>
            </div>
          </div>

          <div className="card sidebar-panel">
            <span className="section-tag">Call output</span>
            <h2>What the demo is proving</h2>
            <ul className="bullet-list">
              <li>The bill facts are grounding the conversation.</li>
              <li>The turn sequence follows a deterministic concession policy.</li>
              <li>Any savings shown on the result page are calculated outside the model.</li>
            </ul>
            {negotiation.status === "completed" ? (
              <Link className="primary-button link-button" href={`/result/${negotiation.id}`}>
                View result
              </Link>
            ) : null}
          </div>
        </aside>
      </section>
    </main>
  );
}
