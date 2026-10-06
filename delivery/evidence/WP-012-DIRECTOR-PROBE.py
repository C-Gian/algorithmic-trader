import json
from datetime import timedelta
import adviser4_fixtures as fx
from adviser3_fixtures import Stepper
from test_mp003_paths import main_records, _late_tape

out = []
for side in ('LONG', 'SHORT'):
    ms = _late_tape(99900)
    ms[fx.index_of(fx.T(4, 0))] = fx.minute(100100, 100100, 99750, 99950)
    if side == 'SHORT':
        ms = fx.mirror(ms)
    evs = fx.delayed_events(ms, {fx.index_of(fx.T(3, 59)): 30})
    st = Stepper(ms, events=evs, method='v0.4', allowance=timedelta(seconds=30))
    st.finish()
    rows = main_records(st.journal)
    out.append({'side': side, 'publication_straddled': '2025-09-01T04:00:30Z',
                'minute_interval': '[04:00,04:01)',
                'old_V': '99800' if side == 'LONG' else '100200',
                'new_V': '99650' if side == 'LONG' else '100350',
                'contact_extremum': '99750' if side == 'LONG' else '100250',
                'expected': 'anchor UNASSESSABLE; no confirmation using that anchor',
                'actual': [{k: r[k] for k in ('transition','anchor_epoch','anchor_status','reason')} |
                            {'clock':r['env']['clock_time']} for r in rows],
                'unexpected_confirmation': any(r['transition']=='CONFIRM' and r['anchor_epoch']==2 for r in rows)})
print(json.dumps(out, indent=2))
