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
      const negotiation = await createNegotiation(bill.id);
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
    <div className="panel card">
      <div className="panel-header">
        <span className="section-tag">Start with your bill</span>
        <h2>Upload a telecom bill</h2>
        <p>PDF, JPG, or PNG. RateDrop extracts the actual charges first, then builds the call plan around them.</p>
      </div>

      <form className="upload-form" onSubmit={handleUpload}>
        <label className="upload-dropzone" htmlFor="bill-upload">
          <span>{selectedFile ? selectedFile.name : "Choose a bill file"}</span>
          <small>{selectedFile ? "Ready to extract bill facts." : "Drag in a statement or tap to browse."}</small>
        </label>
        <input
          id="bill-upload"
          className="sr-only"
          type="file"
          accept=".pdf,image/png,image/jpeg,image/jpg"
          onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
        />
        <button className="primary-button" disabled={uploading} type="submit">
          {uploading ? "Extracting bill..." : "Extract bill summary"}
        </button>
      </form>

      {demoBills.length > 0 ? (
        <div className="detail-block">
          <h4>Or start with a demo bill</h4>
          <div className="demo-bill-list">
            {demoBills.map((item) => (
              <button
                className="demo-bill-card"
                disabled={loadingDemo !== null}
                key={item.id}
                onClick={() => handleDemoBill(item.id)}
                type="button"
              >
                <strong>{item.label}</strong>
                <span>
                  {money(item.monthlyTotal)}/mo · {item.headlineAngle}
                </span>
                <small>{loadingDemo === item.id ? "Loading demo bill..." : "Use this scenario"}</small>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {error ? <div className="error-banner">{error}</div> : null}

      {bill ? (
        <div className="bill-review">
          <div className="review-topline">
            <div>
              <span className="section-tag">Extracted summary</span>
              <h3>
                {bill.provider} · {money(bill.monthlyTotal)}/mo
              </h3>
            </div>
            <div className="confidence-pill">{Math.round(bill.extractionConfidence * 100)}% confidence</div>
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <span>Plan</span>
              <strong>{bill.planName}</strong>
            </div>
            <div className="stat-card">
              <span>Line items</span>
              <strong>{bill.lineItems.length}</strong>
            </div>
            <div className="stat-card">
              <span>Likely leverage</span>
              <strong>{bill.negotiationAngles[0] ?? "Retention review"}</strong>
            </div>
          </div>

          <div className="detail-block">
            <h4>Negotiation angles</h4>
            <div className="chip-row">
              {bill.negotiationAngles.map((angle) => (
                <span className="chip" key={angle}>
                  {angle}
                </span>
              ))}
            </div>
          </div>

          <div className="detail-block">
            <h4>Bill charges</h4>
            <div className="line-item-list">
              {bill.lineItems.map((item) => (
                <div className="line-item" key={`${item.label}-${item.amount}`}>
                  <div>
                    <strong>{item.label}</strong>
                    <small>{item.category}</small>
                  </div>
                  <span>{money(item.amount)}</span>
                </div>
              ))}
            </div>
          </div>

          <button className="primary-button" disabled={starting} onClick={handleStart} type="button">
            {starting ? "Dialing sandbox..." : "Start negotiation"}
          </button>
        </div>
      ) : null}

      {!bill && recentNegotiations.length > 0 ? (
        <div className="detail-block">
          <div className="detail-header">
            <h4>Recent negotiations</h4>
            <small>Loaded from MongoDB</small>
          </div>
          <div className="recent-negotiation-list">
            {recentNegotiations.map((item) => (
              <Link className="recent-negotiation-card" href={`/result/${item.id}`} key={item.id}>
                <div className="recent-negotiation-copy">
                  <strong>{item.provider}</strong>
                  <small>{item.scenarioLabel}</small>
                </div>
                <div className="recent-negotiation-metrics">
                  <span>{money(item.currentMonthly)}/mo</span>
                  <small>{historyOutcome(item)}</small>
                </div>
              </Link>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
