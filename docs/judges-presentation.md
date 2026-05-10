# RateDrop Judges Presentation

Target length: 4 to 5 minutes.

Live app:

```text
https://ratedrop-reezumnw5a-uc.a.run.app
```

Cloud readiness:

```text
https://ratedrop-reezumnw5a-uc.a.run.app/api/readiness
```

## Roles

Person A: Hamza

- Runs the product.
- Answers the phone as the fake Rogers representative.
- Explains the Google Cloud architecture.

Person B:

- Opens the pitch.
- Explains why the agent is useful.
- Narrates the call behavior.
- Closes with broader use cases.

## 0:00-0:35 Opening

Person B:

```text
Don’t you hate when you call support, sit on hold, explain the same issue again and again, and still leave without the refund, credit, or better price you needed?

Companies already use AI to deal with consumers. RateDrop gives consumers an agent back. You upload a bill or receipt, tell it the problem, and RateDrop extracts the company and issue, researches the right support contact, calls on your behalf, waits through the queue, pushes for the outcome, and returns a transcript and proof.
```

Person A:

```text
For judging, we are not calling Rogers directly. We are making a real Twilio call to our verified demo number, and I will act as the Rogers representative.

This one controlled call shows both core capabilities: negotiating the monthly price and getting a bad charge credited.
```

## 0:35-1:15 Setup

Person A:

1. Open the live app.
2. Click `Start`.
3. Sign in.
4. Click `Rogers demo`.

Say:

```text
This preloads a Rogers bill at $91.50 per month with a disputed $35 roaming fee.

The mission is specific: lower the recurring bill to $55, apply the $35 credit, and do not close until the rep confirms the rate, credit, effective date, and account notes.
```

Person B:

```text
This is not a generic chatbot. The user defines the facts, constraints, and completion proof. Gemini helps with extraction and natural phrasing, Tavily can support company/contact lookup, but backend policy controls the money, the credit, and when the call can end.
```

## 1:15-2:45 Live Call

Person A:

Click:

```text
Start voice agent
```

Answer the phone and act as Rogers.

Rep script:

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

Person B while transcript is visible:

```text
Watch the reasoning panel. The agent does not accept a vague no, does not accept only the credit, counters the weak $70 offer, accepts the $55 rate with the credit, and only closes after proof is confirmed.
```

## 2:45-3:20 Result And Proof

Person A:

Show the result page and proof email panel.

Say:

```text
This is the proof layer. RateDrop turns a messy support call into a structured outcome: the starting bill, the new monthly rate, the credit, the transcript, and the confirmation.
```

Click:

```text
Email proof
```

Person B:

```text
That is the loop: evidence in, mission defined, phone agent handles the call, and the user gets proof.
```

## 3:20-4:30 Cloud Track

Person A:

Open:

```text
https://ratedrop-reezumnw5a-uc.a.run.app/api/readiness
```

Say:

```text
We are going for Best Use of Cloud Technologies because the cloud is the runtime for the phone agent, not just static hosting.

Cloud Run serves the Next.js frontend, FastAPI backend, Twilio webhooks, SSE transcript events, and the WebSocket endpoint used by Twilio ConversationRelay.

Twilio needs a public callback URL, the browser needs live transcript streaming, and the voice agent needs a server-side WebSocket loop. Cloud Run gives us all of that in one serverless container.

The long-hold use case is why the cloud runtime matters. The user should not have to sit through an hour of support music. RateDrop is designed as the server-side phone agent that can stay connected, wait for the representative, and bring back the outcome.

Secret Manager stores Gemini, Tavily, Twilio, and SMTP credentials. Cloud Build builds the container, Artifact Registry stores the image, and Cloud Run deploys the live revision.

Google ADK wraps the agent loop with Gemini, but deterministic backend tools control money, constraints, completion proof, and when the call can close.
```

Person B:

```text
Without the cloud runtime, Twilio cannot reach the agent, the UI cannot stream the call, and judges would only see a local demo. Here the whole voice-agent loop is live on Google Cloud.
```

## 4:30-5:00 Closing

Person B:

```text
The demo is telecom, but the pattern works for airline refunds, bank fees, subscription disputes, warranties, and account support. The full vision is that RateDrop finds the right company line, waits through the queue, handles the call, and only comes back when it has a result or proof of the next step.
```

Person A:

```text
RateDrop is simple: evidence in, mission defined, phone agent runs, proof comes back.
```

## If The Call Fails

Say:

```text
Twilio trial calls depend on the verified demo phone answering, so we have a deterministic fallback.
```

Then:

- Open `/api/readiness` and show ConversationRelay has no missing callback fields.
- Show a recent completed Rogers result.
- Explain the rep script above as the expected live path.
