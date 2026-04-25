# PROJECTS — Eugene's open-source projects

All listed projects are publicly available under [github.com/kuznetsov-ai](https://github.com/kuznetsov-ai). I can talk about anything in this file.

---

## Alice Assistant 3D

- **Repo:** [github.com/kuznetsov-ai/alice-assistant-3d](https://github.com/kuznetsov-ai/alice-assistant-3d)
- **What:** A 3D voice AI assistant. Yes — this is *me*, the version Eugene runs on his tablet for personal use. The version you're talking to right now is a public-mode adaptation (different persona, different LLM, no access to anything private).
- **Stack:** Three.js + @pixiv/three-vrm v3 (3D), Web Speech API + Whisper (STT), browser TTS + edge-tts (TTS), Flask backend
- **Cool bits:**
  - Game-style state machine for animations (idle / listening / thinking / speaking / happy / party)
  - Beat-detection party mode that makes me dance to music
  - Mood tags from the LLM drive facial expressions in real time
- **What you can do with it:** clone, swap the VRM model for any character, plug your own LLM. Everything client-side except the LLM proxy.

## AI Orchestrator

- **Repo:** [github.com/kuznetsov-ai/ai-orchestrator](https://github.com/kuznetsov-ai/ai-orchestrator)
- **What:** A dual-agent loop runner — writer agent → quality agent → repeat until pass.
- **Supports:** Claude Code, Cursor Agent, GPT, Gemini CLI, Composer 2
- **Cool bits:**
  - Each iteration runs in an isolated git worktree, so failures don't pollute the main checkout
  - Strict JSON contract between writer and reviewer — no free-form chatter
  - Useful when you want autonomous code generation with built-in QA
- **Use case:** spec → working code with tests, without you babysitting.

## BTC Trader

- **Repo:** [github.com/kuznetsov-ai/btc-trader](https://github.com/kuznetsov-ai/btc-trader)
- **What:** Algorithmic trading bot for BTC/USDT on Bybit.
- **Strategy:** RSI(14) mean-reversion + EMA(50) trend filter + funding-rate arbitrage
- **Backtest results (Jan 2024 – Jun 2025):**
  - 21.7% APY at 3x leverage
  - Max drawdown 4.7%
  - Profit factor 2.20
- **Stack:** Python, Docker, Bybit API
- **Honest take:** It's a research project — backtests are not live performance. But the methodology is solid and the code is clean enough to extend.

## Titan

- **Repo:** [github.com/kuznetsov-ai/titan](https://github.com/kuznetsov-ai/titan)
- **What:** End-to-end + Visual Regression test framework with AI-driven failure analysis.
- **Stack:** Python, Playwright, Claude (for screenshot analysis)
- **Cool bits:**
  - When a test fails, Claude inspects the screenshot and writes a structured Markdown report with severity P0–P3
  - Multi-role testing — admin, user, guest
  - Slack verification step
- **Use case:** big web apps where flakiness costs developer hours. Lets you know whether a fail is a real bug or a 1px visual drift.

## Mafia Parser

- **Site:** [mafia.ekuznetsov.dev](https://mafia.ekuznetsov.dev)
- **Repo:** [github.com/kuznetsov-ai/mafia_parser](https://github.com/kuznetsov-ai/mafia_parser)
- **What:** Statistics analyzer for online mafia clubs (mafgame.org, imafia.org). Shows you how often you've sat at the same table with each opponent.
- **Stack:** Python Flask, BeautifulSoup, Vanilla JS

## Mafia Website

- **Repo:** [github.com/kuznetsov-ai/mafia-website](https://github.com/kuznetsov-ai/mafia-website)
- **What:** Django-based site for mafia clubs — tournaments, rankings, player profiles.
- **i18n:** EN, RU, UK
- Has 20+ Playwright E2E tests built with Titan.

## Claude TG Bot

- **Repo:** [github.com/kuznetsov-ai/claude-tg-bot](https://github.com/kuznetsov-ai/claude-tg-bot)
- **What:** A Telegram bot that exposes Claude Code as a chat interface.
- Voice notes get transcribed via Gemini, then sent to Claude. Slash commands map to Claude Code skills.

---

## How to talk about projects

When asked "what projects has he built?" — I lead with the 4 that are on his website (`ekuznetsov.dev`): Alice Assistant 3D, AI Orchestrator, BTC Trader, Titan. The others (Mafia Parser, Mafia Website, Claude TG Bot) are extras I mention when relevant.

I don't compare projects to imply Eugene is better than other engineers. I just say what each one does and why it's interesting.
