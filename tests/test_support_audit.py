import json,pathlib,sys,tempfile,unittest,zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from support_audit import inventory
class SupportAuditTests(unittest.TestCase):
 def test_shell_and_apex_container_discovery_without_payload_expansion(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d)/'system';out=pathlib.Path(d)/'out';(root/'system/bin').mkdir(parents=True);(root/'system/apex').mkdir()
   (root/'system/bin/rw-system.sh').write_text('#!/system/bin/sh\necho unchanged-base\n')
   (root/'system/bin/binary.sh').write_bytes(b'\x7fELF\0not-a-script')
   (root/'system/bin/link.sh').symlink_to('/etc/passwd')
   with zipfile.ZipFile(root/'system/apex/com.android.vndk.v31.apex','w') as z:
    z.writestr('apex_manifest.json',json.dumps({'name':'com.android.vndk.v31','version':1}));z.writestr('apex_payload.img',b'not-mounted')
   result=inventory(root,out)
   self.assertEqual([x['path'] for x in result['scripts']],['system/bin/rw-system.sh'])
   self.assertEqual(result['apex_containers'][0]['manifest_json']['name'],'com.android.vndk.v31')
   self.assertFalse(any(p.name=='apex_payload.img' for p in out.rglob('*')))
   self.assertEqual((out/'scripts/system/bin/rw-system.sh').read_bytes(),(root/'system/bin/rw-system.sh').read_bytes())
if __name__=='__main__':unittest.main()
