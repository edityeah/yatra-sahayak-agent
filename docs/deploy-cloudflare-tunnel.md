# Deploy at `yatri.adityeah.ai` via a Cloudflare Tunnel

This serves the **whole app from one origin** — the FastAPI agent serves both
the web UI and the API — behind a Cloudflare Tunnel. No public IP, no open
ports, no CORS. The LiveKit voice worker (if used) runs separately; it dials
LiveKit outbound and doesn't need the tunnel.

```
browser ──▶ https://yatri.adityeah.ai ──▶ Cloudflare edge ──▶ cloudflared ──▶ agent:8000
                                                                              ├─ /            web UI (built React)
                                                                              ├─ /messages    SwiftChat / chat SSE
                                                                              ├─ /api/*        data + registration
                                                                              └─ /officer/*    officer war-room
```

## Prerequisites
- Docker + Docker Compose on the host that will run the app (a small VPS, or any always-on box).
- `adityeah.ai` added to your Cloudflare account (nameservers pointed at Cloudflare).

## 1. Create the tunnel (one time)
1. Cloudflare dashboard → **Zero Trust** → **Networks → Tunnels** → **Create a tunnel** → **Cloudflared**.
2. Name it `yatri`. On the next screen, **copy the connector token** (the long string after `--token`). You'll put it in `.env` as `TUNNEL_TOKEN`.
3. Under **Public Hostnames**, add:
   - **Subdomain:** `yatri`  **Domain:** `adityeah.ai`
   - **Type:** `HTTP`  **URL:** `agent:8000`
     (`agent` is the compose service name — cloudflared reaches it on the compose network. If you run cloudflared outside compose, use `localhost:8000` and publish the port.)
   - Save. Cloudflare creates the `yatri.adityeah.ai` DNS record for you.

## 2. Configure
```bash
cp deploy/.env.example deploy/.env
# edit deploy/.env — set TUNNEL_TOKEN, INTERNAL_API_KEY, ADMIN_API_KEY (distinct!),
# OPENAI_API_KEY, DATABASE_URL/DIRECT_URL, OFFICER_IDS, SWIFTCHAT_WEBHOOK_SECRET.
```

## 3. Build & run
```bash
docker compose -f deploy/docker-compose.yml up -d --build
```
The UI is baked with `VITE_AGENT_URL=https://yatri.adityeah.ai`, so it calls the
API on the same host. Check it:
```bash
curl -s https://yatri.adityeah.ai/health          # {"status":"ok",...}
open https://yatri.adityeah.ai                      # the app
```

## 4. Point things at the new host
- **SwiftChat bot webhook** → `https://yatri.adityeah.ai/messages` (yatri) and `https://yatri.adityeah.ai/officer/messages` (officer).
- **Officer webviews** are served from the same host, e.g. `https://yatri.adityeah.ai/officer/registry`.

## Updating
```bash
git pull && docker compose -f deploy/docker-compose.yml up -d --build
```

## Notes
- **Voice:** the browser voice call talks to LiveKit directly; the voice worker
  is a separate process (`python voice_agent.py start`) and can keep running on
  Render, or add it as another compose service with the LiveKit env set. Set the
  worker's `AGENT_API_HOST=https://yatri.adityeah.ai` so its tools reach this API.
- **Rebuild after key change:** `INTERNAL_API_KEY` is compiled into the UI at
  build time (it's the browser-shipped key), so change it → rebuild the image.
- **Alternative (no dashboard hostname):** you can instead commit a
  `cloudflared` `config.yml` with `ingress:` rules + a credentials file and run
  `cloudflared tunnel run <name>`; the token+dashboard flow above is simpler for
  containers.
