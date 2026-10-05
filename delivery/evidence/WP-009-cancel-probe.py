import json
from datetime import UTC,datetime,timedelta
from decimal import Decimal as D
from algotrader.adviser import live as lv
from algotrader.adviser.runtime import AdviserRuntime
from algotrader.adviser.core import AdviserCore
from algotrader.feed.contracts import Family
from test_adviser_live import COMPAT
now=datetime(2025,9,1,12,tzinfo=UTC); start=now-timedelta(minutes=10)
sess=lv.LiveSession(COMPAT,'test',lambda:now)
sess.epoch=lv.new_epoch(start,COMPAT)
sess.driver=lv.LiveDriver(lv.new_temporal(start),AdviserRuntime(AdviserCore(lv.live_config(COMPAT,'test')),None))
def fetch(fam,a,b):
    if fam==Family.INDEX_BAR_1M: sess.cancel_requested=True
    return [(a+i*timedelta(minutes=1),D(100000),D(100001),D(99999),D(100000),('1','1','1')) for i in range(10)]
sess.reconstruct(fetch,now)
print(json.dumps({'cancel_seen_before_replay':sess.cancel_requested,'actual_replayed_minutes':sess.progress.get('replayed_minutes'),'actual_factual_cursor':sess.driver.cursor,'expected_new_replay_work_after_cancel':0},indent=2))
