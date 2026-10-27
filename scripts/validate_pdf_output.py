#!/usr/bin/env python3
"""Validate the chart-led Pixelkiez customer presentation PDF."""
from __future__ import annotations
import json,re,sys
from pathlib import Path
from pypdf import PdfReader
FORBIDDEN=["TECHNISCHER ANHANG","ID METRIK KLASSE EVIDENZ SCORE WERT","MISSING / SOURCE_NEEDED","not_assessed"]
JARGON=re.compile(r"\b(?:Raw DOM|JSON-LD|LCP|INP|CLS|TTFB|CTA|SERP)\b",re.I)
def fail(m):print('FAIL: '+m,file=sys.stderr);return 1
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
 normalized = re.sub(r"\s+", " ", text).casefold()
 for finding in model.get('findings',[])[:4]:
  headline = re.sub(r"\s+", " ", str(finding.get('headline',''))).casefold()
  probe = headline[:36].rstrip()
  if probe and probe not in normalized:return fail('lever headline missing: '+str(finding.get('id')))
 meta=reader.metadata or {}
 if 'Pixelkiez' not in str(meta.get('/Author','')):return fail('PDF author metadata must contain Pixelkiez')
 print(f"PASS: chart-led customer PDF pages={len(reader.pages)} embedded_visuals={receipt['embedded_visual_count']} levers=4")
 return 0
if __name__=='__main__':raise SystemExit(main(sys.argv))
