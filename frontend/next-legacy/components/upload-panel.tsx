"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  createDemoBill,
  createNegotiation,
  fetchDemoBills,
  fetchRecentNegotiations,
  money,
  startNegotiation,
  uploadBill,
  type DemoBillOption
} from "@/lib/api";
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
      if (!companyName) {
        setCompanyName(extracted.provider);
      }
      setRecentNegotiations(await fetchRecentNegotiations());
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
      const issueContext = hasIssueContext()
        ? {
            companyName,
            issueDescription,
            desiredOutcome,
            customerFacts,
            constraints,
            completionCriteria
          }
        : undefined;

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
      setCompanyName(extracted.provider);
      setCustomAngles([]);
      setCustomInput("");
      setRecentNegotiations(await fetchRecentNegotiations());
    } catch (demoError) {
      setError(demoError instanceof Error ? demoError.message : "Could not load demo bill.");
    } finally {
      setLoadingDemo(null);
    }
  }

  function hasIssueContext() {
    return Boolean(
      companyName ||
        issueDescription ||
        desiredOutcome ||
        customerFacts.length ||
        constraints.length ||
        completionCriteria.length
    );
  }

  function addChip(value: string, values: string[], setValues: (items: string[]) => void, clear: () => void) {
    const clean = value.trim();
    if (!clean || values.includes(clean)) {
      clear();
      return;
    }
    setValues([...values, clean]);
    clear();
  }

  function addCustomAngle() {
    addChip(customInput, customAngles, setCustomAngles, () => setCustomInput(""));
  }

  function historyOutcome(item: Negotiation): string {
    if (item.call.error) {
      return item.call.error;
    }
    if (item.result) {
      return `${money(item.result.newMonthly)}/mo after`;
    }
    return item.status.replace("-", " ");
  }

  return (
    <section className="deploy-grid" aria-label="Agent deployment">
      <div className="deploy-card">
        <div className="panel-head">
          <span className="section-tag">Input</span>
          <h3>Bill or receipt</h3>
          <p>Start with a real statement or load a demo scenario. The extracted bill becomes the agent mission.</p>
        </div>

        <form className="upload-form" onSubmit={handleUpload}>
          <label className="dropzone" htmlFor="bill-upload">
            <span>{selectedFile ? selectedFile.name : "Select statement file"}</span>
            <small>PDF, JPG, or PNG</small>
          </label>
          <input
            id="bill-upload"
            className="sr-only"
            type="file"
            accept=".pdf,image/png,image/jpeg,image/jpg"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
          <button className="primary-button" disabled={uploading} type="submit">
            {uploading ? "Scanning..." : "Scan bill"}
          </button>
        </form>

        {demoBills.length > 0 ? (
          <div className="demo-list">
            <span className="mini-label">Demo scenarios</span>
            {demoBills.map((item) => (
              <button
                className="demo-row"
                key={item.id}
                disabled={loadingDemo !== null}
                onClick={() => handleDemoBill(item.id)}
                type="button"
              >
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.provider} · {money(item.monthlyTotal)}</small>
                </span>
                <em>{loadingDemo === item.id ? "Loading" : "Load"}</em>
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="deploy-card mission-card">
        <div className="panel-head">
          <span className="section-tag">Mission</span>
          <h3>What should the agent fix?</h3>
          <p>Optional context lets RateDrop handle more than telecom negotiation, like refunds, disputes, travel support, or account fixes.</p>
        </div>

        <div className="mission-fields">
          <label>
            <span>Company</span>
            <input value={companyName} onChange={(event) => setCompanyName(event.target.value)} placeholder="Bell, Air Canada, Rogers..." />
          </label>
          <label>
            <span>Problem</span>
            <textarea value={issueDescription} onChange={(event) => setIssueDescription(event.target.value)} placeholder="Describe the charge, booking, account issue, or outcome gap." />
          </label>
          <label>
            <span>Desired outcome</span>
            <input value={desiredOutcome} onChange={(event) => setDesiredOutcome(event.target.value)} placeholder="Refund, lower monthly rate, rebooking, fee removed..." />
          </label>
        </div>

        <ChipEditor
          label="Known facts"
          value={factInput}
          values={customerFacts}
          placeholder="Booking ref, account number, receipt total..."
          onValue={setFactInput}
          onAdd={() => addChip(factInput, customerFacts, setCustomerFacts, () => setFactInput(""))}
          onRemove={(item) => setCustomerFacts(customerFacts.filter((fact) => fact !== item))}
        />
        <ChipEditor
          label="Constraints"
          value={constraintInput}
          values={constraints}
          placeholder="Do not accept vague callback..."
          onValue={setConstraintInput}
          onAdd={() => addChip(constraintInput, constraints, setConstraints, () => setConstraintInput(""))}
          onRemove={(item) => setConstraints(constraints.filter((constraint) => constraint !== item))}
        />
        <ChipEditor
          label="Completion proof"
          value={criteriaInput}
          values={completionCriteria}
          placeholder="Rep confirms refund and gives reference..."
          onValue={setCriteriaInput}
          onAdd={() => addChip(criteriaInput, completionCriteria, setCompletionCriteria, () => setCriteriaInput(""))}
          onRemove={(item) => setCompletionCriteria(completionCriteria.filter((criterion) => criterion !== item))}
        />
      </div>

      <div className="deploy-card outcome-card">
        <div className="panel-head">
          <span className="section-tag">Launch</span>
          <h3>{bill ? "Ready for call" : "Waiting for bill"}</h3>
          <p>{bill ? "Review the extracted bill facts, add optional pressure points, then start the live agent flow." : "Upload or load a demo bill to unlock the launch sequence."}</p>
        </div>

        {bill ? (
          <div className="bill-proof">
            <div>
              <span>Provider</span>
              <strong>{bill.provider}</strong>
            </div>
            <div>
              <span>Plan</span>
              <strong>{bill.planName}</strong>
            </div>
            <div>
              <span>Monthly total</span>
              <strong>{money(bill.monthlyTotal)}</strong>
            </div>
            <div>
              <span>Confidence</span>
              <strong>{Math.round(bill.extractionConfidence * 100)}%</strong>
            </div>
          </div>
        ) : (
          <div className="empty-state">No statement loaded yet.</div>
        )}

        {bill ? (
          <ChipEditor
            label="Extra negotiation angles"
            value={customInput}
            values={customAngles}
            placeholder="Promo expired, competitor price, loyalty issue..."
            onValue={setCustomInput}
            onAdd={addCustomAngle}
            onRemove={(item) => setCustomAngles(customAngles.filter((angle) => angle !== item))}
          />
        ) : null}

        {error ? <div className="error-banner">{error}</div> : null}

        <button className="primary-button launch-button" disabled={!bill || starting} onClick={handleStart} type="button">
          {starting ? "Initializing..." : "Start voice agent"}
        </button>

        {recentNegotiations.length ? (
          <div className="recent-list">
            <span className="mini-label">Recent sessions</span>
            {recentNegotiations.slice(0, 4).map((item) => (
              <Link className="recent-row" href={item.status === "completed" ? `/result/${item.id}` : `/call/${item.id}`} key={item.id}>
                <span>
                  <strong>{item.provider}</strong>
                  <small>{historyOutcome(item)}</small>
                </span>
                <em>{item.status}</em>
              </Link>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

type ChipEditorProps = {
  label: string;
  value: string;
  values: string[];
  placeholder: string;
  onValue: (value: string) => void;
  onAdd: () => void;
  onRemove: (value: string) => void;
};

function ChipEditor({ label, value, values, placeholder, onValue, onAdd, onRemove }: ChipEditorProps) {
  return (
    <div className="chip-editor">
      <span className="mini-label">{label}</span>
      <div className="chip-input-row">
        <input
          value={value}
          onChange={(event) => onValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onAdd();
            }
          }}
          placeholder={placeholder}
        />
        <button type="button" onClick={onAdd}>
          Add
        </button>
      </div>
      {values.length ? (
        <div className="chip-list">
          {values.map((item) => (
            <button type="button" key={item} onClick={() => onRemove(item)}>
              {item}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
