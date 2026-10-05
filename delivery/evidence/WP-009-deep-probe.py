import ast,__future__,json
from pathlib import Path
from types import SimpleNamespace
p=Path('src/algotrader/observe/deep.py');tree=ast.parse(p.read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and any(isinstance(x,ast.FunctionDef) and x.name=='_adv_compare' for x in n.body))
fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_adv_compare')
ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-deep-compare','exec',flags=__future__.annotations.compiler_flag),ns)
# The load path selects seq,digest, not record. A byte-only alteration leaves this exact reference map unchanged.
fresh={'seq':1,'digest':'a'*64,'record':{'meaning':'original'}}
state=SimpleNamespace(_adv=SimpleNamespace(take=lambda:([fresh],[])),_adv_digests={'adviser_journal':{1:'a'*64},'adviser_evaluation_records':{}},counters_deep={})
comparison={'compared':0,'mismatches':[]};ns['_adv_compare'](state,comparison,1)
print(json.dumps({'alteration':'stored record bytes changed; stored seq/digest unchanged','actual_comparisons':comparison['compared'],'actual_mismatches':comparison['mismatches'],'load_query':'SELECT seq, digest FROM adviser_journal WHERE run_id = %s','expected':'stored-byte hash failure or mismatch, never accepted as matching output'},indent=2))
