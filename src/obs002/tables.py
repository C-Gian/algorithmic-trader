"""Tabelle Markdown del report OBS-002 generate da summary.json (arrotondamento solo in visualizzazione)."""

from __future__ import annotations

from obs001.conventions import iso

from .outcomes import CLASSES
from .population import PROFILES

SIDES = ("LONG", "SHORT")
COLS = ("ALL",) + PROFILES
LABEL = {"ALL": "Tutti", "CONCORDANT": "CONCORDANT", "OPPOSITE": "OPPOSITE", "DISCORDANT": "DISCORDANT", "UNAVAILABLE": "UNAVAILABLE"}
CLASS_SHORT = {"F_ONLY": "F", "A_ONLY": "A", "F_BEFORE_A": "F→A", "A_BEFORE_F": "A→F", "BOTH_UNORDERED": "F=A", "NEITHER": "nessuno"}
CONT = [("depth", "Profondità dell'arretramento"), ("LoverA", "L / A"), ("toP1OverA", "Distanza residua a P1 / A"),
        ("toRextOverA", "Distanza a Rext / A"), ("AoverC", "A / C"), ("nearestAheadOverA", "Livello più vicino davanti / A"),
        ("nearestBehindOverA", "Livello più vicino dietro / A"), ("dSmaDist", "d·(SMA20−SMA50)/A"), ("dSmaSlope", "d·pendenza SMA20 / A"),
        ("dSmaPos", "d·(C−SMA20)/A"), ("volumeRatio", "Volume relativo"), ("fibR", "Fibonacci r effettivo")]
CATS = [("structure1D", "Struttura 1D"), ("nearestAheadKind", "Tipo del livello davanti"), ("nearestBehindKind", "Tipo del livello dietro"),
        ("levelAtC", "Livello esattamente a C"), ("crossRelative", "Incrocio SMA alla barra"), ("fibRelation", "Ancore Fibonacci vs movimento"),
        ("fibSameAsContext", "Ancore Fibonacci = contesto")]


def contact_breakdown(classes: dict) -> dict:
    """R1-C: scomposizione aritmetica delle classi di un insieme di esiti completi.
    Entrambi i riferimenti = F→A + A→F + F=A; uno solo = F + A; nessuno = NEITHER. «Almeno uno» non è «entrambi»."""
    both = classes["F_BEFORE_A"] + classes["A_BEFORE_F"] + classes["BOTH_UNORDERED"]
    one = classes["F_ONLY"] + classes["A_ONLY"]
    none = classes["NEITHER"]
    total = both + one + none
    if total != sum(classes.values()):
        raise AssertionError("classi non riconosciute nella scomposizione dei contatti")
    share = (lambda n: n / total) if total else (lambda n: None)  # noqa: E731
    return {"complete": total, "both": both, "oneOnly": one, "none": none, "atLeastOne": both + one,
            "shares": {"both": share(both), "oneOnly": share(one), "none": share(none), "atLeastOne": share(both + one)}}


def f(x, d=2) -> str:
    return "—" if x is None else f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def q(s: dict, d=2) -> str:
    return "n=0" if not s["n"] else f"{f(s['p50'], d)} [{f(s['p10'], d)}; {f(s['p90'], d)}]"


def pct(n: int, tot: int) -> str:
    return "—" if not tot else f"{n * 100 / tot:.0f}%"


def main_table(des: dict) -> list[str]:
    L = ["| Verso | Profilo | Tentativi | Gruppi | Completi | Censurati / lacune / A mancante / A zero | "
         + " | ".join(CLASS_SHORT[c] for c in CLASSES) + " | final P50 [P10; P90] | favorevole | contrario |",
         "|---|---|---:|---:|---:|---|" + "---:|" * len(CLASSES) + "---|---|---|"]
    for side in SIDES:
        for p in COLS:
            c = des[side][p]
            mf = c["missingFlags"]
            L.append(f"| {side} | {LABEL[p]} | {c['attempts']} | {c['groups']} | {c['complete']} | "
                     f"{mf['RIGHT_CENSORED']} / {mf['GAP']} / {mf['MISSING_A']} / {mf['ZERO_A']} | "
                     + " | ".join(str(c["classes"][k]) for k in CLASSES)
                     + f" | {q(c['final'])} | {q(c['favourable'])} | {q(c['adverse'])} |")
    return L


