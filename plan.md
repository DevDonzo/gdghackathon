# RateDrop: AI Telecom Bill Negotiator

> Refined build plan for GDG Hacks 3
> Source draft: `plan-2.md`

---

## 1. Product Thesis

This should stand on its own as a focused consumer product, not as a reaction to another demo or last year's winner.

We win by being narrower, sharper, and more measurable:

- one painful use case
- one visible live demo
- one concrete outcome: lower monthly bill or bill credit
- one grounded input: the actual bill

The core positioning is:

> "This is not a generic assistant. It is a bill-aware negotiation system with a measurable financial outcome."

That is the difference between "cool demo" and "credible product."

---

## 2. The Pitch

### Judge-safe pitch

> "Upload your phone bill. Our AI finds leverage in the charges, calls a carrier line, negotiates in real time, and comes back with a cheaper offer."

### If SMS summary is working

> "Upload your phone bill. Our AI calls the carrier, negotiates using your actual bill, and texts you the result when it's done."

### What not to say

- Do not open with models, APIs, or "we used Gemini."
- Do not call it a generic assistant.
- Do not promise real-carrier production readiness during the demo.
- Do not claim legal coverage you have not actually implemented.

---

## 3. Why This Product Works

### Strong product framing

- We solve one expensive, common problem.
- We produce a measurable outcome, not a vague assistant interaction.
- We use the user's actual bill as grounding evidence.

### Strong demo framing

- We have a grounded input artifact: the bill.
- We have a visible reasoning trace: transcript + negotiation angles.
- We have a numeric output: monthly savings, annual savings, credits recovered.

### Strong technical story

- Bill-aware negotiation, not generic calling
- Structured extraction, not freeform summarization
- Negotiation policy engine, not pure model improv
- Deterministic savings calculator, not hallucinated math

---

## 4. Demo Principles

These are non-negotiable:

1. The first 10 seconds must show a call starting.
2. The bill must visibly affect what the agent says.
3. The UI must show the live transcript.
4. The result must end with a clear before/after number.
5. The demo must stay inside a sandbox. No real Bell/Rogers/Telus call during judging.

If any feature threatens those five rules, cut it.

---

## 5. Sandbox And Legal Positioning

The current draft is directionally right: use a sandbox line, not a real carrier.

Refine it like this:

- We own both phone numbers used in the demo.
- Number A is the "negotiator" line.
- Number B is the "carrier sandbox" line.
- The sandbox line either:
  - runs a deterministic carrier-rep state machine, or
  - runs an AI rep persona on top of deterministic concession rules.

During the pitch, say:

> "For the demo, both ends are our own numbers inside a controlled sandbox. The same bill analysis, negotiation engine, transcript pipeline, and UI would be used against a real provider in production."

That is safer and more precise than saying "same code" if the rep side is partially simulated.

### Hard rule

Do not demo against a real telecom company at the event.

---

## 6. Scope: Must-Have, Nice-To-Have, Do-Not-Build

### Must-have MVP

- Upload bill PDF or image
- Extract structured bill facts
- Show 2-3 negotiation angles before the call
- Start a real outbound call from one number to another
- Run a live negotiation loop
- Stream transcript updates to the UI
- End on a result page with deterministic savings math

### Nice-to-have

- SMS summary after the call
- Call history page
- User can edit extracted bill facts before starting
- Multiple demo scenarios
- IVR preamble before the rep joins
- Annual savings chart

### Do not build in 24 hours

- Mobile app
- Real carrier integrations
- Plaid
- Login/auth
- Browser extension
- Multi-tenant SaaS
- Voice cloning
- Generic "assistant" features like weather/news/appointments

The current draft leaks into "what's next" territory too early. Keep v1 brutally narrow.

---

## 7. Recommended Stack

| Layer | Recommended choice | Why |
|---|---|---|
| Frontend | Next.js + Tailwind on Vercel | Fast UI iteration and clean deploys |
| Backend | FastAPI + Uvicorn | Better than Flask for WebSockets and async voice flows |
| Voice transport | Twilio ConversationRelay first | Twilio handles STT/TTS so we can focus on agent logic |
| Voice fallback | Twilio bidirectional Media Streams | Use only if ConversationRelay blocks us or we need raw audio control |
| OCR + extraction | Gemini `gemini-2.5-flash` | Stable, structured output, good multimodal performance |
| Negotiation reasoning | Gemini `gemini-2.5-flash` | Low-latency enough for text turn generation |
| Stretch realtime audio | Gemini `gemini-3.1-flash-live-preview` | Only if we choose direct audio streaming as a stretch |
| Database | MongoDB Atlas | Good enough, quick, prize-aligned |
| Backend hosting | Railway or Render | Better fit than Vercel for persistent backend/WebSocket needs |
| Tunnel for local dev | ngrok or Cloudflare Tunnel | Fine for local iteration, not for final judged demo |

