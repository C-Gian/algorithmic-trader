import json
from datetime import timedelta
from decimal import Decimal as D
from dataclasses import replace
from test_adviser_evaluator import make, _entered, feed, bar, paths, T0, P0
from adviser_rig import Rig, rec
from test_adviser_rules import prime, balanced_h1, _ongoing_call, T
from algotrader.adviser.core import Attempt, Box
from algotrader.adviser.runtime import AdviserRuntime
out={}
# Stop gap away from any pending discretionary exit.
ev=make(); _entered(ev)
feed(ev,[bar(T0+timedelta(minutes=2),P0-100,P0-60,P0-120,P0-90)])
p=paths(ev)['PRIMARY']
out['ordinary_stop_gap']={'expected_price':str(P0-100),'actual_price':p['exit']['price'],'actual_reason':p['exit']['reason'],'actual_interval':[p['exit']['time_start'],p['exit']['time_end']]}
# A late receipt must not extend the event-end freshness deadline.
r=Rig(); prime(r,T,[P0+(10 if i%2 else -10) for i in range(30)],balanced_h1(T))
c=r.core; c.last_1m=replace(c.last_1m,known_at=T+timedelta(seconds=60)); c.clock=T+timedelta(seconds=60)
c.call=_ongoing_call(c.clock,issued=c.clock); c._touch()
rt=AdviserRuntime(c); due=c.next_deadline(); rt.advance(T+timedelta(seconds=121))
out['late_receipt_freshness']={'expected_first_stale':(T+timedelta(seconds=120,microseconds=1)).isoformat(),'actual_next_deadline':due.isoformat(),'fresh_at_requested_time':c.ready_1m(T+timedelta(seconds=121)),'actual_core_clock':c.clock.isoformat(),'actual_thesis':c.call.thesis if c.call else None}
# Residual equality holds, but the timer must still schedule the first strictly-too-late instant.
r=Rig(); prime(r,T,[P0+(10 if i%2 else -10) for i in range(30)],balanced_h1(T)); c=r.core
c.call=_ongoing_call(T,issued=T-timedelta(hours=3,minutes=30),hard=T+timedelta(minutes=30)); c.call.progress_done=True; c.last_1m=replace(c.last_1m,c=P0)
c._reassess_call(T); c._touch(); rt=AdviserRuntime(c); rt.advance(T+timedelta(microseconds=1))
out['residual_timer']={'actual_entry':c.call.entry,'remaining_is_less_than_minimum':c.call.hard_deadline-(T+timedelta(microseconds=1))<timedelta(minutes=30),'next_deadline':c.next_deadline().isoformat()}
# C pre-trigger invalidation: receipt time differs from market end.
r=Rig(); prime(r,T-timedelta(minutes=15),[P0+(10 if i%2 else -10) for i in range(30)],balanced_h1(T-timedelta(minutes=15))); c=r.core
bx=Box('box-c',P0+5,P0+2005,P0+1005,D(30),D(3),T-timedelta(hours=1),1,T+timedelta(hours=3),['s']); bx.used['C+']=True; c.box=bx
at=Attempt(aid='CL-probe',family='C',d=1,owner=bx.bid,born_at=T-timedelta(minutes=15),born_seq=1,sources=['s'],deadline=T+timedelta(minutes=15),s15=D(30),z=D(3),status='ARMED',k_t=P0+100,v_t=P0-500,arm_at=T-timedelta(minutes=15),arm_seq=2); c.attempts[at.aid]=at
r._bar(T-timedelta(minutes=1),P0+1,P0+2,P0,P0+1); c.admit_sealed(rec('15m',T-timedelta(minutes=15),P0+1,P0+2,P0,P0+1)); r.dispatch(T+timedelta(seconds=1))
out['c_late_close_withdrawal']={'closed_below_L_minus_z':True,'expected_attempt_present':False,'actual_attempt_present':at.aid in c.attempts,'context':c.context(c.clock),'phase':c.phase_now(c.clock)}
# Loss of the candle connection with a still-current public quote.
from test_adviser_live import _ongoing, SEC
from algotrader.adviser.core import Quote
sess,clock=_ongoing(); sess.disconnected(); clock.t+=SEC; px=sess.driver.rt.core.call.ref
sess.on_quote(Quote(px-D('0.1'),px+D('0.1'),clock.t,clock.t,'BTC-USDT-SWAP','q'*64),clock.t); sess.tick(clock.t)
out['disconnected_entry']={'session_status':sess.status,'connected':sess.connected,'actual_entry':sess.driver.rt.core.call.entry,'expected_entry':'UNVERIFIED','actual_reasons':sess.driver.rt.core.call.entry_reasons}
print(json.dumps(out,indent=2))
