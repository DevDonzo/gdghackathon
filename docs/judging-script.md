# RateDrop Judging Script

Target length: 4 to 5 minutes.

Roles:

- Person A: product demo operator and cloud architecture explanation.
- Person B: problem framing, technical framing, transitions, and closing.

## 0:00-0:30 Opening

Person B:

"Companies already use AI to route, delay, and reduce the cost of dealing with customers. RateDrop gives consumers an agent back.

Instead of sitting on hold and negotiating a bill yourself, you upload the evidence, define the exact outcome you want, and RateDrop calls on your behalf. It keeps the conversation bounded by policy, streams the transcript, and shows the final savings proof."

Person A:

"For the demo, we are not calling a real telecom company. We are using a controlled Twilio trial call to our verified number, where I will act as the company representative. The important part is that the same cloud runtime, agent loop, transcript stream, and policy engine are live."

## 0:30-1:15 Product Demo Setup

Person A:

Open:

```text
https://ratedrop-reezumnw5a-uc.a.run.app
```

Click `Start`, continue with the demo account, and load the Bell demo.

Say:

"I am starting from a bill. RateDrop extracts the company, plan, monthly total, fees, and negotiation angles. But the agent does not just guess what to do. The user has to define the mission."

Fill example mission:

- Company: `Bell`
- Problem: `The monthly bill increased after the promotional rate ended.`
- Desired outcome: `Lower the monthly bill and confirm when the new rate takes effect.`
- Target monthly: `52`
- Walk-away max: `58`
- Known fact: `Current bill is $85 on Unlimited 50.`
- Constraint: `Do not accept a vague callback.`
- Completion proof: `Rep confirms the monthly rate and effective date.`

Person B:

"This is important: RateDrop is not a generic chatbot. The user supplies the goal and constraints, and the backend turns that into a bounded phone mission."

## 1:15-2:20 Live Call Demo

Person A:

Click `Start voice agent`.

When the phone rings, answer it. Person A acts as the company support representative.

Suggested rep script:

1. "Thanks for calling Bell, how can I help?"
2. "I see the account, but the current plan is already the standard rate."
3. "I can reduce it to seventy dollars a month."
4. "Let me check retention. I can do fifty-two dollars a month."
5. "Confirmed. The new monthly rate is fifty-two dollars and it starts next billing cycle."

Person A, while demo runs:

"The call is live. The transcript is streaming back into the UI. The reasoning panel shows why the agent is making each move, for example whether it is countering because the offer is above the walk-away threshold or accepting because the offer is within bounds."

Person B:

"The agent can phrase responses with Gemini, but the money decisions are deterministic. That means the model is not allowed to invent savings, accept random numbers, or change the math."

## 2:20-3:10 Result Page

Person A:

After completion, show the result page.

Say:

"The result page gives a deterministic before-and-after number, transcript summary, monthly savings, annualized savings, and any credit captured. This is the proof layer. It turns a messy phone call into a measurable outcome."

Person B:

"That is the product loop: evidence in, bounded agent call, transcript out, savings proof at the end."

## 3:10-4:20 Cloud Architecture

Person A:

Open:

```text
https://ratedrop-reezumnw5a-uc.a.run.app/api/readiness
```

Say:

"This is deployed on Google Cloud Run, and this endpoint proves what is live.

Cloud Run is our real-time phone-agent control plane. It serves the Next.js frontend, FastAPI backend, Twilio webhooks, SSE transcript stream, and the WebSocket ConversationRelay loop from one public HTTPS service.

Secret Manager stores the Gemini, Tavily, and Twilio credentials outside the codebase. Cloud Build builds the container. Artifact Registry stores the image. Cloud Run runs the app with min and max instances set to one for a reliable hackathon demo.

The readiness endpoint shows Google ADK mode is enabled, Gemini is configured, Tavily is configured, Twilio ConversationRelay is configured, and the public WebSocket base is live."

Person B:

"The cloud part is not just hosting. The product depends on the cloud because Twilio needs public callbacks, the browser needs live transcript streaming, and the voice agent needs a WebSocket runtime that stays alive during the call."

## 4:20-4:50 Closing

Person B:

"RateDrop is a focused consumer agent for a real pain point: support calls where companies have more leverage than customers. It is grounded in the user's evidence, constrained by deterministic policy, and deployed as a live Google Cloud voice-agent runtime."

Person A:

"The future version can handle more companies, phone trees, and longer calls. But the core loop is working now: upload evidence, define a mission, launch a cloud-hosted agent, stream the call, and prove the outcome."

## If A Judge Asks About Safety

Person A:

"For the hackathon demo, we only call our own verified Twilio number. We are not calling real companies during judging. The architecture is production-shaped, but the demo is intentionally sandboxed."

## If A Judge Asks Why ADK Matters

Person B:

"ADK gives us an agent wrapper around tools, but the tools enforce boundaries. The model can help phrase and route the response, but the backend policy decides whether to push, counter, accept, or close. That keeps the demo credible because the final math is code-driven."

## If A Judge Asks Why Cloud Run

Person A:

"Cloud Run supports exactly what this app needs: a public HTTPS URL, container deployment, backend APIs, long-lived SSE transcript streams, and WebSocket upgrades for Twilio ConversationRelay. It let us ship the whole voice-agent runtime as one serverless service."
