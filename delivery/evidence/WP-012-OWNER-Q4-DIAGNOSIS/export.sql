\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT jsonb_build_object('meta', jsonb_build_object('transaction_read_only', current_setting('transaction_read_only'),
  'isolation', current_setting('transaction_isolation'), 'snapshot', pg_current_snapshot()::text,
  'server_time', now(), 'server_version', current_setting('server_version')))::text;
SELECT jsonb_build_object('evaluation', to_jsonb(e))::text FROM evaluations e WHERE evaluation_id IN
 ('eval-20261007T094006-67272e','eval-20261007T102821-ae14be','eval-20261007T105636-6d9276',
  'eval-20261006T175135-9ddf6d','eval-20261007T101912-087dd1','eval-20261007T105343-eb536a') ORDER BY evaluation_id;
SELECT jsonb_build_object('replay', to_jsonb(r))::text FROM observation_replays r WHERE replay_id IN
 (SELECT replay_id FROM evaluations WHERE evaluation_id IN
 ('eval-20261007T094006-67272e','eval-20261007T102821-ae14be','eval-20261007T105636-6d9276',
  'eval-20261006T175135-9ddf6d','eval-20261007T101912-087dd1','eval-20261007T105343-eb536a')) ORDER BY replay_id;
SELECT jsonb_build_object('checkpoint', jsonb_build_object('replay_id', replay_id, 'cursor', cursor, 'info_time', info_time,
  'last_event_id', last_event_id, 'snapshot_id', snapshot_id, 'snapshot_digest', snapshot_digest, 'updated_at', updated_at,
  'adviser_view', adviser_view))::text FROM observation_checkpoints WHERE replay_id IN
 (SELECT replay_id FROM evaluations WHERE evaluation_id IN
 ('eval-20261007T094006-67272e','eval-20261007T102821-ae14be','eval-20261007T105636-6d9276',
  'eval-20261006T175135-9ddf6d','eval-20261007T101912-087dd1','eval-20261007T105343-eb536a')) ORDER BY replay_id;
SELECT jsonb_build_object('finish', to_jsonb(f) - 'adviser_blob')::text FROM adviser_finish f WHERE run_id IN
 (SELECT replay_id FROM evaluations WHERE evaluation_id IN
 ('eval-20261007T094006-67272e','eval-20261007T102821-ae14be','eval-20261007T105636-6d9276',
  'eval-20261006T175135-9ddf6d','eval-20261007T101912-087dd1','eval-20261007T105343-eb536a')) ORDER BY run_id;
SELECT jsonb_build_object('pack', to_jsonb(p))::text FROM corpus_packs p WHERE pack_id IN
 ('pack-30c0661ff5dc7b746f821ceb5efeda0702f33f30','pack-47ef402225143c1770129b3d8c0dc03a67928160','pack-bb3e895bab96fb3c740d7263a20dbba2e5c866b1');
SELECT jsonb_build_object('cache', to_jsonb(c))::text FROM observation_feed_caches c WHERE cache_id IN
 ('fc-de5aa4a9d5260d3cfdb135be2d0a90001d6c835f','fc-83bba3018d80145ce65be63d7168efb104d16a49','fc-29ae65c99d81b1d1307c642d14a75cd5fce5d0ef');
SELECT jsonb_build_object('j', jsonb_build_object('run_id', run_id, 'seq', seq, 'kind', kind, 'record_id', record_id,
  'clock_time', clock_time, 'professional_seq', professional_seq, 'factual_cursor', factual_cursor, 'origin', origin,
  'subject', subject, 'digest', digest, 'chain', chain, 'record', record, 'generation', generation))::text
 FROM adviser_journal WHERE run_id IN
 (SELECT replay_id FROM evaluations WHERE evaluation_id IN
 ('eval-20261007T094006-67272e','eval-20261007T102821-ae14be','eval-20261007T105636-6d9276',
  'eval-20261006T175135-9ddf6d','eval-20261007T101912-087dd1','eval-20261007T105343-eb536a')) ORDER BY run_id, seq;
SELECT jsonb_build_object('er', jsonb_build_object('run_id', run_id, 'seq', seq, 'kind', kind, 'record_id', record_id,
  'digest', digest, 'chain', chain, 'record', record, 'generation', generation))::text
 FROM adviser_evaluation_records WHERE run_id IN
 (SELECT replay_id FROM evaluations WHERE evaluation_id IN
 ('eval-20261007T094006-67272e','eval-20261007T102821-ae14be','eval-20261007T105636-6d9276',
  'eval-20261006T175135-9ddf6d','eval-20261007T101912-087dd1','eval-20261007T105343-eb536a')) ORDER BY run_id, seq;
COMMIT;
