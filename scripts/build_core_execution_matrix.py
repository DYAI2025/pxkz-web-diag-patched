#!/usr/bin/env python3
"""Build the exact 48-row baseline-to-active execution truth matrix from canonical registries."""
from __future__ import annotations
import argparse,json
from pathlib import Path

DIRECT_NONCORE={"public_http_fetch","search_sample","performance_field","performance_lab","header_inspection","accessibility_automation"}
EXECUTOR={
 "public_http_fetch":"Measurement Gateway normalized public HTTP subset + agent public HTTP workflow",
 "public_page_render":"browser_measurements.py where applicable + agent-render inspection",
 "html_inspection":"agent fetched-HTML inspection; no dedicated core normalizer",
 "crawl_sample":"agent bounded crawl/sample workflow; no dedicated core normalizer",
 "search_sample":"measurement_adapters.py SERP/GSC enrichment; non-core before migration",
 "structured_data_inspection":"agent structured-data inspection; no dedicated core normalizer",
 "performance_field":"measurement_adapters.py CrUX enrichment; non-core before migration",
 "performance_lab":"measurement_adapters.py PageSpeed/Lighthouse enrichment; non-core before migration",
 "asset_inspection":"agent/page tooling inspection; no dedicated core normalizer",
 "header_inspection":"Measurement Gateway public header subset; non-core before migration",
 "accessibility_manual_sample":"browser keyboard sample + manual review; partial core workflow",
 "accessibility_automation":"browser_measurements.py optional automation; non-core before migration",
 "content_inspection":"agent content/entity/trust inspection; no dedicated core normalizer",
 "private_measurement_export":"authorized GSC/GA4/export enrichment; not a direct TRUST-08 core normalizer"
}

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument('skill_dir'); ap.add_argument('output'); a=ap.parse_args()
 root=Path(a.skill_dir).resolve(); reg=json.loads((root/'assets/measurement-registry.json').read_text()); caps=json.loads((root/'assets/capability-registry.json').read_text()); bind=json.loads((root/'assets/core-evidence-bindings.active.v1.json').read_text())
 cap={x['id']:x for x in caps['capabilities']}; bmap={x['metric_id']:x for x in bind['metrics']}; anchors=reg['metric_score_scale']
 rows=[]
 for m in reg['metrics']:
  b=bmap[m['id']]; c=cap[m['capability_id']]
  current='EXECUTABLE_NOT_SCORE_READY' if m['capability_id'] in DIRECT_NONCORE else 'PARTIALLY_IMPLEMENTED'
  rows.append({
   'metric_id':m['id'],'category':m['category'],'metric_weight':m['weight'],'category_weight':reg['categories'][m['category']]['weight'],
   'score_mode':m['score_mode'],'score_anchor':anchors,'threshold_source_required':b['threshold_source_required'],
   'defined_test_method':m['test_method'],'capability_id':m['capability_id'],'current_executor':EXECUTOR[m['capability_id']],
   'current_data_source':{'permission':c['permission'],'evidence':c['evidence'],'control_basis':m['control_basis']},
   'normalization_path':'BASELINE: direct/agent canonical metric assembly; ACTIVE: CORE_EXECUTION_BUNDLE_V1_TO_DIAGNOSIS_METRIC',
   'required_evidence':b['required_evidence'],'maximum_evidence_grade':m['max_evidence_grade'],
   'current_runtime_status':current,
   'current_score_admission_status':'BASELINE_CANONICAL_ROW_ONLY_NO_EXPLICIT_UPSTREAM_ADMISSION',
   'current_report_mapping':'diagnosis-report metric -> compute_score -> internal analysis; active patch adds weight/contribution traceability',
   'gap':'No explicit per-metric normalized execution/evidence admission contract existed before this migration.',
   'required_patch':'active binding + structured execution bundle + evidence admission + canonical materializer + unchanged compute_score + internal reconciliation',
   'validation_test':f'FULL48-ACTIVE::{m["id"]}',
   'post_patch_execution_status':'EXECUTABLE_AND_SCORE_READY'
  })
 out={'schema_version':'1.0','basis':'installed skill digest frozen before active migration','total_metrics':len(rows),'allowed_current_runtime_statuses':['EXECUTABLE_AND_SCORE_READY','EXECUTABLE_NOT_SCORE_READY','PARTIALLY_IMPLEMENTED','NO_EXECUTION_PATH','POLICY_BLOCKED','SOURCE_BLOCKED','CONTRACT_CONFLICT'],'metrics':rows}
 Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 if len(rows)!=48: raise SystemExit('FAIL: matrix rows != 48')
 print(f'PASS: 48-metric execution matrix rows={len(rows)}')
 return 0
if __name__=='__main__': raise SystemExit(main())
