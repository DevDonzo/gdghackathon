# Next Steps: Live Phone AI via Twilio ConversationRelay

This document captures the exact next implementation path for adding a real phone-number voice agent to RateDrop using **Twilio ConversationRelay**.

The goal is:

1. A user uploads a bill
2. RateDrop creates a deterministic negotiation plan
3. RateDrop places an outbound call to a verified phone number
4. The person answering the phone speaks naturally as the carrier rep
5. The AI negotiator speaks back live on the same call
6. The UI shows the transcript and the result in real time
7. The backend remains the owner of negotiation state, savings math, and transcript persistence

This is the recommended implementation path over Twilio `<Gather>` loops or raw Media Streams because it gives us:

- real phone-number interaction
- live back-and-forth speech
- lower engineering complexity than raw audio streaming
- a cleaner fit with the architecture direction in `plan.md`

This is still a hackathon/demo architecture, not a production contact-center deployment.

---

## 1. Product Goal For This Mode

This mode is not "generic voice chat over the phone."

The product goal is narrower:

> Connect a human acting as a telecom rep to an AI negotiator over a real phone call, while keeping the negotiation policy deterministic and showing the transcript live inside RateDrop.

That means:

- the human side is freeform speech
- the AI side sounds live and responsive
- the backend does **not** allow arbitrary model improvisation to define the economics of the negotiation
- savings math remains code-driven

The important design principle is:

**Conversation style may be natural, but negotiation state must remain controlled.**

---

## 2. Why ConversationRelay Is The Right Path

ConversationRelay is the best path because Twilio handles:

- speech-to-text
- text-to-speech
- interruption handling
- live call orchestration over WebSocket

Our backend then only needs to:

- receive transcript events
- maintain deterministic negotiation state
- decide the allowed next action
- phrase the allowed next response
- persist everything
- push transcript/state changes to the frontend

Compared to alternatives:

### Better than `<Gather>`

`<Gather>` can work, but it is a turn-by-turn IVR pattern, not a real conversational loop.

Problems with `<Gather>` for this feature:

- more robotic
- more pauses
- harder interruption handling
- speech collection feels staged

### Better than Media Streams for now

Bidirectional Media Streams give more raw control but require:

- audio codec conversion
- streaming audio plumbing
- realtime audio model integration
- more failure points

That is a valid fallback, but not the best next move for this repo.

### Better than ElevenLabs-first

ElevenLabs is not necessary here because Twilio ConversationRelay already provides:

- STT
- TTS
- telephony
- WebSocket call orchestration

Adding ElevenLabs early would increase cost and integration surface without solving the main product problem.

---

## 3. What This Mode Should Actually Do

The exact live demo flow should be:

1. User uploads a bill or selects a demo bill
2. Backend extracts bill facts and creates a negotiation record
3. User clicks `Start Live Phone Demo`
4. Twilio calls a verified destination number
5. When the human answers, Twilio connects the call into ConversationRelay
6. ConversationRelay sends speech transcript events to our backend WebSocket
7. Backend interprets the rep's utterance against the deterministic negotiation policy
8. Backend selects the allowed next move
9. Gemini 2.5 Flash phrases that move into natural spoken language
10. Backend sends text back over the ConversationRelay WebSocket
11. Twilio speaks it to the human on the call
12. Transcript turns are persisted in MongoDB
13. The frontend `/call/{id}` view updates live
14. When the backend reaches an acceptance or exit condition, the call ends
15. Result page shows deterministic savings

This gives a real live phone demo while preserving the core RateDrop thesis.

---

## 4. Hard Constraints We Must Preserve

This live mode must respect the existing product constraints in `AGENTS.md` and `plan.md`.

### Constraint A: No pure LLM improvisation

The model must not decide:

- the target monthly rate
- whether a partial offer is good enough
- how much credit was won
- whether the negotiation should accept or continue

Those decisions must stay in backend code.

### Constraint B: Gemini is used for phrasing, not final math

Gemini may:

- turn a chosen move into a natural sentence
- help classify rep language into coarse intents if needed

Gemini may not:

- compute the final savings result
- invent offer values
- override acceptance rules

### Constraint C: Trial-account compatibility matters

The current environment is still built around a Twilio trial account, so this mode must assume:

- calls can only go to verified numbers
- one Twilio number may be all we have
- calls are capped at 10 minutes
- a trial message may play before the call flow starts

