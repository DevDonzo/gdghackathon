# RateDrop

RateDrop is a standalone hackathon MVP for delegating support calls to a bounded voice agent.

The demo flow is:

1. Upload a bill or receipt, or load a built-in demo bill
2. Describe the company, problem, desired outcome, facts, and completion proof
3. Extract structured bill facts
4. Create a deterministic phone mission
5. Start a Twilio voice flow
6. Stream transcript updates in the UI
7. Show a deterministic outcome/result page

## Repo Structure

- [`frontend/next-legacy/`](/Users/hparacha/Projects/gdghackathon/frontend/next-legacy): active Next.js frontend
- [`backend/`](/Users/hparacha/Projects/gdghackathon/backend): FastAPI API, storage, extraction, policy, Google ADK agent routing, and Twilio webhooks
- [`packages/ratedrop-agent/`](/Users/hparacha/Projects/gdghackathon/packages/ratedrop-agent): local JavaScript client SDK package
- [`scripts/`](/Users/hparacha/Projects/gdghackathon/scripts): backend sanity, live policy, agent wrapper, company lookup, and smoke tests
- [`docs/cloud-and-sdk.md`](/Users/hparacha/Projects/gdghackathon/docs/cloud-and-sdk.md): cloud-track and npm package story
- [`deploy/gcp/cloud-run/`](/Users/hparacha/Projects/gdghackathon/deploy/gcp/cloud-run): Google Cloud Run deployment for the full demo stack

## Stack

- Frontend: Next.js 15
- Backend: FastAPI
- Storage: local JSON by default, MongoDB optional
- Extraction: Gemini when configured, deterministic demo fixtures otherwise
- Agent: Google ADK-backed negotiator agent with deterministic policy tools
- Model provider: Gemini by default
- Voice: Twilio Programmable Voice and ConversationRelay-ready webhook paths
- Search/contact lookup: Tavily when configured

## Install

```bash
cd frontend/next-legacy
npm install
cd ../..
python3 -m pip install -r backend/requirements.txt
```

## Run Locally

Backend:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend/next-legacy
npm run dev -- --port 3001
```

Open:

```text
http://127.0.0.1:3001
```

The backend API is available at:

```text
http://127.0.0.1:8000
```

## Environment

The backend reads the root `.env.local`.

Important values:

- `RATEDROP_DATABASE_MODE=local` or `mongo`
- `MONGODB_URI`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `RATEDROP_AGENT_MODE=adk`
- `RATEDROP_AGENT_MODEL_PROVIDER=gemini`
- `TAVILY_API_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `TWILIO_VERIFY_ORIG_NUMBERS`
- `TWILIO_SANDBOX_TO_NUMBER`
- `PUBLIC_BASE_URL`
- `FRONTEND_BASE_URL=http://127.0.0.1:3001`
- `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`

Behavior notes:

- Local storage is the default reliable demo path.
- If `PUBLIC_BASE_URL` is missing, real Twilio callbacks cannot reach localhost.
- Twilio trial mode requires verified destination numbers.
- Do not describe the system as production-grade.

## API Surface

- `POST /api/bills/upload`
- `GET /api/demo-bills`
- `POST /api/bills/demo/{scenarioId}`
- `GET /api/bills/{id}`
- `GET /api/negotiations?limit=N`
- `POST /api/negotiations`
- `POST /api/negotiations/{id}/start`
- `GET /api/negotiations/{id}`
- `GET /api/negotiations/{id}/transcript`
- `GET /api/negotiations/{id}/events`
- `POST /twilio/voice/negotiations/{id}`
- `POST /twilio/status/{id}`
- `WS /ws/conversation-relay/{id}`

## SDK Package

The app-facing SDK lives in `packages/ratedrop-agent`.

```bash
cd packages/ratedrop-agent
npm run build
npm pack
```

Example:

```ts
import { RateDropAgent } from "@ratedrop/agent";

const agent = new RateDropAgent({
  apiBaseUrl: "https://your-ratedrop-api.com"
});

const run = await agent.createSupportRun({
  billId: "bill_123",
  companyName: "Air Canada",
  problemSummary: "Wrong baggage fee charged",
  desiredOutcome: "Refund the fee and capture a reference number"
});

await agent.startVoiceCall(run.id);
```

## Validation

Backend compile:

```bash
python3 -m py_compile backend/app/main.py backend/app/services/negotiation.py backend/app/services/twilio_voice.py backend/app/services/conversation_relay.py backend/app/db/mongo.py backend/app/models/schemas.py
```

Frontend build:

```bash
cd frontend/next-legacy
npm run build
```

SDK typecheck:

```bash
cd packages/ratedrop-agent
npm install
npm run build
```

Backend sanity and smoke require a running backend:

```bash
python3 scripts/backend_sanity.py
python3 scripts/smoke_mvp.py
```

## GCP Cloud Run Deployment

For the Google hackathon demo, deploy the full app to Cloud Run:

```bash
PROJECT_ID=ayafinancial REGION=us-central1 SERVICE_NAME=ratedrop ./deploy/gcp/cloud-run/deploy.sh
```

The Cloud Run container serves the Next.js frontend and FastAPI backend from one public HTTPS URL. See [`deploy/gcp/cloud-run/README.md`](/Users/hparacha/Projects/gdghackathon/deploy/gcp/cloud-run/README.md) for details and cost controls.
