import json,os,sqlite3,tempfile,time,unittest
from unittest.mock import patch
import sales_ai
class SalesTests(unittest.TestCase):
 def test_software_warranty_uses_approved_text(self):
  with patch.object(sales_ai,'api') as api:
   answer=sales_ai.answer('software warranty Android updates forever?', 'test','unused')
   self.assertIn('does not guarantee lifetime',answer)
   api.assert_not_called()
 def test_china_spec_regression_and_business_terms(self):
  data=sales_ai.get_chinese_specs('OPPO Find X10')
  self.assertTrue(data['verified'])
  self.assertEqual(data['model_code'],'PMW110')
  self.assertIn('8000 mAh',data['facts'])
  self.assertNotIn('4500',data['facts'])
  catalog=sales_ai.search_catalog('oppo find x10','phone')
  self.assertEqual(catalog['market'],'China')
  self.assertEqual(catalog['sale_type'],'preorder')
  self.assertEqual(catalog['delivery_days_to_sri_lanka'],15)
 def test_unsupported_battery_claim_is_not_sent(self):
  response={'output':[{'type':'message','content':[{'type':'output_text','text':'OPPO Find X10 battery 4500mAh'}]}]}
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'WHATSAPP_VERIFY_TOKEN':'test'}),patch.object(sales_ai,'api',return_value=response):
   result=sales_ai.answer('Find X10 battery?','customer',d+'/test.db')
   self.assertNotIn('4500',result)
   self.assertIn('verification',result)
 def test_catalog_then_spec_tool_sequence(self):
  tool=lambda name,args,cid:{'type':'function_call','name':name,'arguments':json.dumps(args),'call_id':cid}
  results=[{'output':[tool('search_catalog',{'query':'oppo find x10','category':'phone','max_lkr':0},'cat')]},{'output':[tool('get_chinese_specs',{'model':'OPPO Find X10'},'spec')]},{'output':[{'type':'message','content':[{'type':'output_text','text':'Chinese OPPO Find X10: battery 8000mAh. Preorder, 15 days.'}]}]}]
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'WHATSAPP_VERIFY_TOKEN':'test'}),patch.object(sales_ai,'api',side_effect=results):
   result=sales_ai.answer('Find X10 battery?','customer',d+'/test.db')
   self.assertIn('8000mAh',result)
   self.assertIn('oppo.com/cn/',result)
 def test_base_model_search_excludes_pro_and_normalizes_gb(self):
  data=sales_ai.search_catalog('OPPO Find X10 12GB 256GB','phone')
  self.assertGreater(data['total_matches'],0)
  self.assertTrue(all('pro' not in p['model'].lower() for p in data['variants']))
  self.assertTrue(all('x10e' not in p['model'].lower() for p in data['variants']))
 def test_price_table_uses_exact_catalog_rows(self):
  call={'type':'function_call','name':'search_catalog','arguments':json.dumps({'query':'vivo x300 ultra 12gb 256gb','category':'phone','max_lkr':0}),'call_id':'p'}
  results=[{'output':[call]},{'output':[{'type':'message','content':[{'type':'output_text','text':'Choose a colour.'}]}]}]
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'WHATSAPP_VERIFY_TOKEN':'test'}),patch.object(sales_ai,'api',side_effect=results):
   result=sales_ai.answer('price','customer',d+'/test.db')
   self.assertIn('Silver Tone | LKR 379,000',result)
   self.assertIn('Film Green | LKR 383,000',result)
   self.assertIn('delivery: 15 days',result)
 def test_catalog_exact_variant_and_conflict(self):
  r=sales_ai.search_catalog('vivo x300 ultra 12+256','phone')
  self.assertEqual(r['total_matches'],3)
  self.assertEqual({p for v in r['variants'] for p in v['prices_lkr']},{379000,383000})
  r=sales_ai.search_catalog('vivo x300 ultra 12+512 silver tone','phone')
  self.assertEqual(r['variants'][0]['prices_lkr'],[410000,411000])
  self.assertTrue(r['variants'][0]['price_needs_confirmation'])
 def test_unknown_and_budget(self):
  self.assertEqual(sales_ai.search_catalog('notarealmodel999')['total_matches'],0)
  for p in sales_ai.search_catalog('', 'phone',150000)['variants']:self.assertLessEqual(max(p['prices_lkr']),150000)
 def test_no_cost_data_in_customer_catalog(self):
  self.assertNotIn('CNY',json.dumps(sales_ai.CATALOG))
 def test_memory_isolation_expiry_and_delete(self):
  response={'output':[{'type':'message','content':[{'type':'output_text','text':'Welcome. Which phone?'}]}]}
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'WHATSAPP_VERIFY_TOKEN':'test'}),patch.object(sales_ai,'api',return_value=response) as api:
   db=d+'/test.db'
   sales_ai.answer('hi','+94111',db)
   sales_ai.answer('hi','+94222',db)
   self.assertNotIn('+94111',json.dumps(api.call_args.args))
   self.assertEqual(len(api.call_args.args[0]),1)
   sales_ai.answer('camera','+94111',db)
   self.assertEqual(len(api.call_args.args[0]),3)
   sales_ai.answer('forget','+94111',db)
   with sqlite3.connect(db) as c:
    self.assertEqual(c.execute('select count(*) from ai_history').fetchone()[0],2)
    c.execute('update ai_history set stamp=?',(int(time.time())-90000,))
   sales_ai.cleanup(db)
   with sqlite3.connect(db) as c:self.assertEqual(c.execute('select count(*) from ai_history').fetchone()[0],0)
 def test_ungrounded_price_falls_back(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'WHATSAPP_VERIFY_TOKEN':'test'}),patch.object(sales_ai,'api',return_value={'output':[{'type':'message','content':[{'type':'output_text','text':'Price Rs. 999,999'}]}]}):
   self.assertIn('contact our team',sales_ai.answer('price','customer',d+'/test.db'))
 def test_provider_failure_falls_back(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'WHATSAPP_VERIFY_TOKEN':'test'}),patch.object(sales_ai,'api',side_effect=TimeoutError):
   self.assertIn('contact our team',sales_ai.answer('hi','customer',d+'/test.db'))
if __name__=='__main__':unittest.main()
