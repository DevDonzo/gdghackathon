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

const DEMO_MISSION_PRESETS: Record<
  string,
  {
    companyName: string;
    issueDescription: string;
    desiredOutcome: string;
    targetMonthly: string;
    walkAwayMonthly: string;
    customerFacts: string[];
    constraints: string[];
    completionCriteria: string[];
    customAngles?: string[];
  }
> = {
  rogers_loyalty_review: {
    companyName: "Rogers",
    issueDescription: "The monthly bill is too high and there is a disputed $35 roaming fee that should be credited.",
    desiredOutcome: "Lower the monthly bill to $55 and apply a $35 credit for the disputed roaming fee.",
    targetMonthly: "55",
    walkAwayMonthly: "60",
    customerFacts: [
      "Current Rogers bill is $91.50 on Infinite Essentials 75",
      "There is a disputed $35 roaming fee",
      "Comparable plans are materially cheaper"
    ],
    constraints: [
      "Do not accept a vague callback",
      "Do not accept only a one-time credit without monthly rate relief",
      "Ask for loyalty or retention if frontline support cannot approve it"
    ],
    completionCriteria: [
      "Rep confirms the new monthly rate",
      "Rep confirms the $35 credit",
      "Rep confirms the effective date and account notes"
    ],
    customAngles: ["Refund incorrect roaming fee", "Lower monthly plan rate", "Retention review"]
  }
};

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
  const [targetMonthly, setTargetMonthly] = useState("");
  const [walkAwayMonthly, setWalkAwayMonthly] = useState("");
  const [customerFacts, setCustomerFacts] = useState<string[]>([]);
  const [factInput, setFactInput] = useState("");
  const [constraints, setConstraints] = useState<string[]>([]);
  const [constraintInput, setConstraintInput] = useState("");
  const [completionCriteria, setCompletionCriteria] = useState<string[]>([]);
  const [criteriaInput, setCriteriaInput] = useState("");

  useEffect(() => {
    async function loadHomeData() {
      const [demoResult, historyResult] = await Promise.allSettled([fetchDemoBills(), fetchRecentNegotiations()]);

      if (demoResult.status === "fulfilled") {
        setDemoBills(demoResult.value);
      } else {
        setDemoBills([]);
      }

      if (historyResult.status === "fulfilled") {
        setRecentNegotiations(historyResult.value);
      } else {
        setRecentNegotiations([]);
      }
    }

    loadHomeData();
  }, []);

  async function refreshRecentNegotiations() {
    try {
      setRecentNegotiations(await fetchRecentNegotiations());
    } catch {
      setRecentNegotiations([]);
    }
  }

  async function refreshDemoBills() {
    try {
      const items = await fetchDemoBills();
      setDemoBills(items);
    } catch {
      setDemoBills([]);
    }
  }

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
      await refreshRecentNegotiations();
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
    if (!hasUserMission()) {
      setError("Add the outcome, target, or completion proof before starting the voice agent.");
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
            targetMonthly: parseMoneyInput(targetMonthly),
            walkAwayMonthly: parseMoneyInput(walkAwayMonthly),
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
      const preset = DEMO_MISSION_PRESETS[scenarioId];
      setBill(extracted);
      setSelectedFile(null);
      setCompanyName(preset?.companyName ?? extracted.provider);
      setIssueDescription(preset?.issueDescription ?? "");
      setDesiredOutcome(preset?.desiredOutcome ?? "");
      setTargetMonthly(preset?.targetMonthly ?? "");
      setWalkAwayMonthly(preset?.walkAwayMonthly ?? "");
      setCustomerFacts(preset?.customerFacts ?? []);
      setConstraints(preset?.constraints ?? []);
      setCompletionCriteria(preset?.completionCriteria ?? []);
      setCustomAngles(preset?.customAngles ?? []);
      setCustomInput("");
      await refreshRecentNegotiations();
      await refreshDemoBills();
    } catch (demoError) {
      setError(demoError instanceof Error ? demoError.message : "Could not load demo bill.");
    } finally {
      setLoadingDemo(null);
    }
  }

  function hasIssueContext() {
    return Boolean(
      companyName.trim() ||
        issueDescription.trim() ||
        desiredOutcome.trim() ||
        targetMonthly.trim() ||
        walkAwayMonthly.trim() ||
        customerFacts.length ||
        constraints.length ||
        completionCriteria.length
    );
  }

  function hasUserMission() {
    return Boolean(
      issueDescription.trim() ||
        desiredOutcome.trim() ||
        targetMonthly.trim() ||
        walkAwayMonthly.trim() ||
        customerFacts.length ||
        constraints.length ||
        completionCriteria.length ||
        customAngles.length
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

  const readyForLaunch = Boolean(bill && hasUserMission());
  const visibleDemoBills = demoBills.filter((item) => item.id === "rogers_loyalty_review");

  return (
    <section className="agent-workspace" aria-label="Agent deployment">
      <div className="workspace-rail">
        <span className="mini-label">Mission setup</span>
        <strong>{bill ? bill.provider : "Choose evidence"}</strong>
        <p>{bill ? "Evidence loaded. Now enter what the agent should push for and what counts as done." : "Load sample evidence or scan a real statement, then define the mission yourself."}</p>
        <div className="workspace-progress" aria-label="Setup progress">
          <span className={bill ? "is-done" : ""}>Evidence</span>
          <span className={hasUserMission() ? "is-done" : ""}>Mission</span>
          <span className={readyForLaunch ? "is-done" : ""}>Launch</span>
        </div>
      </div>

      <div className="workspace-main">
        <div className="workspace-card evidence-card">
          <div className="panel-head compact-panel-head">
            <span className="section-tag">Evidence</span>
            <h3>Start with a bill.</h3>
            <p>Use sample evidence for a clean phone test, or scan a real statement.</p>
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

        {visibleDemoBills.length > 0 ? (
          <div className="demo-list">
            <span className="mini-label">Demo scenario</span>
            {visibleDemoBills.map((item) => (
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

        <div className="workspace-card mission-card">
          <div className="panel-head compact-panel-head">
            <span className="section-tag">Mission</span>
            <h3>What should happen on the call?</h3>
            <p>Tell the agent what you want. The bill is evidence, but your fields control the mission.</p>
          </div>

          <div className="mission-presets">
            <button
              type="button"
              onClick={() => {
                setCompanyName("");
                setIssueDescription("");
                setDesiredOutcome("");
                setTargetMonthly("");
                setWalkAwayMonthly("");
                setCustomerFacts([]);
                setConstraints([]);
                setCompletionCriteria([]);
              }}
            >
              Clear
            </button>
          </div>

          <div className="mission-form-grid">
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
              <div className="money-fields">
                <label>
                  <span>Target monthly</span>
                  <input inputMode="decimal" value={targetMonthly} onChange={(event) => setTargetMonthly(event.target.value)} placeholder="Your target price" />
                </label>
                <label>
                  <span>Walk-away max</span>
                  <input inputMode="decimal" value={walkAwayMonthly} onChange={(event) => setWalkAwayMonthly(event.target.value)} placeholder="Highest acceptable price" />
                </label>
              </div>
            </div>

            <div className="mission-chip-stack">
              <ChipEditor
                label="Known facts"
                value={factInput}
                values={customerFacts}
                placeholder="Account detail, receipt total, current bill..."
                onValue={setFactInput}
                onAdd={() => addChip(factInput, customerFacts, setCustomerFacts, () => setFactInput(""))}
                onRemove={(item) => setCustomerFacts(customerFacts.filter((fact) => fact !== item))}
              />
              <ChipEditor
                label="Constraints"
                value={constraintInput}
                values={constraints}
                placeholder="No contract, no vague callback..."
                onValue={setConstraintInput}
                onAdd={() => addChip(constraintInput, constraints, setConstraints, () => setConstraintInput(""))}
                onRemove={(item) => setConstraints(constraints.filter((constraint) => constraint !== item))}
              />
              <ChipEditor
                label="Completion proof"
                value={criteriaInput}
                values={completionCriteria}
                placeholder="Rep confirms rate, date, notes..."
                onValue={setCriteriaInput}
                onAdd={() => addChip(criteriaInput, completionCriteria, setCompletionCriteria, () => setCriteriaInput(""))}
                onRemove={(item) => setCompletionCriteria(completionCriteria.filter((criterion) => criterion !== item))}
              />
            </div>
          </div>
        </div>

        <div className="workspace-card outcome-card">
          <div className="panel-head compact-panel-head">
            <span className="section-tag">Launch</span>
            <h3>{readyForLaunch ? "Ready for the phone." : bill ? "Add the mission." : "Waiting for evidence."}</h3>
            <p>{readyForLaunch ? "The backend will build the user-directed plan, dial your verified number, and stream the call." : bill ? "Enter the outcome, target, or completion proof so the agent knows what to pursue." : "Load sample evidence or scan a bill first."}</p>
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

        <button className="primary-button launch-button" disabled={!readyForLaunch || starting} onClick={handleStart} type="button">
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

function parseMoneyInput(value: string): number | null {
  const normalized = value.replace(/[^0-9.]/g, "");
  if (!normalized) {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}