def coordinates_table(des: dict, side: str) -> list[str]:
    cells = [des[side][p] for p in COLS]
    L = [f"| {side}: coordinata all'origine | " + " | ".join(f"{LABEL[p]} (n={c['attempts']})" for p, c in zip(COLS, cells)) + " |",
         "|---|" + "---|" * len(COLS)]
    for key, label in CONT:
        row = []
        for c in cells:
            x = c["coordinates"].get(key)
            if not c["attempts"]:
                row.append("—")
                continue
            miss = sum(x["missing"].values())
            row.append(q(x, 4 if key == "AoverC" else 2) + (f" · mancanti {miss}" if miss else ""))
        L.append(f"| {label} | " + " | ".join(row) + " |")
    for key, label in CATS:
        row = []
        for c in cells:
            cnt = c["categories"].get(key, {})
            tot = sum(cnt.values())
            row.append("—" if not tot else " · ".join(f"{k} {v} ({pct(v, tot)})" for k, v in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))))
        L.append(f"| {label} | " + " | ".join(row) + " |")
    return L


def periods_table(periods: dict) -> list[str]:
    L = ["| Periodo | Verso | Tentativi | CONC / OPP / DISC / UNAV | Completi | " + " | ".join(CLASS_SHORT[c] for c in CLASSES)
         + " | final P50 [P10; P90] | favorevole P50 | contrario P50 |",
         "|---|---|---:|---|---:|" + "---:|" * len(CLASSES) + "---|---:|---:|"]
    for name, des in periods.items():
        for side in SIDES:
            c = des[side]["ALL"]
            prof = " / ".join(str(des[side][p]["attempts"]) for p in PROFILES)
            fp, ap = c["favourable"], c["adverse"]
            L.append(f"| {name} | {side} | {c['attempts']} | {prof} | {c['complete']} | " + " | ".join(str(c["classes"][k]) for k in CLASSES)
                     + f" | {q(c['final'])} | {f(fp['p50']) if fp['n'] else 'n=0'} | {f(ap['p50']) if ap['n'] else 'n=0'} |")
    return L


def flow_table(fl: dict) -> list[str]:
    a, v, g, e = fl["attempts"], fl["versions"], fl["groups"], fl["eventOutcomes"]
    rows = [
        ("Eventi FIB_SEQUENCE (APPEND / REPLACE / KEEP), input", " / ".join(str(fl["fibEvents"]["input"].get(k, 0)) for k in ("APPEND", "REPLACE", "KEEP"))),
        ("Esito degli eventi, input", " · ".join(f"{k} {n}" for k, n in e["input"].items())),
        ("Esito degli eventi, DEV", " · ".join(f"{k} {n}" for k, n in e["dev"].items())),
        ("Versioni create (input / con disponibilità in DEV)", f"{v['input']} / {v['dev']}"),
        ("Versioni per motivo di ritiro (input)", " · ".join(f"{k} {n}" for k, n in v["byRetireReason"].items())),
        ("Versioni senza alcun tentativo (input / DEV)", f"{v['withoutAttempt']} / {v['devWithoutAttempt']}"),
        ("Gruppi (input) · iniziati prima del DEV", f"{g['input']} · {g['startedBeforeStudy']}"),
        ("Gruppi senza alcun tentativo (input)", str(g["withoutAnyAttempt"])),
        ("Gruppi attivi in DEV · senza tentativo DEV", f"{g['activeInDev']} · {g['activeInDevWithoutDevAttempt']}"),
        ("Gruppi con tentativo DEV · di cui iniziati prima del DEV", f"{g['withDevAttempt']} · {g['withDevAttemptStartedBeforeStudy']}"),
        ("Tentativi: input / inizializzazione / DEV", f"{a['input']} / {a['initialization']} / {a['dev']}"),
        ("Tentativi DEV: primi (ordinal 1) / ripetuti", f"{a['devPrimary']} / {a['devRepeated']}"),
        ("Ripetuti DEV con tentativi precedenti nell'inizializzazione", str(a["devRepeatedAfterInitializationAttempts"])),
        ("Primi tentativi DEV per verso", " · ".join(f"{k} {n}" for k, n in a["devPrimaryBySide"].items())),
        ("Tentativi DEV per ordinal (5 = 5 o più)", " · ".join(f"{k}: {n}" for k, n in a["devByOrdinal"].items())),
    ]
    return ["| Voce | Valore |", "|---|---|"] + [f"| {k} | {x} |" for k, x in rows]


