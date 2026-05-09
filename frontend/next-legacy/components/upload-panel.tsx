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
      const negotiation = await createNegotiation(bill.id, customAngles);
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
                style={{ padding: '20px', background: 'transparent' }}
              >
                <div>
                  <strong style={{ fontSize: '0.9rem' }}>{item.label}</strong>
                  <span style={{ fontSize: '0.75rem', color: 'var(--foreground-subtle)', marginLeft: '8px' }}>{item.provider}</span>
                </div>
                <small style={{ fontSize: '0.6rem' }}>{loadingDemo === item.id ? "..." : "Load"}</small>
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
                placeholder="Custom leverage..."
                type="text"
                value={customInput}
              />
              <button style={{ padding: '0 20px', background: 'var(--foreground-subtle)', color: 'var(--foreground)', borderRadius: '2px', fontSize: '0.8rem', fontWeight: '700', cursor: 'pointer' }} disabled={!customInput.trim()} type="submit">
                Add
              </button>
            </form>
          </div>

          <button className="primary-button" disabled={starting} onClick={handleStart} type="button" style={{ marginTop: '80px' }}>
            {starting ? "Initializing Voice..." : "Run Negotiation"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
