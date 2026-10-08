# MP-004 — Director methodological closure
Date: 2026-10-08. Specification: [MP-004-V05-RETURN-RESPONSE.md](MP-004-V05-RETURN-RESPONSE.md), SHA-256 `ddb09102cf31e31336dcfb440aea20dad01381b0e0dd769c206b212e39103c51` (registered byte-identical to the file attached to the Owner's activation). Semantic base: v0.4 at `776752e10b4153900647004cab305a0a6a29e0c6`.
Owner-relayed Director closure, recorded verbatim (activation of WP-014, 8 October 2026):

> Attivo WP-014 — implementazione del candidato v0.5 secondo MP-004-V05-RETURN-RESPONSE allegata, chiusa metodologicamente dal Director.
>
> La chiusura approva la semantica candidata, non efficacia economica.
> Sono accettati entrambi i raccordi del §8:
> - contatto locale a cavallo della pubblicazione → UNASSESSABLE, senza rinnovo;
> - prima ripresa osservata tardivamente e non più corrente → valutazione non emettibile, senza cercare una barra successiva.

## What the closure decides

- MP-004 §§1–7 are the authoritative candidate semantics of `btc.context-action.v0.5`: only the A RETURN child changes (first usable RETURN prepares one immutable local reference; a later complete 1m local recovery is then required; one reference, no replacement, every intermediate bar checked, first recovery consumed once).
- Both §8 joints are accepted as written. They are not tolerances and not evidence of effectiveness; a later wish to wait for further bars in those cases reopens the first-attempt/causality decision explicitly (MP-004 §8), it is never an implicit fallback.
- The closure approves candidate semantics only. Economic usefulness, frequency and profitability remain UNVALIDATED. C (MP-004 §8) stays a distinct alternative, not an automatic fallback.

## What it does not decide

- No numerical threshold is added or changed (MP-004 §8). The executor-derived register [MP-004-PARAMETERS.json](MP-004-PARAMETERS.json) keeps every inherited MP-003 value and names the MP-004 categorical delta; it is submitted with WP-014 for Director review, not pre-approved by this closure.
- No Owner economic run is activated. The continuous v0.4/v0.5 comparison is prepared INACTIVE in WP-014 and launched by the Owner only from the app after technical acceptance and green exact-SHA CI.
