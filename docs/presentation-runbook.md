# RateDrop Presentation Runbook

Use this for the live judging presentation.

## Roles

Person A: Hamza

- Runs the product.
- Answers the Twilio call as the fake Rogers representative.
- Explains the Google Cloud architecture.

Person B:

- Opens the pitch.
- Explains why the agent is policy-bound, not a generic chatbot.
- Narrates what judges should notice during the call.
- Closes with use cases.

## Required Tabs

Open these before presenting:

- `https://ratedrop-reezumnw5a-uc.a.run.app`
- `https://ratedrop-reezumnw5a-uc.a.run.app/api/readiness`
- `docs/mock-demo.md`

## Live Demo Steps

1. Person B gives the hook:

```text
Companies already use AI to deal with us. RateDrop gives consumers an agent back.
```

2. Person A opens RateDrop, clicks `Start`, signs in, and loads `Rogers demo`.

3. Person A says:

```text
This is one controlled call that proves two outcomes: lower the recurring bill and get a bad charge credited.
```

4. Person A clicks `Start voice agent`.

5. Person A answers the phone and uses this rep script:

```text
Thanks for calling Rogers, how can I help?
```

```text
I do not see any promotions available.
```

```text
I can apply a 35 dollar credit for the roaming fee, but the monthly plan would stay the same.
```

```text
I can reduce it to 70 dollars a month and keep the 35 dollar credit.
```

```text
I can get approval for 55 dollars a month and a 35 dollar credit.
```

```text
Confirmed, the new monthly rate is 55 dollars, the 35 dollar credit is applied, it starts next billing cycle, and it is noted on the account.
```

6. Person B narrates:

```text
Notice the guardrails: it refuses to close on a vague no, refuses a credit-only fix, counters the weak offer, and only completes once the rep confirms proof.
```

7. Person A shows the result page and clicks `Email proof`.

8. Person A opens `/api/readiness` and explains:

```text
Cloud Run is the live runtime for the product. Twilio needs public HTTPS webhooks and a WebSocket endpoint, the UI needs live transcript streaming, and the agent needs server-side credentials.

One Cloud Run service handles the frontend, FastAPI backend, Twilio callbacks, SSE, and ConversationRelay WebSocket. Secret Manager stores Gemini, Tavily, Twilio, and SMTP credentials. Cloud Build builds the container and Artifact Registry stores the image.

Google ADK wraps the agent loop with Gemini, but deterministic backend tools own the money math, constraints, and completion criteria.
```

9. Person B closes:

```text
The demo is telecom, but the pattern works for airline refunds, bank fees, subscription disputes, warranties, and account support. Evidence in, mission defined, phone agent runs, proof comes back.
```

## If The Live Call Fails

Use the fallback:

- Say Twilio trial calls depend on the verified demo phone answering.
- Run the cloud smoke path result that already exists in recent sessions.
- Open `/api/readiness` to prove ConversationRelay is configured with no missing callback fields.
- Show `docs/mock-demo.md` for the planned call transcript.

