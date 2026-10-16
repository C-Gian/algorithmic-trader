"""Bundle JSON versionato letto dalla dashboard e tabelle Markdown dei riepiloghi.

Il bundle non contiene orari di esecuzione: a parità di input, convenzioni e software il suo
contenuto è identico. Gli esiti stanno nella sezione separata `retrospective`.
"""

from __future__ import annotations

from . import BUNDLE_SCHEMA, ENGINE_VERSION
from .conventions import Conventions, iso
from .outcomes import study_origins
from .pipeline import columnar
from .summary import MEASURES, RELATIONS, S_STATES, TOTAL


def build_bundle(conv: Conventions, chain: dict, input_manifest: dict, run_ref: dict) -> dict:
    src = conv.section("source")
    return {
        "kind": "OBS001_BUNDLE",
        "schema": BUNDLE_SCHEMA,
        "engineVersion": ENGINE_VERSION,
        "conventions": {"id": conv.raw["id"], "hash": conv.hash, "config": conv.raw},
        "timeUnit": "ms epoch UTC",
        "source": {
            "name": src["name"], "attribution": src["attribution"], "symbol": src["symbol"], "segment": src["segment"],
            "contractType": src["contractType"], "priceType": src["priceType"], "interval": src["interval"],
            "termsUrl": "https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md",
            "note": "Dati per uso personale di ricerca non produttiva; non redistribuire il bundle.",
        },
        "periods": {"inputStart": conv.input_start, "studyStart": conv.study_start, "end": conv.end},
        "run": run_ref,
        "inputQuality": {
            "totals": input_manifest["totals"],
            "files": [
                {k: f[k] for k in ("month", "file", "sha256", "checksumOk", "rows", "duplicatesIdentical", "duplicatesDiscordantMinutes",
                                   "outOfOrder", "outsideMonth", "corruptRows", "coverage")}
                for f in input_manifest["files"]
            ],
            "instrument": input_manifest["instrumentMetadata"].get("instrument"),
        },
        "bars": {"45m": columnar(chain["bars45"]), "1D": columnar(chain["bars1d"])},
        "observations": {"45m": chain["observed"]["45m"], "1D": chain["observed"]["1D"]},
        "events": chain["observed"]["events"],
        "origins": study_origins(conv),
        "retrospective": {
            "label": "A POSTERIORI — seguito retrospettivo, non disponibile al momento dell'origine",
            "rows": chain["rows"],
            "summary": chain["summary"],
        },
    }


def _fmt(x, digits=3):
    return "—" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _month_label(p: str) -> str:
    names = {"2025-09": "Settembre 2025", "2025-10": "Ottobre 2025", "2025-11": "Novembre 2025", "2025-12": "Dicembre 2025", TOTAL: "Totale"}
    return names.get(p, p)


def summary_markdown(summary: dict) -> str:
    """Tabelle prefissate (sezione 6 del task), con arrotondamento solo in visualizzazione."""
    lines: list[str] = []
    tables = summary["tables"]
    periods = summary["periods"]
    lines.append("### Copertura e disponibilità\n")
    lines.append("| Periodo | Origini | Origine valida | A45m valida | Futuro completo | Censurate a destra | Con lacuna | Misure disponibili | Misure mancanti |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for p in periods:
        c = tables[p]["coverage"]
        lines.append(f"| {_month_label(p)} | {c['n']} | {c['originValid']} | {c['aValid']} | {c['futureComplete']} | "
                     f"{c['missingFlags']['RIGHT_CENSORED']} | {c['missingFlags']['GAP']} | {c['measuresAvailable']} | {c['measuresMissing']} |")
    lines.append("\n### Matrice dei conteggi s45 × s1d\n")
    for p in periods:
        m = tables[p]["matrix"]
        lines.append(f"**{_month_label(p)}**\n")
        lines.append("| s45 \\ s1d | " + " | ".join(S_STATES) + " | Totale |")
        lines.append("|---|" + "---:|" * (len(S_STATES) + 1))
        for s in S_STATES:
            lines.append(f"| {s} | " + " | ".join(str(m[s][d]) for d in S_STATES) + f" | {sum(m[s].values())} |")
        lines.append("")
    stat_cols = ["n", "mean", "min", "p10", "p25", "p50", "p75", "p90", "max"]
    header = "| Gruppo | Misura | n | Media | Min | P10 | P25 | Mediana | P75 | P90 | Max |"
    sep = "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"

    def stat_rows(label: str, group: dict) -> list[str]:
        out = []
        for meas in MEASURES:
            s = group["stats"][meas]
            out.append(f"| {label} | {meas} | {s['n']} | " + " | ".join(_fmt(s[k]) for k in stat_cols[1:]) + " |")
        return out

    lines.append("### Sola struttura 45m (unità: A45m all'origine)\n")
    for p in periods:
        lines.append(f"**{_month_label(p)}**\n")
        lines.append("| s45 | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for s in S_STATES:
            g = tables[p]["s45"][s]
            lines.append(f"| {s} | {g['n']} | {g['originValid']} | {g['aValid']} | {g['futureComplete']} | {g['measuresAvailable']} | {g['measuresMissing']} |")
        lines.append("")
        lines.append(header)
        lines.append(sep)
        for s in S_STATES:
            lines.extend(stat_rows(s, tables[p]["s45"][s]))
        lines.append("")
    lines.append("### Struttura 45m UP e DOWN per relazione con la struttura 1D\n")
    lines.append("Confronto entro lo stesso verso s45, mai fra versi diversi. final è firmato nel verso del prezzo anche per DOWN; up/down sono ampiezze non negative, non profitti o perdite.\n")
    for p in periods:
        lines.append(f"**{_month_label(p)}**\n")
        lines.append("| s45 | Relazione 1D | Origini | Origine valida | A valida | Futuro completo | Misure disponibili | Mancanti | Flag mancanti |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|")
        for s in ("UP", "DOWN"):
            for rel in RELATIONS:
                g = tables[p]["relation"][s][rel]
                flags = ", ".join(f"{k} {v}" for k, v in g["missingFlags"].items() if v) or "—"
                lines.append(f"| {s} | {rel} | {g['n']} | {g['originValid']} | {g['aValid']} | {g['futureComplete']} | {g['measuresAvailable']} | {g['measuresMissing']} | {flags} |")
        lines.append("")
        lines.append(header)
        lines.append(sep)
        for s in ("UP", "DOWN"):
            for rel in RELATIONS:
                lines.extend(stat_rows(f"{s} · {rel}", tables[p]["relation"][s][rel]))
        lines.append("")
    ex = summary["examples"]
    lines.append("### Esempi (criterio retrospettivo dichiarato)\n")
    for side in ("UP", "DOWN"):
        e = ex[side]
        lines.append(f"- s45 {side}: prima origine disponibile {iso(e['first']) if e['first'] else '—'}; "
                     f"final più opposto al verso {iso(e['contrary']) if e['contrary'] else '—'}.")
    return "\n".join(lines) + "\n"
