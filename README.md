# RateDrop

RateDrop is a standalone hackathon MVP for telecom bill negotiation.

The product flow is:

1. Upload a telecom bill PDF or image, or load a built-in demo bill.
2. Extract provider, monthly total, line items, and negotiation angles.
3. Review the bill summary in the Next.js frontend.
4. Start a controlled Twilio sandbox call.
5. Watch the transcript update live.
6. Land on a deterministic savings result page.

## Stack

- Next.js 15 frontend in the repo root
- FastAPI backend in [`backend/`](/Users/hparacha/Projects/gdghackathon/backend)
- MongoDB Atlas for bills, negotiations, and transcript turns
- Gemini 2.5 Flash for bill extraction and line phrasing
- Twilio Programmable Voice for the sandbox call
- Deterministic negotiation policy and deterministic savings math

## Repo Layout

- [`app/`](/Users/hparacha/Projects/gdghackathon/app): Next.js routes
- [`components/`](/Users/hparacha/Projects/gdghackathon/components): upload, live call, and result UI
- [`lib/`](/Users/hparacha/Projects/gdghackathon/lib): frontend API client and shared types
- [`backend/app/`](/Users/hparacha/Projects/gdghackathon/backend/app): FastAPI app, Mongo access, extraction, negotiation engine, Twilio hooks
- [`plan.md`](/Users/hparacha/Projects/gdghackathon/plan.md): product plan used for this build

## Environment

The backend reads the root `.env.local` directly. The frontend reads the root `.env.local` through Next.js.

Existing required vars already match the app:

- `MONGODB_URI`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `TWILIO_VERIFY_ORIG_NUMBERS`

Additional optional vars for a real Twilio sandbox run:

- `TWILIO_SANDBOX_TO_NUMBER`
- `PUBLIC_BASE_URL`
- `FRONTEND_BASE_URL`
- `NEXT_PUBLIC_API_BASE_URL`

If `PUBLIC_BASE_URL` is missing, the app still runs the deterministic negotiation and transcript flow, but the Twilio call stays in simulated mode because Twilio cannot reach a localhost webhook.

## Install

### Frontend

```bash
npm install
```

### Backend

```bash
python3 -m pip install -r backend/requirements.txt
```

## Run

Start the API:

```bash
npm run dev:api
```

Start the frontend in a second terminal:

```bash
npm run dev
```

Then open `http://127.0.0.1:3000`.

Optional smoke check once the API is running:

```bash
python3 scripts/smoke_mvp.py
```

## API Surface

- `POST /api/bills/upload`
- `GET /api/demo-bills`
- `POST /api/bills/demo/{scenarioId}`
- `GET /api/bills/{id}`
- `POST /api/negotiations`
- `POST /api/negotiations/{id}/start`
- `GET /api/negotiations/{id}`
- `GET /api/negotiations/{id}/transcript`
- `GET /api/negotiations/{id}/events`
- `POST /twilio/voice/negotiations/{id}`
- `POST /twilio/status/{id}`

## How The MVP Works

### Bill extraction

The upload endpoint accepts a PDF or image, sends it to Gemini, and stores a strict structured summary in MongoDB. If Gemini is unavailable, the backend falls back to a demo extraction template so the UI still works.

### Negotiation engine

Negotiation logic is not improvised by the model.

- The backend picks a deterministic scenario: `happy_path`, `escalation_path`, or `fee_recovery_path`.
- The policy engine sets the intent, objective, and numeric offer ladder.
- Gemini is only used to phrase the already-decided turns.
- Savings math is always computed in code from the structured offer values.

### Twilio sandbox

When a negotiation starts, the backend tries to place an outbound call from `TWILIO_PHONE_NUMBER` to `TWILIO_SANDBOX_TO_NUMBER` or the first verified number in `TWILIO_VERIFY_ORIG_NUMBERS`.

The Twilio voice webhook reads out the scripted negotiation line by line so the sandbox number receives a controlled live demo while the frontend streams the same negotiation transcript.

## Demo Notes

- The UI is branded only as RateDrop.
- The call side is explicitly sandboxed and consumer-product oriented.

## Known Limits

- A public API URL is required for Twilio to hit the voice/status webhooks.
- The current Twilio flow is a narrated sandbox call, not a full duplex speech loop.
- Gemini failures fall back to a canned extraction/phrasing path so the demo remains stable.
