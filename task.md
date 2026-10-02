# Active Task — WP-008-R1B correction

Status: **READY — ONLY ACTIVE IMPLEMENTATION PACKAGE**
Date: 2026-10-02
Implementation under review: `464f449e5961e240eab588876d21ab1bdd444145`.

Correct all findings in `delivery/WP-008-R1B-DIRECTOR-REVIEW.md` under AGENTS.md and the accepted SR-003 disposition. Preserve the implemented sequential kernel, sparse fenced checkpoint commits, direct restore, reconciliation labels and committed-prefix inspection.

## Required outcomes

1. Bound working memory and file descriptors across cold preparation, including long gaps, unsorted Parquet, recorded first-completion deduplication/exclusions/lifecycle, request-log verification and external-sort merge. Exact disk-backed indexes/external passes are allowed. Preserve reference event identities, order, admission, gap classifications and row provenance. Add progress/control hooks in scans and no-yield work; document configured block/fan-in/index limits and any small administrative metadata growth.
2. Establish an enforced verified-byte boundary between cold source verification and normalization/publication. Mutations after verification, including unchanged source-manifest cases, must not become verified cache evidence. Protect relevant manifest/config/report inputs too. Avoid routine duplicate original-source verification on warm launches; define the actual trusted snapshot/consumption mechanism.
3. Give fresh warm launches a trusted cache-manifest integrity root beyond the mutable manifest's own source/version key. Detect compatible metadata corruption before accepting source facts/feed identity/partition hashes/commitments. Preserve existing run pins, concurrent publication and quarantine/rebuild diagnostics. Make receipt/reference publication crash-consistent with durably published cache files and test its boundaries.

## Required verification

Implement the correction acceptance fixtures and measurements in the Director review. Include increasing gap/shuffled/recorded-duplicate/raw-page fixtures and enough sort runs to cross the configured fan-in; exact differential identities and bounded collection/descriptor counts; memory measured with RSS where supported and Python heap separately; cancellation during long no-yield work; source mutation immediately after verification with unchanged manifest; compatible cache-manifest alteration on a NEW warm run. Existing resume pins and partition-only corruption tests remain required.

These are short/medium synthetic or captured engineering fixtures. Retain checkpoint/CAS/generation/fallback/API/report/E2E and schema compatibility checks. Report actual results and residual limits; no month/year performance claim from short fixtures.

## Boundary and exit

This remains R1B, not R1C, R2 or adviser work. No real September retry, acquisition, old-run salvage, method/P&L evaluation or external platform. Frozen schemas/evidence semantics remain unchanged unless the existing versioned operational extension rules require a documented compatible addition.

Finish with **READY FOR DIRECTOR REVIEW — R1B CORRECTION ONLY**.
**NOT READY FOR OWNER MARKET REPLAY.**
