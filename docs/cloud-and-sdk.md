# Cloud and SDK Story

RateDrop can be presented as a cloud agent product, not just a local demo.

## Best Cloud Track Angle

The strongest cloud story is:

RateDrop is a cloud-hosted voice-agent runtime for support calls. The frontend collects the job, the backend runs the deterministic policy and Google ADK agent, Gemini provides the model reasoning and phrasing, Twilio handles the phone call, and the transcript/result state is persisted for replay.

## Practical Cloud Architecture

Recommended hackathon deployment:

- Frontend/backend: Google Cloud Run with one HTTPS service for the Next.js UI and FastAPI API
- Model: Gemini through Google ADK
- Secrets: Google Secret Manager
- Storage: local JSON for the hackathon demo, or Firestore/Cloud SQL later if you want a deeper GCP-native persistence story
- Logs/observability: CloudWatch
- Voice: Twilio webhooks pointed at the public backend URL

The important cloud requirement is that Twilio needs a public HTTPS backend URL for:

- `/twilio/voice/negotiations/{id}`
- `/twilio/status/{id}`
- `/ws/conversation-relay/{id}`

## What To Say To Judges

RateDrop is cloud-native because the phone agent cannot live only in the browser. The browser starts the job; the cloud runtime owns the agent loop, policy, model credentials, Twilio webhooks, transcript persistence, and replayable outcome proof.

For the Google Cloud track, emphasize:

- Google ADK is the agent runtime and Gemini is the default model
- FastAPI exposes the public webhook surface Twilio needs
- The agent loop is event-driven by phone conversation turns
- CloudWatch/App Runner/ECS make every agent run observable
- Secrets and phone credentials stay server-side

## NPM Package Story

`@ratedrop/agent` should not contain the Google ADK agent itself. That would expose credentials and policy internals.

Instead, the npm package is a client SDK for other apps. It lets a website, dashboard, or partner app create a RateDrop support run, start the voice call, fetch transcript state, and subscribe to events.

Example:

```ts
import { RateDropAgent } from "@ratedrop/agent";

const agent = new RateDropAgent({
  apiBaseUrl: "https://api.ratedrop.ai"
});

const run = await agent.createSupportRun({
  billId: "bill_123",
  companyName: "Air Canada",
  problemSummary: "Wrong baggage fee charged",
  desiredOutcome: "Refund the fee and capture a reference number",
  completionCriteria: ["Refund confirmed", "Reference number captured"]
});

await agent.startVoiceCall(run.id);
```

## How People Would Use It

There are two valid product surfaces:

- Consumer website: user signs in, uploads a bill/receipt, describes the issue, and starts the agent from the RateDrop UI.
- Developer SDK: another company embeds RateDrop into its own support dashboard by installing `@ratedrop/agent` and calling the hosted RateDrop API.

For this hackathon, the website is the primary demo. The npm package is the proof that RateDrop can become a platform.

## Publish Path

Local package validation:

```bash
cd packages/ratedrop-agent
npm run build
npm pack
```

Public npm publish later:

```bash
npm login
npm publish --access public
```

Only publish after choosing the final package name, adding real package ownership metadata, and confirming the hosted API contract is stable.
