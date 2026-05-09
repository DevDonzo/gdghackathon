# RateDrop

RateDrop is a standalone hackathon MVP for telecom bill negotiation.

The product flow is:

1. Upload a telecom bill PDF or image, or load a built-in demo bill
2. Extract provider, monthly total, line items, and negotiation angles
3. Review the bill summary in the frontend
4. Start a controlled Twilio sandbox call
5. Watch the transcript update live
6. Land on a deterministic savings result page

## Repo Structure

- [`frontend/static/`](/Users/hparacha/Projects/gdghackathon/frontend/static): active frontend, written in plain HTML, CSS, and JavaScript
- [`frontend/next-legacy/`](/Users/hparacha/Projects/gdghackathon/frontend/next-legacy): archived Next.js implementation kept only as a reference
- [`backend/`](/Users/hparacha/Projects/gdghackathon/backend): FastAPI backend, MongoDB integration, Gemini extraction, negotiation engine, and Twilio flow
- [`scripts/`](/Users/hparacha/Projects/gdghackathon/scripts): smoke and backend sanity checks

## Stack

- Frontend: static HTML, CSS, and JavaScript
- Backend: FastAPI
- Database: MongoDB Atlas
- Model: Gemini 2.5 Flash
- Voice: Twilio Programmable Voice
- Logic: deterministic negotiation policy and deterministic savings math

## Environment

The backend reads the root `.env.local`.

Required:

- `MONGODB_URI`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`

Important optional values:

- `TWILIO_VERIFY_ORIG_NUMBERS`
- `TWILIO_SANDBOX_TO_NUMBER`
- `PUBLIC_BASE_URL`
- `FRONTEND_BASE_URL`

Behavior notes:

- If `PUBLIC_BASE_URL` is missing, the backend falls back to simulated call mode
- Twilio trial mode requires verified destination numbers
- If Atlas is unreachable, the static shell still loads, but API-backed flows that need persistence will fail until MongoDB is reachable

## Install

```bash
python3 -m pip install -r backend/requirements.txt
```

## Run

Start the backend:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

The active frontend is served directly by FastAPI from `frontend/static/`.

## Frontend Notes

If you are only working on the UI, focus on:

- [`frontend/static/index.html`](/Users/hparacha/Projects/gdghackathon/frontend/static/index.html)
- [`frontend/static/styles.css`](/Users/hparacha/Projects/gdghackathon/frontend/static/styles.css)
- [`frontend/static/app.js`](/Users/hparacha/Projects/gdghackathon/frontend/static/app.js)

The old Next.js code in [`frontend/next-legacy/`](/Users/hparacha/Projects/gdghackathon/frontend/next-legacy) is not the active app path.

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

## Validation

Backend compile:

```bash
python3 -m py_compile backend/app/main.py backend/app/services/negotiation.py backend/app/services/twilio_voice.py backend/app/db/mongo.py backend/app/models/schemas.py
```

Frontend syntax:

```bash
node --check frontend/static/app.js
```

End-to-end smoke:

```bash
python3 scripts/smoke_mvp.py
```

## Known Limits

- A public API URL is still required for Twilio to hit the voice and status webhooks
- The current Twilio flow is a narrated sandbox call, not a full duplex speech loop
- Trial-account call reliability still depends on verified destination numbers
- This is a hackathon MVP, not a production-grade deployment
