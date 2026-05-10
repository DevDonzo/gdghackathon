# @ratedrop/agent

Small JavaScript client SDK for launching RateDrop voice-agent runs against a deployed RateDrop backend.

The actual live-call decision loop is server-side. In this repo, Twilio ConversationRelay calls into `backend/app/services/conversation_relay.py`, which routes each representative utterance through the Google ADK-backed negotiator agent in `backend/app/agent/negotiator_agent.py` when `RATEDROP_AGENT_MODE=adk`.

## Install

```bash
npm install @ratedrop/agent
```

For the hackathon repo, this package is local in `packages/ratedrop-agent`.

## Use

```ts
import { RateDropAgent } from "@ratedrop/agent";

const agent = new RateDropAgent({
  apiBaseUrl: "https://your-ratedrop-api.com"
});

const run = await agent.createSupportRun({
  billId: "bill_123",
  companyName: "Air Canada",
  problemSummary: "Wrong baggage fee charged",
  desiredOutcome: "Refund the fee and capture a reference number",
  customerFacts: ["Booking ABC123", "Receipt shows $75 baggage fee"],
  completionCriteria: ["Rep confirms refund", "Reference number captured"]
});

await agent.startVoiceCall(run.id);
```

## What this proves

`@ratedrop/agent` is the app-facing SDK. The Google ADK wrapper stays on the backend so private model credentials, policy bounds, Twilio callbacks, and deterministic result math are not shipped to the browser.
