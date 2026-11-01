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
 def test_supplemental_parallel_job_latest_status_is_not_lost(self):
  remote={'supplemental_base_audit':{'at':'2026-11-01T01:00:00+00:00','status':'done'}}
  local={'supplemental_base_audit':{'at':'2026-11-01T00:59:00+00:00','status':'running'}}
  self.assertEqual(merge_journals(remote,local,local)['supplemental_base_audit']['status'],'done')
if __name__=='__main__':unittest.main()
