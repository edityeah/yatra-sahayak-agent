# Single-image build: compiles the web UI and serves it + the API from one
# FastAPI origin, so a single Cloudflare tunnel can front the whole app at
# yatri.adityeah.ai. Build context is the REPO ROOT (see docker-compose.yml).

# ---- stage 1: build the web UI ----
FROM node:20-slim AS web
WORKDIR /web
COPY webview/package.json webview/package-lock.json* ./
RUN npm ci
COPY webview/ ./
# The UI talks to the API on the SAME origin (the tunnel host), so no CORS.
ARG VITE_AGENT_URL=https://yatri.adityeah.ai
ARG VITE_AGENT_KEY=local-dev-key
ENV VITE_AGENT_URL=$VITE_AGENT_URL
ENV VITE_AGENT_KEY=$VITE_AGENT_KEY
RUN npm run build

# ---- stage 2: agent runtime that also serves the built UI ----
FROM python:3.11-slim AS app
# libpq5 for psycopg (Postgres); curl for the container healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY agent/ /app/agent/
COPY data/ /app/data/
RUN pip install --no-cache-dir /app/agent
COPY --from=web /web/dist /app/webview/dist
ENV DATA_DIR=/app/data \
    WEBVIEW_DIST=/app/webview/dist \
    PORT=8000
WORKDIR /app/agent
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1
CMD ["sh", "-c", "uvicorn webhook:app --host 0.0.0.0 --port ${PORT:-8000}"]
