#!/usr/bin/env python3
"""Regression cases for the final-presentation quality patch."""
from __future__ import annotations
import copy,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; PY=sys.executable
def run(cmd,expect=0):
 p=subprocess.run(cmd,text=True,capture_output=True)
 if p.returncode!=expect: raise RuntimeError(f"rc={p.returncode} expected={expect}: {' '.join(map(str,cmd))}\n{p.stdout}\n{p.stderr}")
 return p
def main()->int:
 checks=[]
 fixture=json.loads((ROOT/'evals/fixtures/synthetic-report.json').read_text(encoding='utf-8'))
 registry=json.loads((ROOT/'assets/measurement-registry.json').read_text(encoding='utf-8')); cat={m['id']:m['category'] for m in registry['metrics']}
 with tempfile.TemporaryDirectory(prefix='pxk-quality-') as td:
  t=Path(td); partial=copy.deepcopy(fixture)
  for m in partial['metrics']:
   if cat.get(m.get('id'))=='ux_conversion' and m.get('applicable') is True:
    m.update({'measurement_class':'not_assessed','status':'not_assessed','score':None,'confidence':1,'threshold_source':None,'source_or_method':'quality eval intentionally unassessed','does_not_prove':'eval'})
  src=t/'partial.json'; scored=t/'partial-scored.json'; model=t/'partial-model.json'; src.write_text(json.dumps(partial,ensure_ascii=False,indent=2))
  run([PY,str(ROOT/'scripts/compute_score.py'),str(src),str(scored)]); s=json.loads(scored.read_text())
  if s['score_summary']['display_status']!='PARTIAL_SCORE': raise RuntimeError('fixture did not produce PARTIAL_SCORE')
  run([PY,str(ROOT/'scripts/build_client_report_model.py'),str(scored),str(model)]); m=json.loads(model.read_text())
  if m['cover']['score'] is None or m['cover']['score_label']!='Pixelkiez Bewertungsstand': raise RuntimeError('partial score projection regression')
  if 'coverage' in json.dumps(m['cover'],ensure_ascii=False).casefold() or 'teilscore' in json.dumps(m,ensure_ascii=False).casefold(): raise RuntimeError('internal partial-score metadata leaked')
  checks.append('partial_score_as_bewertungsstand')
  # V03 must be ordinal-only.
  full_scored=t/'full-scored.json'; plan=t/'plan.json'; run([PY,str(ROOT/'scripts/compute_score.py'),str(ROOT/'evals/fixtures/synthetic-report.json'),str(full_scored)]); run([PY,str(ROOT/'scripts/build_visualization_plan.py'),str(full_scored),str(plan)]); p=json.loads(plan.read_text())
  v03=next(v for v in p['visuals'] if v.get('template_id')=='V03_TOP_LEVERS' and v.get('status')=='SELECTED')
  if any('score' in row or 'value' in row for row in v03['data']): raise RuntimeError('synthetic priority magnitude still present')
  if [r.get('priority') for r in v03['data']]!=[1,2,3,4]: raise RuntimeError('ordinal priority order changed')
  checks.append('ordinal_priority_no_fake_magnitude')
  # Client semantic guard must reject the exact overclaim class seen in the bad first pass.
  bad=copy.deepcopy(m); bad['closing']['actions']=['Eine vollständige Maßnahme.']*4; bad['cover']['verdict']='Einwilligungen sind OK und klar.'; bp=t/'bad-model.json'; bp.write_text(json.dumps(bad,ensure_ascii=False,indent=2))
  run([PY,str(ROOT/'scripts/validate_client_semantics.py'),str(bp)],expect=1); checks.append('privacy_overclaim_rejected')
  # Character clipping / sentence fragments must fail instead of being silently rendered.
  fragment=copy.deepcopy(m); fragment['closing']['actions']=list(fragment['closing']['actions']); fragment['closing']['actions'][0]='Eine klare Hauptaktion im ersten sichtbaren Bereich priorisieren und Nebenwege'
  fp=t/'fragment-model.json'; fp.write_text(json.dumps(fragment,ensure_ascii=False,indent=2))
  run([PY,str(ROOT/'scripts/validate_client_semantics.py'),str(fp)],expect=1); checks.append('closing_action_fragment_rejected')
  # Every four-lever card must expose the already-approved business impact.
  template=(ROOT/'templates/presentation.html.j2').read_text(encoding='utf-8')
  if '{{ finding.impact }}' not in template or 'Warum das zählt:' not in template:
   raise RuntimeError('four-lever business impact is not rendered by the presentation template')
  checks.append('four_lever_business_impact_rendered')
 report={'schema_version':'1.0','status':'PASS','checks':checks,'quality_contract':'non_compensatory','regression_target':'bad-first-pass -> inspected/repaired-second-pass'}
 (ROOT/'reports/customer-presentation-quality-eval-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS: customer presentation quality evals -> '+', '.join(checks)); return 0
if __name__=='__main__':
 try: raise SystemExit(main())
 except Exception as e: print('FAIL: '+str(e),file=sys.stderr); raise SystemExit(1)