def report_tables(summary: dict, sel: dict) -> str:
    L = ["### Flusso della popolazione\n"] + flow_table(summary["flow"])
    dep = summary["dependence"]
    L += ["", "### Dipendenza", "",
          f"- Primi tentativi DEV: {dep['primaryOverlap']['attempts']}, di cui con finestra 24h sovrapposta ad almeno un altro: "
          f"{dep['primaryOverlap']['overlappingAnother']}; massimo di finestre contemporanee {dep['primaryOverlap']['maxConcurrentWindows']}.",
          f"- Tutti i tentativi DEV: {dep['allDevOverlap']['attempts']}, sovrapposti {dep['allDevOverlap']['overlappingAnother']}, "
          f"massimo contemporanee {dep['allDevOverlap']['maxConcurrentWindows']}.",
          f"- Gruppi con tentativi DEV: {dep['devGroups']}; tentativi per gruppo: " + " · ".join(f"{k}: {n}" for k, n in dep["devAttemptsPerGroup"].items()) + "."]
    L += ["", "### Tabella principale: primi tentativi DEV (ordinal 1), verso × profilo congiunto\n",
          "Classi di contatto ±A: F = solo favorevole, A = solo contrario, F→A / A→F = ordine a risoluzione 1m, F=A = stesso minuto non ordinabile, "
          "nessuno = finestra completa senza contatti. final, favorevole, contrario in unità di A all'origine.\n"] + main_table(summary["main"])
    for side in SIDES:
        L += ["", f"### Profilo simultaneo delle coordinate, {side} (primi tentativi DEV)\n",
              "P50 [P10; P90]; categorie con conteggio e quota sulla cella. Distanze firmate d·(livello − C)/A: positive davanti nel verso del movimento.\n"]
        L += coordinates_table(summary["main"], side)
    L += ["", "### Periodi (primi tentativi)\n"] + periods_table(summary["periods"])
    L += ["", "### Mesi (primi tentativi, mese dell'origine)\n"] + periods_table(summary["months"])
    L += ["", "### Riepilogo secondario: tutti i tentativi DEV, collegati e dipendenti\n"] + main_table(summary["secondary"]["DEV"])
    L += ["", "### Esempi (regola del task §6)\n", "| # | Tentativo | Origine UTC | Verso | Profilo | Ordinal | Categorie |", "|---:|---|---|---|---|---:|---|"]
    for n, c in enumerate(sel["cases"], 1):
        L.append(f"| {n} | `{c['attemptId']}` | {iso(c['t']).replace('T', ' ')[:16]} | {c['side']} | {c['profile']} | {c['ordinal']} | {', '.join(c['categories'])} |")
    L.append("")
    L.append("Categorie vuote: " + (", ".join(sel["emptyCategories"]) or "nessuna") + ".")
    return "\n".join(L) + "\n"
