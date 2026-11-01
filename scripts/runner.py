#!/usr/bin/env python3
"""Input/code-fingerprinted stage cache. Unsupported inputs do not cause busy loops."""
import datetime, hashlib, json, os, subprocess, sys
from common import *
TASKS={'stock-audit':['audit.py','stock'],'base-audit':['audit.py','base'],'summary':['audit.py','summary'],'design':['design.py'],'build':['patch_image.py'],'emulator':['emulator.py'],'sandbox':['sandboxed_play.py']}

STAGE_BLOCKERS={
 'stock-audit':{'stock-audit','interrupted-3'},
 'base-audit':{'base-audit'},
 'summary':{'summary-audit','audit-summary','audit-coverage'},
 'design':{'patch-design','no-proven-system-patch','otg-control'},
 'build':{'image-build'},
 'emulator':{'emulator','emulator-artifact-pin','emulator-infrastructure','interrupted-5'},
 'sandbox':{'sandbox-prerequisite','sandboxed-play'},
}
def owned_blockers(name,blockers):
 return sorted(b['id'] for b in blockers if b['id'] in STAGE_BLOCKERS.get(name,set()) or b['id']=='stage-'+name)

def run(name):
 cmd=TASKS[name]; s=state(); h=hashlib.sha256()
 for f in sorted((ROOT/'scripts').iterdir()):
  if f.is_file() and f.suffix in ['.py','.sh']: h.update(f.read_bytes())
 h.update(json.dumps({'stock':json.loads((ROOT/'stock-manifest.json').read_text()).get('sha256') if (ROOT/'stock-manifest.json').exists() else None,'base':s.get('base_input',{}).get('sha256'),'fragments':s.get('audit_fragments',{}) if name in ['summary','design'] else None,'candidate':s.get('candidate',{}).get('sha256') if name=='emulator' else None,'phase5':s['phases']['5']['status'] if name=='sandbox' else None},sort_keys=True).encode())
 if name in ['build','emulator']:
  for f in sorted((ROOT/'patches').rglob('*')):
   if f.is_file(): h.update(f.read_bytes())
 if name=='emulator' and (ROOT/'docs/EMULATOR_ARTIFACTS.json').exists(): h.update((ROOT/'docs/EMULATOR_ARTIFACTS.json').read_bytes())
 fingerprint=h.hexdigest(); cached=s.get('stage_cache',{}).get(name,{})
 if cached.get('fingerprint')==fingerprint:
  retry_at=cached.get('retry_after')
  if not cached.get('blockers') and not owned_blockers(name,s['blockers']) and cached.get('exit_code')==0:
   print('Unchanged successful stage evidence/inputs; skipped:',name); return
  if retry_at and datetime.datetime.fromisoformat(retry_at)>datetime.datetime.now(datetime.timezone.utc):
   print('Blocked stage is in bounded retry backoff:',name); return
  print('Retrying blocked/interrupted stage after backoff:',name)
 # Only initial phases need input prerequisites. Base analysis proceeds without stock.
 if name=='stock-audit' and not ((ROOT/'stock-manifest.json').exists() and json.loads((ROOT/'stock-manifest.json').read_text()).get('complete')): print('Stock audit awaits complete mirror'); return
 if name in ['base-audit','build','emulator'] and not s.get('base_input'): print('Stage awaits base mirror:',name); return
 notify('KL5 stage '+name+' started.')
 s=state(); s.setdefault('stages',{})[name]={'status':'running','started':now(),'run_id':os.getenv('GITHUB_RUN_ID')}; save(s)
 checkpoint('stage: '+name+' started')
 p=subprocess.run([sys.executable,str(ROOT/'scripts'/cmd[0])]+cmd[1:])
 if p.returncode: blocker('stage-'+name,'Stage process exited '+str(p.returncode)+'; Release checkpoints retained.')
 else: clear('stage-'+name)
 after=state(); after.setdefault('stage_cache',{})[name]={'fingerprint':fingerprint,'at':now(),'exit_code':p.returncode,'blockers':owned_blockers(name,after['blockers'])}; save(after)
 issues=after['stage_cache'][name]['blockers']
 after['stage_cache'][name]['retry_after']=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(hours=6)).isoformat() if issues or p.returncode else None
 after.setdefault('stages',{})[name].update({'status':'blocked' if issues or p.returncode else 'done','finished':now(),'blockers':issues})
 save(after)
 checkpoint('cache: '+name+' input fingerprint')
 issues=after['stage_cache'][name]['blockers']
 notify('KL5 stage '+name+' finished'+(' with blockers: '+', '.join(issues) if issues else '.')+' This is not a hardware verification result.')

if __name__=='__main__': run(sys.argv[1])
