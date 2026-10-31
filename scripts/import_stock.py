#!/usr/bin/env python3
"""Accept user-uploaded Release parts after Drive quota failure. No Drive access."""
import argparse, hashlib, json, os, pathlib, requests
from common import *

def run(tag):
 source=release(tag); listing={a['name']:a for a in assets(source)}
 if 'stock-manifest.json' not in listing: raise RuntimeError('Upload stock-manifest.json and stock-part-0001... to the selected Release')
 r=requests.get(listing['stock-manifest.json']['browser_download_url'],timeout=30); r.raise_for_status(); m=r.json()
 if not m.get('parts') or not m.get('sha256'): raise RuntimeError('Manifest must contain parts and original full SHA-256')
 destination=release('stock-mirror'); records=[]; total=0; whole=hashlib.sha256()
 for i,part in enumerate(m['parts'],1):
  name=f'stock-part-{i:04d}'
  if part['name']!=name or not 0<part['size']<=PART_SIZE: raise RuntimeError('Invalid part order/size')
  a=listing.get(name)
  if not a or a['size']!=part['size']: raise RuntimeError('Uploaded part is missing or has wrong size: '+name)
  p=download(a['browser_download_url'],WORK/name,part['sha256'])
  with p.open('rb') as f:
   for b in iter(lambda:f.read(4*1024**2),b''): whole.update(b)
  uploaded=upload(destination,p); p.unlink(); total+=part['size']
  records.append({'name':name,'size':part['size'],'sha256':part['sha256'],'url':uploaded['browser_download_url']})
  s=state(); s['stock_mirror_parts']=records; save(s); checkpoint('import: verified stock part '+name)
 if whole.hexdigest()!=m['sha256'] or total!=m['size']: raise RuntimeError('Rejoined stock checksum/size mismatch')
 m.update({'complete':True,'parts':records,'source':'Verified uploaded Release parts','part_limit':PART_SIZE})
 (ROOT/'stock-manifest.json').write_text(json.dumps(m,indent=2)+'\n'); json_asset(destination,'stock-manifest.json',m)
 clear('stock-download'); notify('KL5 stock Release import complete; all part/full hashes verified.'); checkpoint('import: stock mirror ready')
 api('POST',f'/repos/{REPO}/actions/workflows/pipeline.yml/dispatches',json={'ref':'main'})

if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--tag',default='stock-upload'); a=p.parse_args()
 try: run(a.tag)
 except Exception as e: blocker('stock-import',str(e),2); notify('KL5 stock import blocked: '+str(e)); checkpoint('state: stock import blocker')
