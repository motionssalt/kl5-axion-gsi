#!/usr/bin/env python3
"""Supplemental base-only GSI shell/APEX audit. No image writes or Android builds.
Runs in its own Actions job, publishing small evidence and merging state atomically.
"""
import base64,json,lzma,os,pathlib,shutil,subprocess,tarfile,time,zipfile
from common import *
from images import raw_from_stream,readonly_mount

def inventory(root,out):
 result={'scope':'Static integration scripts and APEX containers only; no boot/hardware proof','scripts':[],'apex_containers':[],'errors':[]}
 scriptout=out/'scripts';scriptout.mkdir(parents=True,exist_ok=True)
 for directory,dirs,files in os.walk(root,followlinks=False):
  dirs[:]=[d for d in dirs if not (pathlib.Path(directory)/d).is_symlink()]
  for name in files:
   path=pathlib.Path(directory)/name
   if path.is_symlink():continue
   relative=path.relative_to(root).as_posix()
   if name.endswith('.sh') or name in ['phh-prop','rw-system','phh-on-boot']:
    if path.stat().st_size>2*1024**2:continue
    try:
     data=path.read_bytes()
     if b'\0' in data:continue
     target=scriptout/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
     result['scripts'].append({'path':relative,'size':len(data),'sha256':sha256(path),'evidence_file':str(target.relative_to(out))})
    except OSError as exc:result['errors'].append({'path':relative,'error':type(exc).__name__})
   if '/apex/' in '/'+relative and name.endswith(('.apex','.capex')):
    try:
     rec={'path':relative,'size':path.stat().st_size,'sha256':sha256(path)}
     with zipfile.ZipFile(path) as archive:
      rec['members']=[{'name':m.filename,'size':m.file_size,'compression':m.compress_type} for m in archive.infolist()]
      if 'apex_manifest.json' in archive.namelist():rec['manifest_json']=json.loads(archive.read('apex_manifest.json'))
     result['apex_containers'].append(rec)
    except (OSError,zipfile.BadZipFile,ValueError) as exc:result['errors'].append({'path':relative,'error':type(exc).__name__})
 result['limitations']=['APEX payload filesystems not unpacked; container presence does not prove runtime activation or VNDK namespace exports.','Shell scripts are stock base behavior; audit does not modify or approve overriding performance logic.']
 (out/'support-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
 return result

def persist_status(status,notes,evidence=None):
 # Atomic single-file API update merges into CURRENT remote state, not this
 # parallel job's checkout. GitHub sha preconditions prevent lost updates.
 path='/repos/'+REPO+'/contents/BUILD_STATE.json'
 for attempt in range(5):
  current=api('GET',path); data=json.loads(base64.b64decode(current['content']))
  data['supplemental_base_audit']={'status':status,'at':now(),'notes':notes,'evidence':evidence or [],'run_id':os.getenv('GITHUB_RUN_ID')}
  data['updated']=now()
  for url in evidence or []:
   if '/releases/tag/' in url:
    tag=url.rsplit('/',1)[-1]
    if not any(x.get('tag')==tag for x in data.get('releases',[])):data.setdefault('releases',[]).append({'tag':tag,'url':url})
  response=SESSION.put(API+path,json={'message':'audit: supplemental base integration '+status,'sha':current['sha'],'content':base64.b64encode((json.dumps(data,indent=2)+'\n').encode()).decode(),'branch':'main'},timeout=45)
  if response.status_code in [200,201]:return
  if response.status_code not in [409,422]:raise RuntimeError('Supplemental state update HTTP '+str(response.status_code))
  time.sleep(attempt+1)
 raise RuntimeError('Supplemental state update lost bounded concurrency retries; Release evidence retained')

def run():
 persist_status('running','Read-only base shell/APEX container inventory; no performance or image modifications.')
 manifest=state().get('base_input')
 if not manifest:raise RuntimeError('Base mirror unavailable')
 tag='audit-base-support-'+manifest['sha256'][:12];rel=release(tag,'Supplemental read-only GSI integration shell and APEX-container evidence. Not emulator/hardware proof. No image changes or performance tuning. State updates merge against the latest remote JSON with SHA preconditions.')
 if asset(rel,'base-support.tar.gz'):
  persist_status('done','Existing Release evidence reused; no input re-download.',[rel['html_url']])
  notify('KL5 supplemental base support audit already published: '+rel['html_url']);return
 notify('KL5 supplemental base shell/APEX audit started; uses mirrored Release only.')
 packed=WORK/'support-base.img.xz';raw=WORK/'support-base.img'
 with packed.open('wb') as output:
  for part in manifest['parts']:
   p=download(part['url'],WORK/part['name'],part['sha256'])
   with p.open('rb') as src:shutil.copyfileobj(src,output,4*1024**2)
   p.unlink()
 if sha256(packed)!=manifest['sha256']:raise RuntimeError('Base mirror whole-file checksum mismatch')
 with lzma.open(packed) as source:raw_from_stream(source,raw)
 packed.unlink()
 out=WORK/'support-evidence';out.mkdir(exist_ok=True)
 with readonly_mount(raw) as (mount,fs):
  subprocess.run(['sudo','python3',str(ROOT/'scripts/support_audit.py'),'inspect',str(mount),str(out)],check=True,timeout=300)
  subprocess.run(['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(out)],check=True)
 raw.unlink()
 p=WORK/'base-support.tar.gz'
 with tarfile.open(p,'w:gz') as tf:
  for f in out.rglob('*'):
   if f.is_file():tf.add(f,arcname=str(f.relative_to(out)),recursive=False)
 upload(rel,p);upload(rel,out/'support-inventory.json')
 persist_status('done','GSI shell scripts and APEX containers inventoried. APEX payloads/activation and hardware remain unverified.',[rel['html_url']])
 notify('KL5 supplemental shell/APEX audit complete: '+rel['html_url']+'. Static evidence only; no hardware or boot pass.')

if __name__=='__main__':
 import sys
 if len(sys.argv)>1 and sys.argv[1]=='inspect':inventory(pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]))
 else:
  try:run()
  except Exception as exc:
   try:persist_status('blocked',str(exc))
   except Exception:pass
   notify('KL5 supplemental support audit failed: '+str(exc));raise
