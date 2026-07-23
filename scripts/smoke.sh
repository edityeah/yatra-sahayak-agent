#!/usr/bin/env bash
# Manual smoke test — a natural multi-turn conversation against a locally
# running agent. Cross-turn state (language, yatra, registration intake) is
# held server-side (persistence + session store), so nothing is faked here.
# Turns that hit the LLM router (weather/logistics/helpline) need a real
# OPENAI_API_KEY; language selection, the registration intake once started,
# and SOS work without one.
set -euo pipefail
BASE=${BASE:-http://localhost:8000}
KEY=${KEY:-local-dev-key}
CONV=${CONV:-smoke-$$}

turn () {
  curl -s -N -X POST "$BASE/messages" -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
    -d "{\"user_id\":\"u1\",\"conversation_id\":\"$CONV\",\"message\":{\"content\":[{\"type\":\"text\",\"text\":{\"value\":\"$1\"}}]}}"
  echo; echo "----"
}

echo "== health =="; curl -s "$BASE/health"; echo

echo "== 1: greeting -> language ask =="; turn "hello"
echo "== 2: pick English -> yatra ask =="; turn "English"
echo "== 3: pick Pandharpur =="; turn "pandharpur"
echo "== 4: weather on the route (live IMD or cached) =="; turn "what is the weather on the route today"
echo "== 5: pony/transport rates =="; turn "what are the palkhi and transport rates"
echo "== 6: helpline numbers =="; turn "give me the emergency helpline numbers"
echo "== 7: register for the yatra (starts intake) =="; turn "I want to register for the yatra"
echo "== 7a-f: intake answers =="; turn "Asha Patil"; turn "9812345678"; turn "Dindi 5"; turn "9800000000"; turn "elderly"; turn "yes"
echo "== 8: switch to the Nashik Kumbh =="; turn "switch to the Nashik Kumbh"
echo "== 9: emergency (SOS -> control room alerted, no key needed) =="; turn "stampede help emergency"
