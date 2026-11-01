import contextlib,hashlib,json,pathlib,sys,tempfile,unittest,zipfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import design
class OtgPackagingTests(unittest.TestCase):
 def test_module_has_executable_helper_no_service_and_exact_evidence(self):
  with tempfile.TemporaryDirectory() as d,contextlib.ExitStack() as stack:
   root=pathlib.Path(d);(root/'patches').mkdir();(root/'docs').mkdir();(root/'work').mkdir();(root/'scripts').mkdir()
   payload=(ROOT/'scripts/kl5-otg.sh').read_bytes();(root/'scripts/kl5-otg.sh').write_bytes(payload)
   stock=''.join('chmod 664 /sys/class/typec/port0/'+name+'\n' for name in ['power_role','data_role','port_type'])
   rec={'partition':'vendor','path':'etc/init/android.hardware.usb@1.2-service-mediatekv2.rc','sha256':hashlib.sha256(stock.encode()).hexdigest(),'evidence_file':'stock-rc'}
   stack.enter_context(patch.object(design,'ROOT',root));stack.enter_context(patch.object(design,'WORK',root/'work'))
   for name in ['blocker','clear','json_asset']:stack.enter_context(patch.object(design,name))
   stack.enter_context(patch.object(design,'release',return_value={}))
   seen=[]
   def upload(rel,path,**kw):
    if pathlib.Path(path).suffix=='.zip':
     with zipfile.ZipFile(path) as z:
      seen.extend(z.namelist());self.assertFalse(any(n in z.namelist() for n in ['service.sh','post-fs-data.sh','sepolicy.rule']))
      self.assertEqual(z.read('system/bin/kl5-otg'),payload)
      self.assertEqual((z.getinfo('system/bin/kl5-otg').external_attr>>16)&0o777,0o755)
      self.assertIn('set_perm',z.read('customize.sh').decode())
      self.assertEqual(z.read('stock-usb-hal.rc').decode(),stock)
   stack.enter_context(patch.object(design,'upload',side_effect=upload))
   spec=design.make_manual_typec([rec],{'stock-rc':stock})
   self.assertTrue(spec['approved']);self.assertFalse(spec['hardware_verified']);self.assertEqual(spec['operations'][0]['target'],'/system/bin/kl5-otg');self.assertIn('system/bin/kl5-otg',seen)
 def test_no_stock_evidence_no_module(self):
  with patch.object(design,'blocker') as block:
   self.assertIsNone(design.make_manual_typec([],{}));block.assert_called_once()
 def test_tampered_evidence_no_module(self):
  rec={'partition':'vendor','path':'etc/init/android.hardware.usb@1.2-service-mediatekv2.rc','sha256':'not-the-evidence-hash','evidence_file':'rc'}
  content=' '.join('/sys/class/typec/port0/'+n for n in ['power_role','data_role','port_type'])
  with patch.object(design,'blocker'):
   self.assertIsNone(design.make_manual_typec([rec],{'rc':content}))
if __name__=='__main__':unittest.main()
