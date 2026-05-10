"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import Link from "next/link";

import { createDemoBill, createNegotiation, fetchDemoBills, fetchRecentNegotiations, money, startNegotiation, uploadBill, type DemoBillOption } from "@/lib/api";
import { BillSummary, Negotiation } from "@/lib/types";

export function UploadPanel() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [bill, setBill] = useState<BillSummary | null>(null);
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [loadingDemo, setLoadingDemo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [demoBills, setDemoBills] = useState<DemoBillOption[]>([]);
  const [recentNegotiations, setRecentNegotiations] = useState<Negotiation[]>([]);
  const [customAngles, setCustomAngles] = useState<string[]>([]);
  const [customInput, setCustomInput] = useState("");

  // Issue Context State
  const [companyName, setCompanyName] = useState("");
  const [issueDescription, setIssueDescription] = useState("");
  const [desiredOutcome, setDesiredOutcome] = useState("");

  const [customerFacts, setCustomerFacts] = useState<string[]>([]);
  const [factInput, setFactInput] = useState("");

  const [constraints, setConstraints] = useState<string[]>([]);
  const [constraintInput, setConstraintInput] = useState("");

  const [completionCriteria, setCompletionCriteria] = useState<string[]>([]);
  const [criteriaInput, setCriteriaInput] = useState("");

  useEffect(() => {
    async function loadHomeData() {
      try {
        const [items, history] = await Promise.all([fetchDemoBills(), fetchRecentNegotiations()]);
        setDemoBills(items);
        setRecentNegotiations(history);
      } catch {
        setDemoBills([]);
        setRecentNegotiations([]);
      }
    }

    loadHomeData();
  }, []);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setError("Choose a PDF or image bill first.");
      return;
    }

    setError(null);
    setUploading(true);
    try {
      const extracted = await uploadBill(selectedFile);
      setBill(extracted);
      setCustomAngles([]);
      setCustomInput("");
      const history = await fetchRecentNegotiations();
      setRecentNegotiations(history);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleStart() {
    if (!bill) {
      return;
    }

    setError(null);
    setStarting(true);
    try {
      const issueContext = companyName || issueDescription || desiredOutcome || customerFacts.length || constraints.length || completionCriteria.length ? {
        companyName,
        issueDescription,
        desiredOutcome,
        customerFacts,
        constraints,
        completionCriteria
      } : undefined;

      const negotiation = await createNegotiation(bill.id, customAngles, issueContext);
      const started = await startNegotiation(negotiation.id);
      router.push(`/call/${started.id}`);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Could not start negotiation.");
    } finally {
      setStarting(false);
    }
  }

  async function handleDemoBill(scenarioId: string) {
    setError(null);
    setLoadingDemo(scenarioId);
    try {
      const extracted = await createDemoBill(scenarioId);
      setBill(extracted);
      setSelectedFile(null);
      setCustomAngles([]);
      setCustomInput("");
      const history = await fetchRecentNegotiations();
      setRecentNegotiations(history);
    } catch (demoError) {
      setError(demoError instanceof Error ? demoError.message : "Could not load demo bill.");
    } finally {
      setLoadingDemo(null);
    }
  }

  function historyOutcome(item: Negotiation): string {
    if (item.call.error) {
      return item.call.error;
    }
    if (item.call.status === "failed") {
      return "Sandbox call failed";
    }
    if (item.result) {
      return `${money(item.result.newMonthly)}/mo after`;
    }
    return item.status.replace("-", " ");
  }

  return (
    <div className="card" style={{ padding: '60px' }}>
      <div className="panel-header" style={{ marginBottom: '80px' }}>
        <span className="section-tag">Direct Input</span>
        <h2 style={{ fontSize: '2rem', letterSpacing: '-0.04em' }}>Carrier Statement</h2>
        <p style={{ color: 'var(--foreground-muted)', fontSize: '0.95rem', maxWidth: '320px', marginTop: '12px' }}>
          Upload your statement to extract deterministic leverage points.
        </p>
      </div>

      <div className="upload-intel" style={{ marginBottom: '80px', gap: '60px' }}>
        <div>
          <span className="intel-label">Extraction</span>
          <strong style={{ fontSize: '0.9rem' }}>Plan / Fees</strong>
        </div>
        <div>
          <span className="intel-label">Strategy</span>
          <strong style={{ fontSize: '0.9rem' }}>Policy-Based</strong>
        </div>
      </div>

      <form className="upload-form" onSubmit={handleUpload}>
        <label className="upload-dropzone" htmlFor="bill-upload" style={{ padding: '80px' }}>
          <span style={{ fontSize: '1rem' }}>{selectedFile ? selectedFile.name : "Select bill file"}</span>
          <small>{selectedFile ? "File ready" : "PDF or Image"}</small>
        </label>
        <input
          id="bill-upload"
          className="sr-only"
          type="file"
          accept=".pdf,image/png,image/jpeg,image/jpg"
          onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
        />
        <button className="primary-button" disabled={uploading} type="submit" style={{ marginTop: '40px' }}>
          {uploading ? "Parsing..." : "Extract Charges"}
        </button>
      </form>

      {demoBills.length > 0 ? (
        <div style={{ marginTop: '100px', borderTop: '1px solid var(--paper-border)', paddingTop: '60px' }}>
          <h4 style={{ marginBottom: '32px' }}>Scenarios</h4>
          <div className="demo-bill-list" style={{ gap: '16px' }}>
            {demoBills.map((item) => (
              <button
                className="demo-bill-card"
                disabled={loadingDemo !== null}
                key={item.id}
                onClick={() => handleDemoBill(item.id)}
                type="button"
                style={{ padding: '24px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
              >
                <div style={{ textAlign: 'left' }}>
                  <strong style={{ display: 'block', fontSize: '0.95rem' }}>{item.label}</strong>
                  <div style={{ fontSize: '0.75rem', color: 'var(--foreground-subtle)', marginTop: '4px' }}>
                    {item.provider} · {money(item.monthlyTotal)}/mo · {item.headlineAngle}
                  </div>
                </div>
                <small style={{ fontSize: '0.65rem', fontFamily: 'var(--font-mono)', color: 'var(--foreground-subtle)' }}>{loadingDemo === item.id ? "LOADING" : "EXECUTE"}</small>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {error ? <div className="error-banner">{error}</div> : null}

      {bill ? (
        <div style={{ marginTop: '100px', borderTop: '1px solid var(--paper-border)', paddingTop: '80px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '48px' }}>
            <div>
              <span className="section-tag">Analysis</span>
              <h3 style={{ fontSize: '2rem' }}>{bill.provider}</h3>
            </div>
            <div className="status-pill">{Math.round(bill.extractionConfidence * 100)}% Match</div>
          </div>

          <div className="call-meta-grid" style={{ gap: '24px', marginBottom: '60px' }}>
            <div className="stat-card" style={{ padding: '32px' }}>
              <span>Plan</span>
              <strong>{bill.planName}</strong>
            </div>
            <div className="stat-card" style={{ padding: '32px' }}>
              <span>Monthly</span>
              <strong>{money(bill.monthlyTotal)}</strong>
            </div>
          </div>

          <div className="detail-block">
            <h4 style={{ marginBottom: '24px' }}>Leverage</h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '24px' }}>
              {bill.negotiationAngles.map((angle) => (
                <span key={angle} style={{ padding: '6px 12px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', fontSize: '0.8rem', color: 'var(--foreground-muted)' }}>
                  {angle}
                </span>
              ))}
            </div>
            <form
              className="leverage-form"
              onSubmit={(event) => {
                event.preventDefault();
                const trimmed = customInput.trim();
                if (!trimmed) return;
                if (!customAngles.includes(trimmed) && !bill.negotiationAngles.includes(trimmed)) {
                  setCustomAngles((current) => [...current, trimmed]);
                }
                setCustomInput("");
              }}
              style={{ display: 'flex', gap: '12px' }}
            >
              <input
                style={{ flex: 1, height: '48px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', padding: '0 16px', fontSize: '0.9rem' }}
                maxLength={80}
                onChange={(event) => setCustomInput(event.target.value)}
                placeholder="Custom leverage point..."
                type="text"
                value={customInput}
              />
              <button style={{ padding: '0 20px', background: 'var(--foreground-subtle)', color: 'var(--foreground)', borderRadius: '2px', fontSize: '0.8rem', fontWeight: '700', cursor: 'pointer' }} disabled={!customInput.trim()} type="submit">
                Add
              </button>
            </form>
          </div>

          <div className="detail-block" style={{ marginTop: '60px' }}>
            <span className="section-tag">Task Configuration</span>
            <h4 style={{ marginBottom: '32px', marginTop: '8px' }}>What do you need RateDrop to fix?</h4>

            <div style={{ display: 'grid', gap: '32px' }}>
              <div>
                <label className="intel-label">Company Name</label>
                <input
                  style={{ width: '100%', height: '48px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', padding: '0 16px' }}
                  placeholder="e.g. Air Canada"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
              </div>

              <div>
                <label className="intel-label">Problem Description</label>
                <textarea
                  style={{ width: '100%', minHeight: '100px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', padding: '16px', font: 'inherit' }}
                  placeholder="e.g. My flight was cancelled and the refund has not been processed."
                  value={issueDescription}
                  onChange={(e) => setIssueDescription(e.target.value)}
                />
              </div>

              <div>
                <label className="intel-label">Desired Outcome</label>
                <input
                  style={{ width: '100%', height: '48px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', padding: '0 16px' }}
                  placeholder="e.g. Get the refund processed or confirmed rebooking"
                  value={desiredOutcome}
                  onChange={(e) => setDesiredOutcome(e.target.value)}
                />
              </div>

              {/* Customer Facts */}
              <div>
                <label className="intel-label">Known Facts</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                  {customerFacts.map((fact, i) => (
                    <span key={i} style={{ padding: '4px 10px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', fontSize: '0.8rem' }}>{fact}</span>
                  ))}
                </div>
                <form style={{ display: 'flex', gap: '12px' }} onSubmit={(e) => { e.preventDefault(); if (factInput.trim()) { setCustomerFacts([...customerFacts, factInput.trim()]); setFactInput(""); }}}>
                  <input
                    style={{ flex: 1, height: '40px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', padding: '0 12px' }}
                    placeholder="e.g. Booking reference ABC123"
                    value={factInput}
                    onChange={(e) => setFactInput(e.target.value)}
                  />
                  <button type="submit" style={{ padding: '0 16px', background: 'var(--paper-border)', borderRadius: '2px', fontSize: '0.8rem', cursor: 'pointer' }}>Add</button>
                </form>
              </div>

              {/* Constraints */}
              <div>
                <label className="intel-label">Constraints</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                  {constraints.map((c, i) => (
                    <span key={i} style={{ padding: '4px 10px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', fontSize: '0.8rem' }}>{c}</span>
                  ))}
                </div>
                <form style={{ display: 'flex', gap: '12px' }} onSubmit={(e) => { e.preventDefault(); if (constraintInput.trim()) { setConstraints([...constraints, constraintInput.trim()]); setConstraintInput(""); }}}>
                  <input
                    style={{ flex: 1, height: '40px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', padding: '0 12px' }}
                    placeholder="e.g. Do not accept a vague callback"
                    value={constraintInput}
                    onChange={(e) => setConstraintInput(e.target.value)}
                  />
                  <button type="submit" style={{ padding: '0 16px', background: 'var(--paper-border)', borderRadius: '2px', fontSize: '0.8rem', cursor: 'pointer' }}>Add</button>
                </form>
              </div>

              {/* Completion Criteria */}
              <div>
                <label className="intel-label">Completion Criteria</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                  {completionCriteria.map((c, i) => (
                    <span key={i} style={{ padding: '4px 10px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', fontSize: '0.8rem' }}>{c}</span>
                  ))}
                </div>
                <form style={{ display: 'flex', gap: '12px' }} onSubmit={(e) => { e.preventDefault(); if (criteriaInput.trim()) { setCompletionCriteria([...completionCriteria, criteriaInput.trim()]); setCriteriaInput(""); }}}>
                  <input
                    style={{ flex: 1, height: '40px', background: 'var(--bg-subtle)', border: '1px solid var(--paper-border)', borderRadius: '2px', padding: '0 12px' }}
                    placeholder="e.g. Refund is processed or reference number secured"
                    value={criteriaInput}
                    onChange={(e) => setCriteriaInput(e.target.value)}
                  />
                  <button type="submit" style={{ padding: '0 16px', background: 'var(--paper-border)', borderRadius: '2px', fontSize: '0.8rem', cursor: 'pointer' }}>Add</button>
                </form>
              </div>
            </div>
          </div>

          <button className="primary-button" disabled={starting} onClick={handleStart} type="button" style={{ marginTop: '80px' }}>
            {starting ? "Initializing Voice..." : "Run Negotiation"}
          </button>
        </div>
      ) : null}

      {recentNegotiations.length > 0 ? (
        <div style={{ marginTop: '120px', borderTop: '1px solid var(--paper-border)', paddingTop: '80px' }}>
          <h4 style={{ marginBottom: '40px' }}>History</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {recentNegotiations.map((item) => (
              <Link href={`/result/${item.id}`} key={item.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '20px 24px', background: 'transparent', borderRadius: '4px', border: '1px solid var(--paper-border)' }}>
                <div>
                  <strong style={{ display: 'block', fontSize: '0.95rem', letterSpacing: '-0.02em' }}>{item.provider}</strong>
                  <small style={{ color: 'var(--foreground-subtle)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: '4px', display: 'block' }}>{item.scenarioLabel}</small>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ display: 'block', fontSize: '1rem', fontWeight: '600' }}>{money(item.currentMonthly)}</span>
                  <small style={{ color: 'var(--foreground-muted)', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>{historyOutcome(item)}</small>
                </div>
              </Link>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
