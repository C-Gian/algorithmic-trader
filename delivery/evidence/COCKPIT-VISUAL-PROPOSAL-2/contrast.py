"""WCAG 2.x contrast of the second proposal's colour pairs, on the actual backgrounds (soft tints composited).

Token values from web/src/styles/tokens.css; fills and inks from the draft (draft-ui.patch). Text needs 4.5:1 (AA, normal
text); graphic objects (candles, level lines, band edges) need 3:1 (WCAG 1.4.11).
Usage: uv run python delivery/evidence/COCKPIT-VISUAL-PROPOSAL-2/contrast.py
"""

from __future__ import annotations

import json
from pathlib import Path


def rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def over(fg: str, alpha: float, bg: str) -> str:
    f, b = rgb(fg), rgb(bg)
    return "#" + "".join(f"{round((alpha * x + (1 - alpha) * y) * 255):02x}" for x, y in zip(f, b))


def lum(h: str) -> float:
    def ch(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


T = {"surface": "#11161e", "surface2": "#151b25", "surface3": "#1b2230", "bg": "#0a0d12", "text": "#e9ecf2",
     "text2": "#b1b9c7", "text3": "#7c8697", "pos": "#43c890", "neg": "#f07470", "warn": "#f19a55", "info": "#6cb6e0",
     "neutral": "#9aa4b5", "pending": "#8ea3c7"}
PAIRS = [  # (what, foreground, background, kind)
    ("Ingresso disponibile: ink on blue fill", "#06121a", T["info"], "text"),
    ("Non verificabile: ink on amber fill", "#1c0f04", T["warn"], "text"),
    ("Neutral state (attesa / chiuso / conclusa): text-2 on surface-3", T["text2"], T["surface3"], "text"),
    ("LONG chip: ink on green fill", "#07140e", T["pos"], "text"),
    ("SHORT chip: ink on red fill", "#1a0706", T["neg"], "text"),
    ("Concluded chip: grey on panel", T["neutral"], T["surface2"], "text"),
    ("Recognised guidance: text on surface-3", T["text"], T["surface3"], "text"),
    ("Technical badge: blue on its soft tint over the panel", T["info"], over(T["info"], 0.12, T["surface2"]), "text"),
    ("Technical badge: blue on its soft tint over a card", T["info"], over(T["info"], 0.12, T["surface"]), "text"),
    ("Session-not-current chip: amber on its soft tint", T["warn"], over(T["warn"], 0.12, T["surface2"]), "text"),
    ("Neutral notice (alerts): text-2 on neutral tint over the page", T["text2"], over(T["neutral"], 0.10, T["bg"]), "text"),
    ("Timeline LONG: green on card", T["pos"], T["surface"], "text"),
    ("Timeline SHORT: red on card", T["neg"], T["surface"], "text"),
    ("Market reading expected direction Rialzo: green on page", T["pos"], T["bg"], "text"),
    ("Market reading expected direction Ribasso: red on page", T["neg"], T["bg"], "text"),
    ("Secondary notes: text-3 on panel", T["text3"], T["surface2"], "text"),
    ("Chart legend / ticks: text-3 on card", T["text3"], T["surface"], "text"),
    ("Chart label 'fascia ammessa ora': blue on card", T["info"], T["surface"], "text"),
    ("Chart: rising candle (green) on card", T["pos"], T["surface"], "graphic"),
    ("Chart: falling candle (red) on card", T["neg"], T["surface"], "graphic"),
    ("Chart: target/stop line (text colour) on card", T["text"], T["surface"], "graphic"),
    ("Chart: support/resistance dashed (neutral) on card", T["neutral"], T["surface"], "graphic"),
    ("Chart: box dotted (pending) on card", T["pending"], T["surface"], "graphic"),
    ("Chart: admissible band edge (blue) on card", T["info"], T["surface"], "graphic"),
    ("Chart: rising candle on the admissible band", T["pos"], over(T["info"], 0.22, T["surface"]), "graphic"),
    ("Chart: falling candle on the structural-area tint", T["neg"], over("#cdb27a", 0.10, T["surface"]), "graphic"),
]


def main() -> None:
    rows = []
    for what, fg, bg, kind in PAIRS:
        r = ratio(fg, bg)
        need = 4.5 if kind == "text" else 3.0
        rows.append({"pair": what, "fg": fg, "bg": bg, "kind": kind, "ratio": r, "required": need, "pass": r >= need})
    out = Path(__file__).resolve().parent / "contrast.json"
    out.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    for x in rows:
        print(f"{x['ratio']:>6}  {'PASS' if x['pass'] else 'FAIL'}  ({x['required']})  {x['pair']}")


if __name__ == "__main__":
    main()
