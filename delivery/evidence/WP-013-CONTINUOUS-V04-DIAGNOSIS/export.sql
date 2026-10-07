\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT jsonb_build_object('meta', jsonb_build_object('transaction_read_only', current_setting('transaction_read_only'),
  'isolation', current_setting('transaction_isolation'), 'snapshot', pg_current_snapshot()::text,
  'server_time', now(), 'server_version', current_setting('server_version')))::text;
SELECT jsonb_build_object('evaluation', to_jsonb(e))::text FROM evaluations e WHERE evaluation_id = 'eval-20261007T182934-3f41ad';
SELECT jsonb_build_object('replay', to_jsonb(r))::text FROM observation_replays r WHERE replay_id = 'obs-20261007T182934-f8c3d4';
SELECT jsonb_build_object('checkpoint', jsonb_build_object('replay_id', replay_id, 'cursor', cursor, 'info_time', info_time,
  'last_event_id', last_event_id, 'snapshot_id', snapshot_id, 'snapshot_digest', snapshot_digest, 'updated_at', updated_at,
  'adviser_view', adviser_view))::text FROM observation_checkpoints WHERE replay_id = 'obs-20261007T182934-f8c3d4';
SELECT jsonb_build_object('finish', to_jsonb(f) - 'adviser_blob')::text FROM adviser_finish f WHERE run_id = 'obs-20261007T182934-f8c3d4';
SELECT jsonb_build_object('pack', to_jsonb(p))::text FROM corpus_packs p WHERE pack_id = 'pack-1ae7d36c20adbde0a468a7e0f6d8750a9951aa8e';
SELECT jsonb_build_object('cache', to_jsonb(c))::text FROM observation_feed_caches c WHERE cache_id IN
  (SELECT r.engine->>'cache_id' FROM observation_replays r WHERE replay_id = 'obs-20261007T182934-f8c3d4'
   UNION SELECT r.source_id FROM observation_replays r WHERE replay_id = 'obs-20261007T182934-f8c3d4');
SELECT jsonb_build_object('j', jsonb_build_object('run_id', run_id, 'seq', seq, 'kind', kind, 'record_id', record_id,
  'clock_time', clock_time, 'professional_seq', professional_seq, 'factual_cursor', factual_cursor, 'origin', origin,
  'subject', subject, 'digest', digest, 'chain', chain, 'record', record, 'generation', generation))::text
 FROM adviser_journal WHERE run_id = 'obs-20261007T182934-f8c3d4' ORDER BY seq;
SELECT jsonb_build_object('er', jsonb_build_object('run_id', run_id, 'seq', seq, 'kind', kind, 'record_id', record_id,
  'digest', digest, 'chain', chain, 'record', record, 'generation', generation))::text
 FROM adviser_evaluation_records WHERE run_id = 'obs-20261007T182934-f8c3d4' ORDER BY seq;
COMMIT;
