#!/usr/bin/env python3
"""Input/code-fingerprinted stage cache. Unsupported inputs do not cause busy loops."""
import hashlib, json, os, subprocess, sys
from common import *
TASKS={'stock-audit':['audit.py','stock'],'base-audit':['audit.py','base'],'summary':['audit.py','summary'],'design':['design.py'],'build':['patch_image.py'],'emulator':['emulator.py'],'sandbox':['sandboxed_play.py']}

def run(name):
 cmd=TASKS[name]; s=state(); h=hashlib.sha256()
 for f in sorted((ROOT/'scripts').glob('*.py')): h.update(f.read_bytes())
 h.update(json.dumps({'stock':json.loads((ROOT/'stock-manifest.json').read_text()).get('sha256') if (ROOT/'stock-manifest.json').exists() else None,'base':s.get('base_input',{}).get('sha256'),'fragments':s.get('audit_fragments',{}) if name in ['summary','design'] else None,'candidate':s.get('candidate',{}).get('sha256') if name=='emulator' else None,'phase5':s['phases']['5']['status'] if name=='sandbox' else None},sort_keys=True).encode())
 if name in ['build','emulator']:
  for f in sorted((ROOT/'patches').rglob('*')):
   if f.is_file(): h.update(f.read_bytes())
 if name=='emulator' and (ROOT/'docs/EMULATOR_ARTIFACTS.json').exists(): h.update((ROOT/'docs/EMULATOR_ARTIFACTS.json').read_bytes())
 fingerprint=h.hexdigest(); cached=s.get('stage_cache',{}).get(name,{})
 if cached.get('fingerprint')==fingerprint:
  print('Unchanged stage evidence/inputs; skipped:',name); return
 # Only initial phases need input prerequisites. Base analysis proceeds without stock.
 if name=='stock-audit' and not ((ROOT/'stock-manifest.json').exists() and json.loads((ROOT/'stock-manifest.json').read_text()).get('complete')): print('Stock audit awaits complete mirror'); return
 if name in ['base-audit','build','emulator'] and not s.get('base_input'): print('Stage awaits base mirror:',name); return
 notify('KL5 stage '+name+' started.')
 before={b['id']:b for b in s['blockers']}
 p=subprocess.run([sys.executable,str(ROOT/'scripts'/cmd[0])]+cmd[1:])
 after=state(); after.setdefault('stage_cache',{})[name]={'fingerprint':fingerprint,'at':now(),'exit_code':p.returncode,'blockers':[b['id'] for b in after['blockers'] if b['id'] not in before or before[b['id']]!=b]}; save(after)
 checkpoint('cache: '+name+' input fingerprint')
 issues=after['stage_cache'][name]['blockers']
 notify('KL5 stage '+name+' finished'+(' with blockers: '+', '.join(issues) if issues else '.')+' This is not a hardware verification result.')

if __name__=='__main__': run(sys.argv[1])
