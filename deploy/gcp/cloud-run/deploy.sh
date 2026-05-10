#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-ayafinancial}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-ratedrop}"
REPOSITORY="${REPOSITORY:-ratedrop}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:${IMAGE_TAG}"
ENV_FILE="${ENV_FILE:-.env.local}"

gcloud config set project "$PROJECT_ID" >/dev/null

gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com

if ! gcloud artifacts repositories describe "$REPOSITORY" --location "$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY" \
    --repository-format=docker \
    --location="$REGION" \
    --description="RateDrop demo containers"
fi

if [[ -f "$ENV_FILE" ]]; then
  PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
  RUNTIME_SERVICE_ACCOUNT="${RUNTIME_SERVICE_ACCOUNT:-${PROJECT_NUMBER}-compute@developer.gserviceaccount.com}"

  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    case "$key" in
      GEMINI_API_KEY|TAVILY_API_KEY|TWILIO_ACCOUNT_SID|TWILIO_AUTH_TOKEN|TWILIO_PHONE_NUMBER|TWILIO_SANDBOX_TO_NUMBER|TWILIO_VERIFY_ORIG_NUMBERS|SMTP_HOST|SMTP_PORT|SMTP_USERNAME|SMTP_PASSWORD|SMTP_FROM_EMAIL|RATEDROP_PROOF_EMAIL_TO)
        secret_name="ratedrop-$(echo "$key" | tr '[:upper:]_' '[:lower:]-')"
        if ! gcloud secrets describe "$secret_name" >/dev/null 2>&1; then
          gcloud secrets create "$secret_name" --replication-policy=automatic >/dev/null
        fi
        printf '%s' "$value" | gcloud secrets versions add "$secret_name" --data-file=- >/dev/null
        gcloud secrets add-iam-policy-binding "$secret_name" \
          --member="serviceAccount:${RUNTIME_SERVICE_ACCOUNT}" \
          --role="roles/secretmanager.secretAccessor" >/dev/null
        ;;
    esac
  done < "$ENV_FILE"
fi

gcloud builds submit --tag "$IMAGE" .

secret_mappings=(
  "GEMINI_API_KEY=ratedrop-gemini-api-key:latest"
  "TAVILY_API_KEY=ratedrop-tavily-api-key:latest"
  "TWILIO_ACCOUNT_SID=ratedrop-twilio-account-sid:latest"
  "TWILIO_AUTH_TOKEN=ratedrop-twilio-auth-token:latest"
  "TWILIO_PHONE_NUMBER=ratedrop-twilio-phone-number:latest"
  "TWILIO_SANDBOX_TO_NUMBER=ratedrop-twilio-sandbox-to-number:latest"
  "TWILIO_VERIFY_ORIG_NUMBERS=ratedrop-twilio-verify-orig-numbers:latest"
)

for optional_key in SMTP_HOST SMTP_PORT SMTP_USERNAME SMTP_PASSWORD SMTP_FROM_EMAIL RATEDROP_PROOF_EMAIL_TO; do
  optional_secret="ratedrop-$(echo "$optional_key" | tr '[:upper:]_' '[:lower:]-')"
  if gcloud secrets describe "$optional_secret" >/dev/null 2>&1; then
    secret_mappings+=("${optional_key}=${optional_secret}:latest")
  fi
done

set_secrets_arg="$(IFS=,; echo "${secret_mappings[*]}")"

gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --no-invoker-iam-check \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 1 \
  --concurrency 10 \
  --timeout 3600 \
  --no-cpu-throttling \
  --session-affinity \
  --set-env-vars "NODE_ENV=production,RATEDROP_DATABASE_MODE=local,RATEDROP_LOCAL_DB_PATH=/tmp/ratedrop/local-db,RATEDROP_AGENT_MODE=adk,RATEDROP_AGENT_MODEL_PROVIDER=gemini,RATEDROP_TWILIO_MODE=conversation_relay,NEXT_PUBLIC_API_BASE_URL=" \
  --set-secrets "$set_secrets_arg"

SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"

gcloud run services update "$SERVICE_NAME" \
  --region "$REGION" \
  --update-env-vars "PUBLIC_BASE_URL=${SERVICE_URL},FRONTEND_BASE_URL=${SERVICE_URL},RATEDROP_CONVERSATION_RELAY_WS_BASE=${SERVICE_URL/https:/wss:}/ws/conversation-relay"

echo "$SERVICE_URL"
