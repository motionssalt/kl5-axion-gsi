import os,pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ManualOtgTests(unittest.TestCase):
 def fixture(self,root,device='TECNO-KL5',board='mt6768',initial='dual'):
  port=root/'typec/port0';port.mkdir(parents=True);(port/'port_type').write_text(initial);(port/'power_role').write_text('[source] sink');(port/'data_role').write_text('[host] device')
  tools=root/'tools';tools.mkdir()
  for name,body in [('id','echo 0'),('getprop',f'case "$1" in ro.product.vendor.device) echo {device};; ro.board.platform) echo {board};; esac')]:
   f=tools/name;f.write_text('#!/bin/sh\n'+body+'\n');f.chmod(0o755)
  src=(ROOT/'scripts/kl5-otg.sh').read_text()
  # Redirect hardware paths only in this test copy, never in the shipped helper.
  src=src.replace('/sys/class/typec',str(root/'typec')).replace('/data/adb/kl5-otg-manual',str(root/'state')).replace('/sys/class/power_supply',str(root/'power')).replace('/sys/bus/usb/devices',str(root/'devices'))
  helper=root/'helper';helper.write_text(src)
  env=os.environ.copy();env['PATH']=str(tools)+':'+env['PATH']
  return helper,port,env
 def run_helper(self,helper,env,action):return subprocess.run(['sh',str(helper),action],env=env,capture_output=True,text=True)
 def test_on_off_restore_without_boot_daemon(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);helper,port,env=self.fixture(root)
   for action,value in [('on','source'),('off','sink'),('restore','dual')]:
    p=self.run_helper(helper,env,action);self.assertEqual(p.returncode,0,p.stderr+p.stdout);self.assertEqual((port/'port_type').read_text().strip(),value)
   self.assertFalse((root/'state/original-port-type').exists())
 def test_connected_partner_refuses_source(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);helper,port,env=self.fixture(root);(root/'typec/port0-partner').mkdir()
   p=self.run_helper(helper,env,'on');self.assertNotEqual(p.returncode,0);self.assertEqual((port/'port_type').read_text(),'dual')
 def test_external_power_refuses_source(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);helper,port,env=self.fixture(root);(root/'power/usb').mkdir(parents=True);(root/'power/usb/online').write_text('1')
   self.assertNotEqual(self.run_helper(helper,env,'on').returncode,0);self.assertEqual((port/'port_type').read_text(),'dual')
 def test_other_device_never_written(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);helper,port,env=self.fixture(root,device='OTHER')
   self.assertNotEqual(self.run_helper(helper,env,'on').returncode,0);self.assertEqual((port/'port_type').read_text(),'dual')
 def test_unknown_port_type_never_written(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);helper,port,env=self.fixture(root,initial='unexpected')
   self.assertNotEqual(self.run_helper(helper,env,'on').returncode,0);self.assertEqual((port/'port_type').read_text(),'unexpected')
 def test_active_bracketed_type_is_saved(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);helper,port,env=self.fixture(root,initial='source sink [dual]')
   self.assertEqual(self.run_helper(helper,env,'on').returncode,0)
   self.assertEqual((root/'state/original-port-type').read_text().strip(),'dual')
 def test_no_background_or_policy_bypass(self):
  src=(ROOT/'scripts/kl5-otg.sh').read_text()
  self.assertNotIn('setenforce',src);self.assertNotIn('resetprop',src);self.assertNotIn('service.sh',src);self.assertNotIn('while ',src);self.assertNotIn('setprop ',src)
if __name__=='__main__':unittest.main()
