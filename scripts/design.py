#!/usr/bin/env python3
"""Conservative deterministic design: only proveable missing XML includes auto-apply."""
import hashlib, json, pathlib, re, xml.etree.ElementTree as ET, zipfile
from common import *
from audit import collect

def design():
 auditpath=ROOT/'docs/audit.json'
 if not auditpath.exists(): raise RuntimeError('No static audit exists; speculative compatibility fixes are prohibited')
 audit=json.loads(auditpath.read_text()); stock,text=collect('stock'); base,basetext=collect('base')
 stockrecords=[r for x in stock for r in x['records']]; baserecords=[r for x in base for r in x['records']]
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
   spec={'id':name,'approved':True,'status':'evidence-gated','what':'Restore an empty XML include explicitly referenced by stock vendor configuration','why':'Absolute include is absent in base; exact stock system file is empty MediaCodecs XML. No codec declarations or performance behavior are changed.','evidence':[{'partition':rec['partition'],'path':rec['path'],'sha256':rec['sha256']},{'path':href,'sha256':source['sha256']}],'operations':[{'target':href,'source':'payload.xml','sha256':source['sha256'],'expected_before':None,'mode':'0644','uid':0,'gid':0,'selinux':'u:object_r:system_file:s0'}]}
   (folder/'patch.json').write_text(json.dumps(spec,indent=2)+'\n'); approved.append(spec)
 for p in proposals:
  folder=ROOT/'patches'/p['id']; folder.mkdir(exist_ok=True); (folder/'patch.json').write_text(json.dumps(p,indent=2)+'\n')
 summary={'approved':[p['id'] for p in approved],'proposed':[p['id'] for p in proposals],'no_performance_changes':True}
 (ROOT/'docs/PATCH_PLAN.json').write_text(json.dumps(summary,indent=2)+'\n')
 if not approved: blocker('no-proven-system-patch','Audit differences do not yet establish a safe system-side fix. No unchanged image will be mislabeled as patched.',4)
 else: clear('no-proven-system-patch')
 make_otg(text)
 phase(4,'pending' if approved else 'blocked','Design report generated. Proposed patches are never applied automatically.',['docs/PATCH_PLAN.json'])
 checkpoint('patches: evidence-gated design and OTG discovery'); notify('KL5 patch design complete: '+str(len(approved))+' proven-safe image operations; unproven gaps remain blocked.')

def make_otg(text):
 matches=[]
 for path,content in text.items():
  if not path.endswith('.rc'): continue
  # Use vendor init's existing property triggers, not guessed sysfs writes.
  triggers=re.findall(r'^on property:([\w.]+)=(\S+)\s*\n((?:[ \t]+[^\n]*\n|\n)*)',content+'\n',re.M)
  for prop,value,body in triggers:
   if 'otg' not in prop.lower() or value not in ['1','true','on']: continue
   off=next(((v,b) for p,v,b in triggers if p==prop and v in ['0','false','off']),None)
   if not off: continue
   if not re.search(r'^\s*write\s+/sys/[^\n]*(?:otg|role|host)',body,re.M|re.I): continue
   matches.append({'property':prop,'on':value,'off':off[0],'stock_rc':path,'on_actions':body,'off_actions':off[1]})
 discovery={'matches':matches,'selected':matches[0] if len(matches)==1 else None,'warning':'Unverified on physical KL5. Property invokes stock vendor init actions; does not prove USB HAL role negotiation or mouse enumeration.'}
 (ROOT/'docs/OTG_DISCOVERY.json').write_text(json.dumps(discovery,indent=2)+'\n')
 if len(matches)!=1:
  blocker('otg-control','No unambiguous paired stock OTG property trigger found. No guessed sysfs writes or always-on service installed.',4); return
 clear('otg-control'); plan=matches[0]
 module=WORK/'kl5-otg-manual.zip'
 script='''#!/system/bin/sh
# Manual only. No boot service, polling, property watcher or forced startup state.
case "$1" in
  on) value="ON_VALUE" ;;
  off) value="OFF_VALUE" ;;
  status) getprop "PROPERTY"; exit $? ;;
  *) echo 'usage: kl5-otg on|off|status'; exit 2 ;;
esac
[ "$(id -u)" = 0 ] || { echo 'Root required'; exit 1; }
setprop "PROPERTY" "$value" || exit 1
actual=$(getprop "PROPERTY")
[ "$actual" = "$value" ] || { echo 'Property write rejected'; exit 1; }
echo 'Stock OTG trigger requested. Verify role and device enumeration; this is not proof of success.'
'''.replace('PROPERTY',plan['property']).replace('ON_VALUE',plan['on']).replace('OFF_VALUE',plan['off'])
 # KernelSU supports module.prop + system overlay; deliberately no service.sh.
 with zipfile.ZipFile(module,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('module.prop','id=kl5_otg_manual\nname=KL5 manual stock OTG trigger (experimental)\nversion=1\nversionCode=1\nauthor=MOTIONSALT\ndescription=Manual stock property trigger only. Hardware unverified. No boot daemon.\n')
  info=zipfile.ZipInfo('system/bin/kl5-otg'); info.external_attr=0o100755<<16; z.writestr(info,script)
  z.writestr('stock-evidence.json',json.dumps(discovery,indent=2))
 rel=release('experimental-otg','EXPERIMENTAL manual OTG helper. Stock init property evidence is bundled. No boot daemon or auto-detection. No USB mouse/hardware success is claimed. KernelSU overlay availability varies.'); upload(rel,module,replace=True); module.unlink()

if __name__=='__main__':
 try: design()
 except Exception as e: blocker('patch-design',str(e),4); phase(4,'blocked',str(e)); checkpoint('state: patch design blocked')
