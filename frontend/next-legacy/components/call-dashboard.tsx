"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";

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
    if (negotiation.call.mode === "conversation_relay") {
      return negotiation.call.status === "not-started" ? "connecting live relay" : negotiation.call.status.replace("-", " ");
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
    <main className="bg-white text-black min-h-screen">
      <nav className="p-8 flex justify-between items-center bg-white/80 backdrop-blur-md border-b border-black/5 sticky top-0 z-50">
        <Link className="flex items-center gap-4" href="/">
          <div className="w-8 h-8 bg-black text-white flex items-center justify-center font-black">R</div>
          <span className="mono font-bold tracking-tight">AGENT_INTERFACE</span>
        </Link>
        <div className="badge">
          <div className="status-dot" />
          <span className="mono text-[10px]">
            {negotiation.call.mode === "conversation_relay" ? "LIVE_REP_MODE" : "VOICE_SANDBOX_ACTIVE"}
          </span>
        </div>
      </nav>

      <section className="section grid lg:grid-cols-[1.5fr_1fr] gap-24 items-start">
        <div className="fade-in">
          <div className="mb-16">
            <span className="mono text-accent mb-4 block font-bold">Negotiation_Live_Log</span>
            <h2 className="text-5xl font-black italic tracking-tighter">{pageTitle.toUpperCase()}</h2>
            <div className="flex gap-4 mt-8">
               <div className="badge">STATUS: {displayCallStatus.toUpperCase()}</div>
               <div className="badge">ENGINE: DETERMINISTIC</div>
            </div>
          </div>

          <div className="p-12 border border-black/5 bg-gray-50/50 mb-16 shadow-sm">
            <div className="flex justify-between items-end mb-8">
              <div>
                <span className="mono text-muted text-[10px] block mb-2">Protocol_Progress</span>
                <strong className="text-4xl font-black italic">{progress}%</strong>
              </div>
              <div className="text-right">
                <span className="mono text-muted text-[10px] block mb-2">Turns_Captured</span>
                <strong className="text-4xl font-black italic">{turns.length}</strong>
              </div>
            </div>
            <div className="w-full h-1 bg-black/5 rounded-full overflow-hidden">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                className="h-full bg-accent shadow-[0_0_10px_var(--accent)]"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-16">
            <div className="p-8 border border-black/5 bg-white shadow-sm">
              <span className="mono text-muted text-[10px] block mb-2">Current_Objective</span>
              <strong className="text-lg font-bold">{negotiation.currentObjective}</strong>
            </div>
            <div className="p-8 border border-black/5 bg-white shadow-sm">
              <span className="mono text-muted text-[10px] block mb-2">Best_Offer_Captured</span>
              <strong className="text-lg font-bold text-accent">{negotiation.bestOfferMonthly ? `${money(negotiation.bestOfferMonthly)}/mo` : "ANALYZING..."}</strong>
            </div>
          </div>

          <div className="flex flex-col gap-6">
            {turns.length === 0 && (
              <div className="p-16 border border-dashed border-black/10 text-center mono text-muted italic">
                {negotiation.call.mode === "conversation_relay"
                  ? "Answer the phone and speak as the company support rep."
                  : "Awaiting carrier response..."}
              </div>
            )}
            {turns.map((turn, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-10 border-l-4 ${turn.role === 'negotiator' ? 'border-accent bg-accent-soft' : 'border-black/5 bg-gray-50/30'}`}
              >
                <div className="flex justify-between items-center mb-4">
                  <span className="mono font-black text-xs">
                    {turn.role === 'negotiator' ? 'AGENT_RD' : 'PROVIDER_REP'}
                  </span>
                  <span className="mono text-muted text-[10px] font-bold">{turn.intent.toUpperCase()}</span>
                </div>
                <p className="text-xl leading-relaxed text-carbon font-medium">{turn.text}</p>
                {(turn.proposedMonthly || turn.credit) && (
                  <div className="mt-8 pt-6 border-t border-black/5 flex gap-8">
                     {turn.proposedMonthly && <div><span className="mono text-[10px] block text-muted">OFFER</span><strong className="text-sm">{money(turn.proposedMonthly)}/mo</strong></div>}
                     {turn.credit && <div><span className="mono text-[10px] block text-muted">CREDIT</span><strong className="text-sm">{money(turn.credit)}</strong></div>}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>

        <aside className="sticky top-40 flex flex-col gap-8">
           <div className="p-10 border border-black/5 bg-white shadow-xl">
              <span className="section-tag mb-6">Target_Parameters</span>
              <h3 className="text-2xl font-black italic mb-8">{negotiation.scenarioLabel.toUpperCase()}</h3>
              <div className="flex flex-col gap-8">
                <div className="p-6 bg-gray-50 border border-black/5">
                  <span className="mono text-muted text-[10px] block mb-1 font-bold">CURRENT_MONTHLY</span>
                  <strong className="text-3xl font-black italic">{money(negotiation.currentMonthly)}</strong>
                </div>
                <div className="p-6 bg-accent-soft border border-accent/20">
                  <span className="mono text-accent text-[10px] block mb-1 font-bold">NEGOTIATION_TARGET</span>
                  <strong className="text-3xl font-black italic">{money(negotiation.targetMonthly)}</strong>
                </div>
              </div>
           </div>

           {negotiation.status === "completed" && (
             <Link className="primary-button h-20 text-lg shadow-2xl" href={`/result/${negotiation.id}`}>
               PROCEED_TO_FINAL_PROOF
             </Link>
           )}
        </aside>
      </section>
    </main>
  );}
