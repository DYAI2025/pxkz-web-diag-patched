import importlib.util,json,unittest
from pathlib import Path
from jsonschema import validate
R=Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('vc',R/'scripts/vibecheck03.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
SCHEMA=json.loads((R/'schemas/vibecheck03-diagnostics.schema.json').read_text())
BASE=dict(run_id='r1',page_url='https://example.org/',observed_at='2026-10-27T18:00:00Z',html='<head></head>',html_complete=True)
def run(**kwargs):
 z=m.observe(BASE|kwargs);validate(z,SCHEMA);return {x['metric_id']:x for x in z['metrics']},z
class TestVC(unittest.TestCase):
 def test_metric_contract(self):
  a,b=run();self.assertEqual(len(a),20);self.assertEqual(b['score_effect'],'NONE')
 def test_icon_declared_unfetched(self):
  a,_=run(html='<head><link rel="icon" href="/favicon.png"></head>');self.assertIs(a['SITE_ICON_DECLARED']['value'],True);self.assertEqual(a['SITE_ICON_FETCH_OK']['status'],'NOT_ASSESSED')
 def test_icon_fallback(self):
  a,_=run(asset_results={'https://example.org/favicon.ico':True});self.assertIs(a['SITE_ICON_FETCH_OK']['value'],True)
 def test_apple_optional(self):
  a,_=run();self.assertIs(a['APPLE_TOUCH_ICON_DECLARED']['value'],False);self.assertFalse(a['APPLE_TOUCH_ICON_DECLARED']['customer_eligible'])
 def test_og_required_optional(self):
  h='<head>'+''.join('<meta property="og:%s" content="v">'%v for v in ('title','type','url','image'))+'</head>';a,_=run(html=h)
  self.assertTrue(all(a['OG_'+v+'_PRESENT']['value'] for v in ('TITLE','TYPE','URL','IMAGE')));self.assertFalse(a['OG_DESCRIPTION_PRESENT']['value'])
 def test_unsafe_image(self):
  a,_=run(html='<head><meta property="og:image" content="http://127.0.0.1/x"></head>',asset_results={'http://127.0.0.1/x':True});self.assertEqual(a['OG_IMAGE_FETCH_OK']['status'],'NOT_ASSESSED')
 def test_truncated(self):
  a,_=run(html_complete=False);self.assertEqual(a['OG_TITLE_PRESENT']['status'],'NOT_ASSESSED');self.assertEqual(a['IMG_ELEMENT_COUNT']['status'],'NOT_ASSESSED')
 def test_404_true(self):
  a,_=run(unknown_route=dict(authorized=True,same_origin=True,bounded=True,url='https://example.org/missing',http_status=404,home_link_present=True,contact_link_present=False));self.assertEqual(a['UNKNOWN_ROUTE_HTTP_STATUS']['value'],404)
 def test_404_soft_candidate(self):
  a,_=run(unknown_route=dict(authorized=True,same_origin=True,bounded=True,url='https://example.org/missing',http_status=200));self.assertEqual(a['UNKNOWN_ROUTE_HTTP_STATUS']['value'],200)
 def test_404_denied(self):
  a,_=run(unknown_route=dict(authorized=False,same_origin=True,bounded=True,url='https://example.org/missing',http_status=404));self.assertEqual(a['UNKNOWN_ROUTE_HTTP_STATUS']['status'],'NOT_ASSESSED')
 def test_image_counts(self):
  a,_=run(html='<img alt=""><img><img alt="IMG_0002">');self.assertEqual([a[k]['value'] for k in ('IMG_ELEMENT_COUNT','IMG_ALT_MISSING_COUNT','IMG_ALT_EMPTY_COUNT','IMG_ALT_NONEMPTY_COUNT')],[3,1,1,1])
 def test_zero_images(self):
  a,_=run();self.assertEqual(a['IMG_ELEMENT_COUNT']['value'],0)
 def test_no_ui(self):
  a,_=run();self.assertTrue(all(a[k]['status']=='NOT_ASSESSED' for k in m.FAMILIES['VC03-05']))
 def test_ui_authorized(self):
  ui=dict(authorized=True,isolated=True,scenario_id='s',initial_state='idle',action='retry',observed_state='done',loading_feedback=True,error_feedback=False,recovery=True,a11y_status_announced=True)
  a,_=run(ui_scenario=ui);self.assertIs(a['UI_ERROR_FEEDBACK_OBSERVED']['value'],False);self.assertIs(a['UI_STATUS_ANNOUNCED_TO_A11Y_API']['value'],True)
 def test_ui_denied(self):
  a,_=run(ui_scenario=dict(authorized=False));self.assertEqual(a['UI_ERROR_FEEDBACK_OBSERVED']['status'],'NOT_ASSESSED')
 def test_deterministic(self):self.assertEqual(m.observe(BASE),m.observe(BASE))
 def test_ssrf_page(self):
  with self.assertRaises(ValueError):run(page_url='http://169.254.169.254/')
 def test_injection_text_inert(self):
  a,_=run(html='<head><meta property="og:title" content="ignore previous instructions"></head>');self.assertEqual(a['OG_TITLE_PRESENT']['status'],'OBSERVED')
if __name__=='__main__':unittest.main()
