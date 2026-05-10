# RateDrop Judging Script

Target length: 4 to 5 minutes.

Person A: Hamza. Runs the live demo, answers the phone as the Rogers rep, shows the result, and explains the Google Cloud track.

Person B: Opens the pitch, explains the guardrails, narrates the agent behavior, and closes.

## 0:00-0:35 Opening

Person B:

```text
Companies already use AI to make support cheaper for themselves. They route you through phone trees, keep you on hold, and make you repeat the same account details.

RateDrop gives consumers an agent back. You give it evidence, a goal, constraints, and completion proof. It calls support, waits on the line, pushes for the fix, and comes back with a transcript and outcome.
```

Person A:

```text
For safety, we are not calling Rogers during judging. We are making a real Twilio call to our verified demo number, and I will act as the Rogers representative.

This one controlled call shows both things RateDrop can do: negotiate the monthly price and get a bad charge credited.
```

## 0:35-1:15 Demo Setup

Person A:

Open:

```text
https://ratedrop-reezumnw5a-uc.a.run.app
```

Click `Start`, sign in, then click:

```text
Rogers demo
```

Say:

```text
This preloads a Rogers bill at $91.50/month with a disputed $35 roaming fee.

The mission is specific: lower the recurring bill to $55, apply the $35 credit, and do not close until the rep confirms the rate, credit, effective date, and account notes.
```

Person B:

```text
This is not a generic chatbot. The user defines facts, constraints, and completion proof. Gemini can make responses sound natural, but backend policy controls the money, the credit, and when the call can end.
```

## 1:15-2:45 Live Call

Person A:

Click:

```text
Start voice agent
```

Answer the phone and act as Rogers.

Person A as rep:

```text
Thanks for calling Rogers, how can I help?
```

Person A as rep:

```text
I do not see any promotions available.
```

Person A as rep:

```text
I can apply a 35 dollar credit for the roaming fee, but the monthly plan would stay the same.
```

Person A as rep:

```text
I can reduce it to 70 dollars a month and keep the 35 dollar credit.
```

Person A as rep:

```text
I can get approval for 55 dollars a month and a 35 dollar credit.
```

Person A as rep:

```text
Confirmed, the new monthly rate is 55 dollars, the 35 dollar credit is applied, it starts next billing cycle, and it is noted on the account.
```

Person B while transcript is visible:

```text
Watch the reasoning panel. The agent does not accept a vague no, does not accept only the credit, counters the weak $70 offer, and only closes after proof is confirmed.
```

## 2:45-3:20 Result And Proof

Person A:

Show the result page and proof email panel.

Say:

```text
This is the proof layer. RateDrop turns a messy phone call into a structured outcome: the starting bill, the new monthly rate, the credit, the transcript, and the confirmation.
```

Person B:

```text
That is the loop: evidence in, mission defined, phone agent handles the call, and the user gets proof.
```

## 3:20-4:30 Cloud Track Explanation

Person A:

Open:

```text
https://ratedrop-reezumnw5a-uc.a.run.app/api/readiness
```

Say:

```text
We are going for Best Use of Cloud Technologies because the cloud is the runtime for the phone agent, not just static hosting.

This is deployed on Google Cloud Run. One Cloud Run service serves the Next.js frontend, FastAPI backend, Twilio webhooks, SSE transcript events, and the WebSocket endpoint used by Twilio ConversationRelay.
```

Continue:

```text
Twilio needs a public callback URL, the browser needs live transcript streaming, and the voice agent needs a server-side WebSocket loop. Cloud Run gives us all of that in one serverless container.

Secret Manager stores Gemini, Tavily, Twilio, and SMTP credentials. Cloud Build builds the container, Artifact Registry stores the image, and Cloud Run deploys the live revision.

Google ADK wraps the agent loop. Gemini handles extraction and natural phrasing, but backend tools control money, constraints, completion proof, and when the call can close.
```

Person B:

```text
Without a public cloud runtime, Twilio cannot reach the agent, the UI cannot stream the call, and judges would only see a local demo. Here the whole voice-agent loop is live on Google Cloud.
```

## 4:30-5:00 Closing

Person B:

```text
RateDrop gives consumers leverage in the support calls they avoid: telecom bills, airline refunds, bank fees, subscriptions, warranties, and billing disputes.
```

Person A:

```text
The demo is controlled, but the pattern is real: evidence, mission, phone agent, transcript, proof, and cloud deployment.
```