### Important technical corrections

- Do not center the final plan on Flask + ngrok. That is acceptable for hour-1 prototyping, but too fragile for the judged demo.
- Do not center the call loop on TwiML `<Gather>` unless it is an emergency fallback. It is usable, but it is not the cleanest way to build a live AI voice agent.
- Do not base the project on Gemini 2.0 Flash. It is on a shutdown path. Use Gemini 2.5 Flash for the stable core.

---

## 8. Architecture Decision

### Primary architecture

Use Twilio ConversationRelay on both phone numbers.

Why:

- Twilio handles speech-to-text and text-to-speech.
- Our backend only needs to manage WebSocket messages and conversation state.
- This is simpler than handling raw audio ourselves.
- It reduces moving parts versus stitching together STT, TTS, and telephony manually.

### Fallback architecture

Use Twilio bidirectional Media Streams only if:

- ConversationRelay is unavailable or blocked
- we explicitly want raw audio control
- we have enough time to bridge audio into a realtime model

### Emergency architecture

Use TwiML `<Gather input="speech">` + webhook turns only if the realtime path fails.

This is the "ship something that works" fallback, not the preferred plan.

---

## 9. Product Flow

1. User uploads a telecom bill or selects a demo bill fixture.
2. Backend sends the file to Gemini for structured extraction.
3. Backend derives negotiation angles and a target outcome.
4. Frontend shows a short pre-call review:
   - provider
   - current monthly total
   - suspicious fees / expired promo / overage / loyalty angle
   - target savings
5. User clicks `Start negotiation`.
6. Backend creates a negotiation record and triggers a Twilio outbound call.
7. Negotiator line connects to our backend voice session.
8. Carrier sandbox line connects to a separate backend voice session.
9. Each turn is persisted and pushed to the frontend.
10. When the negotiation ends, the UI shows:
   - old monthly bill
   - new monthly bill
   - one-time credit if any
   - annualized savings
   - transcript summary

---

## 10. Core Insight: Do Not Let The Model Freestyle The Whole Negotiation

This is the single biggest refinement to the original draft.

Pure LLM-to-LLM negotiation is flashy, but it is also the fastest way to get:

- fake dollar amounts
- random acceptance criteria
- inconsistent difficulty
- broken demos

### Better design

Split the system into:

1. deterministic policy/state
2. LLM phrasing

### Negotiator side

The model should not directly decide everything.

Instead:

- a policy engine decides the current objective:
  - probe
  - challenge fee
  - ask for retention
  - counter-offer
  - accept
  - exit
- Gemini turns that objective into natural spoken language

### Carrier rep side

Do not make the rep purely generative.

Use a deterministic concession ladder:

- start firm
- reject first ask
- offer small promo
- escalate to retention if pushed correctly
- allow a final discount floor based on the scenario

Then let Gemini phrase the rep response in character.

That gives you realism without randomness destroying the demo.

---

## 11. Data Model

### `bill_documents`

```json
{
  "_id": "bill_123",
  "filename": "bell-demo.pdf",
  "provider": "Bell",
  "currency": "CAD",
  "monthlyTotal": 85.00,
  "planName": "Unlimited 50",
  "lineItems": [
    {
      "label": "Plan charge",
      "amount": 70.00,
      "recurring": true,
      "category": "plan"
    },
    {
      "label": "Overage fee",
      "amount": 10.00,
      "recurring": false,
      "category": "overage"
    }
  ],
  "negotiationAngles": [
    "Expired promotional pricing",
    "Overage fee forgiveness",
    "Retention discount"
  ],
  "extractionConfidence": 0.88,
  "createdAt": "2026-05-09T01:00:00Z"
}
```

### `negotiations`

```json
{
  "_id": "neg_123",
  "billId": "bill_123",
  "scenarioId": "bell_happy_path",
  "status": "queued",
  "targetMonthly": 52.00,
  "walkAwayMonthly": 60.00,
  "bestOfferMonthly": null,
  "oneTimeCredit": 0,
  "mode": "sandbox",
  "startedAt": null,
  "endedAt": null
}
```

### `transcript_turns`

