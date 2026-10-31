#!/usr/bin/env python3
"""Re-applicable exact-hash patch engine. Conflicts fail closed, metadata preserved."""
import argparse, hashlib, json, lzma, os, pathlib, re, shutil, struct, subprocess
from common import *
from images import *

def specs():
 result=[]
 for p in sorted((ROOT/'patches').glob('*/patch.json')):
  s=json.loads(p.read_text()); s['_folder']=str(p.parent)
  if s.get('approved'):
   if not s.get('evidence') or not s.get('operations'): raise RuntimeError('Approved patch requires evidence and operations: '+s.get('id','?'))
  result.append(s)
 return result

def safe_target(mount,target):
 if not target.startswith('/system/'): raise RuntimeError('Only /system image edits are allowed by this engine')
 rel=pathlib.PurePosixPath(target)
 if '..' in rel.parts: raise RuntimeError('Path traversal refused')
 # System-as-root image has system/; legacy GSI root directly has etc/, bin/, ...
 p=mount/target.lstrip('/') if (mount/'system').is_dir() else mount/target.removeprefix('/system/')
 current=p
 while current!=mount:
  if current.is_symlink(): raise RuntimeError('Symlink path edit refused: '+target)
  current=current.parent
 return p

def plan(mount,patches):
 operations=[]; report=[]
 for patch in patches:
  entry={'id':patch['id'],'status':'skipped','operations':[]}
  if not patch.get('approved'): entry['reason']='Proposed/unproven patch; not applied'; report.append(entry); continue
  if patch.get('api_levels'):
   sdk=None
   for prop in [mount/'system/build.prop',mount/'build.prop',mount/'system/etc/prop.default',mount/'etc/prop.default']:
    if prop.is_file():
     match=re.search(r'^ro.build.version.sdk=(\d+)\s*$',prop.read_text(errors='replace'),re.M)
     if match: sdk=int(match[1]); break
   if sdk not in patch['api_levels']:
    entry.update({'status':'conflicted','reason':'Unverified or incompatible Android API level'}); report.append(entry); continue
  for op in patch['operations']:
   target=safe_target(mount,op['target']); before=sha256(target) if target.exists() else None
   source=pathlib.Path(patch['_folder'])/op['source']
   if source.is_symlink() or not source.resolve().is_relative_to(pathlib.Path(patch['_folder']).resolve()): raise RuntimeError('Unsafe patch payload path')
   if sha256(source)!=op['sha256']: raise RuntimeError('Patch payload checksum mismatch')
   if before==op['sha256']: status='skipped'
   elif before!=op.get('expected_before'): status='conflicted'
   else: status='apply'
   if not re.fullmatch(r'u:object_r:[a-zA-Z0-9_]+:s0',op.get('selinux','')): raise RuntimeError('Exact SELinux file label is required')
   if int(op.get('uid',0))!=0: raise RuntimeError('Only root-owned config additions supported')
   entry['operations'].append({'target':op['target'],'status':status,'before':before,'after':op['sha256']})
   if status=='apply': operations.append((target,source,op))
  entry['status']='conflicted' if any(o['status']=='conflicted' for o in entry['operations']) else 'applied' if any(o['status']=='apply' for o in entry['operations']) else 'skipped'
  report.append(entry)
 return operations,report

def edit(mount,operations):
 for target,source,op in operations:
  # Creating directories would require separate SELinux/ownership evidence.
  if not target.parent.is_dir(): raise RuntimeError('Target directory missing; refusing to invent metadata')
  subprocess.run(['sudo','install','-o',str(op.get('uid',0)),'-g',str(op.get('gid',0)),'-m',op['mode'],str(source),str(target)],check=True)
  subprocess.run(['sudo','setfattr','-n','security.selinux','-v','0x'+(op['selinux']+'\x00').encode().hex(),str(target)],check=True)
  if sha256(target)!=op['sha256']: raise RuntimeError('Post-write patch checksum mismatch')
 subprocess.run(['sync'],check=True)

def strip_avb(path):
 with path.open('r+b') as f:
  f.seek(-64,2); footer=f.read(64)
  if footer[:4]==b'AVBf':
   _,major,minor,original,offset,size,_=struct.unpack('>4sIIQQQ28s',footer)
   if original<4096 or original>path.stat().st_size-64: raise RuntimeError('Invalid AVB footer size')
   f.truncate(original); decision('Removed now-invalid appended AVB footer from modified system image. No signing keys available; device-specific AVB handling remains mandatory. Stock boot/vendor_boot untouched.')

