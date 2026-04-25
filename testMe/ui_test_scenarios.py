"""Alice Guest (alice.ekuznetsov.dev) layout & responsiveness test suite.

Catches the failure mode that bit us repeatedly: chat / avatar / quick-action
chips / mic / input must NOT overlap on any viewport.
"""
from __future__ import annotations

import asyncio

from scenarios.base import BaseScenario


VIEWPORTS = {
    "desktop":     {"width": 1440, "height": 900},
    "tablet":      {"width": 768,  "height": 1024},
    "mobile":      {"width": 393,  "height": 852},
    # Mimics Telegram in-app browser & similar embedded WebViews where top/bottom
    # bars eat ~150px of usable height. This is the regression that bit on real iPhone.
    "mobile_short":{"width": 393,  "height": 700},
    "tiny":        {"width": 360,  "height": 640},
}


def _rects_overlap(a: dict, b: dict, tolerance: int = 0) -> bool:
    """Return True if two bounding rects overlap (with optional tolerance)."""
    return not (
        a["right"] - tolerance <= b["left"]
        or b["right"] - tolerance <= a["left"]
        or a["bottom"] - tolerance <= b["top"]
        or b["bottom"] - tolerance <= a["top"]
    )


class AliceGuestScenario(BaseScenario):
    OUTPUT_SUBDIR = "alice-guest"

    async def _go(self, path: str = "/") -> None:
        # cache-bust for fresh deploy
        url = f"{self.base_url}{path}?v={int(asyncio.get_event_loop().time() * 1000)}"
        await self.page.goto(url, wait_until="networkidle")
        # VRM model takes a few seconds to load
        await asyncio.sleep(4)

    async def _set_viewport(self, name: str) -> None:
        await self.page.set_viewport_size(VIEWPORTS[name])
        await asyncio.sleep(0.4)

    async def _rect(self, selector: str) -> dict | None:
        loc = self.page.locator(selector).first
        if await loc.count() == 0:
            return None
        try:
            return await loc.bounding_box()
        except Exception:
            return None

    # ── S01: All key elements visible on each viewport ─────────────────────

    async def test_s01_elements_visible(self):
        """S01: chat, avatar, chips, mic, text input, footer-CTA — visible."""
        for vp_name in VIEWPORTS:
            start = await self._step(f"s01_visible_{vp_name}")
            try:
                await self._set_viewport(vp_name)
                await self._go("/")

                checks = {
                    "chat":        "#chat-area",
                    "avatar":      "#avatar-canvas",
                    "quick-actions": "#quick-actions",
                    "mic":         "#voice-btn",
                    "input":       "#text-input",
                    "footer":      "#footer-cta",
                }
                missing = []
                rects = {}
                for label, sel in checks.items():
                    loc = self.page.locator(sel)
                    if await loc.count() == 0 or not await loc.first.is_visible():
                        missing.append(label)
                    else:
                        rects[label] = await loc.first.bounding_box()

                screenshot = await self._screenshot(f"s01_visible_{vp_name}")
                status = "FAIL" if missing else "PASS"
                self._record(
                    f"s01_visible_{vp_name}", status,
                    f"[{vp_name.upper()}] all 6 anchors present"
                    + (f" | MISSING: {missing}" if missing else ""),
                    screenshot, start,
                )
            except Exception as e:
                screenshot = await self._screenshot(f"s01_visible_{vp_name}_error")
                self._record(f"s01_visible_{vp_name}", "FAIL",
                             f"[{vp_name.upper()}] Exception: {e}", screenshot, start)

    # ── S02: No element overlaps another ───────────────────────────────────

    async def test_s02_no_overlap(self):
        """S02: chat / avatar / chips / mic / input must not overlap each other."""
        # Pairs we explicitly forbid from overlapping (the regressions we fixed)
        FORBIDDEN_PAIRS = [
            ("#chat-area",    "#avatar-canvas"),
            ("#chat-area",    "#quick-actions"),
            ("#avatar-canvas","#quick-actions"),
            ("#avatar-canvas","#voice-btn"),
            ("#quick-actions","#voice-btn"),
            ("#voice-btn",    "#text-input"),
        ]
        for vp_name in VIEWPORTS:
            start = await self._step(f"s02_overlap_{vp_name}")
            try:
                await self._set_viewport(vp_name)
                await self._go("/")

                problems = []
                for sel_a, sel_b in FORBIDDEN_PAIRS:
                    a = await self._rect(sel_a)
                    b = await self._rect(sel_b)
                    if not a or not b:
                        problems.append(f"{sel_a}|{sel_b}: missing rect")
                        continue
                    a_box = {"left": a["x"], "top": a["y"],
                             "right": a["x"]+a["width"], "bottom": a["y"]+a["height"]}
                    b_box = {"left": b["x"], "top": b["y"],
                             "right": b["x"]+b["width"], "bottom": b["y"]+b["height"]}
                    if _rects_overlap(a_box, b_box, tolerance=2):
                        problems.append(f"{sel_a} ∩ {sel_b}")

                screenshot = await self._screenshot(f"s02_overlap_{vp_name}")
                status = "FAIL" if problems else "PASS"
                self._record(
                    f"s02_overlap_{vp_name}", status,
                    f"[{vp_name.upper()}] no overlaps"
                    + (f" | OVERLAP: {'; '.join(problems)}" if problems else ""),
                    screenshot, start,
                )
            except Exception as e:
                screenshot = await self._screenshot(f"s02_overlap_{vp_name}_error")
                self._record(f"s02_overlap_{vp_name}", "FAIL",
                             f"[{vp_name.upper()}] Exception: {e}", screenshot, start)

    # ── S03: Avatar stays in safe zone (not behind the header, not under the mic) ──

    async def test_s03_avatar_in_safe_zone(self):
        """S03: Avatar must sit between the chat box bottom and the mic button top."""
        for vp_name in VIEWPORTS:
            start = await self._step(f"s03_safezone_{vp_name}")
            try:
                await self._set_viewport(vp_name)
                await self._go("/")

                chat = await self._rect("#chat-area")
                avatar = await self._rect("#avatar-canvas")
                mic = await self._rect("#voice-btn")
                vp = VIEWPORTS[vp_name]

                issues = []
                if not (chat and avatar and mic):
                    issues.append("missing layout anchor")
                else:
                    if avatar["y"] < (chat["y"] + chat["height"]):
                        issues.append("avatar overlaps chat from above")
                    if (avatar["y"] + avatar["height"]) > mic["y"]:
                        issues.append("avatar touches mic from above")
                    # Avatar must be horizontally centered (within 4 % of viewport width)
                    avatar_center = avatar["x"] + avatar["width"] / 2
                    deviation = abs(avatar_center - vp["width"] / 2)
                    if deviation > vp["width"] * 0.04:
                        issues.append(f"avatar off-center by {deviation:.0f}px")

                screenshot = await self._screenshot(f"s03_safezone_{vp_name}")
                status = "FAIL" if issues else "PASS"
                self._record(
                    f"s03_safezone_{vp_name}", status,
                    f"[{vp_name.upper()}] avatar in safe zone"
                    + (f" | ISSUES: {'; '.join(issues)}" if issues else ""),
                    screenshot, start,
                )
            except Exception as e:
                screenshot = await self._screenshot(f"s03_safezone_{vp_name}_error")
                self._record(f"s03_safezone_{vp_name}", "FAIL",
                             f"[{vp_name.upper()}] Exception: {e}", screenshot, start)

    # ── S04: Welcome message shows up ──────────────────────────────────────

    async def test_s04_welcome(self):
        """S04: Alice greets on first load."""
        for vp_name in VIEWPORTS:
            start = await self._step(f"s04_welcome_{vp_name}")
            try:
                await self._set_viewport(vp_name)
                await self._go("/")

                # Greet message arrives ~800ms after VRM loads
                await asyncio.sleep(2)
                msgs = self.page.locator(".msg.alice")
                count = await msgs.count()
                first_text = ""
                if count:
                    first_text = (await msgs.first.text_content() or "").strip()

                issues = []
                if count == 0:
                    issues.append("no welcome message")
                if first_text and len(first_text) < 5:
                    issues.append(f"welcome too short: {first_text!r}")

                screenshot = await self._screenshot(f"s04_welcome_{vp_name}")
                status = "FAIL" if issues else "PASS"
                self._record(
                    f"s04_welcome_{vp_name}", status,
                    f"[{vp_name.upper()}] welcome={first_text[:80]}"
                    + (f" | ISSUES: {'; '.join(issues)}" if issues else ""),
                    screenshot, start,
                )
            except Exception as e:
                screenshot = await self._screenshot(f"s04_welcome_{vp_name}_error")
                self._record(f"s04_welcome_{vp_name}", "FAIL",
                             f"[{vp_name.upper()}] Exception: {e}", screenshot, start)

    # ── S05: Chat round-trip via /api/chat (text input) ────────────────────

    async def test_s05_chat_roundtrip(self):
        """S05: Type → enter → Alice replies (text only, no voice)."""
        start = await self._step("s05_chat_roundtrip_desktop")
        try:
            await self._set_viewport("desktop")
            await self._go("/")
            await asyncio.sleep(2)

            inp = self.page.locator("#text-input")
            await inp.fill("What projects has Eugene built?")
            await inp.press("Enter")
            # Wait up to 30 s for an alice reply newer than the welcome
            for _ in range(30):
                await asyncio.sleep(1)
                count = await self.page.locator(".msg.alice").count()
                if count >= 2:
                    break

            count = await self.page.locator(".msg.alice").count()
            last_reply = ""
            if count:
                last_reply = (await self.page.locator(".msg.alice").last.text_content() or "").strip()

            issues = []
            if count < 2:
                issues.append("no reply received within 30 s")
            if "**" in last_reply:
                issues.append("reply contains raw markdown asterisks")
            screenshot = await self._screenshot("s05_chat_reply")

            status = "FAIL" if issues else "PASS"
            self._record(
                "s05_chat_roundtrip", status,
                f"reply={last_reply[:120]}"
                + (f" | ISSUES: {'; '.join(issues)}" if issues else ""),
                screenshot, start,
            )
        except Exception as e:
            screenshot = await self._screenshot("s05_chat_error")
            self._record("s05_chat_roundtrip", "FAIL", f"Exception: {e}", screenshot, start)

    async def run_all(self, only=None, random_n=None):
        """Run every test_* in order. Returns the recorded results."""
        await self.test_s01_elements_visible()
        await self.test_s02_no_overlap()
        await self.test_s03_avatar_in_safe_zone()
        await self.test_s04_welcome()
        await self.test_s05_chat_roundtrip()
        return self.results
