export type RateDropAgentOptions = {
  apiBaseUrl: string;
  fetch?: typeof fetch;
};

export type SupportRunInput = {
  billId: string;
  customAngles?: string[];
  companyName?: string;
  issueDescription?: string;
  problemSummary?: string;
  desiredOutcome?: string;
  customerFacts?: string[];
  constraints?: string[];
  completionCriteria?: string[];
};

export type RateDropRun = {
  id: string;
  billId: string;
  status: "draft" | "in-progress" | "completed" | "failed";
  provider: string;
  currentObjective: string;
  call: {
    sid: string | null;
    status: string;
    mode: "sandbox" | "simulated" | "conversation_relay";
    error: string | null;
  };
};

export type TranscriptTurn = {
  role: "negotiator" | "rep" | "system";
  intent: string;
  objective: string;
  text: string;
  createdAt: string;
};

export class RateDropAgent {
  private readonly apiBaseUrl: string;
  private readonly fetcher: typeof fetch;

  constructor(options: RateDropAgentOptions) {
    this.apiBaseUrl = options.apiBaseUrl.replace(/\/$/, "");
    this.fetcher = options.fetch ?? fetch;
  }

  async createSupportRun(input: SupportRunInput): Promise<RateDropRun> {
    const response = await this.fetcher(`${this.apiBaseUrl}/api/negotiations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        billId: input.billId,
        customAngles: input.customAngles ?? [],
        companyName: input.companyName,
        issueDescription: input.issueDescription ?? input.problemSummary,
        desiredOutcome: input.desiredOutcome,
        customerFacts: input.customerFacts ?? [],
        constraints: input.constraints ?? [],
        completionCriteria: input.completionCriteria ?? []
      })
    });

    return this.handle<RateDropRun>(response);
  }

  async startVoiceCall(runId: string): Promise<RateDropRun> {
    const response = await this.fetcher(`${this.apiBaseUrl}/api/negotiations/${runId}/start`, {
      method: "POST"
    });
    return this.handle<RateDropRun>(response);
  }

  async getRun(runId: string): Promise<RateDropRun> {
    const response = await this.fetcher(`${this.apiBaseUrl}/api/negotiations/${runId}`, {
      cache: "no-store"
    });
    return this.handle<RateDropRun>(response);
  }

  async getTranscript(runId: string): Promise<TranscriptTurn[]> {
    const response = await this.fetcher(`${this.apiBaseUrl}/api/negotiations/${runId}/transcript`, {
      cache: "no-store"
    });
    const payload = await this.handle<{ turns: TranscriptTurn[] }>(response);
    return payload.turns;
  }

  eventsUrl(runId: string): string {
    return `${this.apiBaseUrl}/api/negotiations/${runId}/events`;
  }

  private async handle<T>(response: Response): Promise<T> {
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return response.json() as Promise<T>;
  }
}
