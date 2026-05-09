"use client";

import { useEffect, useState } from "react";
import { money } from "@/lib/api";

type Props = {
  currentMonthly: number;
  newMonthly: number;
};

export function SavingsChart({ currentMonthly, newMonthly }: Props) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const timeout = window.setTimeout(() => setReady(true), 500);
    return () => window.clearTimeout(timeout);
  }, []);

  const afterPct = Math.min(newMonthly / currentMonthly, 1);
  const deltaPct = Math.round(((currentMonthly - newMonthly) / currentMonthly) * 100);

  return (
    <div className="savings-chart" aria-label={`Bar chart comparing before ${currentMonthly} per month and after ${newMonthly} per month`}>
      <div className="savings-chart-bars" style={{ display: 'flex', gap: '32px', height: '160px', alignItems: 'flex-end', padding: '20px 0' }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '100%', background: 'var(--foreground-subtle)', height: '100%', borderRadius: '4px' }} />
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--foreground-muted)' }}>{money(currentMonthly)}</span>
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '100%', background: 'var(--foreground)', height: ready ? `${afterPct * 100}%` : '0%', borderRadius: '4px', transition: 'height 1s cubic-bezier(0.16, 1, 0.3, 1)' }} />
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--foreground)' }}>{money(newMonthly)}</span>
        </div>
      </div>
      <p style={{ marginTop: '20px', fontSize: '0.9rem', fontWeight: '600', color: 'var(--success)', textAlign: 'center' }}>
        {ready ? `-${deltaPct}% monthly` : 'Calculating...'}
      </p>
    </div>
  );
}

