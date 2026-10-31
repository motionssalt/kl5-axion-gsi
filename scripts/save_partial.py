#!/usr/bin/env python3
"""Save only complete 1.9 GB chunks after a timed-out Drive transfer."""
import hashlib,json,pathlib
from common import *

def run():
 if (ROOT/'stock-manifest.json').exists() and json.loads((ROOT/'stock-manifest.json').read_text()).get('complete'): return
 candidates=[p for p in WORK.glob('stock.download*') if p.is_file() and p.stat().st_size>=PART_SIZE]
 if not candidates: return
 source=max(candidates,key=lambda p:p.stat().st_size); rel=release('stock-mirror'); records=[]
 with source.open('rb') as f:
  for i in range(source.stat().st_size//PART_SIZE):
   p=WORK/f'stock-part-{i+1:04d}'; h=hashlib.sha256(); remaining=PART_SIZE
   with p.open('wb') as out:
    while remaining:
     b=f.read(min(4*1024**2,remaining)); out.write(b); h.update(b); remaining-=len(b)
   a=upload(rel,p); records.append({'name':p.name,'size':PART_SIZE,'sha256':h.hexdigest(),'url':a['browser_download_url']}); p.unlink()
   m={'complete':False,'part_limit':PART_SIZE,'parts':records,'reason':'Complete prefix chunks recovered from interrupted download; final full input SHA not yet known'}
   (ROOT/'stock-manifest.json').write_text(json.dumps(m,indent=2)+'\n'); json_asset(rel,'stock-manifest.json',m); checkpoint('mirror: recovered complete prefix part')
 if records: notify('KL5 recovered '+str(len(records))+' complete stock chunks before runner teardown; full mirror still incomplete.')

if __name__=='__main__':
 try: run()
 except Exception as e: blocker('partial-stock-checkpoint',str(e),2); checkpoint('state: partial mirror checkpoint blocker')
