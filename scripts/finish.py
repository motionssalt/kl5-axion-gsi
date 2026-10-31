#!/usr/bin/env python3
"""Publish evidence-backed builds, always publish a truthful incremental status report."""
import datetime, json, os, pathlib, re, requests, shutil
from common import *

def promote():
 s=state(); candidate=s.get('candidate'); result=s.get('emulator',{}).get('candidate',{})
 if not candidate or not result.get('boot_completed') or result.get('image_sha256')!=candidate['sha256']:
  return
 if s.get('published_build',{}).get('sha256')==candidate['sha256']: return
 tag='build-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')+'-'+os.getenv('GITHUB_RUN_NUMBER','1')
 body='Patched ARM64 AxionOS GSI. Emulator boot_completed=1 and UI screenshots verified. **Emulator proves boot/UI ONLY: KL5 MediaTek hardware has NOT been verified.**\n\nBase SHA-256: '+candidate['base_sha256']+'\n\nPatch set SHA-256: '+candidate['patchset_sha256']+'\n\nSee patch-report.json, build-manifest.json, FLASHING.md and DEVICE_TEST_CHECKLIST.md. No performance tuning or vendor/boot partition modifications were made. Sandboxed Google Play is not enabled.\n'
 rel=release(tag,body); records=[]
 for part in candidate['parts']:
  p=download(part['url'],WORK/part['name'],part['sha256']); a=upload(rel,p); p.unlink(); record=dict(part); record['url']=a['browser_download_url']; records.append(record)
 final=dict(candidate); final.update({'release':tag,'parts':records,'boot_verified':True,'hardware_verified':False,'emulator':result})
 json_asset(rel,'build-manifest.json',final); json_asset(rel,'patch-report.json',candidate['patch_report'])
 evidence=release('emulator-evidence')
 for a in assets(evidence):
  if a['name'].startswith(('candidate-','base-')) or a['name']=='boot-results.json':
   p=download(a['browser_download_url'],WORK/a['name']); upload(rel,p); p.unlink()
 for path in ['scripts/asset_tool.py','docs/FLASHING.md','docs/DEVICE_TEST_CHECKLIST.md','docs/MANUAL_OTG.md','docs/SANDBOXED_PLAY.md']:
  upload(rel,ROOT/path)
 api('PATCH',f'/repos/{REPO}/releases/{rel["id"]}',json={'prerelease':False})
 s=state(); s['published_build']=final; save(s); checkpoint('release: emulator-verified compatibility build'); notify('KL5 build Release published: '+rel['html_url']+'. Emulator boot/UI only; physical hardware still needs testing.')

def report():
 s=state(); lines=['# KL5 pipeline status','',f'Updated: {now()}','', '**No emulator result proves MediaTek hardware compatibility.**','', '| Phase | Status | Notes |','|---|---|---|']
 for number,p in sorted(s['phases'].items(),key=lambda x:int(x[0])): lines.append('| '+number+' | '+p['status']+' | '+p.get('notes','').replace('\n',' ').replace('|','/')+' |')
 lines+=['','## Delivered infrastructure','', 'Public repository, encrypted secrets, Telegram notifications, stock-first split mirror/checksums, selective static audit, exact-hash patch application/reporting, manual OTG evidence discovery, ARM64 emulator harness, scheduled upstream/manual update and Release import workflows. Infrastructure is not a claim that device fixes are complete.','', '## Actual image status','']
 if s.get('published_build'): lines.append('Final build: https://github.com/'+REPO+'/releases/tag/'+s['published_build']['release'])
 else: lines.append('**No final patched, emulator-verified GSI build exists yet. Do not flash intermediate/status assets.**')
 lines+=['','## Open blockers','']
 for b in s['blockers']: lines.append('- **'+b['id']+'**: '+b['message'])
 if not s['blockers']: lines.append('No blockers currently recorded. This does not by itself assert hardware success.')
 lines+=['','## Next autonomous actions','']
 actions=[]
 if not (ROOT/'stock-manifest.json').exists() or not json.loads((ROOT/'stock-manifest.json').read_text()).get('complete'): actions.append('Retry stock mirroring after backoff or accept verified uploaded Release parts; independent base analysis can proceed.')
 if s['phases']['3']['status']!='done': actions.append('Resume selective stock/base audits; preserve per-partition evidence and explicit container/coverage limits.')
 if s['phases']['4']['status']!='done': actions.append('Resolve evidence-backed system-side mismatch; proposed differences are not automatically safe patches.')
 if s['phases']['5']['status']!='done': actions.append('Obtain matching pinned Android 16 ARM64 emulator artifacts and collect genuine patched-image boot/UI evidence.')
 if s['phases']['6']['status']!='done': actions.append('Keep sandboxed Play hidden until framework port and emulator installation proof exist; do not delay the compatibility release.')
 lines+=['- '+x for x in actions]
 s['next_actions']=actions; save(s)
 text='\n'.join(lines)+'\n'; (ROOT/'docs/FINAL_REPORT.md').write_text(text)
 readme=ROOT/'README.md'; content=readme.read_text(); summary='\n'+text.replace('# KL5 pipeline status','### Latest execution report',1)+'\n'
 content=re.sub(r'<!-- STATUS:START -->.*?<!-- STATUS:END -->','<!-- STATUS:START -->'+summary+'<!-- STATUS:END -->',content,flags=re.S); readme.write_text(content)
 rel=release('pipeline-status',text); upload(rel,ROOT/'docs/FINAL_REPORT.md',replace=True); upload(rel,ROOT/'BUILD_STATE.json',replace=True)
 for p in ['scripts/asset_tool.py','NEEDS_STOCK_UPLOAD.md','docs/DEVICE_TEST_CHECKLIST.md','docs/FLASHING.md']:
  upload(rel,ROOT/p,replace=True)
 checkpoint('report: latest verified results and remaining blockers')
 notify('KL5 final status report updated: '+rel['html_url']+'. '+('Verified emulator build available; hardware unverified.' if s.get('published_build') else 'No final patched/boot-verified GSI yet; blockers and automatic next steps documented.'))
 with open(os.getenv('GITHUB_STEP_SUMMARY',os.devnull),'a') as f: f.write(text)

def continuation():
 count=int(os.getenv('CONTINUATION_COUNT','0') or 0); s=state()
 incomplete=any(p['status']=='running' for p in s['phases'].values())
 failed=os.getenv('INFRA_FAILED')=='true'
 if (incomplete or failed) and count<3:
  decision('Bounded self-dispatch continuation after interrupted/failed job; next attempt '+str(count+1)+'. Deterministic blockers use scheduled backoff instead of busy loops.')
  checkpoint('resume: schedule bounded continuation')
  api('POST',f'/repos/{REPO}/actions/workflows/pipeline.yml/dispatches',json={'ref':'main','inputs':{'continuation_count':str(count+1),'base_url':os.getenv('CONTINUE_BASE_URL',''),'stock_asset_url':os.getenv('CONTINUE_STOCK_URL','')}})

if __name__=='__main__':
 import sys
 try:
  if '--promote' in sys.argv: promote()
  else: report(); continuation()
 except Exception as e:
  blocker('report-delivery',str(e)); checkpoint('state: final report/release delivery blocker'); notify('KL5 report delivery needs retry: '+str(e)); raise
