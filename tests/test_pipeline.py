import hashlib,io,json,lzma,pathlib,struct,sys,tempfile,unittest,zipfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
import asset_tool,images,patch_image

class SparseTests(unittest.TestCase):
 def test_raw(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'raw'; data=b'rawtest'*100
   self.assertFalse(images.raw_from_stream(io.BytesIO(data),p)); self.assertEqual(p.read_bytes(),data)
 def test_sparse_raw_fill_hole(self):
  bs=4096
  header=struct.pack('<IHHHHIIII',0xed26ff3a,1,0,28,12,bs,3,3,0)
  raw=struct.pack('<HHII',0xcac1,0,1,12+bs)+b'A'*bs
  fill=struct.pack('<HHII',0xcac2,0,1,16)+b'BCDE'
  hole=struct.pack('<HHII',0xcac3,0,1,12)
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'raw'; self.assertTrue(images.raw_from_stream(io.BytesIO(header+raw+fill+hole),p)); self.assertEqual(p.read_bytes(),b'A'*bs+b'BCDE'*(bs//4)+b'\0'*bs)
 def test_truncated(self):
  header=struct.pack('<IHHHHIIII',0xed26ff3a,1,0,28,12,4096,1,1,0)
  raw=struct.pack('<HHII',0xcac1,0,1,4108)+b'A'
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RuntimeError): images.raw_from_stream(io.BytesIO(header+raw),pathlib.Path(d)/'raw')
 def test_unknown_chunk(self):
  header=struct.pack('<IHHHHIIII',0xed26ff3a,1,0,28,12,4096,1,1,0)
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RuntimeError): images.raw_from_stream(io.BytesIO(header+struct.pack('<HHII',1,0,1,12)),pathlib.Path(d)/'raw')

class PatchTests(unittest.TestCase):
 def patchspec(self,folder):
  (folder/'payload').write_text('safe config\n'); h=hashlib.sha256(b'safe config\n').hexdigest()
  return {'id':'test','approved':True,'_folder':str(folder),'operations':[{'target':'/system/etc/test.xml','source':'payload','sha256':h,'expected_before':None,'mode':'0644','uid':0,'gid':0,'selinux':'u:object_r:system_file:s0'}]}
 def test_plan_apply_skip_conflict(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d); m=root/'mount'; m.mkdir(); (m/'etc').mkdir(); f=root/'patch'; f.mkdir(); spec=self.patchspec(f)
   ops,report=patch_image.plan(m,[spec]); self.assertEqual(len(ops),1); self.assertEqual(report[0]['status'],'applied')
   (m/'etc/test.xml').write_text('safe config\n'); ops,report=patch_image.plan(m,[spec]); self.assertFalse(ops); self.assertEqual(report[0]['status'],'skipped')
   (m/'etc/test.xml').write_text('upstream changed'); ops,report=patch_image.plan(m,[spec]); self.assertEqual(report[0]['status'],'conflicted')
 def test_proposal_never_applies(self):
  with tempfile.TemporaryDirectory() as d:
   ops,report=patch_image.plan(pathlib.Path(d),[{'id':'proposed','approved':False}]); self.assertFalse(ops); self.assertEqual(report[0]['status'],'skipped')
 def test_path_escape_and_symlink(self):
  with tempfile.TemporaryDirectory() as d:
   m=pathlib.Path(d); (m/'etc').symlink_to('/tmp')
   for target in ['/vendor/etc/test','/system/../vendor/evil','/system/etc/evil']:
    with self.assertRaises(RuntimeError): patch_image.safe_target(m,target)
 def test_corrupt_payload(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d); f=root/'patch'; f.mkdir(); spec=self.patchspec(f); (f/'payload').write_text('changed')
   with self.assertRaises(RuntimeError): patch_image.plan(root,[spec])

class AssetTests(unittest.TestCase):
 def test_split_join_and_corruption(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d); source=root/'input'; source.write_bytes(b'abcdefghij'*50)
   with patch.object(asset_tool,'LIMIT',91): asset_tool.split(source,root/'parts','stock-part')
   manifest=root/'parts/stock-manifest.json'; out=root/'rejoined'; asset_tool.verify(manifest,str(out)); self.assertEqual(source.read_bytes(),out.read_bytes())
   (root/'parts/stock-part-0002').write_bytes(b'corrupt')
   with self.assertRaises(RuntimeError): asset_tool.verify(manifest,str(root/'bad'))
   self.assertFalse((root/'bad').exists()); self.assertFalse((root/'bad.unverified').exists())
 def test_avb_footer(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'image'; p.write_bytes(b'A'*8192+struct.pack('>4sIIQQQ28s',b'AVBf',1,0,8192,8192,0,b'\0'*28))
   with patch.object(patch_image,'decision') as dec: patch_image.strip_avb(p)
   self.assertEqual(p.stat().st_size,8192)
 def test_no_embedded_credentials(self):
  import re
  patterns=[r'github_pat_[A-Za-z0-9_]{20,}',r'ghp_[A-Za-z0-9]{25,}',r'\b\d{8,12}:AA[A-Za-z0-9_-]{25,}']
  for folder in ['scripts','.github','docs','patches']:
   for p in (ROOT/folder).rglob('*'):
    if p.is_file() and '__pycache__' not in str(p):
     text=p.read_text(errors='replace')
     for pattern in patterns: self.assertIsNone(re.search(pattern,text),str(p))

if __name__=='__main__': unittest.main()
