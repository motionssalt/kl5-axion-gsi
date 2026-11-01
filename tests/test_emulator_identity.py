import json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import emulator_system

class GuestIntegrationTests(unittest.TestCase):
 def test_legacy_system_override_uses_actual_gsi(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);image=p/'gsi.img';image.write_bytes(b'actual-gsi')
   args=emulator_system.system_args(p,image,p,'<name>system_image</name>',{})
   self.assertEqual(args,['--system_image='+str(image)])
   self.assertEqual(json.loads((p/'system-integration.json').read_text())['image_sha256'],emulator_system.sha256(image))
 def test_default_runtime_system_is_never_a_pass(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);image=p/'gsi.img';image.write_bytes(b'actual-gsi')
   with self.assertRaisesRegex(RuntimeError,'default AOSP boot is NOT accepted'):emulator_system.system_args(p,image,p,'',{})
 def test_fingerprint_taken_from_real_base_inventory(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'docs').mkdir();(p/'docs/audit.json').write_text(json.dumps({'base':[{'records':[{'properties':{'ro.system.build.fingerprint':'actual-axion-fingerprint'}}]}]}))
   with patch.object(emulator_system,'ROOT',p):self.assertEqual(emulator_system.expected_identity(),'actual-axion-fingerprint')
 def test_missing_fingerprint_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'docs').mkdir();(p/'docs/audit.json').write_text('{"base":[]}')
   with patch.object(emulator_system,'ROOT',p):
    with self.assertRaises(RuntimeError):emulator_system.expected_identity()

if __name__=='__main__':unittest.main()
