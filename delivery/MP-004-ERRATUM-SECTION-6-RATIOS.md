# MP-004 — erratum of the §6 illustrative ratios (presentation only)

Date: 2026-10-08. Registered under the WP-014 correction (Owner-relayed Director instruction on the Astra review of `0526641`).

**Scope.** This erratum concerns illustrative example numbers only. The authoritative pinned document [MP-004-V05-RETURN-RESPONSE.md](MP-004-V05-RETURN-RESPONSE.md) is **not rewritten**: its bytes, SHA-256 `ddb09102…3c51` and the v0.5 rules identity (`mp004.rules.v0.5` manifest) are unchanged. This file is **not** part of the packaged rules manifest. No rule, threshold or fixture outcome changes.

**What §6 states.** For the valid paths, "circa 1,94 LONG e 2,08 SHORT". For the insufficient-economics rows, "rapporto circa 0,97/0,98".

**Exact values with the inherited predicate.** The predicate is (G − K)/(Q + K), with G = 10⁴·d·(T − p)/p, Q = 10⁴·d·(p − V)/p, K = 14 bps and minimum ratio 1.2. The §6 illustrative geometry is LONG V 990 / T 1050 and SHORT V 1050 / T 990.

| Case | Price | Exact ratio | Decimal | ≥ 1.2 |
|---|---|---|---|---|
| LONG valid | close 1009 | 65979/34021 | 1.939360982922… | yes |
| SHORT valid | close 1031 | 197783/102217 | **1.934932545466…** (not ≈ 2.08) | yes |
| LONG insufficient | close 1019 | 49289/50711 | 0.971958746623… | no |
| SHORT insufficient | close 1021 | 147853/152147 | **0.971777294327…** (≈ 0.97, not 0.98) | no |

Every §6 outcome is unchanged: both valid paths are admissible and both insufficient rows are not. The values are checked in `tests/test_mp004_paths.py::test_mp004_section_6_illustrative_economics_with_the_inherited_predicate`.
