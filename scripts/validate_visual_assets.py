#!/usr/bin/env python3
"""Validate visual receipt, SVG assets, hashes, brand tokens and plan coverage."""
from __future__ import annotations
import hashlib,json,re,sys,xml.etree.ElementTree as ET
from pathlib import Path
from jsonschema import Draft202012Validator

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fail(m):print('FAIL: '+m,file=sys.stderr);return 1

def main(argv):
    if len(argv)!=4:return fail('usage: validate_visual_assets.py <plan.json> <receipt.json> <visual-dir>')
    planp,receiptp,visualdir=map(lambda x:Path(x).resolve(),argv[1:]); root=Path(__file__).resolve().parents[1]
    try:
        plan=json.loads(planp.read_text(encoding='utf-8')); receipt=json.loads(receiptp.read_text(encoding='utf-8'))
        schema=json.loads((root/'schemas/visual-render-receipt.schema.json').read_text(encoding='utf-8'))
        errs=list(Draft202012Validator(schema).iter_errors(receipt))
        if errs:return fail('receipt schema: '+errs[0].message)
        if receipt['plan_sha256']!=sha(planp):return fail('receipt stale against plan')
        selected=[x for x in plan['visuals'] if x['status']=='SELECTED']
        if receipt['rendered_count']!=len(selected) or len(receipt['visuals'])!=len(selected):return fail('rendered count mismatch')
        expected={(x['id'],x['template_id']) for x in selected}; observed={(x['id'],x['template_id']) for x in receipt['visuals']}
        if observed!=expected:return fail('visual set mismatch')
        brand_colors={'#EC5E43','#0E1414','#B6C7C4','#C6D4D1','#566360','#FFFFFF'}
        for row in receipt['visuals']:
            spec=(receiptp.parent/row['spec_path']).resolve(); svg=(receiptp.parent/row['svg_path']).resolve()
            if not spec.is_file() or not svg.is_file():return fail('missing spec/svg '+row['id'])
            if sha(spec)!=row['spec_sha256'] or sha(svg)!=row['svg_sha256']:return fail('hash mismatch '+row['id'])
            if visualdir not in svg.parents:return fail('SVG outside declared visual directory')
            text=svg.read_text(encoding='utf-8')
            if not re.search(r'<svg\b',text) or not re.search(r'viewBox="0 0 \d+ \d+"',text):return fail('invalid SVG envelope '+row['id'])
            try: xml_root=ET.fromstring(text)
            except Exception as exc:return fail(f"invalid SVG XML {row['id']}: {exc}")
            for element in xml_root.iter():
                local=element.tag.rsplit('}',1)[-1].casefold()
                if local in {'script','foreignobject'}:return fail('unsafe SVG element '+row['id']+':'+local)
                for key,value in element.attrib.items():
                    attr=key.rsplit('}',1)[-1].casefold()
                    if attr.startswith('on'):return fail('unsafe SVG event attribute '+row['id']+':'+attr)
                    if attr in {'href','xlink:href'} and value and not str(value).startswith('#'):return fail('external SVG reference '+row['id'])
            used={x.upper() for x in re.findall(r'#[0-9A-Fa-f]{6}',text)}
            if not used.intersection(brand_colors):return fail('no Pixelkiez brand color '+row['id'])
            sizes=[float(x) for x in re.findall(r'font-size="([0-9.]+)"',text)]
            if sizes and min(sizes)<13:return fail(f"SVG font too small {row['id']}={min(sizes)}px")
            if 'Beweist nicht:' in text:return fail('internal does_not_prove footer leaked into customer SVG '+row['id'])
            if '…' in text or '...' in text:return fail('truncation marker leaked into SVG '+row['id'])
        print(f"PASS: visual assets {len(selected)}/{len(selected)} hashed, branded, legible")
        return 0
    except Exception as e:return fail(str(e))
if __name__=='__main__':raise SystemExit(main(sys.argv))
