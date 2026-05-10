FROM node:22-bookworm AS frontend-build

WORKDIR /app
COPY frontend/next-legacy/package.json frontend/next-legacy/package-lock.json ./frontend/next-legacy/
RUN cd frontend/next-legacy && npm ci

COPY frontend/next-legacy ./frontend/next-legacy
RUN cd frontend/next-legacy && NEXT_PUBLIC_API_BASE_URL= npm run build

FROM node:22-bookworm AS runtime

ENV NODE_ENV=production \
    NEXT_PUBLIC_API_BASE_URL= \
    RATEDROP_DATABASE_MODE=local \
    RATEDROP_LOCAL_DB_PATH=/tmp/ratedrop/local-db \
    RATEDROP_AGENT_MODE=adk \
    RATEDROP_AGENT_MODEL_PROVIDER=gemini \
    RATEDROP_TWILIO_MODE=sandbox_tts

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        nginx \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf

COPY backend/requirements.txt ./backend/requirements.txt
RUN python3 -m venv .venv \
    && .venv/bin/pip install --upgrade pip wheel \
    && .venv/bin/pip install -r backend/requirements.txt

COPY backend ./backend
COPY --from=frontend-build /app/frontend/next-legacy ./frontend/next-legacy
COPY deploy/gcp/cloud-run/start.sh /usr/local/bin/ratedrop-start

RUN chmod +x /usr/local/bin/ratedrop-start \
    && mkdir -p /tmp/ratedrop /var/cache/nginx /var/log/nginx /run

EXPOSE 8080

CMD ["ratedrop-start"]
