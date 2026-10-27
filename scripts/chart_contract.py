#!/usr/bin/env python3
"""Shared deterministic validation for Pixelkiez V01-V12 chart payloads."""
from __future__ import annotations
from typing import Any

TEMPLATES={f"V{i:02d}" for i in range(1,13)}

def _num(v:Any)->bool: return isinstance(v,(int,float)) and not isinstance(v,bool)
def _list(d:dict[str,Any],k:str)->list[Any]:
    v=d.get(k); return v if isinstance(v,list) else []
def validate_visualization(v:dict[str,Any])->list[str]:
    e=[]; vid=str(v.get('id','?')); tid=v.get('template_id'); data=v.get('data') if isinstance(v.get('data'),dict) else {}
    if tid not in TEMPLATES: return [f"{vid}: invalid template_id {tid}"]
    ev=v.get('evidence') if isinstance(v.get('evidence'),dict) else {}
    for k in ('grade','mode','scope','population','tool','date'):
        if not str(ev.get(k,'')).strip(): e.append(f"{vid}: evidence.{k} required")
    if not str(v.get('title','')).strip(): e.append(f"{vid}: finding-style title required")
    if not str(v.get('does_not_prove','')).strip(): e.append(f"{vid}: does_not_prove required")
    th=v.get('threshold')
    if th is not None:
        if not isinstance(th,dict) or not str(th.get('source','')).strip(): e.append(f"{vid}: threshold requires provenance source")
    if tid=='V01':
        pts=_list(data,'series');
        if not 4<=len(pts)<=12 or any(not isinstance(x,dict) or not _num(x.get('value')) for x in pts): e.append(f"{vid}: V01 series must contain 4-12 numeric points")
    elif tid=='V02':
        pts=_list(data,'series'); bands=_list(data,'bands')
        if not 4<=len(pts)<=24 or any(not isinstance(x,dict) or not _num(x.get('value')) for x in pts): e.append(f"{vid}: V02 series must contain 4-24 numeric points")
        if len(bands)!=3 or any(not isinstance(x,dict) or not _num(x.get('boundary')) or not str(x.get('source','')).strip() for x in bands): e.append(f"{vid}: V02 requires exactly three sourced bands")
    elif tid=='V03':
        groups=_list(data,'groups'); series=_list(data,'series')
        if not 3<=len(groups)<=6 or any(not str(g).strip() for g in groups): e.append(f"{vid}: V03 groups must be 3-6 non-empty labels")
        if not str(data.get('unit','')).strip(): e.append(f"{vid}: V03 unit required once for the grouped comparison")
        if not 2<=len(series)<=3 or any(not isinstance(s,dict) or not str(s.get('name','')).strip() or len(_list(s,'values'))!=len(groups) or any(not _num(n) for n in _list(s,'values')) for s in series): e.append(f"{vid}: V03 requires 2-3 named numeric series matching groups")
    elif tid=='V04':
        rows=_list(data,'rows')
        if not 4<=len(rows)<=8 or any(not isinstance(x,dict) or not _num(x.get('value')) for x in rows): e.append(f"{vid}: V04 rows must be 4-8 numeric rows")
        vals=[x.get('value') for x in rows if isinstance(x,dict) and _num(x.get('value'))]
        if vals and vals!=sorted(vals,reverse=True): e.append(f"{vid}: V04 rows must be sorted descending")
    elif tid=='V05':
        rows=_list(data,'rows'); classes=_list(data,'classes')
        if not 1<=len(rows)<=4 or not 2<=len(classes)<=4: e.append(f"{vid}: V05 requires 1-4 rows and 2-4 classes")
        if any(not isinstance(c,dict) or not str(c.get('name','')).strip() or c.get('status') not in {'good','warn','bad','context'} for c in classes): e.append(f"{vid}: V05 classes require name and status good/warn/bad/context")
        for r in rows:
            vals=_list(r,'values') if isinstance(r,dict) else []
            if not isinstance(r,dict) or not str(r.get('label','')).strip() or len(vals)!=len(classes) or any(not _num(n) for n in vals) or abs(sum(vals)-100)>0.2: e.append(f"{vid}: every V05 row needs a label and class percentages summing to 100")
    elif tid=='V06':
        parts=_list(data,'parts')
        if not 2<=len(parts)<=4 or any(not isinstance(x,dict) or not str(x.get('label','')).strip() or not _num(x.get('value')) for x in parts): e.append(f"{vid}: V06 parts must be 2-4 labelled numeric parts")
        if not _num(data.get('sum')): e.append(f"{vid}: V06 sum required")
        elif parts and abs(float(data['sum'])-sum(float(x['value']) for x in parts))>1e-6: e.append(f"{vid}: V06 sum must equal the sum of all parts")
        if not str(data.get('unit','')).strip(): e.append(f"{vid}: V06 unit required for the centre total")
    elif tid=='V07':
        if not _num(data.get('value')) or not 0<=float(data.get('value'))<=100: e.append(f"{vid}: V07 value must be 0-100")
        scale=data.get('scale') if isinstance(data.get('scale'),dict) else {}
        if not all(_num(scale.get(k)) for k in ('min','max')) or float(scale.get('min',0))>=float(scale.get('max',0)) or not str(scale.get('source','')).strip(): e.append(f"{vid}: V07 sourced min/max scale required")
        tiles=_list(data,'tiles')
        if not 2<=len(tiles)<=3 or any(not isinstance(t,dict) or not str(t.get('label','')).strip() or 'value' not in t for t in tiles): e.append(f"{vid}: V07 requires 2-3 value/label tiles")
    elif tid=='V08':
        pts=_list(data,'points')
        if not 3<=len(pts)<=8 or any(not isinstance(x,dict) or not str(x.get('label','')).strip() or any(not _num(x.get(k)) for k in ('x','y','r')) or float(x.get('r',0))<0 for x in pts): e.append(f"{vid}: V08 requires 3-8 labelled numeric x/y/r points with non-negative radius values")
        for axis_key in ('x_axis','y_axis'):
            axis=data.get(axis_key) if isinstance(data.get(axis_key),dict) else {}
            if not str(axis.get('name','')).strip() or 'unit' not in axis: e.append(f"{vid}: V08 {axis_key} requires name and unit (unit may be empty)")
        if not str(data.get('radius_legend','')).strip(): e.append(f"{vid}: V08 radius_legend required")
    elif tid=='V09':
        axes=_list(data,'axes'); nets=_list(data,'nets')
        if not 5<=len(axes)<=8 or any(not isinstance(a,dict) or not str(a.get('label','')).strip() for a in axes): e.append(f"{vid}: V09 axes must be 5-8 labelled axes")
        if not 1<=len(nets)<=2: e.append(f"{vid}: V09 nets must be 1-2")
        sc=data.get('scale') if isinstance(data.get('scale'),dict) else {}
        if not all(_num(sc.get(k)) for k in ('min','max')) or float(sc.get('min',0))>=float(sc.get('max',0)): e.append(f"{vid}: V09 valid scale min/max required")
        lo=float(sc.get('min',0)) if _num(sc.get('min')) else None; hi=float(sc.get('max',0)) if _num(sc.get('max')) else None
        for n in nets:
            vals=_list(n,'values') if isinstance(n,dict) else []
            if not isinstance(n,dict) or not str(n.get('name','')).strip() or len(vals)!=len(axes) or any(not _num(x) for x in vals): e.append(f"{vid}: V09 named net values must match axes")
            elif lo is not None and hi is not None and any(float(x)<lo or float(x)>hi for x in vals): e.append(f"{vid}: V09 net values must stay inside the declared scale")
    elif tid=='V10':
        rows=_list(data,'rows')
        if not 3<=len(rows)<=6 or any(not isinstance(x,dict) or not str(x.get('label','')).strip() or not _num(x.get('value_a')) or not _num(x.get('value_b')) or not str(x.get('unit','')).strip() for x in rows): e.append(f"{vid}: V10 requires 3-6 labelled delta rows with value_a/value_b/unit")
        comp=data.get('comparison') if isinstance(data.get('comparison'),dict) else {}
        if not str(comp.get('definition','')).strip() or not isinstance(comp.get('n'),int) or comp.get('n')<=0: e.append(f"{vid}: V10 comparison requires a cohort/benchmark definition and positive n")
    elif tid=='V11':
        bins=_list(data,'classes')
        if not 5<=len(bins)<=10 or any(not isinstance(x,dict) or not str(x.get('label','')).strip() or not isinstance(x.get('n'),int) or x.get('n')<0 for x in bins): e.append(f"{vid}: V11 requires 5-10 labelled nonnegative count classes")
        if not isinstance(data.get('total_n'),int) or data.get('total_n')<0 or not _num(data.get('median')): e.append(f"{vid}: V11 total_n and median required")
        elif sum(int(x['n']) for x in bins if isinstance(x,dict) and isinstance(x.get('n'),int))!=data.get('total_n'): e.append(f"{vid}: V11 total_n must equal the sum of class counts")
        if bins and not str(bins[-1].get('label','')).strip().endswith('+'): e.append(f"{vid}: V11 last class must be open-ended and marked with +")
    elif tid=='V12':
        rows=_list(data,'rows')
        if not 1<=len(rows)<=8: e.append(f"{vid}: V12 requires 1-8 rows")
        for r in rows:
            if not isinstance(r,dict) or any(not str(r.get(k,'')).strip() for k in ('metric','value','threshold_origin','evidence','does_not_prove')): e.append(f"{vid}: every V12 row requires metric/value/threshold_origin/evidence/does_not_prove")
    return e

def validate_visualizations(values:Any)->list[str]:
    if not isinstance(values,list): return ['visualizations must be an array']
    e=[]; ids=set()
    for v in values:
        if not isinstance(v,dict): e.append('visualization item must be object'); continue
        vid=str(v.get('id',''))
        if not vid or vid in ids: e.append(f'duplicate or missing visualization id {vid!r}')
        ids.add(vid); e.extend(validate_visualization(v))
    return e
