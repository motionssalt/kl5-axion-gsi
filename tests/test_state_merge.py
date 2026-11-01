import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from common import merge_journals
class JournalTests(unittest.TestCase):
 def test_concurrent_decisions_and_receipts_retained(self):
  remote={'phase':'3','decisions':[{'decision':'remote'}],'telegram_deliveries':{'r':{}}}
  local={'phase':'4','decisions':[{'decision':'local'}],'telegram_deliveries':{'l':{}}}
  merged=merge_journals(remote,local,local)
  self.assertEqual(merged['phase'],'4');self.assertEqual(len(merged['decisions']),2);self.assertEqual(set(merged['telegram_deliveries']),{'r','l'})
 def test_merge_is_idempotent(self):
  s={'decisions':[{'decision':'same'}],'releases':[{'tag':'one'}]}
  self.assertEqual(merge_journals(s,s,s),s)
if __name__=='__main__':unittest.main()