### Constraint D: Transcript/state persistence remains first-class

The live voice experience is not enough on its own.

The UI must still show:

- live transcript
- current objective
- current best offer
- final result

This is part of what makes the demo legible to judges.

---

## 5. High-Level Architecture

### Current architecture

Right now the repo uses:

- FastAPI backend
- static frontend served by FastAPI
- MongoDB-backed bills/negotiations/transcript turns
- Twilio outbound call launch
- TwiML narrated playback per scripted turn

### New live-phone architecture

We keep:

- bill extraction
- negotiation document creation
- deterministic result math
- transcript persistence
- frontend transcript/result screens

We replace the Twilio voice interaction layer with:

- outbound call to human phone
- TwiML `<Connect><ConversationRelay>`
- backend WebSocket session manager
- event-to-policy response loop

### Architecture diagram in words

1. Frontend creates negotiation
2. Backend stores negotiation document
3. Backend starts Twilio outbound call
4. Twilio requests `/twilio/voice/negotiations/{id}`
5. Backend responds with TwiML containing `<Connect><ConversationRelay>`
6. Twilio opens a WebSocket to our backend
7. ConversationRelay sends:
   - setup/session events
   - speech transcript events
   - call lifecycle events
8. Backend:
   - updates negotiation state
   - persists turns
   - sends AI text responses back
9. ConversationRelay synthesizes that text into speech
10. Frontend listens to `/api/negotiations/{id}/events` and renders the transcript

---

## 6. Required Backend Changes

This section is the actual implementation scope.

### 6.1 Add a dedicated live-phone mode to negotiation call metadata

Current call metadata has:

- `mode: sandbox | simulated`

We should extend this to distinguish:

- `simulated`
- `sandbox`
- `conversation_relay`

This matters because the frontend and result page should clearly reflect which execution path ran.

Suggested change area:

- `backend/app/models/schemas.py`

Also update any serialization assumptions in:

- `backend/app/models/schemas.py`
- `frontend/static/app.js`

### 6.2 Add a launch path for ConversationRelay calls

Current launch logic in:

- `backend/app/services/twilio_voice.py`

uses:

- `client.calls.create(...)`
- a TwiML voice URL
- status callbacks

We should keep the same basic outbound call creation, but the TwiML returned by the voice webhook should no longer narrate the whole script turn-by-turn.

Instead, it should connect the active phone call to ConversationRelay.

Suggested implementation:

- new function:
  - `launch_conversation_relay_call(negotiation_id, request)`
- or a mode branch inside:
  - `launch_sandbox_call(...)`

The function should still return call metadata with:

- `sid`
- `to`
- `fromNumber`
- `status`
- `mode = "conversation_relay"`
- `error`

### 6.3 Replace current TwiML playback route with ConversationRelay TwiML

Current route:

- `/twilio/voice/negotiations/{id}`

currently calls:

- `negotiation_twiml(negotiation, request, step)`

That function currently:

- says an intro line
- speaks each scripted turn
- redirects between steps

This must change for live-phone mode.

For ConversationRelay mode, the TwiML should be more like:

- `<Response>`
- `<Connect>`
- `<ConversationRelay url="wss://...">`
- optional parameters with negotiation id, provider, scenario, current objective

We should keep the old narrated mode available as a fallback, but add a branch:

- if negotiation mode is `conversation_relay`, return ConversationRelay TwiML
- else return current scripted fallback TwiML

### 6.4 Add a WebSocket endpoint for ConversationRelay

FastAPI needs a WebSocket route such as:

- `/ws/conversation-relay/{negotiation_id}`

This endpoint will:

1. accept Twilio’s WebSocket connection
2. receive structured events from ConversationRelay
3. interpret speech transcript messages
4. persist transcript turns
5. compute the next backend move
6. send response text back to Twilio

Important:

- validate Twilio signatures if feasible
- store session metadata
- handle disconnects cleanly

Suggested file:

- new file: `backend/app/services/conversation_relay.py`

### 6.5 Add a conversation session manager

We need a proper session object per active negotiation call.

Suggested responsibilities:

- track current negotiation id
- current turn index or state node
- latest best offer
- whether the AI is waiting for the rep
- whether the call is closing
- timestamps

This should be explicit code, not inferred ad hoc from raw transcript text.

Suggested structure:

