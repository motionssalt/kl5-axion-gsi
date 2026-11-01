#!/usr/bin/env python3
"""Record unavailable emulator pins without costly host setup or a false green boot."""
import os
from common import blocker, checkpoint, clear, notify, phase
from emulator import discover

def run():
 ready=False
 try:
  config=discover()
  ready=True
  clear('emulator-artifact-pin')
  notify('KL5 emulator matched artifact pins validated for build '+str(config['build_id'])+'. Preparing host; boot is not yet verified.')
 except Exception as exc:
  message=str(exc)
  phase(5,'blocked',message)
  blocker('emulator-artifact-pin',message,5)
  notify('KL5 emulator prerequisite blocked: matching Android 16 ARM64 host/image pins unavailable. No emulator boot or screenshots claimed.')
 checkpoint('test: persist emulator artifact preflight evidence')
 output=os.getenv('GITHUB_OUTPUT')
 if output:
  with open(output,'a') as f: f.write('ready='+str(ready).lower()+'\n')
 return ready

if __name__=='__main__': run()
