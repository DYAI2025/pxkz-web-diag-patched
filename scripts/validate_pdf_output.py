#!/usr/bin/env python3
"""Validate the chart-led Pixelkiez customer presentation PDF."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
from pypdf import PdfReader
FORBIDDEN=["TECHNISCHER ANHANG","ID METRIK KLASSE EVIDENZ SCORE WERT","MISSING / SOURCE_NEEDED","not_assessed"]
JARGON=re.compile(r"\b(?:Raw DOM|JSON-LD|LCP|INP|CLS|TTFB|CTA|SERP)\b",re.I)
MM=72/25.4
def fail(m):print('FAIL: '+m,file=sys.stderr);return 1
def layout_errors(pdf):
 """Footer clearance: no body text or card may reach into the footer band (fixed-height pages clip silently).
 The footer is identified by its template signature (a bottom line carrying the page number), not by position,
 so body text pushed into the bottom band cannot be mistaken for the footer."""
 import fitz
 errors=[]
 for no,page in enumerate(fitz.open(str(pdf)),1):
  h,w=page.rect.height,page.rect.width
  spans=[s for b in page.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text'].strip()]
  marks=[s['bbox'][1] for s in spans if s['text'].strip()==f'{no:02d}' and s['bbox'][1]>h-15*MM]
  ftop=min(marks) if marks else h-10*MM
  body=[s['bbox'][3] for s in spans if abs(s['bbox'][1]-ftop)>0.5*MM or not marks]
  limit=ftop-1.5*MM
  shapes=[d['rect'].y1 for d in page.get_drawings() if d['rect'].y0<limit and d['rect'].height<h*0.9 and d['rect'].width<w*0.95]
  low=max(body+shapes,default=0)
  if low>limit:errors.append(f'page {no}: content ends at {low/MM:.1f}mm, footer clearance limit {limit/MM:.1f}mm')
 return errors
def lever_page_errors(pdf,findings,squash):
 """Every lever field must be on the lever page itself; the roadmap repeats headlines/actions elsewhere."""
 import fitz
 pages=[squash(page.get_text()) for page in fitz.open(str(pdf))]
 hits=[i for i,t in enumerate(pages) if squash('Vier konkrete Hebel') in t]
 if len(hits)!=1:return [f'expected exactly one lever page, found {len(hits)}']
 text=pages[hits[0]]
 return [f'lever {f.get("id")} {k} not visible on lever page {hits[0]+1}' for f in findings for k in ('headline','observation','impact','action') if squash(f.get(k,'')) not in text]
def main(argv):
 if len(argv)!=3:return fail('usage: validate_pdf_output.py <output.pdf> <client-report-model.json>')
 pdf,modelp=map(lambda x:Path(x).resolve(),argv[1:])
 if not pdf.is_file() or pdf.stat().st_size<20000:return fail('PDF missing or implausibly small')
 try:
  model=json.loads(modelp.read_text(encoding='utf-8')); reader=PdfReader(str(pdf)); base=modelp.parent
  plan=json.loads((base/'visualization-plan.json').read_text(encoding='utf-8')); receipt=json.loads((base/'presentation-render-receipt.json').read_text(encoding='utf-8'))
 except Exception as e:return fail(str(e))
 if not 8<=len(reader.pages)<=12:return fail(f'customer PDF page count must be 8-12, got {len(reader.pages)}')
 box=reader.pages[0].mediabox
 if float(box.width)<=float(box.height):return fail('PDF must be landscape')
 if receipt.get('renderer')!='WEASYPRINT' or receipt.get('embedded_visual_count',0)<4:return fail('WeasyPrint receipt/visual count invalid')
 if len(plan.get('top_levers',[]))!=4:return fail('exactly four top levers required')
 text='\n'.join(page.extract_text() or '' for page in reader.pages);fold=text.casefold()
 required=['Pixelkiez','Website-Analyse','Vier konkrete Hebel','Roadmap','Nächster Schritt',str(model.get('meta',{}).get('customer',''))]
 miss=[x for x in required if x and x.casefold() not in fold]
 if miss:return fail('missing presentation markers: '+', '.join(miss))
 if 'beweist nicht:' in re.sub(r'\s+', ' ', text).casefold():return fail('internal chart evidence-boundary boilerplate leaked into customer PDF')
 hits=[x for x in FORBIDDEN if x.casefold() in fold]
 if hits:return fail('internal material leaked: '+', '.join(hits))
 m=JARGON.search(text)
 if m:return fail('customer jargon leaked: '+m.group(0))
 # pypdf emits kerning gaps anywhere, even inside words ("t erminvereinbarung", "lesbar , aber"); compare copy
 # without whitespace. Probes are whole lever fields (20-135 chars), so cross-word false matches are negligible.
 def squash(value):
  return re.sub(r"\s+", "", str(value)).casefold()
 normalized = squash(text)
 for finding in model.get('findings',[])[:4]:
  probe = squash(finding.get('headline','')).strip()
  if not probe or probe not in normalized:return fail('lever headline missing: '+str(finding.get('id')))
 try:
  layout=layout_errors(pdf)+lever_page_errors(pdf,model.get('findings',[])[:4],squash)
 except Exception as e:return fail(f'layout clearance check unavailable: {e}')
 if layout:return fail('layout overlap: '+'; '.join(layout))
 meta=reader.metadata or {}
 if 'Pixelkiez' not in str(meta.get('/Author','')):return fail('PDF author metadata must contain Pixelkiez')
 print(f"PASS: chart-led customer PDF pages={len(reader.pages)} embedded_visuals={receipt['embedded_visual_count']} levers=4")
 return 0
if __name__=='__main__':raise SystemExit(main(sys.argv))
