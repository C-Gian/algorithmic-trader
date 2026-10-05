import ast, __future__, hashlib, json
from pathlib import Path
from types import SimpleNamespace
from algotrader.feed.ordering import canonical
from algotrader.adviser.core import INITIAL_JOURNAL
tr=ast.parse(Path('src/algotrader/observe/deep.py').read_text())
cl=next(n for n in tr.body if isinstance(n,ast.ClassDef) and n.name=='DeepJob')
ns={'MAX_MISMATCHES':100,'__name__':'algotrader.observe.deep','__package__':'algotrader.observe'}
for name in ('_adv_load_stored','_adv_compare','_adv_extra'):
 fn=next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-deep-'+name,'exec',flags=__future__.annotations.compiler_flag),ns)
validate=next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name=='_validate')
guard=next(n for n in ast.walk(validate) if isinstance(n,ast.If) and isinstance(n.test,ast.UnaryOp) and isinstance(n.test.operand,ast.Name) and n.test.operand.id=='start' and any(isinstance(x,ast.Name) and x.id=='stored_problems' for x in ast.walk(n)))
record={'fixture':'unchanged bytes'}
digest=hashlib.sha256(canonical(record)).hexdigest()
chain=hashlib.sha256(bytes.fromhex(INITIAL_JOURNAL)+bytes.fromhex(digest)).hexdigest()
class Conn:
 def execute(self,q,args):
  rows=[] if 'adviser_evaluation_records' in q else [{'seq':1,'digest':'f'*64,'chain':chain,'record':record}]
  return SimpleNamespace(fetchall=lambda:rows)
out={};state=SimpleNamespace(conn=Conn(),counters_deep={},_adv_seen={'adviser_journal':set(),'adviser_evaluation_records':set()})
problems=ns['_adv_load_stored'](state,'fixture',out)
comparison={'compared':0,'mismatches':[]}
ctx={'start':1,'stored_problems':problems,'comparisons':comparison,'MAX_MISMATCHES':100}
exec(compile(ast.Module(body=[guard],type_ignores=[]),'actual-resume-guard','exec'),ctx)
state._adv_digests=out
state._adv=SimpleNamespace(take=lambda:([{'seq':1,'digest':digest,'chain':chain}],[]))
ns['_adv_compare'](state,comparison,1)
ns['_adv_extra'](state,comparison,1)
print(json.dumps({'scope':'actual Deep methods and actual resume conditional; mocked storage; no DB/full job claim','mutation':'digest column changed while Deep paused; record and chain unchanged','loader_detected':problems,'resumed_comparisons':comparison,'expected':'stored metadata inconsistency must remain a mismatch after resume'},indent=2))
