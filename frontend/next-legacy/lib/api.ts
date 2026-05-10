import { BillSummary, Negotiation, TranscriptTurn } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function handle<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Request failed.");
  }
  return response.json() as Promise<T>;
}

export async function uploadBill(file: File): Promise<BillSummary> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/bills/upload`, {
    method: "POST",
    body: formData
  });
  return handle<BillSummary>(response);
}

export type DemoBillOption = {
  id: string;
  label: string;
  provider: string;
  monthlyTotal: number;
  headlineAngle: string;
};

export async function fetchDemoBills(): Promise<DemoBillOption[]> {
  const response = await fetch(`${API_BASE}/api/demo-bills`, {
    cache: "no-store"
  });
  const payload = await handle<{ items: DemoBillOption[] }>(response);
  return payload.items;
}

export async function createDemoBill(scenarioId: string): Promise<BillSummary> {
  const response = await fetch(`${API_BASE}/api/bills/demo/${scenarioId}`, {
    method: "POST"
  });
  return handle<BillSummary>(response);
}

export async function createNegotiation(
  billId: string,
  customAngles: string[] = [],
  issueContext?: {
    companyName?: string;
    issueDescription?: string;
    desiredOutcome?: string;
    targetMonthly?: number | null;
    walkAwayMonthly?: number | null;
    customerFacts?: string[];
    constraints?: string[];
    completionCriteria?: string[];
  }
): Promise<Negotiation> {
  const response = await fetch(`${API_BASE}/api/negotiations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      billId,
      customAngles,
      ...issueContext
    })
  });
  return handle<Negotiation>(response);
}

export async function fetchRecentNegotiations(limit = 6): Promise<Negotiation[]> {
  const response = await fetch(`${API_BASE}/api/negotiations?limit=${limit}`, {
    cache: "no-store"
  });
  const payload = await handle<{ items: Negotiation[] }>(response);
  return payload.items;
}

export async function startNegotiation(negotiationId: string): Promise<Negotiation> {
  const response = await fetch(`${API_BASE}/api/negotiations/${negotiationId}/start`, {
    method: "POST",
    headers: {
      "x-ratedrop-call-mode": "conversation_relay"
    }
  });
  return handle<Negotiation>(response);
}

export async function fetchNegotiation(negotiationId: string): Promise<Negotiation> {
  const response = await fetch(`${API_BASE}/api/negotiations/${negotiationId}`, {
    cache: "no-store"
  });
  return handle<Negotiation>(response);
}

export async function fetchTranscript(negotiationId: string): Promise<TranscriptTurn[]> {
  const response = await fetch(`${API_BASE}/api/negotiations/${negotiationId}/transcript`, {
    cache: "no-store"
  });
  const payload = await handle<{ turns: TranscriptTurn[] }>(response);
  return payload.turns;
}

export function eventsUrl(negotiationId: string): string {
  return `${API_BASE}/api/negotiations/${negotiationId}/events`;
}

export function money(value: number): string {
  return new Intl.NumberFormat("en-CA", {
    style: "currency",
    currency: "CAD",
    maximumFractionDigits: 2
  }).format(value);
}
