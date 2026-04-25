# alice-assistant-3d

Two deployments share this codebase:

| Mode | URL | Workspace | LLM | Purpose |
|---|---|---|---|---|
| **Personal** (default) | local Flask `:5577` | `~/.openclaw/workspace/` | Claude (Max proxy `:3456`) → Grok fallback | Eugene's tablet Alice — full access (calendar, soul reload, private memory) |
| **Guest** (`ALICE_GUEST_MODE=1`) | https://alice.ekuznetsov.dev | `/opt/alice-guest/workspace/` | DeepSeek → Gemini Flash | Public AI representative on Eugene's site — only public material, lead capture |

Same `api.py` and `index.html` are reused — environment variables decide the mode.

---

## Highlights

- **3D VRM avatar** (Three.js + @pixiv/three-vrm v3) — one of three swappable models (`alice-e`, `AvatarSample_A`, `AvatarSample_B`).
- **Game-style animation system** — exponential lerp, idle micro-actions (glance, smile, head tilt, deep breath), state machine (idle / listening / thinking / speaking / happy / party).
- **Voice in/out** — Web Speech API STT (browser-native; auto-language by `navigator.language`) → Whisper (Groq) → Gemini multimodal fallback. Browser `speechSynthesis` for TTS, edge-tts as server fallback.
- **Markdown stripping** — chat & TTS clean `**bold**`, bullets, code, links so the spoken voice doesn't read "asterisk asterisk".
- **Lang-aware** — answers mirror the user's language; system prompt enforces no unilateral switching.
- **Guest-mode safety**:
  - Filesystem isolation (`/opt/alice-guest/workspace/` only, no `USER.md` / `MEMORY.md` / private credentials)
  - Refuse-to-start sanity check — if private files appear in guest workspace, the process bails out
  - In-memory rate limiting (configurable via ENV)
  - CORS whitelist on production origins
  - System prompt enforces refusal patterns for personal / work-private questions
- **Lead capture** — visitor → name + need + contact → forwarded to Eugene's Telegram via bot

---

## Repo layout

```
alice-assistant-3d/
├── api.py                     # Flask backend — both modes (ENV-driven)
├── index.html                 # Personal Alice frontend (3D + chat + voice)
├── index_guest.html           # Public Aliska frontend (chat-first, smaller avatar, lead modal)
├── manifest.json, sw.js       # PWA manifest + service worker
├── iAmHere/                   # Synced runtime copy (older deployment)
├── workspace_guest/           # Guest-mode persona files (no private data)
│   ├── IDENTITY.md            # Name, role, tone, avatar, language stance
│   ├── SOUL.md                # Behavioural principles, lead-capture flow,
│   │                            anti-injection guard, anti-markdown rule
│   ├── PUBLIC_BIO.md          # Public bio (no employer, no clients)
│   ├── PROJECTS.md            # All public GitHub projects + how to talk about them
│   ├── SERVICES.md            # Areas of work (no rates, no availability)
│   ├── CONTACT.md             # Telegram / email / GitHub / LinkedIn
│   ├── FAQ.md                 # Typical Q&A in Alice's voice
│   └── BOUNDARIES.md          # Hard refusal list + injection countermeasures
├── docs/
│   ├── ARCHITECTURE.md        # Technical architecture (this doc)
│   └── GUEST_MODE_PLAN.md     # Original design doc with decision log
└── testMe/
    └── ui_test_scenarios.py   # Titan E2E suite (5 viewports, no-overlap, chat round-trip)
```

---

## Quick start (personal mode)

```bash
cd alice-assistant-3d
python3 api.py                # http://localhost:5577
```

Visits `~/.openclaw/workspace/SOUL.md` etc. Personal Alice is normally launched via Docker
(`docker-compose.alice.yml` in the parent `alice-assistant/` repo).

## Quick start (guest mode)

Provision on Silver server (89.167.108.210):

```bash
useradd -r -s /bin/false -d /opt/alice-guest alice-guest
mkdir -p /opt/alice-guest/{workspace,}
# rsync workspace_guest/ → /opt/alice-guest/workspace/
# rsync api.py           → /opt/alice-guest/api.py
# write /opt/alice-guest/.env (chmod 600) with the keys below
# install systemd unit alice-guest.service
systemctl enable --now alice-guest
```

`.env` example (full list in `docs/ARCHITECTURE.md`):

