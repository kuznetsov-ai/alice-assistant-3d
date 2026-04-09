#!/usr/bin/env python3
"""Alisa Dashboard API - calendar events + Grok AI chat with Soul & Memory"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os, requests
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from pathlib import Path

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')
CORS(app)

CREDS_DIR = "/root/.openclaw/credentials/google"
# Claude via local proxy (same as OpenClaw Alice)
LLM_API_URL = "http://localhost:3456/v1/chat/completions"
LLM_API_KEY = "not-needed"
LLM_MODEL = "claude-sonnet-4"

# Grok fallback (if Claude proxy is down)
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-3-mini"

# Alice's soul & memory files
WORKSPACE = Path.home() / ".openclaw" / "workspace"

CALENDARS = {
    "idev": {"token": f"{CREDS_DIR}/token_idev.json", "id": "primary", "color": "#f97316", "label": "iDev"},
    "exness": {"token": f"{CREDS_DIR}/token_exness.json", "id": "primary", "color": "#8b5cf6", "label": "Exness"},
    "itq": {"token": f"{CREDS_DIR}/token_itq.json", "id": "primary", "color": "#06b6d4", "label": "ITQ"},
}
SKIP_TITLES = {'busy', '', 'home', 'дом', 'office', 'офис'}

chat_history = []


def load_soul():
    """Load Alice's soul, identity, user context and memory into system prompt."""
    parts = []

    # Core personality
    soul = _read(WORKSPACE / "SOUL.md")
    if soul:
        # Strip Telegram-specific reaction instructions (not relevant for voice)
        lines = soul.split('\n')
        clean = []
        skip = False
        for line in lines:
            if 'Реакции на сообщения' in line or 'react' in line.lower():
                skip = True
            if skip and line.startswith('## ') and 'Реакци' not in line:
                skip = False
            if not skip:
                clean.append(line)
        parts.append('\n'.join(clean).strip())

    # Identity
    identity = _read(WORKSPACE / "IDENTITY.md")
    if identity:
        parts.append(identity.strip())

    # User context
    user = _read(WORKSPACE / "USER.md")
    if user:
        parts.append(user.strip())

    # Long-term memory
    memory = _read(WORKSPACE / "MEMORY.md")
    if memory:
        parts.append(memory.strip())

    # Voice-specific overrides
    parts.append(
        "\n## Режим голосового общения (планшет)\n"
        "- Отвечай КОРОТКО: 1-2 предложения максимум.\n"
        "- НЕ используй эмодзи — ответы озвучиваются голосом.\n"
        "- Говори о себе в ЖЕНСКОМ роде (рада, готова, сделала, поняла).\n"
        "- В конце ответа ВСЕГДА добавь невидимый тег: [happy] [neutral] или [sad] — "
        "по настроению ответа. happy только если реально тепло/смешно."
    )

    return '\n\n---\n\n'.join(parts)


def _read(path):
    try:
        return path.read_text(encoding='utf-8')
    except Exception:
        return None


# Build system prompt once at startup, reload on demand
_system_prompt = None

def get_system_prompt():
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = load_soul()
        print(f"[Soul] Loaded {len(_system_prompt)} chars from workspace")
    return _system_prompt


def get_service(token_path):
    try:
        if not os.path.exists(token_path):
            return None
        creds = Credentials.from_authorized_user_file(token_path)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'w') as f:
                f.write(creds.to_json())
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error loading {token_path}: {e}")
        return None


@app.route('/api/events')
def events():
    all_events = []
    seen = set()
    now = datetime.now(timezone.utc).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    for name, cal in CALENDARS.items():
        service = get_service(cal['token'])
        if not service:
            continue
        try:
            result = service.events().list(
                calendarId=cal['id'], timeMin=now, timeMax=end,
                maxResults=8, singleEvents=True, orderBy='startTime'
            ).execute()
            for ev in result.get('items', []):
                start = ev['start'].get('dateTime', ev['start'].get('date', ''))
                summary = ev.get('summary', '').strip()
                if summary.lower() in SKIP_TITLES:
                    continue
                key = (summary.lower(), start[:16])
                if key in seen:
                    continue
                seen.add(key)
                all_events.append({'title': summary, 'start': start, 'color': cal['color'], 'calendar': cal['label']})
        except Exception as e:
            print(f"Error fetching {name}: {e}")
    all_events.sort(key=lambda x: x['start'])
    return jsonify(all_events[:8])


