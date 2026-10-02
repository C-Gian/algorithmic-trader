# WP-008-R1B Director review

Date: 2026-10-02
Reviewed implementation: `464f449e5961e240eab588876d21ab1bdd444145`.
Base: `17b57206d46d1950f55f383506718ef0043171f8`.
Decision: **CHANGES REQUIRED — R1B ONLY**. R1C and Owner September replay remain inactive.

## Evidence and retained implementation

Independently inspected GitHub Actions run `37052483628`: checks SUCCESS and compose-smoke SUCCESS. The executor reports 348 non-E2E + 10 E2E tests; these counts and the Windows fixture timings were not independently rerun. Schema-related files have no diff from the base. The Director inspected cache/preparation, dataset and recorded adapters, kernel, checkpoint/restore, reconciliation and regression fixtures. No Owner database, dataset or live stack was accessed; no full local suite or historical evaluation ran.

Retain the implemented sequential accepted reducer, sparse fenced checkpoint/range transactions, direct state restore, explicit reconciliation scope, committed-prefix endpoints and old-run suspension/readers. The short differential/fault evidence is useful. However the following requirements are part of R1B, not optional limitations deferred to R1C.

## 1. Input preparation is not bounded by working-block limits

`feed/adapter.py:_absent_slots` retains every absent minute; `_absent_slots_unordered` retains every present row plus absent minutes; `_absent_slot_classes` retains missing-key classifications/raw variants. `recorder/feed_bridge.py:RecordedStream.events` retains one de-duplication key per completed slot and all exclusions, and materializes lifecycle records. `marketdata/dataset.py:verify` materializes the entire request log/page-reference list. These structures grow with source length or gap length, even if clean short fixtures show a stable Python heap. Semantic exactness does not require an unbounded RAM set: exact disk-backed indexes/external passes are allowed.

`observe/feedcache.py:ExternalSorter.merged` also opens every spill run concurrently. Independent execution of the actual extracted sorter with 20 records/block size 2 opened 10 spill files at once. At larger inputs this grows without a configured fan-in bound, affecting descriptors and gzip/text buffering. Use a bounded multi-pass merge; bound associated metadata or state the small administrative index budget honestly.

Correct these admitted source paths without dropping evidence, altering first-completed-receipt wins, gap classification, original row provenance or identities. Include cooperative progress/control hooks in scans, spill/merge, deduplication and gap classification, including long stretches yielding no events. A 1-day versus 4-day clean-source tracemalloc comparison does not prove the affected paths bounded and does not measure native Arrow allocations.

## 2. Cold verification does not pin the bytes subsequently normalized

`prepare_stream_source` hashes the manifest, calls verify on original files, then reopens those same mutable files via `dataset_feed_meta`, `iter_dataset_events` or `RecordedStream`. There is no protected verified snapshot or equivalent guarantee tying later reads to the verified bytes. A mutation after VERIFYING_SOURCE and before/during BUILDING_FEED can therefore be normalized and published under the original source-manifest key. Partition hashes authenticate the resulting cache bytes, not their equality to the previously verified source.

Establish a concrete enforced preparation trust boundary. A private verified snapshot, hash-checked stable consumption, or an equally justified mechanism is acceptable; source path/mtime/normal application conventions alone are insufficient. Do not solve this by routinely re-running the whole original verification on warm cache launches. Define what remains trusted after preparation and preserve the verify-once objective within that actual boundary. Fault-test a source data-file mutation after successful verification with an unchanged source manifest, plus mutation of manifest/config/report inputs during preparation. No cache may be published as verified from unverified replacement bytes.

## 3. New warm runs do not have a trusted cache-manifest pin

`prepare_stream_source` opens a warm cache with `open_cache(root, cid, key)` and no expected manifest SHA. The key authenticates the source-manifest/version tuple, but does not commit to feed_manifest, source_facts, partitions or final_commitment. `open_cache` accepts compatible JSON changes to those fields and the new run then pins the changed manifest. Existing resumed runs have a DB engine pin; that does not protect a fresh warm launch.

Independent execution of the actual extracted cache-open/key functions accepted a changed source_facts quality field while format, source key and cache_id stayed unchanged; the manifest SHA changed without rejection. This is an open-path regression probe, not a full DB/replay integration test. The existing tampering fixture changes format to an incompatible version, so it does not cover compatible manifest alteration.

Anchor published cache metadata to a trusted preparation receipt/persistent pin or another explicit integrity root outside the mutable manifest itself; validate that root on every warm launch before accepting its facts/partition hashes. Protect first publication, concurrent builders and resumed-run pins. Establish the trusted receipt only after the referenced cache files/metadata have been durably published on the supported volume; a directory rename alone is not sufficient evidence. Exercise crashes around file publication and receipt/reference commit. Detect/quarantine compatible metadata corruption; do not merely take a new SHA of whatever is present. Add tests changing compatible source_facts/feed metadata, partition hash metadata and final commitments without changing the source key. Partition-only corruption and source-manifest changes must remain covered. No new cryptographic signing service is needed.

## Correction acceptance evidence

Keep existing differential, checkpoint/CAS/generation, restore/fallback, cancellation, inspection and compatibility tests. Add deterministic offline fixtures with increasing long gaps, shuffled Parquet, many repeated recorded completions/exclusions/raw pages, and enough spills to cross a configured merge fan-in. Verify exact reference identities/order/slot classification and bounded in-memory cardinalities/open descriptors. Report peak RSS when supported alongside Python heap; distinguish metadata proportional to partitions from evidence collections proportional to events. Instrument configured limits and cancellation during no-yield work.

Add the post-verification source-mutation and compatible warm-manifest corruption fixtures described above. Demonstrate that the rejected bytes are not applied and no falsely verified cache/run completes. Preserve R1A bounded diagnostics and cold/warm identity parity. Run required existing checks and CI on isolated services under AGENTS.md. No real September/month/year replay or acquisition is needed to close these defects.

## Correction review and closure — 2026-10-02

Correction: `9d814ec957e17fc33c1fcfbfb96034844e416444`, base `418d033495da4bfd3f047f9c6b7f69e6c665d5d4`.
Final decision: **ACCEPTED — R1B structural slice only**. The CHANGES REQUIRED decision above remains the historical review of `464f449`.

The Director inspected private source snapshot/verification/normalization, PostgreSQL receipt publication and warm matching, deterministic cache manifests/fsync ordering, bounded multi-pass merge, disk-backed gap/dedup paths, incremental request-log verification and the new corruption/mutation/crash fixtures. These close the three R1B findings. Independently confirmed CI `37065434955`: checks SUCCESS and compose-smoke SUCCESS. Executor reports 366 non-E2E + 10 E2E and the process-isolated memory figures; the Director did not rerun those suites or Windows memory measurements. No schema-related diff from the correction base.

An independent stdlib execution of the actual extracted ExternalSorter on 100 records/block2/fan-in3 passed sorted output and maximum-open-run limits: 75 runs created, 3 merge passes, maximum 3 open runs and 2 buffered records. No Owner database/dataset/live stack was used.

R1B acceptance is not month/year performance or universal control-latency acceptance. Snapshot copy still hooks between files (copy buffers alone are not cancellation hooks); large-file copy/hashing, no-yield scans and publication boundaries require representative control measurements in R1C. Partition/file metadata and disk storage scale with source size and are disclosed. Windows has no directory-fsync guarantee; receipts expose this limit. R1C must verify safe failure/rebuild after lost cache files and preserve that qualification, rather than claim proven Windows power-loss durability.

R1C is now activated by task.md. Owner September replay remains blocked pending Director release review.
