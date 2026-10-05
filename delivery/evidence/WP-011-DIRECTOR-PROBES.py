"""Offline Director synthetic probes at f1a8023. No DB, network or Owner data.
Run from repository root: PYTHONPATH=src:tests python delivery/evidence/WP-011-DIRECTOR-PROBES.py
Prints counterexamples; false expected properties reproduce the reviewed findings.
"""
import json
from datetime import timedelta
import adviser3_fixtures as fx
from adviser_fixtures import box_fixture
from algotrader.adviser.harness import run_pure

def box_collision():
    minutes=box_fixture('B')
    first,last=fx.index_of(fx.T(4,46)),fx.index_of(fx.T(5))-1
    for i in range(first,last):
        minutes[i]=fx.minute(101860,101860,101860,101860)
    minutes[last]=fx.minute(101860,101860,99930,99930)
    st=fx.Stepper(minutes)
    st.run_until(fx.T(4,59))
    old=st.core.box.bid
    pre=[s.sid for s in st.core.scen.values() if s.family=='B' and s.d==1]
    st.run_until(fx.T(5))
    retires=[r for r in st.kinds('observation') if r.get('category')=='BOX_RETIRED']
    post=[s.sid for s in st.core.scen.values() if s.owner==old]
    return {'id':'F1','pre_dispatch_B':pre,'old_box':old,
            'post_dispatch_box':st.core.box.bid if st.core.box else None,
            'box_retire_records':len(retires),'new_episodes_on_old_box':post,
            'expected_property':st.core.box is None or st.core.box.bid!=old,
            'B_terminals':[(s['env']['clock_time'],s['reason']) for s in st.kinds('scenario')
                           if s['family']=='B' and s['transition']=='TERMINAL']}

def confirmed_samples():
    res=run_pure(fx.DAY1,fx.a3_stall_after_return(),eval_start=fx.DAY2,method='v0.3')
    conf=next(s for s in res.scenarios('AL') if s['transition']=='CONFIRM')
    rows=[r['record'] for r in res.records if r['kind']=='view_sample'
          and r['record']['scenario_id']==conf['scenario_id']
          and r['record']['sample_time']>'2025-09-01T04:01:00Z']
    return {'id':'F2','confirmation':conf['env']['clock_time'],
            'samples':[{'at':s['sample_time'],'activated_1h':s['antecedent_activated_1h'],
                        'activated_4h':s['antecedent_activated_4h']} for s in rows],
            'expected_property':bool(rows) and all(s['antecedent_activated_1h'] and
                                                  s['antecedent_activated_4h'] for s in rows)}

print(json.dumps({'reviewed_commit':'f1a8023763e820e41cbd6085be14b4ebabbcb0d3',
                  'scope':'synthetic offline pure paths, no economic/Owner run',
                  'probes':[box_collision(),confirmed_samples()]},indent=2))
