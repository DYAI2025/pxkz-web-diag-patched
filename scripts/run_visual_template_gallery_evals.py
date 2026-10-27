#!/usr/bin/env python3
"""Validate and fallback-render every approved Pixelkiez visualization template."""
from __future__ import annotations
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
from jsonschema import Draft202012Validator


def run(args):
 p=subprocess.run(args,text=True,capture_output=True)
 if p.returncode: raise AssertionError(f"{' '.join(args)}\n{p.stdout}\n{p.stderr}")
 return p

def main(argv):
 if len(argv)!=2:
  print('FAIL: usage: run_visual_template_gallery_evals.py <skill-dir>',file=sys.stderr);return 1
 root=Path(argv[1]).resolve(); py=sys.executable
 try:
  schema=json.loads((root/'assets/vega-lite-schema-v6.4.3.json').read_text(encoding='utf-8'))
  validator=Draft202012Validator(schema)
  visuals=[]
  for idx,path in enumerate(sorted((root/'templates/visualizations').glob('*.vl.json')),1):
   spec=json.loads(path.read_text(encoding='utf-8')); errs=list(validator.iter_errors(spec))
   if errs: raise AssertionError(f"{path.name}: {errs[0].message}")
   tid=path.name.removesuffix('.vl.json')
   visuals.append({'id':f'VIZ-{idx:03d}','template_id':tid,'engine':'VEGA_LITE','status':'SELECTED','title':spec.get('usermeta',{}).get('name',tid),'subtitle':'Pixelkiez Template Gallery','metric_refs':[],'finding_refs':[],'evidence_class':'SYNTHETIC_TEMPLATE_TEST','population':'synthetische Template-Daten','method':'bundled template gallery eval','does_not_prove':'Die Galerie beweist keine Kundendaten, Geschäftswirkung oder externe Runtime-Kompatibilität.','data':spec.get('data',{}).get('values',[])})
  visuals.append({'id':f'VIZ-{len(visuals)+1:03d}','template_id':'D01_PROCESS_FLOW','engine':'MERMAID','status':'SELECTED','title':'Befund bis Prüfung','subtitle':'Optionales Strukturdiagramm','metric_refs':[],'finding_refs':[],'evidence_class':'SYNTHETIC_TEMPLATE_TEST','population':'vier Prozessschritte','method':'bundled Mermaid-source gallery eval','does_not_prove':'Das Ablaufdiagramm beweist keine technische Implementierung oder Geschäftswirkung.','data':[{'label':'Befund'},{'label':'Auswirkung'},{'label':'Maßnahme'},{'label':'Prüfung'}]})
  with tempfile.TemporaryDirectory(prefix='pxk-viz-gallery-') as td:
   t=Path(td); plan=t/'plan.json'; out=t/'visuals'; receipt=t/'receipt.json'
   payload={'schema_version':'1.0','source_report_sha256':'0'*64,'brand_token_sha256':hashlib.sha256((root/'assets/brand-tokens.json').read_bytes()).hexdigest(),'top_levers':['G1','G2','G3','G4'],'visuals':visuals,'excluded_candidates':[]}
   plan.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
   run([py,str(root/'scripts/render_visualizations.py'),str(plan),str(out),'--receipt',str(receipt),'--force-fallback'])
   run([py,str(root/'scripts/validate_visual_assets.py'),str(plan),str(receipt),str(out)])
   r=json.loads(receipt.read_text(encoding='utf-8'))
   if r.get('rendered_count')!=15: raise AssertionError(f"expected 15 rendered templates, got {r.get('rendered_count')}")
  report={'status':'PASS','suite':'visualization-template-gallery','vega_lite_templates':14,'mermaid_or_fallback_templates':1,'rendered_count':15,'vega_lite_schema':'assets/vega-lite-schema-v6.4.3.json','backend_under_test':'PIXELKIEZ_SVG_FALLBACK','does_not_prove':['external Vega or Mermaid runtime availability','customer data quality','commercial outcome']}
  (root/'reports/visualization-gallery-eval-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print('PASS: visual template gallery 14 Vega-Lite + 1 Mermaid/fallback templates')
  return 0
 except Exception as exc:
  report={'status':'FAIL','suite':'visualization-template-gallery','error':str(exc)}
  (root/'reports/visualization-gallery-eval-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print(f'FAIL: {exc}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main(sys.argv))