- in-memory active session registry keyed by negotiation id
- persisted canonical state in MongoDB negotiation document

### 6.6 Add rep utterance classification

The human Bell rep will speak naturally.
The backend must map that natural speech into a limited set of deterministic rep intents.

Examples:

- refusal
- soft refusal
- small offer
- retention escalation
- credit offer
- final offer
- close

This should be done with:

1. keyword/rule matching first
2. optional Gemini classification only if the rules are uncertain

This is important:

The model should classify into a **closed set**, not invent next moves.

Suggested function:

- `classify_rep_utterance(text, negotiation_state) -> RepIntent`

Possible file:

- `backend/app/services/negotiation_live.py`

### 6.7 Add a deterministic response policy for live mode

The current turn plan is a fixed scripted 8-turn sequence.

Live speech mode needs a stateful but still deterministic policy.

That means:

- not fully scripted line-by-line
- but also not fully generative

We need a policy graph like:

#### Example state graph

- `open`
  - AI opens with bill facts and objective
- `rep_refusal`
  - if rep refuses, AI pushes for retention
- `small_offer_seen`
  - if rep gives weak offer, AI counters toward target
- `credit_only_seen`
  - if rep offers only credit, AI asks for monthly reduction too
- `acceptable_offer_seen`
  - if rep reaches threshold, AI accepts
- `walkaway_reached`
  - if no acceptable outcome, AI exits politely

Each state should define:

- allowed incoming rep intents
- next state
- next backend action
- whether to update best offer / credit
- whether to end the negotiation

This is the core of keeping the live phone conversation controlled.

### 6.8 Add phrasing for live-mode negotiator turns

Once the backend picks the next move, Gemini can phrase it.

Example input to Gemini:

- provider
- bill facts
- objective
- latest rep move
- allowed numeric values
- tone rules

Example output:

- one short spoken line

This is similar to the current phrasing role, but now it is dynamic per live state instead of precomputed for the whole call.

Suggested rule set:

- keep responses short
- one or two sentences
- no new money values
- no new concessions
- natural phone speech

### 6.9 Persist live transcript turns in the same collection

Current transcript persistence already exists.

We should preserve the existing shape:

- role
- intent
- objective
- text
- proposedMonthly
- credit
- createdAt

For live mode, use:

- `role = "rep"` for recognized human rep speech
- `role = "negotiator"` for AI replies
- `role = "system"` for call/session events if useful

This keeps the frontend mostly compatible.

### 6.10 Update call status handling

Current Twilio status webhook handling should stay, but we should add:

- explicit session completion if WebSocket closes after acceptance
- explicit failure state if ConversationRelay session fails early
- better separation of:
  - call transport completion
  - negotiation completion

This avoids cases where the call disconnects before the result is finalized.

---

## 7. Required Frontend Changes

The active frontend is:

- `frontend/static/index.html`
- `frontend/static/styles.css`
- `frontend/static/app.js`

### 7.1 Add a distinct CTA for live phone mode

Right now the UI is oriented around:

- upload bill
- start negotiation

We should make the execution path explicit.

Recommended button:

- `Start live phone demo`

Optional secondary path:

- `Run narrated sandbox`

This helps keep the live mode distinct from the current fallback mode.

### 7.2 Add call-mode labeling on the call screen

On `/call/{id}`, clearly show:

- `Live phone call`
- `You are speaking as the carrier rep`

This matters for demo comprehension.

### 7.3 Add setup instructions before placing the call

Before the call starts, show a small note:

- Answer the call on the verified phone
- Speak naturally as the rep
- Keep replies short and realistic
- Mention discounts, credits, or retention options

This reduces confusion during the demo.

### 7.4 Keep transcript rendering as-is, but add live-mode cues

The transcript screen already works conceptually.

We should add:

- a more explicit “listening” state
- a more explicit “AI speaking” state
- a banner when the AI is waiting for the rep

This improves legibility for judges.

### 7.5 Result screen should reflect live voice mode

The result page should note:

- call mode: `Live phone demo`

This helps differentiate it from the narrated sandbox fallback.

---

## 8. Environment And Configuration Changes

We will need a few new config values.

Suggested additions in:

- `backend/app/core/config.py`

### Required additions

- `RATEDROP_TWILIO_MODE`
  - values:
    - `simulated`
    - `sandbox_tts`
    - `conversation_relay`

