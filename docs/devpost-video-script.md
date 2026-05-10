# RateDrop Devpost Video Script

Target length: 2 minutes.

Recording setup:

- Open `https://ratedrop-reezumnw5a-uc.a.run.app`.
- Keep your phone nearby because the demo call goes to the verified demo number.
- Use the Rogers demo only.
- Do not mention that this is an internal prototype. Present it as RateDrop.

## 0:00-0:15 Hook

Narration:

```text
Companies already use AI to make support cheaper for themselves. They route you through bots, keep you on hold, and make it hard to get a real outcome.

RateDrop gives consumers an agent back. You upload evidence, define the mission, and RateDrop calls support for you.
```

On screen:

- Show the landing page.
- Slowly scroll the hero and the agent workflow section.

## 0:15-0:35 Mission Setup

On screen:

- Click `Start`.
- Sign in.
- Click `Rogers demo`.

Narration:

```text
This demo uses a Rogers bill at $91.50 per month with a disputed $35 roaming fee.

The mission is not vague. We tell the agent to lower the monthly bill to $55, get the $35 fee credited, and only finish when the rep confirms the new rate, the credit, the effective date, and account notes.
```

Show:

- Company: Rogers
- Problem field
- Desired outcome
- Target monthly and walk-away max
- Known facts, constraints, and completion proof chips

## 0:35-1:20 Live Phone Agent

On screen:

- Click `Start voice agent`.
- Answer the phone.
- Act as the Rogers representative.

Say as the rep:

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

Narration over transcript if needed:

```text
The important part is the agent loop. It does not accept a vague no, it does not accept only a one-time credit, it counters the weak monthly offer, and it closes only after proof is confirmed.
```

## 1:20-1:45 Result And Proof

On screen:

- Show the result page.
- Show before, after, annual savings, and one-time credit.
- Click `Email proof` with the field blank to use the configured demo inbox.

Narration:

```text
RateDrop turns a messy support call into a structured outcome: original bill, new monthly rate, one-time credit, transcript, and proof email.
```

## 1:45-2:00 Cloud And Agent Stack

On screen:

- Open `https://ratedrop-reezumnw5a-uc.a.run.app/api/readiness`.

Narration:

```text
This is deployed on Google Cloud Run. The same cloud service serves the frontend, backend API, Twilio webhooks, SSE transcript stream, and the WebSocket endpoint for Twilio ConversationRelay.

Google ADK wraps the agent loop with Gemini, while deterministic backend tools control money, constraints, and completion proof. Secrets are stored in Google Secret Manager, the container is built with Cloud Build, and the image is stored in Artifact Registry.
```

Final line:

```text
RateDrop is a cloud-hosted phone agent for the support calls consumers do not want to make.
```

