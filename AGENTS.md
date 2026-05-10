# AGENTS

This repository is a standalone product called RateDrop.

Do not frame it as related to ASSIST, prior demos, or internal prototypes.
Do not add ASSIST references to UI copy, docs, comments, or commit messages.

## Product Summary

RateDrop is a hackathon MVP that:

1. Accepts a bill PDF/image or demo bill
2. Captures the support problem and desired outcome
3. Extracts structured bill facts
4. Builds a deterministic phone mission
5. Starts a Twilio voice flow
6. Routes live rep utterances through a Google ADK-backed agent when enabled
7. Streams transcript updates in the UI
8. Shows deterministic result math and outcome proof

## Current Architecture

- Frontend: Next.js 15 in `frontend/next-legacy/`
- Backend: FastAPI in `backend/app/`
- Storage: local JSON by default, MongoDB optional
- Extraction: Gemini when configured, demo fixtures otherwise
- Agent: Google ADK-backed negotiator in `backend/app/agent/`
- Default model provider: Gemini
- Voice: Twilio Programmable Voice and ConversationRelay-ready routes
- SDK package: `packages/ratedrop-agent/`

## Non-Negotiable Product Constraints

- Keep the product consumer-facing and standalone
- Do not rely on pure LLM improvisation for negotiation logic
- Keep final math deterministic and code-driven
- Prefer a reliable demo path over extra features
- Do not break existing API contracts unless the whole stack is updated together
- Do not describe the system as production-grade

## Backend Ownership

Backend owns request validation, bill extraction, issue context building, scenario selection, deterministic policy, transcript persistence, SSE publishing, Twilio callbacks, Google ADK routing, and storage document shapes.

Frontend owns layout, styling, interaction polish, loading/error states, mobile responsiveness, and rendering backend data clearly.

## API Contracts To Preserve

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

Primary frontend contract files:

- `frontend/next-legacy/lib/api.ts`
- `frontend/next-legacy/lib/types.ts`

## Local Run Commands

Install:

```bash
cd frontend/next-legacy
npm install
cd ../..
python3 -m pip install -r backend/requirements.txt
```

Run backend:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000
```

Run frontend:

```bash
cd frontend/next-legacy
npm run dev -- --port 3001
```

Open:

```text
http://127.0.0.1:3001
```

## Required Validation After Meaningful Changes

For backend changes:

```bash
python3 -m py_compile backend/app/main.py backend/app/services/negotiation.py backend/app/services/twilio_voice.py backend/app/services/conversation_relay.py backend/app/db/mongo.py backend/app/models/schemas.py
python3 scripts/backend_sanity.py
```

For frontend changes:

```bash
cd frontend/next-legacy
npm run build
```

For SDK changes:

```bash
cd packages/ratedrop-agent
npm run build
```

For end-to-end checks:

```bash
python3 scripts/smoke_mvp.py
```

## If You Are Acting As An Agent

- Read `plan.md` first for product intent
- Keep the product branded as RateDrop
- Favor small, production-minded changes
- Use the simplest path that keeps the demo reliable
- Do not remove unrelated user changes
- Do not claim functionality is flawless without verification
