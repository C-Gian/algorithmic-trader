"""Director F3 codec compatibility probe on 9b05a3e, synthetic and offline.
PYTHONPATH=src:tests python delivery/evidence/WP-011-CORRECTION-DIRECTOR-PROBE.py
No monkeypatch: uses the production unpack_runtime with a complete synthetic method configuration.
"""
import hashlib
import json
import zlib
from datetime import UTC, datetime, timedelta
from algotrader.adviser.harness import make_runtime
from algotrader.adviser import engine, methods
from algotrader.feed.ordering import canonical

es=datetime(2025,9,1,tzinfo=UTC)
ee=es+timedelta(days=1)
rt=make_runtime(method='v0.3',eval_start=es,eval_end=ee)
cfg=rt.core.cfg
rel=methods.get('v0.3')
eng={'format':rel.engine_format,'adviser':{
    'method':rel.key,'format':rel.runtime_format,
    'identity':rel.composite_identity(cfg.profile,{'instrument':cfg.instrument},None),
    'profile':cfg.profile.model_dump(mode='json'),'tick':str(cfg.tick),
    'clock_policy':cfg.clock_policy,'eval_start':es.isoformat(),'eval_end':ee.isoformat(),
    'origin':cfg.origin,'channels':cfg.channel_ids,'evaluator':rt.ev.identity(),'build':None}}
old=rt.encode()
del old['core']['v3']['deps']  # exactly the earlier v3 encoded shape; same compatible method/state identity
results=[]
for label,doc in [('legacy_without_deps',old),('new_with_deps',rt.encode())]:
    raw=canonical(doc)
    try:
        out=engine.unpack_runtime(zlib.compress(raw),hashlib.sha256(raw).hexdigest(),eng)
        results.append({'fixture':label,'restored':True,'exact_round_trip':canonical(out.encode())==raw})
    except engine.AdviserStateError as exc:
        results.append({'fixture':label,'restored':False,'error':str(exc)})
print(json.dumps({'reviewed_commit':'9b05a3e4bd3767ea627fa821ceaea3a32da34460',
                  'scope':'production codec, synthetic config, no DB/network/economic run','results':results},indent=2))
