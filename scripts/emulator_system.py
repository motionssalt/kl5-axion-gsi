#!/usr/bin/env python3
"""Put the actual GSI into the emulator; never accept booting its default AOSP system.
Only emulator runtime files are changed. Phone vendor/boot partitions are untouched.
"""
import json,pathlib,subprocess
from common import WORK,ROOT,sha256
from images import raw_from_stream,tool_lpunpack

def supported_flags(cvd,env):
 text=''
 for tool in ['launch_cvd','assemble_cvd']:
  binary=cvd/'bin'/tool
  if not binary.exists():continue
  try:
   p=subprocess.run([str(binary),'--helpxml'],cwd=cvd,env=env,capture_output=True,text=True,timeout=45)
   text+=p.stdout+'\n'+p.stderr
  except (OSError,subprocess.TimeoutExpired):continue
 return text

def system_args(cvd,image,evidence,flags,env):
 if '<name>system_image</name>' in flags:
  (evidence/'system-integration.json').write_text(json.dumps({'method':'launcher system_image override','image_sha256':sha256(image)},indent=2)+'\n')
  return ['--system_image='+str(image)]
 # Modern Cuttlefish often exposes super_image instead of a system_image flag.
 lpadd=cvd/'bin/lpadd';superimage=cvd/'super.img'
 if not lpadd.exists() or not superimage.exists():raise RuntimeError('Runtime has no system_image override and lacks lpadd/super.img for safe GSI integration; default AOSP boot is NOT accepted')
 raw=WORK/'runtime-test-super.img'
 with superimage.open('rb') as src:raw_from_stream(src,raw)
 try:
  tool=tool_lpunpack()
  p=subprocess.run(['python3',str(tool),'--info','-f','json',str(raw)],capture_output=True,text=True,timeout=120,check=True)
  meta=json.loads(p.stdout)
  candidates=[x for x in meta.get('partitions',[]) if x.get('name') in ['system_a','system']]
  target=next((x for x in candidates if x.get('name')=='system_a'),None) or next((x for x in candidates if x.get('name')=='system'),None) or (candidates[0] if candidates else None)
  if not target:raise RuntimeError('Emulator super does not identify a system or system_a partition')
  name=target['name'];group=target['group_name']
  p=subprocess.run([str(lpadd),'--replace','--readonly',str(raw),name,group,str(image)],cwd=cvd,env=env,capture_output=True,text=True,timeout=600)
  (evidence/'system-integration.log').write_text(p.stdout+'\n'+p.stderr)
  if p.returncode:raise RuntimeError('Emulator lpadd could not replace system (capacity/metadata failure); see integration log. Default AOSP boot is not accepted')
  (evidence/'system-integration.json').write_text(json.dumps({'method':'lpadd emulator-only system replacement','partition':name,'group':group,'image_sha256':sha256(image),'other_partitions':'Matching AOSP emulator vendor/product/boot; NOT KL5 hardware.'},indent=2)+'\n')
  avb=cvd/'bin/avbtool';vbmeta=WORK/'runtime-test-vbmeta.img'
  if not avb.exists() or ('<name>vbmeta_image</name>' not in flags and 'vbmeta' not in flags):raise RuntimeError('No verified emulator vbmeta override path for changed system; refusing unverifiable default images')
  p=subprocess.run([str(avb),'make_vbmeta_image','--flags','3','--padding_size','4096','--output',str(vbmeta)],cwd=cvd,env=env,capture_output=True,text=True,timeout=120)
  (evidence/'emulator-avb.log').write_text(p.stdout+'\n'+p.stderr)
  if p.returncode:raise RuntimeError('Emulator-only unsigned vbmeta generation failed')
  return ['--super_image='+str(raw),'--vbmeta_image='+str(vbmeta)]
 except Exception:
  raw.unlink(missing_ok=True);raise

def expected_identity():
 p=ROOT/'docs/audit.json'
 if not p.exists():raise RuntimeError('Base audit needed for independent guest identity verification')
 data=json.loads(p.read_text())
 for inv in data.get('base',[]):
  for rec in inv.get('records',[]):
   props=rec.get('properties',{})
   fingerprint=props.get('ro.system.build.fingerprint')
   if fingerprint:return fingerprint
 raise RuntimeError('Base system build fingerprint was not captured; no generic AOSP boot may be accepted')
