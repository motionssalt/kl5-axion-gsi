#!/usr/bin/env python3
import os
from common import *

def run():
 releases=api('GET','/repos/itisFarzin/AxionOS_GSI/releases?per_page=10')
 candidates=[]
 for rel in releases:
  if rel.get('draft'): continue
  for a in rel['assets']:
   n=a['name'].upper()
   if n.endswith('.IMG.XZ') and 'VANILLA' in n and not any(x in n for x in ['GAPPS','X86','ARM32']): candidates.append((rel,a))
 if not candidates: blocker('upstream-watch','No eligible vanilla GSI found; previous base preserved.',7); checkpoint('update: upstream selection blocked'); return
 rel,asset=candidates[0]; url=asset['browser_download_url']; current=state().get('base_input',{}).get('url',BASE_URL)
 if url==current: print('Upstream unchanged; no build dispatched'); return
 decision('Updater selects newest upstream vanilla .img.xz from the known maintainer repository. Architecture/API are re-audited; no performance modifications are added.')
 checkpoint('update: new upstream input selected')
 api('POST',f'/repos/{REPO}/actions/workflows/pipeline.yml/dispatches',json={'ref':'main','inputs':{'base_url':url}})
 notify('KL5 new upstream vanilla input detected; re-patch workflow dispatched. No updated build is verified yet.')

if __name__=='__main__': run()
