#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path

def main(argv):
    if len(argv) not in {2,3}: print('FAIL: usage: validate_impressum_compliance.py <skill-dir> [sidecar.json]',file=sys.stderr); return 1
    root=Path(argv[1]); errors=[]
    reg=json.loads((root/'assets/impressum-compliance-registry.v1.json').read_text())
    ids=[x['id'] for x in reg['submetrics']]
    if ids != [f'LEGAL-IMP-{i:02d}' for i in range(1,12)]: errors.append('LEGAL-IMP IDs must be exact 01..11')
    if sum(reg['iles_dimensions'].values())!=100 or len(reg['iles_dimensions'])!=8: errors.append('ILES dimensions must be 8 and sum to 100')
    if any(x['weight']!=0 for x in reg['submetrics'] if x['id'] in {'LEGAL-IMP-01','LEGAL-IMP-10','LEGAL-IMP-11'}): errors.append('aggregator/modifier weights must be zero')
    if set(reg['defect_types'])!={"ABSENT","INCOMPLETE","INCORRECT","CONTRADICTORY","UNVERIFIABLE","INACCESSIBLE","NOT_CONTINUOUSLY_AVAILABLE","UNTIMELY"}: errors.append('defect enum mismatch')
    core=json.loads((root/'assets/measurement-registry.json').read_text())
    blob=json.dumps(core)
    if 'LEGAL-IMP-' in blob: errors.append('LEGAL metrics leaked into core registry')
    if len(core.get('metrics',[]))!=48: errors.append('core metric count changed')
    # Schema parse is deterministic and local.
    try:
        import jsonschema
        for name in ['impressum-evidence.schema.json','impressum-compliance.schema.json']:
            jsonschema.Draft202012Validator.check_schema(json.loads((root/'schemas'/name).read_text()))
    except Exception as exc: errors.append('schema validation failed: '+str(exc))
    if len(argv)==3:
        try:
            import jsonschema
            sidecar=json.loads(Path(argv[2]).read_text(encoding='utf-8'))
            schema=json.loads((root/'schemas/impressum-compliance.schema.json').read_text(encoding='utf-8'))
            jsonschema.Draft202012Validator(schema).validate(sidecar)
            if sidecar.get('pixelkiez_score_impact')!='NONE_DIRECT': errors.append('sidecar direct score impact forbidden')
            if any(int(r.get('iles_points',0))>0 and r.get('applicability_status')!='APPLICABLE' for r in sidecar.get('results',[]) if isinstance(r,dict)): errors.append('unadmitted applicability received ILES')
        except Exception as exc: errors.append('sidecar instance invalid: '+str(exc))
    if errors:
        for e in errors: print('FAIL:',e,file=sys.stderr)
        return 1
    print('PASS: impressum compliance registry/schema invariants')
    return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
