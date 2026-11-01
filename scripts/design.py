#!/usr/bin/env python3
"""Evidence-gated additions only; experimental manual helper is never a hardware fix."""
import hashlib, json, pathlib, re, xml.etree.ElementTree as ET, zipfile
from common import *
from audit import collect

def design():
 auditpath=ROOT/'docs/audit.json'
 if not auditpath.exists(): raise RuntimeError('No static audit exists; speculative compatibility fixes are prohibited')
 audit=json.loads(auditpath.read_text()); stock,text=collect('stock'); base,basetext=collect('base')
 stockrecords=[r for x in stock for r in x['records']]; baserecords=[r for x in base for r in x['records']]
 sdk={rec.get('properties',{}).get('ro.build.version.sdk') for rec in baserecords}
 if '36' not in sdk: raise RuntimeError('Base Android API 36 was not verified from build.prop; no compatibility patches approved for an unrecognized framework version')
 def systempath(r):
  if r['partition']!='system': return None
  p=r['path']; return '/'+p if p.startswith('system/') else '/system/'+p
 basepaths={systempath(r) for r in baserecords}
 approved=[]; proposals=[]
 for gap in audit['gap_list']:
  patch={'id':f'{gap["rank"]:04d}-{gap["category"]}','status':'proposed','approved':False,'reason':'Stock-only file differences are insufficient to prove system-side incompatibility. Preserve base performance behavior.','evidence':gap['stock_different_or_absent_in_base'][:100],'operations':[]}
  proposals.append(patch)
 # Exact absolute references only. Do not reinterpret vendor-relative includes.
 for rec in stockrecords:
  if rec['partition'] not in ['vendor','odm'] or 'media' not in rec['categories']: continue
  xml=text.get(rec.get('evidence_file',''),'')
  try: root=ET.fromstring(xml)
  except ET.ParseError: continue
  for include in root.findall('.//Include')+root.findall('.//include'):
   href=include.get('href','')
   if not re.fullmatch(r'/system/etc/media_codecs[A-Za-z0-9_.-]*\.xml',href) or href in basepaths: continue
   source=next((r for r in stockrecords if systempath(r)==href and r.get('evidence_file') in text),None)
   if not source: continue
   data=text[source['evidence_file']].encode()
   if hashlib.sha256(data).hexdigest()!=source['sha256']: continue
   try:
    if ET.fromstring(data).tag!='MediaCodecs': continue
   except ET.ParseError: continue
   # No new components may be introduced without runtime evidence. Pure include lists only.
   contents=ET.fromstring(data)
   if any(e.tag in ['MediaCodec','Quirk','Limit','Feature'] for e in contents.iter()): continue
   if list(contents): continue # Empty compatibility include only; actual codec changes stay proposed.
   name='0100-missing-codec-include-'+str(len(approved)+1); folder=ROOT/'patches'/name; folder.mkdir(exist_ok=True)
   (folder/'payload.xml').write_bytes(data)
   spec={'id':name,'approved':True,'api_levels':[36],'status':'evidence-gated','what':'Restore an empty XML include explicitly referenced by stock vendor configuration','why':'Absolute include is absent in base; exact stock system file is empty MediaCodecs XML. No codec declarations or performance behavior are changed.','evidence':[{'partition':rec['partition'],'path':rec['path'],'sha256':rec['sha256']},{'path':href,'sha256':source['sha256']}],'operations':[{'target':href,'source':'payload.xml','sha256':source['sha256'],'expected_before':None,'mode':'0644','uid':0,'gid':0,'selinux':'u:object_r:system_file:s0'}]}
   (folder/'patch.json').write_text(json.dumps(spec,indent=2)+'\n'); approved.append(spec)
 for p in proposals:
  folder=ROOT/'patches'/p['id']; folder.mkdir(exist_ok=True); (folder/'patch.json').write_text(json.dumps(p,indent=2)+'\n')
 helper=make_manual_typec(stockrecords,text)
 if helper: approved.append(helper)
 summary={'approved':[p['id'] for p in approved],'proposed':[p['id'] for p in proposals],'no_performance_changes':True,'hardware_fixes_verified':False,'manual_helper_only':bool(helper) and len(approved)==1}
 (ROOT/'docs/PATCH_PLAN.json').write_text(json.dumps(summary,indent=2)+'\n')
 if not approved: blocker('no-proven-system-patch','Audit differences do not yet establish a safe system-side fix. No unchanged image will be mislabeled as patched.',4)
 else: clear('no-proven-system-patch')
 clear('patch-design')
 phase(4,'pending' if approved else 'blocked','Design report generated. Proposed patches are never applied automatically.',['docs/PATCH_PLAN.json'])
 checkpoint('patches: evidence-gated design and manual Type-C helper'); notify('KL5 patch design: '+str(len(approved))+' approved additions. Manual Type-C helper is experimental, NOT a video/fingerprint/OTG hardware fix. Unproven gaps remain open.')

