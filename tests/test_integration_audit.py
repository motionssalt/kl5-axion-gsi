import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from integration_audit import analyze,logical_path,property_lines

def record(part,path,**kw):return {'partition':part,'path':path,'categories':[],**kw}
def inv(part,records):return {'partition':part,'records':records}
class IntegrationTests(unittest.TestCase):
 def test_system_as_root_and_legacy_paths(self):
  self.assertEqual(logical_path(record('system','system/etc/test.xml')),'/system/etc/test.xml')
  self.assertEqual(logical_path(record('system','etc/test.xml')),'/system/etc/test.xml')
 def test_retained_vendor_include_not_reported_missing(self):
  src=record('vendor','etc/media_codecs.xml',evidence_file='v')
  result=analyze([inv('vendor',[src,record('vendor','etc/codecs.xml')])],[],{'v':'<MediaCodecs><Include href="codecs.xml"/></MediaCodecs>'},{})
  self.assertEqual(result['references'][0]['assessment'],'satisfied-by-base-or-retained-vendor')
 def test_explicit_stock_systemext_import_is_candidate(self):
  rc=record('vendor','etc/init/usb.rc',evidence_file='rc')
  target=record('system_ext','etc/init/hw/init.usb.rc')
  out=analyze([inv('vendor',[rc]),inv('system_ext',[target])],[],{'rc':'import /system_ext/etc/init/hw/init.usb.rc\n'},{})
  self.assertEqual(out['references'][0]['assessment'],'stock-system-side-target-absent-in-gsi')
  self.assertIn('mount_topology_warning',out)
 def test_unknown_target_not_a_proven_gap(self):
  rc=record('vendor','etc/init/test.rc',evidence_file='rc')
  out=analyze([inv('vendor',[rc])],[],{'rc':'import /system/etc/not-in-inventory.rc\n'},{})
  self.assertEqual(out['references'][0]['assessment'],'not-in-selective-inventory-not-proof-of-absence')
 def test_duplicate_properties_preserve_all_values(self):
  self.assertEqual([x['value'] for x in property_lines('ro.sdk=31\nro.sdk=34')['ro.sdk']],['31','34'])
 def test_32bit_provider_does_not_satisfy_64bit_consumer(self):
  consumer=record('vendor','lib64/libcamera.so',categories=['camera'],elf_class=64,needed=['libtest.so'])
  provider=record('system','system/lib/libtest.so',elf_class=32)
  result=analyze([inv('vendor',[consumer])],[inv('system',[provider])],{},{})
  self.assertEqual(result['native_dependencies'][0]['unresolved'][0]['elf_class'],64)
 def test_hidl_11_not_silently_changed_to_aidl(self):
  h=record('vendor','etc/vintf/manifest/c2.xml',hal_declarations=['<hal><name>android.hardware.media.c2</name><version>1.1</version><transport>hwbinder</transport><interface><name>IComponentStore</name><instance>default</instance></interface></hal>'])
  out=analyze([inv('vendor',[h])],[],{},{})
  self.assertEqual(out['hal_declarations']['stock'][0]['format'],'hidl')
  self.assertEqual(out['hal_declarations']['stock'][0]['versions'],['1.1'])
if __name__=='__main__':unittest.main()
