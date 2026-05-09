export type LineItem = {
  label: string;
  amount: number;
  recurring: boolean;
  category: "plan" | "tax" | "fee" | "overage" | "discount" | "other";
};

export type BillSummary = {
  id: string;
  filename: string;
  provider: string;
  currency: string;
  monthlyTotal: number;
  planName: string;
  lineItems: LineItem[];
  negotiationAngles: string[];
  redFlags: string[];
  extractionConfidence: number;
  createdAt: string;
};

export type CallState = {
  sid: string | null;
  to: string | null;
  fromNumber: string | null;
  status: string;
  mode: "sandbox" | "simulated";
  error: string | null;
};

export type NegotiationResult = {
  currentMonthly: number;
  newMonthly: number;
  monthlySavings: number;
  annualSavings: number;
  oneTimeCredit: number;
  effectiveFirstYearValue: number;
  summary: string;
  transcriptSummary: string[];
};

export type Negotiation = {
  id: string;
  billId: string;
  status: "draft" | "in-progress" | "completed";
  scenarioId: string;
  scenarioLabel: string;
  provider: string;
  currentMonthly: number;
  targetMonthly: number;
  walkAwayMonthly: number;
  bestOfferMonthly: number | null;
  oneTimeCredit: number;
  currentObjective: string;
  call: CallState;
  result: NegotiationResult | null;
  createdAt: string;
  startedAt: string | null;
  endedAt: string | null;
};

export type TranscriptTurn = {
  role: "negotiator" | "rep" | "system";
  intent: string;
  objective: string;
  text: string;
  proposedMonthly: number | null;
  credit: number;
  createdAt: string;
};
