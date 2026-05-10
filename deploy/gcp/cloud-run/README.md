# RateDrop on GCP Cloud Run

Cloud Run is the recommended Google hackathon deployment path for RateDrop.

It gives the app a public HTTPS URL by default, supports HTTP streaming and WebSocket upgrade paths, and can be deleted after the demo to stop costs.

## Deploy

```bash
PROJECT_ID=ayafinancial REGION=us-central1 SERVICE_NAME=ratedrop ./deploy/gcp/cloud-run/deploy.sh
```

The script:

- Enables Cloud Run, Cloud Build, Artifact Registry, and Secret Manager APIs
- Creates an Artifact Registry Docker repository if needed
- Builds the app container with Cloud Build
- Uploads local `.env.local` secret values to Secret Manager without printing them
- Deploys one Cloud Run service with nginx, FastAPI, and Next.js in the same container
- Sets `PUBLIC_BASE_URL`, `FRONTEND_BASE_URL`, and the ConversationRelay `wss://.../ws/conversation-relay` base after Cloud Run returns the service URL
- Runs the judged demo in `conversation_relay` mode so Twilio can connect phone speech to the Cloud Run WebSocket agent loop

## Demo Cost Controls

This deployment intentionally uses:

- `--min-instances 1` so the local JSON demo state and background call flow stay alive during judging
- `--max-instances 1` so local demo state cannot split across multiple containers
- `--memory 1Gi` and `--cpu 1` for a reliable Next.js + FastAPI runtime
- `--timeout 3600` for long SSE/WebSocket demo sessions
- `--no-cpu-throttling` so background phone-call work continues after request responses

For a sub-24-hour hackathon demo this should be low cost, but it is not the absolute scale-to-zero cheapest setting. After judging, either delete the service or set min instances to zero.

## Verify

```bash
SERVICE_URL="$(gcloud run services describe ratedrop --region us-central1 --format='value(status.url)')"
curl "$SERVICE_URL/api/demo-bills"
open "$SERVICE_URL"
```

## Stop Costs

```bash
gcloud run services delete ratedrop --region us-central1
```
