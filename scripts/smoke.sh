#!/usr/bin/env bash
# Manual smoke test — requires the agent running locally with a real
# OPENAI_API_KEY (the activity-classification turn calls the LLM).
set -euo pipefail
BASE=${BASE:-http://localhost:8000}
KEY=${KEY:-local-dev-key}

echo "== health =="
curl -s "$BASE/health" | tee /dev/stderr; echo

echo "== turn 1: greeting (expect language ask) =="
curl -s -N -X POST "$BASE/messages" -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"user_id":"u1","conversation_id":"c1","message":{"content":[{"type":"text","text":{"value":"hello"}}]}}'
echo

echo "== turn 2: pick English + yatra + ask weather (expect weather stub) =="
curl -s -N -X POST "$BASE/messages" -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"user_id":"u1","conversation_id":"c1","history":[{"role":"user","text":"hello"},{"role":"assistant","text":"choose your language"},{"role":"user","text":"English"},{"role":"assistant","text":"[yatra-ask] which yatra"},{"role":"user","text":"pandharpur"},{"role":"assistant","text":"[yatra:pandharpur] ok"}],"message":{"content":[{"type":"text","text":{"value":"what is the weather on the route today"}}]}}'
echo
