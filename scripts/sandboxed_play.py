#!/usr/bin/env python3
"""Phase 6 is gated AFTER a released, emulator-tested compatibility build."""
import json
from common import *

def run():
 s=state()
 if s['phases']['5']['status']!='done' or not s.get('published_build'):
  phase(6,'blocked','Deferred until phases 1–5 have produced a released, boot-tested image. No Apps client or Google packages injected.')
  blocker('sandbox-prerequisite','First deliver compatibility build and real patched-image emulator evidence. Sandbox research notes are preliminary only; no implementation claim.',6)
  checkpoint('state: sandboxed Play safely deferred'); return
 repos=['GrapheneOS/platform_packages_apps_GmsCompat','GrapheneOS/platform_frameworks_base','GrapheneOS/Apps','GrapheneOS/platform_packages_apps_GmsCompatConfig']
 pins=[]
 for repo in repos:
  try:
   info=api('GET','/repos/'+repo)
   # Android 16 branch may have been removed; never silently take Android 17.
   branch=SESSION.get(API+'/repos/'+repo+'/branches/16',timeout=30)
   if branch.status_code==200: pins.append({'repository':repo,'branch':'16','sha':branch.json()['commit']['sha']})
   else: pins.append({'repository':repo,'blocked':'Android 16 branch unavailable; locate historical release/tag before attempting port','default_branch':info['default_branch']})
  except Exception as e: pins.append({'repository':repo,'blocked':str(e)})
 (ROOT/'docs/SANDBOXED_PLAY_PINS.json').write_text(json.dumps(pins,indent=2)+'\n')
 # Never binary-patch framework.jar/services.jar without matching framework source,
 # signature/hidden-API integration, dexpreopt and bootclasspath compatibility proof.
 blocker('sandbox-framework','GmsCompat requires framework hooks, Binder/config interfaces, package/permission and installer integration; APK-only installation is not a port. No rigorously validated Android 16 binary-framework patcher exists in this pipeline. Ordinary Play install is NOT a sandboxed-Play fallback.',6)
 phase(6,'blocked','No compatibility layer injected. Install option remains hidden. See SANDBOXED_PLAY.md for exact missing integration.'); checkpoint('sandbox: version pins and honest framework blocker'); notify('KL5 sandboxed Play not enabled: Android 16 framework compatibility remains unproven. Compatibility build is not delayed.')

if __name__=='__main__': run()