```json
{
  "_id": "turn_123",
  "negotiationId": "neg_123",
  "role": "negotiator",
  "text": "I can see an expired promo on this line. What retention options are available today?",
  "latencyMs": 980,
  "createdAt": "2026-05-09T01:12:33Z"
}
```

### `demo_scenarios`

```json
{
  "_id": "bell_happy_path",
  "provider": "Bell",
  "initialMonthly": 85.00,
  "concessionLadder": [
    { "step": 1, "type": "deny" },
    { "step": 2, "type": "offer_discount", "monthly": 68.00 },
    { "step": 3, "type": "retention_offer", "monthly": 52.00, "credit": 25.00 }
  ]
}
```

---

## 12. API Surface

Keep it small.

### Public app API

- `POST /api/bills/upload`
- `GET /api/bills/:id`
- `POST /api/negotiations`
- `POST /api/negotiations/:id/start`
- `GET /api/negotiations/:id`
- `GET /api/negotiations/:id/transcript`

### Twilio HTTP endpoints

- `POST /twilio/voice/negotiator`
- `POST /twilio/voice/rep`
- `POST /twilio/status`

### WebSocket endpoints

- `WS /ws/negotiator/:negotiationId`
- `WS /ws/rep/:negotiationId`

### Frontend realtime

Do not over-engineer this.

Use one of:

- poll transcript every second
- simple SSE stream from backend

Do not spend half the hackathon building frontend realtime infra nobody asked for.

---

## 13. AI Contracts

### Bill extraction output

Gemini must return strict JSON.

```json
{
  "provider": "string",
  "currency": "CAD",
  "monthlyTotal": 0,
  "planName": "string",
  "lineItems": [
    {
      "label": "string",
      "amount": 0,
      "recurring": true,
      "category": "plan|tax|fee|overage|discount|other"
    }
  ],
  "negotiationAngles": ["string"],
  "redFlags": ["string"],
  "confidence": 0
}
```

### Negotiator turn output

```json
{
  "intent": "probe|push_discount|request_retention|counter_offer|accept|exit",
  "say": "string",
  "proposedMonthly": 0,
  "reasoningSummary": "string"
}
```

### Guardrails

- Never invent bill facts not present in extracted data
- Never claim a discount was granted until the rep side explicitly offers it
- Never calculate savings with the model alone
- Always run final savings through deterministic code

---

## 14. Demo Scenarios

Ship exactly three.

### Scenario 1: Happy path

- Bill starts at `$85/month`
- Negotiator identifies expired promo + retention angle
- Rep resists once, then offers `$52/month`
- UI ends with clear savings

### Scenario 2: Escalation path

- Rep initially refuses
- Negotiator asks for retention or loyalty options
- Rep escalates and gives smaller win

### Scenario 3: Fee recovery path

- Negotiator spots a suspicious fee or overage
- Rep waives fee or grants credit
- Shows that bill analysis is actually grounded

Each scenario should be fully deterministic at the business-logic level.

---

## 15. UX Plan

Three pages are still the right shape, but refine their jobs.

### `/`

- Big single CTA
- Upload bill or choose demo bill
- Show extracted summary fast
- Button: `Start negotiation`

### `/call/[id]`

- Live transcript
- Call status indicator
- Current objective label:
  - "Requesting retention"
  - "Pushing back on fee"
  - "Evaluating offer"
- Sidebar with bill facts and best current offer

### `/result/[id]`

- Old monthly total
- New monthly total
- Monthly savings
- Annual savings
- One-time credit
- "What worked" summary

### Design note

Do not make the UI look like a generic dark AI dashboard.
Make it look like a consumer product with one clear job.

---

## 16. 24-Hour Build Plan

### Hour 0-1: Lock decisions

- Freeze the problem: telecom bill negotiation only
- Upgrade Twilio immediately if budget allows
- Create shared env doc
- Deploy empty frontend and backend shells

### Hour 1-3: Prove telephony

- Buy/provision two Twilio numbers
- Make number A call number B
- Return TwiML / ConversationRelay successfully
- Confirm backend receives call events

Exit criterion:

- one real call between owned numbers works reliably

### Hour 3-6: Prove agent loop

- Hardcode a 3-turn negotiator
- Hardcode a 3-turn rep
- Persist transcript turns
- Render transcript in frontend

Exit criterion:

- click button -> call starts -> transcript appears

### Hour 3-6 in parallel: Prove bill extraction

- Build upload flow
- Parse one sample bill reliably
- Save structured JSON
- Render negotiation angles in UI

Exit criterion:

- demo bill parses consistently into usable fields

### Hour 6-10: Join the systems

