#!/usr/bin/env python3
"""Validate WeasyPrint renderer receipt, PDF readability and Pixelkiez brand-state honesty."""
from __future__ import annotations
import argparse,hashlib,json,sys,re
from pathlib import Path
import fitz
from jsonschema import Draft202012Validator

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fail(m):print('FAIL: '+m,file=sys.stderr);return 1

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('pdf');ap.add_argument('receipt');ap.add_argument('brand_tokens');ap.add_argument('--require-exact-fonts',action='store_true');a=ap.parse_args()
 pdf,receiptp,tokensp=map(lambda x:Path(x).resolve(),(a.pdf,a.receipt,a.brand_tokens))
 try:
  r=json.loads(receiptp.read_text(encoding='utf-8'));t=json.loads(tokensp.read_text(encoding='utf-8'))
  root=Path(__file__).resolve().parents[1]
  schema=json.loads((root/'schemas/presentation-render-receipt.schema.json').read_text(encoding='utf-8'))
  Draft202012Validator(schema).validate(r)
  if r.get('status')!='PASS' or r.get('renderer')!='WEASYPRINT':return fail('default presentation renderer must be WEASYPRINT PASS')
  htmlp=(receiptp.parent/str(r.get('html_path') or '')).resolve()
  if not htmlp.is_file() or r.get('html_sha256')!=sha(htmlp):return fail('HTML render receipt stale or missing')
  if r.get('pdf_sha256')!=sha(pdf):return fail('render receipt stale against PDF')
  if r.get('embedded_visual_count',0)<4:return fail('customer PDF requires at least four embedded visuals')
  if not 8<=r.get('page_count',0)<=12:return fail('customer PDF page count must be 8-12')
  if r.get('local_only_resources') is not True:return fail('remote resource boundary not enforced')
  if r.get('legacy_reportlab_default') is not False:return fail('ReportLab must not be default customer renderer')
  expected={v.upper() for v in t.get('palette',{}).values() if isinstance(v,str) and v.startswith('#')}
  actual={x.upper() for x in r.get('brand_palette',[])}
  required={'#EC5E43','#0E1414','#B6C7C4','#C6D4D1','#566360','#FFFFFF'}
  if not required.issubset(actual) or not required.issubset(expected):return fail('Pixelkiez brand palette mismatch')
  if r.get('body_text_size_pt',0)<12:return fail('body text below 12pt')
  if r.get('chart_label_minimum_pt',0)<10:return fail('chart label minimum below 10pt')
  doc=fitz.open(pdf); sizes=[]; text=''
  for page in doc:
   text+=page.get_text()+'\n'
   for block in page.get_text('dict').get('blocks',[]):
    for line in block.get('lines',[]):
     for span in line.get('spans',[]):
      if str(span.get('text') or '').strip() and isinstance(span.get('size'),(int,float)):sizes.append(float(span['size']))
  if not sizes or min(sizes)<8.45:return fail(f'PDF contains text below 8.5pt: {min(sizes) if sizes else "none"}')
  if 'beweistnicht:' in re.sub(r'\s+', '', text).casefold():return fail('internal chart evidence-boundary boilerplate leaked into customer PDF')
  if "…" in text or re.search(r"\.{3}", text):return fail('customer PDF contains truncation ellipsis; rewrite instead of shrinking/truncating')
  internal_markers=("PIXELKIEZ_SVG_FALLBACK","VEGA_LITE_EXTERNAL","MERMAID_CLI","BUILTIN_SVG",".vl.json","V01_OVERALL_SCORE","V02_CATEGORY_BARS","V03_TOP_LEVERS","V11_SEVERITY_DISTRIBUTION")
  leaked=[m for m in internal_markers if m.casefold() in text.casefold()]
  if leaked:return fail('internal renderer/template markers leaked into customer PDF: '+', '.join(leaked))
  pdf_fonts=[str(x) for x in r.get('pdf_fonts',[])]
  if any('serif' in x.casefold() or 'times' in x.casefold() for x in pdf_fonts):return fail('serif font leaked into brand presentation: '+', '.join(pdf_fonts))
  if not any(any(marker in x.casefold() for marker in ('pixelkiezdisplay','schibsted','plexsans','notosans','dejavusans')) for x in pdf_fonts):return fail('no approved display font embedded')
  if not any(any(marker in x.casefold() for marker in ('pixelkiezdata','plexmono','notosansmono','dejavusansmono')) for x in pdf_fonts):return fail('no approved monospaced numeric/label font embedded')
  if r.get('brand_font_status') not in {'EXACT','PARTIAL_EXACT_APPROVED_FALLBACK','APPROVED_FALLBACK'}:return fail('invalid brand font status')
  font_resolution=r.get('font_resolution',{})
  if r.get('brand_font_status')=='EXACT' and font_resolution.get('customer_release_ready') is not True:return fail('exact brand status contradicts font receipt')
  if a.require_exact_fonts and r.get('brand_font_status')!='EXACT':return fail('BRAND_FONT_EXACT_REQUIRED: strict brand font mode requested')
  if r.get('brand_font_status')!='EXACT' and not r.get('limitations'):return fail('font fallback must disclose limitation')
  if font_resolution.get('exact',{}).get('data') is True and not any(any(marker in x.casefold() for marker in ('pixelkiezdata','plexmono')) for x in pdf_fonts):return fail('resolved IBM Plex Mono did not reach PDF')
  print(f"PASS: presentation brand pages={len(doc)} visuals={r['embedded_visual_count']} min_text={min(sizes):.2f}pt font_status={r['brand_font_status']}")
  return 0
 except Exception as e:return fail(str(e))
if __name__=='__main__':raise SystemExit(main())
