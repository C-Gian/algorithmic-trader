"""WP-009 correction, finding 8 (E2E): a repeated copy can never acknowledge an earlier copy. The shared copy hook
(Workbench report, Market cockpit, diagnostics) gives every click a fresh operation: the button leaves "Copied" at once
("Copying…"), confirms only after that operation's own clipboard write succeeded, a slower superseded operation never
writes stale text nor confirms, and a failed fetch shows "Copy failed" without touching the clipboard.

Causal control: an init script wraps ``fetch`` for the analysis Markdown so each request's delay/body/failure is
scripted by the test (no reliance on timing luck); the assertions read the ACTUAL clipboard contents."""

from __future__ import annotations

import time

import pytest
from playwright.sync_api import expect

from test_ui_smoke import browser, evidence_dir, stack  # noqa: F401

pytestmark = [pytest.mark.e2e, pytest.mark.db]

SCRIPT = """(() => {
  window.__copy = { delays: [], bodies: [], fail: false, served: 0 };
  const orig = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input.url;
    if (!url.includes('/api/adviser/live/analysis.md')) return orig(input, init);
    const c = window.__copy;
    const delay = c.delays.length ? c.delays.shift() : 0;
    const body = c.bodies.length ? c.bodies.shift() : null;
    const fail = c.fail;
    await new Promise((r) => setTimeout(r, delay));
    c.served += 1;
    if (fail) return new Response('unavailable', { status: 503 });
    if (body !== null) return new Response(body, { status: 200, headers: { 'content-type': 'text/markdown' } });
    return orig(input, init);
  };
})();"""


def _clip(page) -> str:
    return page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")


def test_repeated_copies_confirm_only_their_own_completed_write(stack, browser):  # noqa: F811
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    ctx.add_init_script(SCRIPT)
    page = ctx.new_page()
    page.goto(f"{stack.base}/#overview")
    btn = page.get_by_test_id("copy-analysis")
    expect(btn).to_be_visible(timeout=20_000)

    # 1. a first copy completes: the actual clipboard holds its content
    page.evaluate("() => { window.__copy.bodies.push('ONE'); }")
    btn.click()
    expect(btn).to_contain_text("Copied")
    assert _clip(page) == "ONE"

    # 2. a second, delayed copy: the earlier "Copied" is withdrawn at once and only the new write confirms
    page.evaluate("() => { window.__copy.delays.push(1200); window.__copy.bodies.push('TWO'); }")
    btn.click()
    expect(btn).to_contain_text("Copying")
    assert _clip(page) == "ONE"  # nothing confirmed while the new operation is pending
    expect(btn).to_contain_text("Copied", timeout=10_000)
    assert _clip(page) == "TWO"

    # 3. out-of-order completions: a slow first click is superseded by a fast second click
    page.evaluate("() => { window.__copy.delays.push(1500, 0); window.__copy.bodies.push('SLOW-OLD', 'FAST-NEW'); }")
    btn.click()
    btn.click()
    expect(btn).to_contain_text("Copied", timeout=10_000)
    page.wait_for_function("() => window.__copy.served >= 4", timeout=10_000)
    time.sleep(0.3)
    assert _clip(page) == "FAST-NEW"  # the superseded slower response never overwrote it
    expect(btn).to_contain_text("Copied")

    # 4. a failed fetch: explicit failure, clipboard untouched
    page.evaluate("() => { window.__copy.fail = true; }")
    btn.click()
    expect(btn).to_contain_text("Copy failed", timeout=10_000)
    assert _clip(page) == "FAST-NEW"
    ctx.close()