def make_manual_typec(stockrecords,text):
 # Stock USB HAL owns exactly these kernel Type-C ABI nodes. Their semantics are
 # standardized upstream; unlike OTG_CTL this does not guess a vendor boolean.
 expected='etc/init/android.hardware.usb@1.2-service-mediatekv2.rc'
 rec=next((r for r in stockrecords if r['partition']=='vendor' and r['path']==expected),None)
 content=text.get(rec.get('evidence_file',''),'') if rec else ''
 required=['/sys/class/typec/port0/'+x for x in ['power_role','data_role','port_type']]
 if not rec or hashlib.sha256(content.encode()).hexdigest()!=rec.get('sha256') or not all(node in content for node in required):
  blocker('otg-control','No exact stock USB HAL Type-C ABI evidence; no manual helper approved.',4)
  return None
 payload=(ROOT/'scripts/kl5-otg.sh').read_bytes()
 folder=ROOT/'patches/0101-manual-typec-control'; folder.mkdir(exist_ok=True)
 (folder/'kl5-otg').write_bytes(payload)
 evidence=[{'partition':'vendor','path':expected,'sha256':rec['sha256'],'evidence_file':rec.get('evidence_file')},{'source':'https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-typec','meaning':'source=source-only DFP, sink=sink-only UFP, dual=DRP; active role shown in brackets'}]
 spec={'id':'0101-manual-typec-control','approved':True,'api_levels':[36],'status':'experimental-manual-helper-only','what':'Add inert root-only on/off/restore/status Type-C helper','why':'User requested manual forced host state. Stock USB HAL exposes standard port_type ABI; helper writes source or sink only on explicit command. No boot service, polling, OTG_CTL guess, property tuning, SELinux bypass or vendor partition edit. Does NOT establish that deeper mouse enumeration issue is fixed.','hardware_verified':False,'evidence':evidence,'operations':[{'target':'/system/bin/kl5-otg','source':'kl5-otg','sha256':hashlib.sha256(payload).hexdigest(),'expected_before':None,'mode':'0755','uid':0,'gid':0,'selinux':'u:object_r:system_file:s0'}]}
 (folder/'patch.json').write_text(json.dumps(spec,indent=2)+'\n')
 discovery={'method':'explicit standard kernel Type-C port_type request','on':'source','off':'sink','restore':'saved pre-test type','boot_behavior':'none','OTG_CTL':'not touched; vendor semantics unproven','evidence':evidence,'hardware_verified':False,'warning':'May be rejected/overridden by HAL or fail to power/enumerate devices. Not a compatibility fix. Unplug charger/USB before on. Off leaves sink-only; restore re-enables original dual-role behavior if originally dual.'}
 (ROOT/'docs/OTG_DISCOVERY.json').write_text(json.dumps(discovery,indent=2)+'\n')
 module=WORK/'kl5-otg-manual-experimental.zip'
 with zipfile.ZipFile(module,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('module.prop','id=kl5_otg_manual\nname=KL5 manual Type-C helper (EXPERIMENTAL)\nversion=2\nversionCode=2\nauthor=MOTIONSALT\ndescription=Manual-only standard Type-C control. NOT a hardware fix. No boot daemon.\n')
  info=zipfile.ZipInfo('system/bin/kl5-otg'); info.external_attr=0o100755<<16; z.writestr(info,payload)
  z.writestr('stock-evidence.json',json.dumps(discovery,indent=2))
  z.writestr('stock-usb-hal.rc',content)
  z.writestr('customize.sh','#!/system/bin/sh\nset_perm "$MODPATH/system/bin/kl5-otg" 0 0 0755\n')
  z.writestr('USAGE.txt','EXPERIMENTAL. NO hardware operation or enumeration verified.\nRoot: kl5-otg on|off|restore|status\nUnplug charger/USB before on, connect OTG device afterward.\nOff means sink-only; restore returns the pre-test port type.\nIf overlay mounting is unavailable: su -c sh /data/adb/modules/kl5_otg_manual/system/bin/kl5-otg status\nNo service.sh or boot work. No OTG_CTL writes, SELinux changes or vendor partition edits.\n')
 rel=release('experimental-otg','EXPERIMENTAL manual Type-C helper only, NOT a hardware fix. No emulator or real KL5 operation verified. Uses stock HAL-exposed standard port_type ABI; no OTG_CTL guess, boot daemon or polling. Disconnect charger/USB before on; off means sink-only; restore returns original mode. It may not resolve mouse detection. Module and direct root script are provided separately from any ROM build.')
 upload(rel,module,replace=True); upload(rel,ROOT/'scripts/kl5-otg.sh',name='kl5-otg.sh',replace=True)
 json_asset(rel,'SHA256SUMS.json',{'module':sha256(module),'script':hashlib.sha256(payload).hexdigest()})
 module.unlink()
 clear('otg-control')
 blocker('otg-hardware','Experimental manual Type-C helper is implemented, but VBUS/mouse enumeration and deeper HAL/kernel issue remain unverified on physical KL5.',4)
 blocker('hardware-compatibility','Media/camera/fingerprint and remaining vendor/framework gaps require evidence-backed fixes. Adding a manual helper does NOT resolve full stock-like compatibility.',4)
 return spec

if __name__=='__main__':
 try: design()
 except Exception as e: blocker('patch-design',str(e),4); phase(4,'blocked',str(e)); checkpoint('state: patch design blocked')
