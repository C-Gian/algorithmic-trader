\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT jsonb_build_object('meta', jsonb_build_object('transaction_read_only', current_setting('transaction_read_only'),
  'isolation', current_setting('transaction_isolation'), 'snapshot', pg_current_snapshot()::text,
  'server_time', now(), 'server_version', current_setting('server_version')))::text;
SELECT jsonb_build_object('count', jsonb_build_object('rows', count(*), 'distinct_record_id', count(DISTINCT record_id),
  'distinct_seq', count(DISTINCT seq), 'min_seq', min(seq), 'max_seq', max(seq)))::text
 FROM adviser_evaluation_records WHERE run_id = 'obs-20261009T155751-0f255b' AND kind = 'view_sample';
SELECT jsonb_build_object('vs', jsonb_build_object('run_id', run_id, 'seq', seq, 'kind', kind, 'record_id', record_id,
  'digest', digest, 'chain', chain, 'record', record, 'generation', generation, 'committed_at', committed_at))::text
 FROM adviser_evaluation_records WHERE run_id = 'obs-20261009T155751-0f255b' AND kind = 'view_sample' ORDER BY seq;
COMMIT;
