from contextlib import contextmanager
from datetime import UTC,datetime,timedelta
from pathlib import Path
import json
import ast, __future__
from algotrader.adviser.harness import trade_bar
from algotrader.observe import feedcache
T=datetime(2025,9,1,tzinfo=UTC)
events=[trade_bar(T+timedelta(minutes=i),100000,100001,99999,100000) for i in range(4)]
class C:
    def execute(self,*a): return self
    def fetchone(self): return {'engine':{'adviser':{'identity':{}},'cache_id':'fixture','cache_manifest_sha256':'pin'},'cursor':1}
@contextmanager
def conn(): yield C()
class Reader:
    def __init__(self,*a): pass
    def iter_from(self,start): return iter([(i,e) for i,e in enumerate(events) if i>=start])
feedcache.CacheReader=Reader; feedcache.open_cache=lambda *a,**k:object(); feedcache.decode=lambda line:line
tree=ast.parse(Path('src/algotrader/adviser/api.py').read_text())
build=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_router')
fn=next(n for n in build.body if isinstance(n,ast.FunctionDef) and n.name=='window'); fn.decorator_list=[]
ns={'__name__':'algotrader.adviser.api','__package__':'algotrader.adviser','conn':conn,'data_root':Path('/unused-fixture'),'Query':lambda v,**kw:v,'HTTPException':RuntimeError}
exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-api-window','exec',flags=__future__.annotations.compiler_flag),ns)
f=ns['window']
got=f('fixture',cursor=1,before=0,after=3)
print(json.dumps({'committed_cursor':1,'requested_cursor':1,'actual_returned_slots':[b['t'] for b in got['bars']],'all_returned_slots_are_uncommitted':True,'expected_returned_slots':[]},indent=2))
