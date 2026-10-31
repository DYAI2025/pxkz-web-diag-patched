#!/usr/bin/env python3
"""Bounded public read-only capture for active Core. Outputs raw evidence, not metric scores."""
from __future__ import annotations
import hashlib
import ipaddress
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime,timezone
from typing import Any

USER_AGENT='PixelkiezWebsiteDiagnosis/CoreEvidence/1.0 (public read-only audit)'

def now()->str:return datetime.now(timezone.utc).isoformat()

def check_public(url:str)->None:
    p=urllib.parse.urlsplit(url)
    if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password:
        raise ValueError('PUBLIC_URL_REQUIRED')
    hostname=p.hostname.lower().rstrip('.')
    if hostname in {'localhost','localhost.localdomain'} or hostname.endswith(('.local','.internal','.localhost','.test')):
        raise ValueError('PRIVATE_HOST_BLOCKED')
    try:entries=socket.getaddrinfo(hostname,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)
    except Exception as exc:raise ValueError(f'PUBLIC_HOST_DNS_UNAVAILABLE: {type(exc).__name__}') from exc
    ips={i[4][0] for i in entries}
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError('PRIVATE_OR_NON_GLOBAL_ADDRESS_BLOCKED')

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        check_public(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def public_fetch(url:str,max_bytes:int=1048576,timeout:float=20)->tuple[dict[str,Any],bytes]:
    check_public(url)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),SafeRedirect())
    req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'text/html,application/xhtml+xml,*/*;q=0.5'},method='GET')
    try:resp=opener.open(req,timeout=timeout)
    except urllib.error.HTTPError as exc:resp=exc
    with resp:
        data=resp.read(max_bytes+1)
        if len(data)>max_bytes:raise ValueError('MAX_RESPONSE_BYTES_EXCEEDED')
        observed=resp.geturl();check_public(observed)
        headers={k.lower():v[:250] for k,v in resp.headers.items() if k.lower() in {'content-type','content-length','cache-control','content-encoding','content-security-policy','x-frame-options','location','vary','last-modified','etag','x-content-type-options','server'}}
        info={'requested_url':url,'observed_url':observed,'status_code':resp.status,'headers':headers,'body_sha256':hashlib.sha256(data).hexdigest(),'body_bytes':len(data),'captured_at':now()}
        return info,data

def normalize_exception(e:Exception)->str:
    return f'{type(e).__name__}: {str(e)[:350]}'

def http_capture(url:str)->dict:
    info,body=public_fetch(url)
    return {'outcome':'SUCCESS_RAW','observed_url':info['observed_url'],'artifacts':[('http_response',json.dumps(info,sort_keys=True,ensure_ascii=False).encode())]+([('html',body)] if body else []),'tool_name':'python-urllib','tool_version':sys.version.split()[0],'exit_code':0,'reason':f"HTTP response status {info['status_code']} captured without score"}

def browser_capture(url:str)->dict:
    check_public(url)
    from browser_measurements import _chromium_path, _dom_accessibility_snapshot
    from playwright.sync_api import sync_playwright
    chromium=_chromium_path()
    if not chromium:raise RuntimeError('CHROMIUM_NOT_INSTALLED')
    viewports=[('mobile',390,844),('desktop',1280,900)]
    artifacts=[];observed=url;records=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, executable_path=chromium, args=['--no-sandbox','--disable-dev-shm-usage'])
        try:
            for key,width,height in viewports:
                context=browser.new_context(viewport={'width':width,'height':height})
                page=context.new_page()
                try:
                    def route_guard(route):
                        try:check_public(route.request.url)
                        except Exception:
                            route.abort('blockedbyclient');return
                        route.continue_()
                    page.route('**/*',route_guard)
                    response=page.goto(url,wait_until='domcontentloaded',timeout=20000)
                    observed=page.url;check_public(observed)
                    dom=page.content()
                    snapshot=_dom_accessibility_snapshot(page)
                    screen=page.screenshot(full_page=False,type='png')
                    artifacts.append(('screenshot',screen))
                    records.append({'device':key,'viewport':{'width':width,'height':height},'url':observed,'http_status':response.status if response else None,'dom':dom[:500000], 'accessibility_snapshot':snapshot})
                finally:context.close()
        finally:browser.close()
    artifacts.append(('dom',json.dumps({'requested_url':url,'observed_url':observed,'records':records},ensure_ascii=False).encode()))
    artifacts.append(('viewport',json.dumps({'requested_url':url,'observed_url':observed,'viewports':[r['viewport'] for r in records]},ensure_ascii=False).encode()))
    return {'outcome':'SUCCESS_RAW','observed_url':observed,'artifacts':artifacts,'tool_name':'playwright-chromium','tool_version':str(subprocess.run([chromium,'--version'],text=True,capture_output=True,timeout=8).stdout.strip())[:120] or 'binary-executed','exit_code':0,'reason':'Two read-only public DOM/viewport captures; no form submission or scoring'}