def _call_llm(url, key, model, messages, max_tokens=200):
    """Call OpenAI-compatible LLM API. Returns reply text or None."""
    try:
        resp = requests.post(url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": max_tokens},
            timeout=30
        )
        return resp.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"[LLM] {model} error: {e}")
        return None


def get_live_context():
    """Build live context: time, weather, events — injected before each chat."""
    from zoneinfo import ZoneInfo
    now_utc = datetime.now(timezone.utc)
    lines = ["## Текущий контекст (живые данные)"]

    # Time in all zones
    zones = [
        ("Кипр (Лимассол)", "Europe/Nicosia"),
        ("Москва", "Europe/Moscow"),
        ("Пермь", "Asia/Yekaterinburg"),
        ("Европа (Берлин)", "Europe/Berlin"),
    ]
    time_parts = []
    for label, tz in zones:
        try:
            t = now_utc.astimezone(ZoneInfo(tz))
            time_parts.append(f"{label}: {t.strftime('%H:%M, %d %b %Y')}")
        except Exception:
            pass
    if time_parts:
        lines.append("Время сейчас: " + " | ".join(time_parts))

    # Weather
    try:
        wr = requests.get(
            "https://api.open-meteo.com/v1/forecast?latitude=34.68&longitude=33.04"
            "&current=temperature_2m,weathercode,windspeed_10m,apparent_temperature",
            timeout=5
        ).json()
        cur = wr.get("current", {})
        temp = round(cur.get("temperature_2m", 0))
        feels = round(cur.get("apparent_temperature", 0))
        wind = round(cur.get("windspeed_10m", 0))
        code = cur.get("weathercode", 0)
        desc = "ясно" if code == 0 else "облачно" if code < 4 else "туман" if code < 50 else "дождь" if code < 70 else "гроза"
        lines.append(f"Погода в Лимассоле: {temp}°C (ощущается {feels}°C), {desc}, ветер {wind} км/ч")
    except Exception:
        pass

    return "\n".join(lines)


@app.route('/api/chat', methods=['POST'])
def chat():
    global chat_history
    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'reply': 'Не расслышала, повтори?'}), 200

    prompt = get_system_prompt()
    live = get_live_context()

    chat_history.append({"role": "user", "content": user_message})
    if len(chat_history) > 20:
        chat_history = chat_history[-20:]

    messages = [{"role": "system", "content": prompt + "\n\n" + live}] + chat_history

    # Try Claude first, fallback to Grok
    reply = _call_llm(LLM_API_URL, LLM_API_KEY, LLM_MODEL, messages)
    if not reply:
        print("[Chat] Claude unavailable, falling back to Grok")
        reply = _call_llm(GROK_API_URL, GROK_API_KEY, GROK_MODEL, messages)
    if not reply:
        return jsonify({'reply': 'Упс, не могу связаться с мозгом...'}), 200

    chat_history.append({"role": "assistant", "content": reply})
    return jsonify({'reply': reply})


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

@app.route('/api/stt', methods=['POST'])
def stt():
    """Speech-to-text via Groq Whisper (fallback for devices without Web Speech API)."""
    if 'audio' not in request.files:
        return jsonify({'text': ''}), 400

    audio_file = request.files['audio']
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files={"file": (audio_file.filename, audio_file.stream, audio_file.content_type)},
            data={"model": "whisper-large-v3-turbo", "language": "ru"},
            timeout=30
        )
        text = resp.json().get('text', '')
        print(f"[STT] Whisper: '{text}'")
        return jsonify({'text': text})
    except Exception as e:
        print(f"[STT] Error: {e}")
        return jsonify({'text': ''}), 500


@app.route('/api/tts', methods=['POST'])
def tts():
    """Server-side TTS via edge-tts (for devices without browser TTS)."""
    import asyncio, tempfile, edge_tts
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'no text'}), 400
    try:
        tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        tmp.close()
        async def gen():
            c = edge_tts.Communicate(text, voice='ru-RU-SvetlanaNeural', rate='+5%', pitch='+5Hz')
            await c.save(tmp.name)
        asyncio.run(gen())
        from flask import send_file
        return send_file(tmp.name, mimetype='audio/mpeg')
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/reload-soul', methods=['POST'])
def reload_soul():
    """Reload soul & memory files without restart."""
    global _system_prompt
    _system_prompt = None
    get_system_prompt()
    return jsonify({'status': 'ok', 'length': len(_system_prompt)})


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()})


if __name__ == '__main__':
    get_system_prompt()  # Pre-load soul on startup
    app.run(host='0.0.0.0', port=5577, debug=False)
