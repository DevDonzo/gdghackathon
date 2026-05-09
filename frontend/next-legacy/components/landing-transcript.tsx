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
    <div className="card" style={{ background: 'var(--bg-subtle)' }}>
      <div className="demo-frame-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
        <span className="section-tag">Sandbox transcript</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--foreground-muted)' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--error)' }} />
          LIVE FLOW
        </div>
      </div>
      <div className="transcript-stream" style={{ gap: '12px' }}>
        {TURNS.map((turn, index) => (
          <article className={`transcript-card role-${turn.role}`} key={`${turn.role}-${index}`} style={{ padding: '12px', fontSize: '0.85rem' }}>
            <div className="transcript-head" style={{ marginBottom: '4px' }}>
              <strong>{turn.role === "negotiator" ? "RateDrop" : "Carrier rep"}</strong>
            </div>
            <p style={{ opacity: 0.9 }}>{turn.text}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