def apply(input_path,output,report_path):
 patches=specs(); raw=WORK/'patch.raw.img'; input_path=pathlib.Path(input_path)
 require_space(input_path.stat().st_size)
 opener=lzma.open if input_path.name.endswith('.xz') else open
 with opener(input_path,'rb') as src: was_sparse=raw_from_stream(src,raw)
 fs=filesystem(raw)
 with readonly_mount(raw) as (mnt,_): operations,report=plan(mnt,patches)
 pathlib.Path(report_path).write_text(json.dumps({'filesystem':fs,'patches':report,'verified':'static file integrity only; not boot or hardware'},indent=2)+'\n')
 if any(r['status']=='conflicted' for r in report): raw.unlink(); raise RuntimeError('Patch conflicts detected; see patch report. No image published.')
 if not operations: raw.unlink(); raise RuntimeError('No new proven-safe patches apply. Refusing to relabel an unchanged image as patched.')
 strip_avb(raw)
 if fs=='ext4':
  p=subprocess.run(['sudo','e2fsck','-f','-y',str(raw)],capture_output=True,text=True)
  if p.returncode not in [0,1]: raise RuntimeError('Base ext4 check failed before modification')
  mount=WORK/'rw'; mount.mkdir(exist_ok=True)
  subprocess.run(['sudo','mount','-t','ext4','-o','loop,rw,nosuid,nodev,noexec',str(raw),str(mount)],check=True)
  try: edit(mount,operations_from_report(mount,patches))
  finally: subprocess.run(['sudo','umount',str(mount)],check=True)
  p=subprocess.run(['sudo','e2fsck','-f','-n',str(raw)],capture_output=True,text=True)
  (WORK/'filesystem-check.txt').write_text(p.stdout+p.stderr)
  if p.returncode!=0: raise RuntimeError('Modified ext4 consistency check failed')
 else:
  # EROFS must be re-packed with all ownership, permissions and SELinux xattrs.
  info=subprocess.run(['dump.erofs','-s',str(raw)],capture_output=True,text=True,check=True).stdout
  algs=re.findall(r'(?:compression algorithms?|compression algorithm IDs?)\s*:\s*([^\n]+)',info,re.I)
  algorithm='lz4' if algs and re.fullmatch(r'\s*(?:lz4|0)\s*',algs[0]) else None
  if algorithm is None: raise RuntimeError('Cannot prove original EROFS compressor is LZ4; refusing a performance-affecting repack')
  tree=WORK/'erofs-tree'; tree.mkdir(exist_ok=True)
  with readonly_mount(raw) as (mnt,_):
   require_space(int(subprocess.check_output(['sudo','du','-s','-B1',str(mnt)]).split()[0])*2)
   subprocess.run(['sudo','cp','-a','--preserve=all',str(mnt)+'/.',str(tree)],check=True)
  edit(tree,operations_from_report(tree,patches)); rebuilt=WORK/'rebuilt.erofs.img'
  subprocess.run(['sudo','mkfs.erofs','-z'+algorithm,str(rebuilt),str(tree)],check=True)
  subprocess.run(['sudo','rm','-rf',str(tree)],check=True); raw.unlink(); rebuilt.replace(raw)
 with readonly_mount(raw) as (mnt,_):
  _,verified=plan(mnt,patches)
  if any(r['status'] not in ['skipped'] for r in verified): raise RuntimeError('Post-rebuild patch integrity check failed')
 if was_sparse:
  sparse=WORK/'patched.sparse.img'; require_space(raw.stat().st_size)
  subprocess.run(['img2simg',str(raw),str(sparse)],check=True); raw.unlink(); sparse.replace(raw)
 # Low-host-resource xz; this affects download compression only, not on-device performance.
 with raw.open('rb') as src,lzma.open(output,'wb',preset=1) as dst: shutil.copyfileobj(src,dst,4*1024**2)
 raw.unlink(); return report

def operations_from_report(mount,patches):
 ops,report=plan(mount,patches)
 if any(r['status']=='conflicted' for r in report): raise RuntimeError('Image contents changed during patch planning')
 return ops

def pipeline():
 manifest=state().get('base_input')
 if not manifest: raise RuntimeError('No mirrored base input')
 fingerprint=hashlib.sha256(json.dumps([{k:v for k,v in x.items() if k!='_folder'} for x in specs()],sort_keys=True).encode()).hexdigest()
 tag='candidate-'+manifest['sha256'][:8]+'-'+fingerprint[:8]
 rel=release(tag,'UNVERIFIED candidate. No emulator or hardware success yet. Do not treat as a release-ready ROM. Emulator can prove boot/UI only, never MediaTek hardware.')
 if asset(rel,'build-manifest.json'):
  a=asset(rel,'build-manifest.json'); r=requests.get(a['browser_download_url'],timeout=30); r.raise_for_status(); s=state(); s['candidate']=r.json(); save(s); return
 if not any(p.get('approved') for p in specs()): raise RuntimeError('No approved evidence-backed compatibility patch; no image fabricated')
 inp=WORK/'base.img.xz'
 with inp.open('wb') as dst:
  for part in manifest['parts']:
   p=download(part['url'],WORK/part['name'],part['sha256'])
   with p.open('rb') as src: shutil.copyfileobj(src,dst,4*1024**2)
   p.unlink()
 if sha256(inp)!=manifest['sha256']: raise RuntimeError('Rejoined base checksum mismatch')
 out=WORK/'KL5-AxionOS-patched.img.xz'; report=WORK/'patch-report.json'
 result=apply(inp,out,report); inp.unlink(); records=split_upload(out,rel,'system.img.xz.part')
 build={'base_sha256':manifest['sha256'],'patchset_sha256':fingerprint,'parts':records,'sha256':sha256(out),'release':tag,'boot_verified':False,'hardware_verified':False,'patch_report':result}
 json_asset(rel,'build-manifest.json',build); upload(rel,report)
 if (WORK/'filesystem-check.txt').exists(): upload(rel,WORK/'filesystem-check.txt')
 out.unlink()
 s=state(); s['candidate']=build; save(s); phase(4,'done','Candidate generated with static integrity checks. Boot/hardware unverified.'); clear('image-build'); checkpoint('build: candidate checksums and patch results'); notify('KL5 candidate image published for emulator testing. Hardware unverified.')

if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('image',nargs='?'); p.add_argument('--output'); p.add_argument('--report',default=str(WORK/'patch-report.json')); a=p.parse_args()
 if a.image:
  if not a.output: p.error('--output is required')
  apply(a.image,a.output,a.report)
 else:
  try: pipeline()
  except Exception as e: blocker('image-build',str(e),4); phase(4,'blocked',str(e)); notify('KL5 image stage blocked: '+str(e)); checkpoint('state: image build blocker')
