# RateDrop Demo Guide

Use this one file for both the live presentation and the Devpost video.

Live app:

```text
https://ratedrop-reezumnw5a-uc.a.run.app
```

Readiness/cloud proof:

```text
https://ratedrop-reezumnw5a-uc.a.run.app/api/readiness
```

## What To Demo

Use one scenario only:

```text
Rogers demo
```

It proves both parts of RateDrop:

- Negotiates the recurring monthly bill from `$91.50` toward `$55`.
- Disputes a bad `$35` roaming fee and asks for a credit.

Do not call Rogers. RateDrop calls the verified demo phone number, and Hamza acts as the Rogers representative.

## Live Presentation Flow

Person A: Hamza

- Runs the product.
- Answers the phone as the fake Rogers rep.
- Explains the Google Cloud architecture.

Person B:

- Opens the pitch.
- Narrates what the agent is doing.
- Closes with use cases.

Opening line:

```text
Companies already use AI to deal with us. RateDrop gives consumers an agent back.
```

Demo steps:

1. Open the live app.
2. Click `Start`.
3. Sign in.
4. Click `Rogers demo`.
5. Show that the mission fields are prefilled.
6. Click `Start voice agent`.
7. Hamza answers the phone and reads the rep script below.
8. Show the live transcript and reasoning panel.
9. Show the result page.
10. Click `Email proof`.
11. Open `/api/readiness` and explain the cloud stack.

Mission summary to say:

```text
This preloads a Rogers bill at $91.50 per month with a disputed $35 roaming fee. The mission is specific: lower the recurring bill to $55, apply the $35 credit, and do not close until the rep confirms the rate, credit, effective date, and account notes.
```

What Person B should point out during the call:

```text
Notice the guardrails: it refuses to close on a vague no, refuses a credit-only fix, counters the weak monthly offer, and only completes once the rep confirms proof.
```

## Rep Script

Say these naturally as the Rogers representative:

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

## Cloud Track Explanation

Say this after opening `/api/readiness`:

```text
We are going for Best Use of Cloud Technologies because the cloud is the runtime for the phone agent, not just static hosting.

Cloud Run serves the Next.js frontend, FastAPI backend, Twilio webhooks, SSE transcript events, and the WebSocket endpoint used by Twilio ConversationRelay.

Twilio needs a public callback URL, the browser needs live transcript streaming, and the voice agent needs a server-side WebSocket loop. Cloud Run gives us all of that in one serverless container.

Secret Manager stores Gemini, Tavily, Twilio, and SMTP credentials. Cloud Build builds the container, Artifact Registry stores the image, and Cloud Run deploys the live revision.

Google ADK wraps the agent loop with Gemini, but deterministic backend tools control money, constraints, completion proof, and when the call can close.
```

Closing line:

```text
The demo is telecom, but the pattern works for airline refunds, bank fees, subscription disputes, warranties, and account support. Evidence in, mission defined, phone agent runs, proof comes back.
```

## Devpost Video Flow

Target length: 2 minutes.

0:00-0:15:

```text
Companies already use AI to make support cheaper for themselves. RateDrop gives consumers an agent back. You upload evidence, define the mission, and RateDrop calls support for you.
```

0:15-0:35:

- Click `Start`.
- Sign in.
- Click `Rogers demo`.
- Show company, problem, desired outcome, target monthly, constraints, and completion proof.

Narration:

```text
This demo uses a Rogers bill at $91.50 per month with a disputed $35 roaming fee. We tell the agent to lower the bill to $55, get the fee credited, and only finish when proof is confirmed.
```

0:35-1:20:

- Click `Start voice agent`.
- Answer the phone.
- Use the rep script above.

Narration:

```text
The agent does not accept a vague no, does not accept only a one-time credit, counters the weak monthly offer, and closes only after proof is confirmed.
```

1:20-1:45:

- Show the result page.
- Click `Email proof`.

Narration:

```text
RateDrop turns a messy support call into a structured outcome: original bill, new monthly rate, one-time credit, transcript, and proof email.
```

1:45-2:00:

- Open `/api/readiness`.

Narration:

```text
This is deployed on Google Cloud Run with Secret Manager, Cloud Build, Artifact Registry, Twilio ConversationRelay, Google ADK, and Gemini.
```

## Fallback If The Live Call Fails

Say:

```text
Twilio trial calls depend on the verified demo phone answering, so we have a deterministic fallback.
```

Then:

- Show `/api/readiness` to prove ConversationRelay has no missing callback fields.
- Show a recent completed Rogers result.
- Use the rep script above to explain the intended live path.

