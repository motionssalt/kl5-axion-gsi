import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from runner import owned_blockers
class StageOwnershipTests(unittest.TestCase):
 def test_unrelated_emulator_issue_does_not_block_stock_audit(self):
  self.assertEqual(owned_blockers('stock-audit',[{'id':'emulator-artifact-pin'}]),[])
 def test_unchanged_summary_issue_still_blocks_summary(self):
  self.assertEqual(owned_blockers('summary',[{'id':'summary-audit'}]),['summary-audit'])
 def test_hardware_uncertainty_does_not_prevent_packaging_helper(self):
  self.assertEqual(owned_blockers('build',[{'id':'otg-hardware'},{'id':'hardware-compatibility'}]),[])
 def test_process_failure_is_owned(self):
  self.assertEqual(owned_blockers('design',[{'id':'stage-design'}]),['stage-design'])
if __name__=='__main__':unittest.main()
