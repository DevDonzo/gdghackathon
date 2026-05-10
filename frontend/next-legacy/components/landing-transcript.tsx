const TURNS = [
  {
    role: "rep" as const,
    objective: "Initial greeting",
    text: "Thanks for calling Bell, how can I help?"
  },
  {
    role: "negotiator" as const,
    objective: "Identifying leverage",
    text: "Hi. My loyalty discount rolled off and my bill jumped. I want the promo restored or a comparable retention offer."
  },
  {
    role: "rep" as const,
    objective: "Initial offer",
    text: "I can offer a smaller monthly credit, but I would need to check whether retention can do more."
  },
  {
    role: "negotiator" as const,
    objective: "Escalating to retention",
    text: "Please check retention. If you can match the previous discount, I can stay and close this out today."
  }
];

export function LandingTranscript() {
  return (
    <div className="transcript-panel">
      <div className="demo-frame-header">
        <span className="section-tag">TRANSCRIPT_PREVIEW</span>
        <div className="live-flow">
          <span />
          LIVE_FLOW
        </div>
      </div>
      <div className="transcript-stream">
        {TURNS.map((turn, index) => (
          <article className={`transcript-card role-${turn.role}`} key={`${turn.role}-${index}`}>
            <div className="transcript-head">
              <strong>{turn.role === "negotiator" ? "RATEDROP" : "CARRIER_REP"}</strong>
              <small>{turn.objective}</small>
            </div>
            <p>{turn.text}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
