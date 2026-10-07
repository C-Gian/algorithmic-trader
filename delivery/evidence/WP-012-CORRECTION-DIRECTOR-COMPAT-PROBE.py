# Reproduction prerequisite: save src/algotrader/adviser/core4.py from immutable product
# e434d4311a947f65f2fccf035d61e79d9108add2 as legacy_core4_review_source.py in the repo cwd.
# Run with PYTHONPATH=src:tests and the project dependencies; no DB or market input used.
import json, sys, types, zlib
from pathlib import Path
from datetime import timedelta
from adviser3_fixtures import Stepper
import adviser4_fixtures as fx
from test_mp003_correction import tape, _events, _engine_doc
from algotrader.adviser import engine
from algotrader.adviser.harness import make_runtime, build_events, temporal_for
from algotrader.feed.ordering import canonical

mod = types.ModuleType('algotrader.adviser._director_old_core4')
mod.__package__ = 'algotrader.adviser'
sys.modules[mod.__name__] = mod
exec(Path('legacy_core4_review_source.py').read_text(), mod.__dict__)
out=[]
for fixture, cut in [('supersession', fx.T(4,0)+timedelta(seconds=45)),
                     ('loss', fx.T(3,51)+timedelta(seconds=15))]:
    ms = tape() if fixture=='supersession' else fx.contact_then_rearm()
    events = _events(ms) if fixture=='supersession' else None
    all_events,cov=build_events(fx.DAY1,ms)
    events=events or all_events
    end=fx.DAY1+len(ms)*timedelta(minutes=1)
    rt=make_runtime(eval_start=fx.DAY2,eval_end=end,method='v0.4')
    rt.core=mod.AdviserCoreV4(rt.core.cfg)
    temporal=temporal_for(cov,allowance=timedelta(seconds=30) if fixture=='supersession' else timedelta(0))
    rt.attach(temporal)
    for i,e in enumerate(events):
        temporal.on_event(e,i)
        rt.before_admit(e)
        rt.admit(e,i)
        if e.available_time>cut:
            break
    rt.take()
    doc=_engine_doc(rt,end)
    blob,sha=engine.pack_runtime(rt)
    restored=engine.unpack_runtime(blob,sha,doc)
    same=canonical(restored.encode())==zlib.decompress(blob)
    scen=next(s for s in restored.core.scen.values() if s.family=='A' and s.ever_armed)
    out.append({'source_product':'e434d4311a947f65f2fccf035d61e79d9108add2', 'fixture':fixture,
                'four_element_domains':all(len(v)==4 for v in scen.v_hist),
                'status':scen.status,'production_unpack_exact':same,'history':scen.v_hist})
    assert same
print(json.dumps(out,indent=2))