- Create negotiation record from uploaded bill
- Use bill facts to drive negotiator policy
- Use scenario state machine to drive rep behavior
- Compute final savings deterministically

Exit criterion:

- same bill produces same believable outcome every run

### Hour 10-14: Make it judge-ready

- Improve copy
- Improve visual hierarchy
- Add preloaded sample bills
- Add recorded backup video
- Add backup transcript replay mode

Exit criterion:

- even if live call fails, the demo still lands

### Hour 14-18: Add second and third scenarios

- escalation path
- fee-waiver / credit path

### Hour 18-22: Freeze and rehearse

- no new backend features
- no model prompt rewrites unless a bug is blocking demo
- record final video
- write Devpost
- rehearse the 90-second pitch three times

### Hour 22-24: Only protect reliability

- refresh deployments
- test on final laptop
- verify audio
- pre-open the app to the upload page
- keep a backup video tab ready

---

## 17. Team Split

### Person A: Voice platform

- Twilio numbers
- outbound call creation
- ConversationRelay / Media Streams wiring
- call status handling

### Person B: AI contracts

- bill extraction schema
- negotiator policy engine
- Gemini prompts
- validation and deterministic math

### Person C: Frontend

- upload flow
- call page
- result page
- scenario fixtures and polish

### Person D: State + delivery

- MongoDB models
- transcript persistence
- demo scenarios
- Devpost, pitch, backup video

### If team of 2

Cut:

- fancy realtime transport
- AI rep persona
- SMS summary

Keep:

- upload
- one call
- one transcript
- one result

---

## 18. Risks And Mitigations

| Risk | Real issue | Mitigation |
|---|---|---|
| Twilio trial limits | Trial accounts restrict who you can call and what voice features you can use | Upgrade early if possible; otherwise verify numbers at hour 0 and keep a backup demo |
| Vercel backend mismatch | Vercel is fine for frontend, not ideal for a persistent voice backend | Keep backend on Railway/Render; frontend on Vercel |
| LLM randomness | Negotiation becomes inconsistent | Deterministic policy engine + scenario ladder |
| OCR errors | Bad bill facts create fake negotiation logic | Support one pre-validated sample bill; allow manual edit if time permits |
| Latency | Call sounds awkward | Keep responses short, precompute targets, stream partial UI updates |
| Live demo failure | Judges see dead air | Record one successful run and build transcript replay fallback |
| Scope creep | Team tries to build a universal assistant | Explicitly reject all non-bill features |

---

## 19. What To Say If Judges Push

### "Why this product?"

> "Telecom bills are expensive, confusing, and annoying to dispute. We focused on one painful workflow and made the result measurable: a lower monthly bill or a credited fee."

### "Why not call a real provider?"

> "Because a judged hackathon demo should be reliable and safe. We built a controlled telecom sandbox to show the actual architecture without depending on a real contact center."

### "How do you stop hallucinations?"

> "The model does not own the math or the negotiation policy. It proposes wording; our backend validates extracted numbers, tracks offers, and computes savings deterministically."

### "What is production next?"

> "Carrier-specific flows, consent and disclosure, stronger bill normalization, and real user review before placing the call."

---

## 20. Submission Strategy

Your Devpost should not read like "we built a cool AI app."

It should read like:

- clear pain
- focused workflow
- grounded AI
- live telephony
- measurable result

### Devpost sections

#### Inspiration

- Canadians waste time and money on telecom bills
- negotiating is annoying, slow, and emotionally draining
- the pain is universal and easy to understand instantly

#### What it does

- uploads a bill
- finds leverage
- calls the carrier sandbox
- negotiates live
- returns savings

#### How we built it

- Next.js frontend
- FastAPI backend
- Twilio voice transport
- Gemini structured extraction + negotiation phrasing
- MongoDB for negotiation state and transcript history

#### Challenges

- telephony reliability
- realtime conversation loops
- keeping savings deterministic
- making the sandbox feel realistic without becoming flaky

#### What's next

- real provider flows
- stronger bill parsers
- multilingual negotiation
- user approval and trust controls before call placement

---

## 21. Final Recommendation

The original draft had the right demo instinct. Its main weakness was treating the voice architecture and the negotiation logic as if they could stay loose and still be reliable.

This version fixes that.

### The winning version of this project is:

- not a general assistant
- not a mobile app
- not a full production telecom platform

It is:

- a focused web demo
- grounded by a real bill
- powered by a live phone call
- protected by deterministic state
- ending with a number judges can remember

### The one thing to protect

> A judge sees a bill, sees a call start, watches the transcript move, and then sees "$33/month saved."

That is the whole project.
