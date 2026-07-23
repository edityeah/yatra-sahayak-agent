#!/usr/bin/env bash
# Manual smoke test — a natural multi-turn conversation against a locally
# running agent. Cross-turn memory is held in the agent's in-process session
# store (keyed by conversation_id), so no history/markers are faked here.
# Turn 3 classifies via the LLM, so a real OPENAI_API_KEY is needed for the
# full run; turns 1, 2 and 4 work without one.
set -euo pipefail
BASE=${BASE:-http://localhost:8000}
KEY=${KEY:-local-dev-key}
CONV=${CONV:-smoke-$$}

turn () {
  curl -s -N -X POST "$BASE/messages" -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
    -d "{\"user_id\":\"u1\",\"conversation_id\":\"$CONV\",\"message\":{\"content\":[{\"type\":\"text\",\"text\":{\"value\":\"$1\"}}]}}"
  echo
}

echo "== health =="
curl -s "$BASE/health"; echo

echo "== turn 1: greeting (expect language ask) =="
turn "hello"

echo "== turn 2: pick Marathi (expect yatra ask, in Marathi) =="
turn "Marathi"

echo "== turn 3: pick Pandharpur, then ask weather (expect weather stub — needs OPENAI_API_KEY) =="
turn "pandharpur"
turn "what is the weather on the route today"

echo "== turn 4: emergency (expect SOS -> drills_sos stub, no key needed) =="
turn "emergency stampede help"
