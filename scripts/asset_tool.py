#!/usr/bin/env python3
"""Termux-friendly split/verify/join. Python standard library only."""
import argparse, hashlib, json, pathlib, shutil
LIMIT=1_900_000_000

def split(source,directory,prefix):
 source=pathlib.Path(source); out=pathlib.Path(directory); out.mkdir(parents=True,exist_ok=True)
 full=hashlib.sha256(); parts=[]
 with source.open('rb') as f:
  i=1
  while True:
   p=out/f'{prefix}-{i:04d}'; h=hashlib.sha256(); n=0
   with p.open('wb') as g:
    while n<LIMIT:
     b=f.read(min(4*1024**2,LIMIT-n))
     if not b: break
     n+=len(b); h.update(b); full.update(b); g.write(b)
   if not n: p.unlink(); break
   parts.append({'name':p.name,'size':n,'sha256':h.hexdigest()}); print('Created',p.name,n); i+=1
 manifest={'schema':1,'complete':True,'source_filename':source.name,'size':source.stat().st_size,'sha256':full.hexdigest(),'part_limit':LIMIT,'parts':parts}
 (out/'stock-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

def verify(manifest_path,output=None):
 path=pathlib.Path(manifest_path); m=json.loads(path.read_text()); whole=hashlib.sha256(); total=0
 temp=pathlib.Path(str(output)+'.unverified') if output else None
 if output and pathlib.Path(output).exists(): raise RuntimeError('Output already exists; refusing to overwrite')
 if temp and temp.exists(): raise RuntimeError('Unverified temporary output already exists')
 dst=temp.open('xb') if temp else None
 try:
  for part in m['parts']:
   if pathlib.Path(part['name']).name!=part['name']: raise RuntimeError('Unsafe part filename')
   p=path.parent/part['name']; h=hashlib.sha256(); size=0
   with p.open('rb') as f:
    while True:
     b=f.read(4*1024**2)
     if not b: break
     h.update(b); whole.update(b); size+=len(b)
     if dst: dst.write(b)
   if h.hexdigest()!=part['sha256'] or size!=part['size']: raise RuntimeError('Part checksum/size failed: '+p.name)
   total+=size; print('Verified',p.name)
  if whole.hexdigest()!=m['sha256'] or (m.get('size') is not None and total!=m['size']): raise RuntimeError('Full image checksum/size failed')
  if dst: dst.close(); dst=None; temp.replace(output)
  print('Full checksum verified:',m['sha256'])
 except BaseException:
  if dst: dst.close()
  if temp: temp.unlink(missing_ok=True)
  raise

if __name__=='__main__':
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
 a=sub.add_parser('split'); a.add_argument('source'); a.add_argument('--directory',default='stock-parts'); a.add_argument('--prefix',default='stock-part')
 a=sub.add_parser('verify'); a.add_argument('manifest')
 a=sub.add_parser('join'); a.add_argument('manifest'); a.add_argument('--output',required=True)
 a=p.parse_args()
 if a.command=='split': split(a.source,a.directory,a.prefix)
 else: verify(a.manifest,getattr(a,'output',None))
