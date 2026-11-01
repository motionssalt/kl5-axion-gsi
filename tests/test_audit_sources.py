import io,json,pathlib,sys,tempfile,unittest,zipfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import audit,common,emulator

class StockSelectionTests(unittest.TestCase):
 def test_scatter_parent_beats_optional_open(self):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:
   z.writestr('Firmware/Open/super.img',b'open')
   z.writestr('Firmware/MT6768_Android_scatter.txt','super.img')
   z.writestr('Firmware/super.img',b'canonical')
  with zipfile.ZipFile(b) as z:
   selected=audit.select_super(z)
   self.assertEqual(selected[0].filename,'Firmware/super.img')
 def test_shallow_super_fallback_without_scatter(self):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:
   z.writestr('firmware/Open/super.img',b'a');z.writestr('firmware/super.img',b'b')
  with zipfile.ZipFile(b) as z:self.assertEqual(audit.select_super(z)[0].filename,'firmware/super.img')
 def test_inventory_properties_and_hal(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d)/'mount';root.mkdir();out=pathlib.Path(d)/'out'
   (root/'build.prop').write_text('ro.build.version.sdk=36\n')
   (root/'manifest.xml').write_text('<manifest><hal format="hidl"><name>android.hardware.biometrics.fingerprint</name><version>2.1</version></hal></manifest>')
   result=audit.inspect_tree(root,'system',out)
   self.assertFalse(result['errors'])
   props=next(r for r in result['records'] if r['path']=='build.prop')
   self.assertEqual(props['properties']['ro.build.version.sdk'],'36')
   hal=next(r for r in result['records'] if r['path']=='manifest.xml')
   self.assertIn('fingerprint',hal['hal_declarations'][0])

class TelegramDeliveryTests(unittest.TestCase):
 def test_duplicate_media_not_resent(self):
  with tempfile.TemporaryDirectory() as d:
   f=pathlib.Path(d)/'home.png';f.write_bytes(b'png');digest=common.sha256(f)
   env={'TELEGRAM_BOT_TOKEN':'test-only','TELEGRAM_CHAT_ID':'test-only'}
   ledger={'telegram_deliveries':{'photo:home.png:'+digest:{}}}
   with patch.dict(common.os.environ,env),patch.object(common,'state',return_value=ledger),patch.object(common.requests,'post') as post:
    self.assertTrue(common.send_telegram_file(f,'test','photo'));post.assert_not_called()
 def test_failed_transport_redacts_exception(self):
  import requests
  with tempfile.TemporaryDirectory() as d:
   f=pathlib.Path(d)/'logcat.txt';f.write_text('public log')
   env={'TELEGRAM_BOT_TOKEN':'test-only','TELEGRAM_CHAT_ID':'test-only'}
   with patch.dict(common.os.environ,env),patch.object(common,'state',return_value={}),patch.object(common.requests,'post',side_effect=requests.RequestException('sensitive-url')),patch.object(common,'blocker') as block:
    self.assertFalse(common.send_telegram_file(f,'test','document'))
    self.assertNotIn('sensitive-url',str(block.call_args))

if __name__=='__main__':unittest.main()