```env
ALICE_GUEST_MODE=1
ALICE_WORKSPACE=/opt/alice-guest/workspace
ALICE_PORT=5578
ALICE_ALLOWED_ORIGINS=https://alice.ekuznetsov.dev,https://ekuznetsov.dev,https://www.ekuznetsov.dev
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_LEAD_CHAT_ID=431603030
RATE_LIMIT_CHAT_REQUESTS=100
RATE_LIMIT_CHAT_WINDOW=600
RATE_LIMIT_LEAD_REQUESTS=10
RATE_LIMIT_LEAD_WINDOW=3600
RATE_LIMIT_STT_REQUESTS=200
RATE_LIMIT_STT_WINDOW=600
RATE_LIMIT_TTS_REQUESTS=300
RATE_LIMIT_TTS_WINDOW=600
```

Caddy block on Silver:

```
alice.ekuznetsov.dev {
    root * /var/www/html/alice-guest
    handle /api/* { reverse_proxy localhost:5578 }
    handle        { file_server }
}
```

---

## Endpoints

| Endpoint | Modes | Notes |
|---|---|---|
| `GET  /api/health` | both | Returns `mode`, `time`, current `rate_limits` |
| `POST /api/chat` | both | DeepSeek (guest) / Claude+Grok (personal); markdown returned, frontend strips |
| `POST /api/stt` | both | Groq Whisper → Gemini multimodal fallback (auto language) |
| `POST /api/tts` | both | edge-tts (Microsoft); guest defaults to `en-US-AvaMultilingualNeural` |
| `POST /api/lead` | guest | Captures `{name, what, contact}`, forwards to Telegram + writes JSONL |
| `GET  /api/events` | personal only | Google Calendar (3 accounts) |
| `POST /api/reload-soul` | personal only | Re-reads SOUL/IDENTITY/USER/MEMORY |

---

## Logs

| File | What |
|---|---|
| `/opt/alice-guest/api.log` | stdout/stderr of the Flask process |
| `/opt/alice-guest/chat.jsonl` | One JSON line per chat exchange (`ts`, `ip`, `ua`, `user`, `reply`) |
| `/opt/alice-guest/leads.jsonl` | Audit trail of lead submissions |

Examples:

```bash
# Last 10 conversations
ssh root@89.167.108.210 "tail -10 /opt/alice-guest/chat.jsonl"

# Unique IPs
ssh root@89.167.108.210 "cut -d'\"' -f8 /opt/alice-guest/chat.jsonl | sort -u"

# All leads
ssh root@89.167.108.210 "cat /opt/alice-guest/leads.jsonl"
```

---

## Tests (Titan)

The Titan E2E suite is in `testMe/ui_test_scenarios.py`. From the `titan` repo:

```bash
cd ~/Projects/Personal\ projects/titan
python3 cli.py test --system config/systems/alice-guest.yaml --scenario alice-guest
```

Coverage: 5 viewports (`desktop` 1440×900, `tablet` 768×1024, `mobile` 393×852, `mobile_short`
393×700 — Telegram WebView, `tiny` 360×640). Asserts all elements visible, no overlap between
chat/avatar/chips/mic/input, avatar in safe zone, welcome message renders, chat round-trip works.

Latest run: **21/21 PASS**.

---

## Operations

```bash
# Check service health (through CF proxy)
curl https://alice.ekuznetsov.dev/api/health

# Edit rate limits / keys
ssh root@89.167.108.210
nano /opt/alice-guest/.env
systemctl restart alice-guest

# Tail server logs
ssh root@89.167.108.210 "journalctl -u alice-guest -f"

# Deploy a fresh frontend
rsync -avz index_guest.html root@89.167.108.210:/var/www/html/alice-guest/index.html
ssh root@89.167.108.210 "chown www-data:www-data /var/www/html/alice-guest/index.html"

# Deploy fresh backend
rsync -avz api.py root@89.167.108.210:/opt/alice-guest/api.py
ssh root@89.167.108.210 "chown alice-guest:alice-guest /opt/alice-guest/api.py && systemctl restart alice-guest"

# Sync persona files
rsync -avz --delete workspace_guest/ root@89.167.108.210:/opt/alice-guest/workspace/
ssh root@89.167.108.210 "chown -R alice-guest:alice-guest /opt/alice-guest/workspace && systemctl restart alice-guest"
```

---

## Stack summary

- **Frontend**: Three.js 0.180 + @pixiv/three-vrm v3 (CDN), vanilla JS, Web Speech API,
  edge-tts (server), no build step
- **Backend**: Python Flask (~600 LOC), in-memory rate limiter, OpenAI-compatible LLM clients
- **Hosting**: Caddy 2 + Let's Encrypt on Silver Server (Hetzner, 89.167.108.210); Cloudflare DNS+proxy
- **LLMs**: DeepSeek, Groq Whisper, Google Gemini 2.0 Flash, Microsoft edge-tts
- **Persona**: Markdown files, hot-reloadable in personal mode
- **Tests**: Titan (Python + Playwright + Claude screenshot analysis)
