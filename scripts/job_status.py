#!/usr/bin/env python3
import sys
from common import *
name=sys.argv[1]; s=state(); s.setdefault('job_checkpoints',{})[name]={'at':now(),'run_id':os.getenv('GITHUB_RUN_ID')}; save(s)
for p in {'inputs':['2'],'audit-build':['3','4'],'emulator':['5']}.get(name,[]):
 s=state(); current=s['phases'][p]
 if current['status']=='running':
  phase(p,'blocked','Job ended before phase completion; persisted Release artifacts allow bounded continuation.')
  blocker('interrupted-'+p,'Interrupted/timeout stage; existing Release checkpoints are retained.',int(p))
 if name=='emulator' and current['status']=='pending':
  phase(5,'blocked','Emulator infrastructure did not reach test harness; no boot pass claimed.')
  blocker('emulator-infrastructure','ARM64 setup/group/package stage failed or was skipped; no screenshots fabricated.',5)
disk('job-end-'+name); checkpoint('checkpoint: '+name+' job end')
