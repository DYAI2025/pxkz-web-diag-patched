#!/usr/bin/env python3
"""Fixture/offline Vibe-Check #03 observation, no networking or side effects.
Input: JSON run with `run_id`, `page_url`, `html`, `html_complete`, `observed_at`,
optional trusted `asset_results`, `unknown_route`, `ui_scenario`. Output: diagnostic JSON.
A rendered/audited external observation must have separately verified provenance.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT=Path(__file__).resolve().parents[1]
CAT=json.loads((ROOT/'assets/vibecheck03.check-catalog.v1.json').read_text())
FAMILIES={c['check_id']:[m['metric_id'] for m in c['metrics']] for c in CAT['checks']}
METRICS={m['metric_id']:(c['check_id'],m['type']) for c in CAT['checks'] for m in c['metrics']}
VERSION='vc03-offline-1.0.0'
HEAD_TAGS={'html','head','meta','link','title','style','script','base','noscript','template'}

class Parser(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.head=False;self.body=False;self.links=[];self.meta=[];self.images=[];self.anchors=[]
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=='head':self.head=True
  if tag=='body' or (not self.head and tag not in HEAD_TAGS):self.body=True;self.head=False
  # HTML5 allows an implied head: link/meta before <body> belong to it; in-body metadata does not count.
  in_head=self.head or not self.body
  if tag=='link' and in_head:self.links.append(d)
  if tag=='meta' and in_head:self.meta.append(d)
  if tag=='img':self.images.append(d)
  if tag=='a':self.anchors.append(d)
 def handle_endtag(self,tag):
  if tag=='head':self.head=False

def safe_public_url(url):
 """Conservative admission only; DNS/redirect safety must be handled by external acquisition."""
 from ipaddress import ip_address
 p=urlsplit(url)
 if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:return False
 h=p.hostname.lower().rstrip('.')
 if h=='localhost' or h.endswith('.localhost') or h.endswith('.local') or h.endswith('.internal'):return False
 try:return ip_address(h).is_global
 except ValueError:return True # DNS still requires revalidation by actual fetcher

def observe(data):
 url=data['page_url'];run=data['run_id'];at=data['observed_at'];html=data['html'];complete=data['html_complete']
 if 'ui_scenarios' in data:raise ValueError('unsupported input key ui_scenarios; supply one authorized ui_scenario object')
 if data.get('source_authority','STANDALONE_OFFLINE')!='STANDALONE_OFFLINE':raise ValueError('PXAPI_CANONICAL requires a verified versioned adapter; not supported by this collector')
 if not isinstance(complete,bool) or not safe_public_url(url) or not run or not at or not isinstance(html,str):raise ValueError('invalid page/run metadata')
 p=Parser();p.feed(html); source_hash=hashlib.sha256(html.encode()).hexdigest()
 results={};evidence=[]
 def emit(mid,val=None,known=False,reason=None,method='HTML_PARSE',scenario=None):
  typ=METRICS[mid][1]
  if known and (type(val) is not (bool if typ=='BOOLEAN' else int if typ=='INTEGER' else str)):
   raise ValueError('type mismatch '+mid)
  eid=f'{run}:{hashlib.sha256(url.encode()).hexdigest()[:12]}:{mid}'
  results[mid]={'metric_id':mid,'check_id':METRICS[mid][0],'type':typ,'status':'OBSERVED' if known else 'NOT_ASSESSED','value':val if known else None,'reason':None if known else (reason or 'NO_VERIFIED_OBSERVATION'),'run_id':run,'page_url':url,'observed_at':at if known else None,'collector_version':VERSION,'method':method,'evidence_ref':eid if known else None,'claim_boundary':'Markup or scenario evidence does not prove UX quality, legal compliance, SEO ranking or actual customer outcomes','manual_review_required':mid.startswith(('IMG_','UI_')),'customer_eligible':False,'scenario':scenario}
  if known:evidence.append({'id':eid,'run_id':run,'page_url':url,'method':method,'source_sha256':source_hash if method=='HTML_PARSE' else None})
 def link(rel):return [x for x in p.links if rel in str(x.get('rel') or '').casefold().split() and x.get('href')]
 icon=link('icon');apple=link('apple-touch-icon')
 emit('SITE_ICON_DECLARED',bool(icon),complete or bool(icon),reason='TRUNCATED_HTML')
 emit('APPLE_TOUCH_ICON_DECLARED',bool(apple),complete or bool(apple),reason='TRUNCATED_HTML')
 assets=data.get('asset_results') or {}
 for mid,items in [('SITE_ICON_FETCH_OK',icon),('OG_IMAGE_FETCH_OK',[])]:
  if mid=='OG_IMAGE_FETCH_OK':
   items=[{'href':x.get('content')} for x in p.meta if str(x.get('property') or '').casefold()=='og:image' and x.get('content')]
  hits=[urljoin(url,x['href']) for x in items]
  if mid=='SITE_ICON_FETCH_OK' and not hits:hits=[urljoin(url,'/favicon.ico')]
  admissible=[h for h in hits if safe_public_url(h)]
  verified=[assets[h] for h in admissible if h in assets and type(assets[h]) is bool]
  # declared private resource must not become a false missing image observation
  emit(mid,any(verified),bool(verified),reason='ASSET_NOT_VERIFIED_OR_BLOCKED',method='EXTERNAL_VERIFIED_ASSET')
 for key,mid in [('og:title','OG_TITLE_PRESENT'),('og:type','OG_TYPE_PRESENT'),('og:url','OG_URL_PRESENT'),('og:image','OG_IMAGE_PRESENT'),('og:description','OG_DESCRIPTION_PRESENT')]:
  matches=[x for x in p.meta if str(x.get('property') or '').casefold()==key]
  valid=[x for x in matches if str(x.get('content') or '').strip()]
  emit(mid,bool(valid),complete or bool(matches),reason='TRUNCATED_HTML')
 n=len(p.images);missing=sum('alt' not in x for x in p.images);empty=sum('alt' in x and x['alt']=='' for x in p.images)
 for mid,num in [('IMG_ELEMENT_COUNT',n),('IMG_ALT_MISSING_COUNT',missing),('IMG_ALT_EMPTY_COUNT',empty),('IMG_ALT_NONEMPTY_COUNT',n-missing-empty)]:emit(mid,num,complete,reason='TRUNCATED_HTML')
 route=data.get('unknown_route')
 route_ok=isinstance(route,dict) and route.get('authorized') is True and route.get('same_origin') is True and route.get('bounded') is True and type(route.get('http_status')) is int and route.get('url')!=url and urlsplit(route.get('url','')).netloc==urlsplit(url).netloc
 for mid in FAMILIES['VC03-03']:
  if mid=='UNKNOWN_ROUTE_HTTP_STATUS':emit(mid,route['http_status'] if route_ok else None,route_ok,reason='NO_AUTHORIZED_SAFE_PROBE',method='EXTERNAL_AUTHORIZED_404_SCENARIO',scenario=route.get('id') if isinstance(route,dict) else None)
  else:
   key='home_link_present' if mid=='ERROR_PAGE_HOME_LINK_PRESENT' else 'contact_link_present'
   yes=route_ok and type(route.get(key)) is bool
   emit(mid,route[key] if yes else None,yes,reason='ERROR_PAGE_NAV_NOT_OBSERVED',method='EXTERNAL_AUTHORIZED_404_SCENARIO')
 ui=data.get('ui_scenario')
 for mid,key in [('UI_LOADING_FEEDBACK_OBSERVED','loading_feedback'),('UI_ERROR_FEEDBACK_OBSERVED','error_feedback'),('UI_ERROR_RECOVERY_OBSERVED','recovery'),('UI_STATUS_ANNOUNCED_TO_A11Y_API','a11y_status_announced')]:
  good=isinstance(ui,dict) and ui.get('authorized') is True and ui.get('isolated') is True and ui.get('scenario_id') and ui.get('initial_state') and ui.get('action') and ui.get('observed_state') and type(ui.get(key)) is bool
  emit(mid,ui[key] if good else None,bool(good),reason='NO_SAFE_SCENARIO_OR_ACCESSIBILITY_EVIDENCE',method='EXTERNAL_ISOLATED_UI_SCENARIO',scenario=ui.get('scenario_id') if isinstance(ui,dict) else None)
 return {'schema_version':'1.0','catalog_version':CAT['catalog_version'],'run_id':run,'page_url':url,'sample_complete':complete,'source_sha256':source_hash,'source_authority':data.get('source_authority','STANDALONE_OFFLINE'),'observed_at':at,'families':FAMILIES,'metrics':[results[m] for m in METRICS],'evidence':evidence,'score_effect':'NONE','customer_findings':[],'limitations':['No live HTTP requests or browser actions are executed by this adapter.','Customer findings require independent evidence admission and strategic relevance.']}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('output');args=ap.parse_args()
 data=json.loads(Path(args.input).read_text());res=observe(data)
 from jsonschema import validate
 validate(res,json.loads((ROOT/'schemas/vibecheck03-diagnostics.schema.json').read_text()))
 Path(args.output).write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n')
 print('PASS: 20 diagnostics, score neutral')
if __name__=='__main__':main()
