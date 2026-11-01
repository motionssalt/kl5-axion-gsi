import contextlib,pathlib,sys,tempfile,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import audit
class AuditSummaryTests(unittest.TestCase):
 def test_symlink_without_sha256_cannot_crash_gap_list(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'docs').mkdir()
   stock=[{'partition':p,'records':[{'partition':p,'path':'etc/test.xml','categories':['media'],'sha256':'stock-hash'}],'errors':[]} for p in ['vendor','product','system_ext']]
   base=[{'partition':'system','records':[{'partition':'system','path':'lib/libtest.so','categories':[],'symlink':'real.so'},{'partition':'system','path':'etc/base.xml','categories':['media'],'sha256':'base-hash'}],'errors':[]}]
   with contextlib.ExitStack() as stack:
    stack.enter_context(patch.object(audit,'ROOT',root));stack.enter_context(patch.object(audit,'collect',side_effect=[(stock,{}),(base,{})]))
    for name in ['clear','phase','blocker','notify','checkpoint','upload']:stack.enter_context(patch.object(audit,name))
    stack.enter_context(patch.object(audit,'release',return_value={}))
    audit.summarize()
   self.assertTrue((root/'docs/audit.json').exists())
if __name__=='__main__':unittest.main()
