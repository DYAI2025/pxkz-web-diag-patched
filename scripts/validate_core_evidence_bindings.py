#!/usr/bin/env python3
"""Validate exact 48/48 active core evidence bindings against canonical registries."""
from __future__ import annotations
import json,sys
from pathlib import Path
import jsonschema


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr); return 1


def main(argv: list[str]) -> int:
    if len(argv)!=2: return fail('usage: validate_core_evidence_bindings.py <skill-dir>')
    root=Path(argv[1]).resolve()
    try:
        binding=json.loads((root/'assets/core-evidence-bindings.active.v1.json').read_text())
        schema=json.loads((root/'schemas/core-evidence-binding.schema.json').read_text())
        registry=json.loads((root/'assets/measurement-registry.json').read_text())
        caps=json.loads((root/'assets/capability-registry.json').read_text())
        jsonschema.Draft202012Validator(schema).validate(binding)
    except Exception as exc:
        return fail(str(exc))
    rows=binding['metrics']; regrows=registry['metrics']
    ids=[x['metric_id'] for x in rows]; regids=[x['id'] for x in regrows]
    if len(ids)!=48 or len(set(ids))!=48: return fail('binding must contain exactly 48 unique metric IDs')
    if set(ids)!=set(regids):
        return fail(f'binding/registry ID mismatch missing={sorted(set(regids)-set(ids))} extra={sorted(set(ids)-set(regids))}')
    if binding['measurement_registry_version']!=registry.get('registry_version'): return fail('measurement registry version mismatch')
    by={x['metric_id']:x for x in rows}; capids={x['id'] for x in caps['capabilities']}
    anchors=set(registry['metric_score_scale'])
    for m in regrows:
        b=by[m['id']]
        if b['category']!=m['category']: return fail(f"{m['id']} category mismatch")
        if float(b['metric_weight'])!=float(m['weight']): return fail(f"{m['id']} metric weight drift")
        if float(b['category_weight'])!=float(registry['categories'][m['category']]['weight']): return fail(f"{m['id']} category weight drift")
        if b['score_mode']!=m['score_mode']: return fail(f"{m['id']} score mode drift")
        if b['capability_id']!=m['capability_id'] or b['capability_id'] not in capids: return fail(f"{m['id']} capability drift")
        if b['defined_test_method']!=m['test_method']: return fail(f"{m['id']} test method drift")
        if b['control_basis']!=m['control_basis']: return fail(f"{m['id']} control basis drift")
        if b['maximum_evidence_grade']!=m['max_evidence_grade']: return fail(f"{m['id']} max evidence grade drift")
        if set(b['allowed_score_statuses'])!=anchors: return fail(f"{m['id']} score anchors drift")
        if bool(b['threshold_source_required']) != (m['score_mode']=='external_threshold'): return fail(f"{m['id']} threshold-source policy drift")
        if b['source_family'] not in b['accepted_source_families']: return fail(f"{m['id']} primary source family not accepted")
    print('PASS: active core evidence bindings metrics=48 registry_weights=unchanged')
    return 0

if __name__=='__main__': raise SystemExit(main(sys.argv))
