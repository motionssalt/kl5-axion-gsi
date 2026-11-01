import hashlib,io,pathlib,sys,tarfile,tempfile,unittest,zipfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import emulator,emulator_runtime

class RuntimePinTests(unittest.TestCase):
 def test_android16_arm64_verified_from_properties(self):
  data=b'ro.build.version.sdk=36\nro.build.version.release=16\nro.product.cpu.abi=arm64-v8a\n'
  with patch.object(emulator_runtime,'PROP_SHA',hashlib.sha256(data).hexdigest()):self.assertEqual(emulator_runtime.validate_properties(data)['ro.build.version.sdk'],'36')
 def test_android17_not_silently_used(self):
  data=b'ro.build.version.sdk=37\nro.build.version.release=17\nro.product.cpu.abi=arm64-v8a\n'
  with patch.object(emulator_runtime,'PROP_SHA',hashlib.sha256(data).hexdigest()):
   with self.assertRaises(RuntimeError):emulator_runtime.validate_properties(data)
 def test_changed_upstream_build_properties_rejected(self):
  with self.assertRaises(RuntimeError):emulator_runtime.validate_properties(b'changed')
 def test_matching_host_and_guest_build_id(self):
  self.assertIn(emulator_runtime.BUILD,emulator_runtime.PINNED['images']['name'])
  self.assertIn('x86_64',emulator_runtime.PINNED['host']['name'])
  for p in emulator_runtime.PINNED.values():self.assertLess(p['size'],1_900_000_000)

class RuntimeArchiveTests(unittest.TestCase):
 def test_safe_internal_tar_symlink_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'host.tar.gz';out=pathlib.Path(d)/'out'
   with tarfile.open(p,'w:gz') as t:
    info=tarfile.TarInfo('bin/runtime');info.size=4;info.mode=0o755;t.addfile(info,io.BytesIO(b'test'))
    link=tarfile.TarInfo('bin/launcher');link.type=tarfile.SYMTYPE;link.linkname='runtime';t.addfile(link)
   emulator.unpack(p,out)
   self.assertTrue((out/'bin/launcher').is_symlink());self.assertEqual((out/'bin/launcher').read_bytes(),b'test')
 def test_escape_tar_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'host.tar.gz'
   with tarfile.open(p,'w:gz') as t:
    link=tarfile.TarInfo('bin/launcher');link.type=tarfile.SYMTYPE;link.linkname='../../../escape';t.addfile(link)
   with self.assertRaises(RuntimeError):emulator.unpack(p,pathlib.Path(d)/'out')
 def test_zip_executable_mode_restored(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'tools.zip';out=pathlib.Path(d)/'out'
   with zipfile.ZipFile(p,'w') as z:
    i=zipfile.ZipInfo('bin/tool');i.external_attr=0o100755<<16;z.writestr(i,b'tool')
   emulator.unpack(p,out);self.assertEqual((out/'bin/tool').stat().st_mode&0o777,0o755)

if __name__=='__main__':unittest.main()