- `RATEDROP_CONVERSATION_RELAY_WS_BASE`
  - base `wss://` URL Twilio should connect to
  - example:
    - `wss://your-api.example.com/ws/conversation-relay`

### Existing values still required

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `TWILIO_VERIFY_ORIG_NUMBERS`
- `TWILIO_SANDBOX_TO_NUMBER`
- `PUBLIC_BASE_URL`

For local testing:

- use a public HTTPS/WSS tunnel
- Cloudflare Tunnel or ngrok is fine for dev

For the actual judged demo:

- use a stable deployed backend URL if possible

---

## 9. Twilio Trial Constraints We Must Design Around

This is critical.

### Constraint 1: Outbound calls only to verified numbers

That means:

- your personal demo phone must be verified in Twilio

### Constraint 2: Only one Twilio number may be available on trial

That is okay for this mode because:

- we do not need a second Twilio sandbox rep number
- the AI lives on the backend/ConversationRelay side

### Constraint 3: 10-minute max calls

That is fine because:

- our live negotiation should be constrained to 2–4 minutes

### Constraint 4: Trial call announcement

Twilio may insert a short trial announcement before the flow starts.

This is not ideal, but it is acceptable for hackathon demo purposes.

### Constraint 5: Public WebSocket availability

Twilio must be able to reach:

- TwiML voice endpoint
- status webhook
- ConversationRelay WebSocket endpoint

So localhost alone is not enough.

---

## 10. Deterministic Live Policy Design

This is the most important logic section.

We must not let live speech destroy determinism.

### 10.1 Closed set of rep intents

Define a rep intent enum such as:

- `greeting`
- `refusal`
- `small_discount_offer`
- `credit_offer`
- `retention_escalation`
- `final_discount_offer`
- `close`
- `ambiguous`

### 10.2 Closed set of negotiator actions

Define a negotiator action enum such as:

- `open_with_bill_facts`
- `push_for_retention`
- `counter_to_target`
- `ask_for_credit_plus_rate_relief`
- `accept_offer`
- `exit_without_accepting`

### 10.3 State transition table

Example:

- if state = `open`
  - rep `refusal` -> action `push_for_retention`
  - rep `small_discount_offer` -> action `counter_to_target`
  - rep `credit_offer` -> action `ask_for_credit_plus_rate_relief`

- if state = `countering`
  - rep `final_discount_offer` and offer <= target -> `accept_offer`
  - rep `small_discount_offer` and offer > walkaway -> continue countering once
  - rep `refusal` after counter -> `exit_without_accepting`

### 10.4 Offer extraction rules

When the rep speaks naturally, we may hear:

- “I can do 65 a month”
- “I can offer 10 dollars off”
- “I can apply a 25 dollar credit”

We need deterministic parsers for:

- monthly dollar value
- discount amount
- one-time credit amount

Use:

1. regex parsing first
2. optional Gemini extraction fallback if regex fails

This allows the backend to update:

- `bestOfferMonthly`
- `oneTimeCredit`

without trusting arbitrary model math.

---

## 11. WebSocket Event Design

We should formalize the event flow for the ConversationRelay session.

### Incoming Twilio -> backend events

Expect categories like:

- setup/session start
- transcript / speech recognized
- interruption markers
- disconnect/stop

### Outgoing backend -> Twilio messages

We need to send:

- text for TTS playback
- optional control messages to end session

### Internal backend -> frontend SSE events

We should continue using the existing SSE route:

- `/api/negotiations/{id}/events`

Event types already used:

- `snapshot`
- `turn`
- `status`

Keep this stable so the frontend does not need a major rewrite.

---

## 12. Suggested File Changes

