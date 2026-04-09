# iAmHere — 3D визуализация Алисы

Интерактивный 3D аватар AI-ассистента Алисы для планшета/браузера.

## Архитектура

```
┌─────────────────────────────────────────────────┐
│  Browser (планшет / десктоп)                     │
│                                                   │
│  Three.js + @pixiv/three-vrm                     │
│  ├── 3D VRM модель (лицо, expressions, bones)    │
│  ├── Animation system (game-style state machine) │
│  ├── Particle system (Canvas 2D)                 │
│  ├── Voice Engine (Web Speech API STT + TTS)     │
│  ├── Music detection (Web Audio API beat detect) │
│  └── UI overlay (chat, controls, info widget)    │
│                                                   │
│  ← HTTP → Flask API (api.py :5577)               │
│           ├── Grok AI (xAI) — чат                │
│           ├── Soul/Memory loader                  │
│           │   └── ~/.openclaw/workspace/          │
│           │       ├── SOUL.md                     │
│           │       ├── IDENTITY.md                 │
│           │       ├── USER.md                     │
│           │       └── MEMORY.md                   │
│           └── Google Calendar API                 │
└─────────────────────────────────────────────────┘
```

## Файлы

| Файл            | Описание                                                |
| --------------- | ------------------------------------------------------- |
| `index.html`    | Весь фронтенд: Three.js сцена, VRM, анимации, голос, UI |
| `api.py`        | Flask backend: чат (Grok + Soul), календарь, статика    |
| `alisa.jpg`     | 2D аватарка (fallback / reference)                      |
| `manifest.json` | PWA манифест                                            |
| `sw.js`         | Service Worker (кэширование)                            |

## Технологии

- **3D**: Three.js 0.180 + @pixiv/three-vrm v3 (CDN)
- **Модель**: VRM формат (сейчас AvatarSample_A, заменить на лису)
- **Анимация**: Game-style — exponential lerp, state machine, procedural idle
- **Голос STT**: Web Speech API (Chrome/Safari) → Whisper fallback (Groq, серверный)
- **Голос TTS**: Browser speechSynthesis → edge-tts fallback (серверный, ru-RU-SvetlanaNeural)
- **AI**: Claude (через локальный прокси :3456) → Grok 3 Mini fallback (xAI API), с полным Soul/Memory контекстом
- **Частицы**: Canvas 2D, state-reactive цвета
- **PWA**: fullscreen, wake lock, service worker

## Состояния анимации (State Machine)

| State       | Описание                                       | happy expr | Аура       |
| ----------- | ---------------------------------------------- | ---------- | ---------- |
| `idle`      | Покой, нейтральное лицо                        | 0          | оранжевая  |
| `listening` | Слушает, внимательная                          | 0          | циановая   |
| `thinking`  | Думает, смотрит в сторону                      | 0          | фиолетовая |
| `speaking`  | Говорит, lip sync                              | по mood    | оранжевая  |
| `happy`     | Только для тёплых/смешных ответов              | 0.7        | золотая    |
| `party`     | Музыкальный режим, качается в такт, губы сжаты | 0          | розовая    |

## Система эмоций (Mood)

API возвращает mood-тег в конце ответа: `[happy]`, `[neutral]`, `[sad]`.

- `[happy]` → speaking с улыбкой → happy state 1.5 сек → idle
- `[neutral]` → speaking нейтрально → сразу idle
- `[sad]` → speaking с грустью → idle

## VRM Expression Mapping

three-vrm v3 нормализует VRM 0.0 → VRM 1.0 имена:

- `a` → `aa`, `o` → `oh`, `i` → `ih`
- `joy` → `happy`, `sorrow` → `sad`
- `blink` остаётся

## Party Mode (музыка)

1. Пользователь нажимает микрофон
2. Вместо речи — музыка (audioLevel > 0.07, >2 сек)
3. Speech recognition перезапускается (не убивает mic)
4. State → `party`: голова в такт басу, happy face, розовая аура
5. Тишина >2 сек → выход из party

## Soul & Memory

`api.py` при старте загружает из `~/.openclaw/workspace/`:

- `SOUL.md` — характер, принципы (без Telegram-реакций)
- `IDENTITY.md` — имя, эмодзи, вайб
- `USER.md` — кто Женя, контакты, работа
- `MEMORY.md` — долгосрочная память

Перезагрузка: `POST /api/reload-soul`

## API Endpoints

| Endpoint           | Method | Описание                                        |
| ------------------ | ------ | ----------------------------------------------- |
| `/`                | GET    | Главная страница (index.html)                   |
| `/api/chat`        | POST   | Чат с Grok + Soul (body: `{message}`)           |
| `/api/events`      | GET    | Календарь на 7 дней                             |
| `/api/stt`         | POST   | Whisper STT fallback (body: multipart `audio`)  |
| `/api/tts`         | POST   | Edge-TTS fallback (body: `{text}`, returns MP3) |
| `/api/health`      | GET    | Health check                                    |
| `/api/reload-soul` | POST   | Перезагрузить Soul/Memory                       |

## Замена VRM модели

1. Скачать/создать .vrm файл (VRoid Studio)
2. Положить в эту папку: `alice.vrm`
3. В `index.html` заменить `MODEL_URL` на `'alice.vrm'`
4. Подстроить камеру (position.y, lookAt.y) под рост модели

## Запуск

```bash
cd "~/Projects/chat bots/Alice My assistant/iAmHere"
python3 api.py
# Открыть http://localhost:5577 или http://<IP>:5577 с планшета
```

## Huawei / HarmonyOS планшет — особенности

Huawei-устройства без Google Play Services требуют серверных fallback'ов:

1. **Import Maps не поддерживаются** — подключён полифил `es-module-shims` (jspm.io CDN)
2. **Web Speech API (STT) не работает** — Google Speech бэкенд недоступен. Детекция по User-Agent (`/huawei|harmonyos|hmscore/i`), сразу используется Whisper STT (запись через MediaRecorder → POST `/api/stt` → Groq Whisper large-v3-turbo)
3. **speechSynthesis (TTS) не работает** — голоса существуют в API, `onstart` срабатывает, но звук не воспроизводится. Детекция по тому же UA, сразу используется серверный edge-tts (`ru-RU-SvetlanaNeural`, POST `/api/tts` → MP3 → `<audio>` playback)
4. **VRM модель (19 МБ) через Cloudflare tunnel** — может таймаутиться. Добавлен автоматический fallback на GitHub-hosted модель (AvatarSample_A)
5. **Переключение аватаров** — камера фреймится по head bone одинаково для всех моделей (`hp.y+0.06, z=0.65`)

### Серверные зависимости для Huawei

```bash
pip3 install --user edge-tts  # TTS fallback
# Groq API (Whisper STT) — ключ в api.py
```

### Диагностика

- Красная плашка ошибок вверху страницы — показывает JS ошибки с полным стектрейсом
- Логи сервера: `tail -f /tmp/alice-api.log`
- Проверить TTS: `curl -X POST http://localhost:5577/api/tts -H 'Content-Type: application/json' -d '{"text":"тест"}'`

## TODO

- [ ] Создать VRM модель лисички-Алисы в VRoid Studio
- [ ] Камера на планшете → face tracking → lookAt следит за пользователем
- [ ] Фоновый режим (always-on listening с wake word)