def lighthouse_capture(url:str,form_factor:str)->dict:
    check_public(url)
    executable=shutil.which('lighthouse')
    if not executable:raise FileNotFoundError('lighthouse CLI not installed')
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'lighthouse.json'
        command=[executable,url,'--only-categories=performance','--output=json','--output-path='+str(out),'--quiet','--chrome-flags=--headless --no-sandbox']
        if form_factor=='desktop':command.append('--preset=desktop')
        result=subprocess.run(command,capture_output=True,text=True,timeout=120)
        if result.returncode!=0 or not out.is_file():raise RuntimeError(f'LIGHTHOUSE_EXIT_{result.returncode} {result.stderr[-350:]}')
        raw=out.read_bytes()
    data=json.loads(raw)
    if not isinstance(data.get('lighthouseVersion'),str) or not data.get('audits'):
        raise RuntimeError('LIGHTHOUSE_SCHEMA_INCOMPLETE')
    return {'outcome':'SUCCESS_RAW','observed_url':url,'artifacts':[('lab_json',raw)],'tool_name':'lighthouse-cli','tool_version':data['lighthouseVersion'],'exit_code':0,'reason':f'{form_factor} lab report; cannot substitute field experience'}

def google_capture(url:str,adapter:str,form_factor:str)->dict:
    # Use the existing, approved enrichment adapters; do not copy credential fields into artifacts.
    from measurement_adapters import fetch_crux,fetch_pagespeed
    api_key=os.getenv('PIXELKIEZ_PAGESPEED_API_KEY')
    if not api_key:raise PermissionError('PIXELKIEZ_PAGESPEED_API_KEY not configured')
    check_public(url)
    try:
        if adapter=='PUBLIC_CRUX':
            obj,records=fetch_crux(url,api_key,'PHONE')
            tool='chrome-ux-report-api'
        else:
            obj,records=fetch_pagespeed(url,api_key,form_factor)
            tool='pagespeed-insights-api'
    except urllib.error.HTTPError as exc:
        if exc.code!=404 or adapter!='PUBLIC_CRUX':
            raise
        # The actual provider 404 response is a negative field-data observation,
        # not a numeric zero and not a license to score lab data as real users.
        evidence={'requested_url':url,'observed_url':url,'status_code':404,
                  'provider':'CrUX','source_absence_marker':'HTTP_404_FROM_CRUX_API',
                  'observed_at':now()}
        return {'outcome':'SOURCE_ABSENT','observed_url':url,
                'artifacts':[('provider_response',json.dumps(evidence,ensure_ascii=False).encode())],
                'tool_name':'chrome-ux-report-api','tool_version':'HTTP-API','exit_code':0,
                'reason':'Provider explicitly returned HTTP 404 for this URL/form-factor; no field p75 asserted'}
    if not records:
        # Zero normalized records can also mean a parser mismatch; do not assert absent field data.
        # Real SOURCE_ABSENT requires the explicit provider 404 observed above.
        return {'outcome':'TOOL_FAILURE','observed_url':url,
                'artifacts':[('provider_response',json.dumps({'requested_url':url,'observed_url':url,'provider_response':obj,'records':[]},ensure_ascii=False).encode()),
                             ('tool_log',b'NORMALIZATION_NO_SUPPORTED_RECORDS: provider response retained; source absent is not proven')],
                'tool_name':tool,'tool_version':str(obj.get('version') or 'provider-response'), 'exit_code':2,
                'reason':'No supported observations normalized; tool/parser compatibility unverified'}
    payload={'requested_url':url,'observed_url':url,'provider_response':obj,'records':records}
    return {'outcome':'SUCCESS_RAW','observed_url':url,'artifacts':[('provider_response',json.dumps(payload,ensure_ascii=False).encode())],'tool_name':tool,'tool_version':str(obj.get('version') or 'provider-response'),'exit_code':0,'reason':'Provider response captured; field/lab distinction retained'}