### Existing files likely to change

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/models/schemas.py`
- `backend/app/services/twilio_voice.py`
- `backend/app/services/negotiation.py`
- `frontend/static/app.js`
- `frontend/static/index.html`
- `frontend/static/styles.css`

### New files likely needed

- `backend/app/services/conversation_relay.py`
- `backend/app/services/negotiation_live.py`

Possible optional helper files:

- `backend/app/services/offer_parser.py`
- `backend/app/services/live_intents.py`

---

## 13. Build Order

This is the recommended implementation sequence.

### Phase 1: Plumbing

1. Add config flags for live Twilio mode
2. Add ConversationRelay TwiML branch
3. Add WebSocket endpoint
4. Ensure Twilio can connect to the WebSocket via public WSS

Goal:

- phone rings
- Twilio connects to backend WebSocket
- backend logs setup event

### Phase 2: Minimal live loop

1. Receive transcript from Twilio
2. Persist human speech as a `rep` transcript turn
3. Send back a simple hardcoded AI sentence
4. Confirm audio plays to the caller

Goal:

- human speaks
- AI talks back

This proves the transport loop.

### Phase 3: Deterministic policy integration

1. Add live rep intent classification
2. Add live negotiation state machine
3. Add best-offer / credit updates
4. Add acceptance and exit rules

Goal:

- real live negotiation logic, not just echo responses

### Phase 4: Gemini phrasing

1. Replace hardcoded AI lines with Gemini phrasing for selected actions
2. Keep numeric values injected by code

Goal:

- natural-sounding negotiator responses

### Phase 5: Frontend demo polish

1. Add live-phone CTA
2. Add instructions
3. Add listening/speaking states
4. Label live call mode clearly

Goal:

- judges understand what they are seeing immediately

### Phase 6: Result hardening

1. Finalize result transition
2. Ensure transcript summary still works
3. Ensure deterministic savings math still closes correctly

Goal:

- live call ends cleanly on the result page

---

## 14. Testing Plan

### Test 1: WebSocket transport test

- Twilio calls your verified number
- you answer
- Twilio connects to backend WebSocket
- backend logs incoming messages

### Test 2: Hardcoded speech response test

- you say: “Hi, how can I help?”
- AI responds with a fixed sentence

### Test 3: Transcript persistence test

- verify both your spoken line and the AI line appear in MongoDB
- verify `/api/negotiations/{id}/transcript` shows them

### Test 4: Deterministic branch test

Say phrases like:

- “there are no discounts available”
- “I can offer ten dollars off”
- “I can add a twenty-five dollar credit”

Confirm the backend classifies them into the right rep intents.

### Test 5: End-to-end result test

- run a full live phone session
- accept a qualifying offer
- verify:
  - transcript persisted
  - call status updated
  - result page computed final savings correctly

### Test 6: Trial-account limit test

- ensure the call stays well below 10 minutes
- verify the verified number setup

---

## 15. Demo Script Recommendation

For the judged demo, do not freestyle as the Bell rep too aggressively.

Use a predictable script.

### Recommended rep script

1. Greeting:
   - “Thanks for calling Bell, how can I help?”
2. Initial resistance:
   - “I don’t see any promotions on the account.”
3. Small offer:
   - “I can reduce it a little, maybe to 70 dollars a month.”
4. Final concession:
   - “I can get approval for 52 dollars a month and a 25 dollar credit.”

This lets the AI show:

- pressure
- escalation
- countering
- acceptance

while keeping the demo stable.

---

## 16. Risks

### Risk: Rep speech recognition is messy

Mitigation:

- keep your spoken rep lines clear and short
- use predictable offer phrasing
- add rule-based parsing first

### Risk: WebSocket tunnel instability

Mitigation:

- use a stable deployed backend if possible
- do not rely on a temporary tunnel for the final judged demo if avoidable

### Risk: Model oversteps its allowed move

Mitigation:

- backend selects the move
- model only phrases the move

### Risk: Trial call announcement hurts flow

Mitigation:

- mention the sandbox nature during the pitch
- start the visible transcript only once the live negotiation starts

---

## 17. Recommendation Summary

The recommended next move for this repo is:

1. Add `conversation_relay` as a new live call mode
2. Implement a FastAPI WebSocket endpoint for Twilio ConversationRelay
3. Keep the negotiation state machine deterministic
4. Use Gemini only to phrase allowed next moves
5. Persist transcript turns exactly as we do now
6. Keep the existing narrated sandbox path as fallback

This is the best balance of:

- realism
- demo wow factor
- architectural cleanliness
- cost control
- trial-account compatibility

---

## 18. Final Decision

If we proceed with live AI over a phone number, **ConversationRelay is the correct Option 1** for RateDrop.

It is:

- technically possible
- compatible with the product thesis
- more aligned with `plan.md`
- better than trying to force ElevenLabs into the telephony path first
- better than rebuilding around raw audio streams unless absolutely necessary

The repo is not there yet, but it is close enough architecturally that this is a reasonable next implementation step.
