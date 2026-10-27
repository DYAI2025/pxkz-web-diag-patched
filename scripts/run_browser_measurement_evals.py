#!/usr/bin/env python3
"""Browser-runtime eval for Pixelkiez privacy/accessibility enrichment.

The eval distinguishes an implementation failure from a host/runtime policy that
prevents Chromium navigation. A blocked host is evidence, not a synthetic PASS.
"""
from __future__ import annotations
import json, tempfile, threading, socket, shutil
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from functools import partial

from browser_measurements import collect_browser_metrics
from measurement_enrichment import bundle, source_record

ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    fixture=(ROOT/'evals/fixtures/browser-consent-accessibility.html').read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='pxk-browser-eval-') as td:
        td=Path(td)
        handler=partial(SimpleHTTPRequestHandler,directory=str(td))
        server=ThreadingHTTPServer(('0.0.0.0',0),handler)
        port=server.server_address[1]
        (td/'index.html').write_text(fixture.replace('__PORT__',str(port)),encoding='utf-8')
        (td/'pixel.gif').write_bytes(b'GIF89a')
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            probe=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            try:
                probe.connect(('8.8.8.8',80)); host=probe.getsockname()[0]
            finally:
                probe.close()
            url=f'http://{host}:{port}/index.html'
            try:
                metrics,details=collect_browser_metrics(url,wait_ms=100,timeout_ms=10000,keyboard_steps=8)
            except Exception as exc:
                message=str(exc)
                blocked="ERR_BLOCKED_BY_ADMINISTRATOR" in message
                report={
                  'schema_version':'1.0',
                  'status':'BLOCKED_RUNTIME_POLICY' if blocked else 'FAIL',
                  'checks':{
                    'playwright_import_available': _module_available('playwright'),
                    'chromium_executable_available': bool(shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')),
                    'browser_navigation_executed': False,
                  },
                  'metric_count':0,
                  'axe_runtime':'OPTIONAL_NOT_REQUIRED_FOR_BASE_EVAL',
                  'runtime_error':message,
                  'runtime_policy_note':(
                    'Chromium navigation is blocked by the execution environment. '
                    'Do not claim live browser validation until the skill is run in a runtime that permits navigation.'
                    if blocked else 'Browser runtime failed before deterministic measurements completed.'
                  ),
                }
                out=ROOT/'reports/browser-measurement-eval-results.json'
                out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                print(f"{report['status']}: {message}")
                return 2 if blocked else 1
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)
    idx={m['id']:m for m in metrics}
    checks={
      'third_party_prechoice_observed': idx['PRIVACY_THIRD_PARTY_REQUESTS_PRECHOICE']['value'] >= 1,
      'cookie_prechoice_observed': idx['PRIVACY_COOKIES_PRECHOICE']['value'] >= 1,
      'storage_prechoice_observed': idx['PRIVACY_STORAGE_ITEMS_PRECHOICE']['value'] >= 1,
      'accept_control_observed': idx['CONSENT_ACCEPT_CONTROL_FOUND']['value'] is True,
      'reject_control_observed': idx['CONSENT_REJECT_CONTROL_FOUND']['value'] is True,
      'unnamed_control_observed': idx['A11Y_UNNAMED_CONTROLS']['value'] >= 1,
      'mobile_overflow_observed': idx['MOBILE_HORIZONTAL_OVERFLOW_PX']['value'] > 0,
      'a11y_manual_boundary': all(m['manual_review_required'] for m in metrics if m['id'].startswith('A11Y_') or m['id']=='MOBILE_HORIZONTAL_OVERFLOW_PX'),
      'privacy_legal_boundary': all(m['legal_review_required'] for m in metrics if m['id'].startswith('PRIVACY_') or m['id'].startswith('CONSENT_')),
    }
    status='PASS' if all(checks.values()) else 'FAIL'
    report={'schema_version':'1.0','status':status,'checks':checks,'metric_count':len(metrics),'axe_runtime':'OPTIONAL_NOT_REQUIRED_FOR_BASE_EVAL','details':details}
    out=ROOT/'reports/browser-measurement-eval-results.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    b=bundle('http://container.local/local-fixture','FIXTURE',[source_record('browser','Chromium/Playwright local fixture','AVAILABLE','deterministic local browser eval')],metrics)
    (ROOT/'reports/browser-measurement-enrichment.fixture.json').write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if status!='PASS':
        print('FAIL: '+json.dumps({k:v for k,v in checks.items() if not v})); return 1
    print(f'PASS: browser measurement eval metrics={len(metrics)}')
    return 0


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False

if __name__=='__main__': raise SystemExit(main())
