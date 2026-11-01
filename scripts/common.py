#!/usr/bin/env python3
"""Small, bounded, secret-safe GitHub Release and state helpers."""
import datetime, hashlib, json, os, pathlib, shutil, subprocess, time, urllib.parse
import requests
ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=ROOT/'work'; WORK.mkdir(exist_ok=True)
REPO=os.getenv('GITHUB_REPOSITORY','motionssalt/kl5-axion-gsi')
API='https://api.github.com'; PART_SIZE=1_900_000_000
BASE_URL='https://github.com/itisFarzin/AxionOS_GSI/releases/download/AxionOS-2.8-20260930/AxionOS-2.8-20260930-VANILLA-GSI.img.xz'
BASE_SHA='2ad2e18b70464338c857f51df9d0c540ce2a109cca09ac87bba14920627c52da'
DRIVE_ID='1xvBYSngZ24MW9N01uo_ZU5WMbmZfC_Uw'
SESSION=requests.Session()
if os.getenv('GH_TOKEN'): SESSION.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
SESSION.headers['Accept']='application/vnd.github+json'
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def api(method,path,**kw):
 r=SESSION.request(method,API+path,timeout=kw.pop('timeout',90),**kw)
 if r.status_code>=400: raise RuntimeError(f'GitHub {method} {path.split("?")[0]} returned HTTP {r.status_code}')
 return r.json() if r.content else None
def state(): return json.loads((ROOT/'BUILD_STATE.json').read_text())
def save(s):
 s['updated']=now(); p=ROOT/'BUILD_STATE.json'; t=p.with_suffix('.tmp'); t.write_text(json.dumps(s,indent=2)+'\n'); t.replace(p)
def decision(text):
 s=state()
 if not any(x.get('decision')==text for x in s['decisions']): s['decisions'].append({'at':now(),'decision':text})
 save(s)
def blocker(key,text,phase=None):
 s=state(); s['blockers']=[b for b in s['blockers'] if b.get('id')!=key]
 s['blockers'].append({'id':key,'at':now(),'phase':phase,'message':text}); save(s)
def clear(key):
 s=state(); s['blockers']=[b for b in s['blockers'] if b.get('id')!=key]; save(s)
def phase(p,status,notes='',evidence=None):
 s=state(); previous=s['phases'].get(str(p),{}); s['phase']=str(p); s['phases'][str(p)]={'status':status,'notes':notes,'evidence':evidence or []}; save(s)
 if previous.get('status')!=status or previous.get('notes')!=notes: notify('KL5 phase '+str(p)+' '+status+': '+notes[:1200])
def notify(text):
 token=os.getenv('TELEGRAM_BOT_TOKEN'); chat=os.getenv('TELEGRAM_CHAT_ID')
 if not token or not chat:
  if os.getenv('CI')=='true': blocker('telegram','Required Telegram repository secrets are unavailable; pipeline continues without notifications.')
  return
 try:
  r=requests.post('https://api.telegram.org/bot'+token+'/sendMessage',json={'chat_id':chat,'text':text[:3500]},timeout=20)
  if r.status_code!=200: blocker('telegram','Telegram notification failed (HTTP '+str(r.status_code)+').')
 except requests.RequestException: blocker('telegram','Telegram notification transport failed; credentials not logged.')
def send_telegram_file(path,caption,kind=None,delivery_name=None):
 """Never expose secret-bearing request URLs; persist content-hash delivery receipts."""
 path=pathlib.Path(path); token=os.getenv('TELEGRAM_BOT_TOKEN'); chat=os.getenv('TELEGRAM_CHAT_ID')
 if not token or not chat:
  if os.getenv('CI')=='true': blocker('telegram','Telegram media delivery requires repository secrets.')
  return False
 kind=kind or ('photo' if path.suffix.lower()=='.png' else 'document')
 digest=sha256(path); key=kind+':'+(delivery_name or path.name)+':'+digest
 if key in state().get('telegram_deliveries',{}): return True
 if path.stat().st_size>10*1024**2:
  notify(caption+' (too large for configured media limit; see GitHub Release)'); return False
 try:
  with path.open('rb') as f:
   response=requests.post('https://api.telegram.org/bot'+token+('/sendPhoto' if kind=='photo' else '/sendDocument'),data={'chat_id':chat,'caption':caption[:1000]},files={kind:(path.name,f)},timeout=(20,90))
  if response.status_code!=200:
   blocker('telegram-media','Telegram '+kind+' delivery HTTP '+str(response.status_code)+'; Release artifact retained.'); return False
  s=state(); s.setdefault('telegram_deliveries',{})[key]={'at':now(),'name':delivery_name or path.name,'sha256':digest}; save(s); return True
 except requests.RequestException:
  blocker('telegram-media','Telegram media transport failed; Release artifact retained; credentials not logged.'); return False

def notify_asset(rel,path,name):
 if name.lower().endswith('.png'):
  send_telegram_file(path,'KL5 '+rel['tag_name']+' / '+name+'. Emulator boot/UI only; physical hardware unverified.','photo',delivery_name=name)
 elif any(x in name.lower() for x in ['logcat','launcher.log','kernel.txt','boot-results','final_report']):
  send_telegram_file(path,'KL5 '+rel['tag_name']+' / '+name,'document',delivery_name=name)

def checkpoint(message):
 if os.getenv('CI')!='true': return
 subprocess.run(['git','add','BUILD_STATE.json','stock-manifest.json','docs','patches','README.md'],cwd=ROOT,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 # Some paths may not yet exist: add tracked/untracked safe project paths individually.
 for path in ['BUILD_STATE.json','stock-manifest.json','docs','patches','README.md']:
  if (ROOT/path).exists(): subprocess.run(['git','add',path],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
  subprocess.run(['git','commit','-m',message],cwd=ROOT,check=True)
  for attempt in range(4):
   pushed=subprocess.run(['git','push','origin','HEAD:main'],cwd=ROOT,capture_output=True,text=True)
   if pushed.returncode==0: break
   subprocess.run(['git','fetch','origin','main'],cwd=ROOT,check=True,capture_output=True)
   # Replay this serialized job's state/docs checkpoint over newer code commits.
   rebased=subprocess.run(['git','-c','core.editor=true','rebase','-X','theirs','origin/main'],cwd=ROOT,capture_output=True,text=True)
   if rebased.returncode: raise RuntimeError('Checkpoint rebase conflict; local outputs remain in Releases')
  else: raise RuntimeError('State push failed after bounded rebase retries')
def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
 return h.hexdigest()
def disk(label):
 d=shutil.disk_usage(WORK); s=state(); s['disk_observations'].append({'at':now(),'label':label,'total':d.total,'free':d.free,'used':d.used}); save(s); print('Disk',label,':',d.free,'bytes free')
def require_space(n):
 if shutil.disk_usage(WORK).free < n+512*1024**2: raise RuntimeError('Insufficient free disk for bounded stage; no unpack attempted')
def release(tag,body=None):
 r=SESSION.get(f'{API}/repos/{REPO}/releases/tags/{urllib.parse.quote(tag,safe="")}',timeout=45)
 if r.status_code==200:
  rel=r.json()
  if body is not None: rel=api('PATCH',f'/repos/{REPO}/releases/{rel["id"]}',json={'body':body})
 elif r.status_code==404:
  rel=api('POST',f'/repos/{REPO}/releases',json={'tag_name':tag,'name':tag,'body':body or 'Pipeline intermediate artifacts; NOT a hardware-verified ROM.','prerelease':True,'target_commitish':'main'})
 else: raise RuntimeError('Cannot access Release: HTTP '+str(r.status_code))
 s=state()
 if not any(x.get('tag')==tag for x in s['releases']):
  s['releases'].append({'tag':tag,'url':rel['html_url']}); save(s)
  notify('KL5 Release published: '+rel['html_url']+' (intermediate unless explicitly verified)')
 return rel
def assets(rel):
 out=[]; page=1
 while True:
  chunk=api('GET',f'/repos/{REPO}/releases/{rel["id"]}/assets?per_page=100&page={page}'); out+=chunk
  if len(chunk)<100: return out
  page+=1
def asset(rel,name): return next((a for a in assets(rel) if a['name']==name),None)
def upload(rel,path,name=None,replace=False):
 path=pathlib.Path(path); name=name or path.name
 if path.stat().st_size>PART_SIZE: raise RuntimeError('Asset exceeds conservative 1.9 GB limit; use split_upload')
 existing=asset(rel,name)
 if existing:
  digest=existing.get('digest')
  if existing['size']==path.stat().st_size and digest=='sha256:'+sha256(path):
   notify_asset(rel,path,name); return existing
  if not replace: raise RuntimeError('Existing asset differs or lacks verifiable digest: '+name)
  api('DELETE',f'/repos/{REPO}/releases/assets/{existing["id"]}')
 url=rel['upload_url'].split('{')[0]+'?name='+urllib.parse.quote(name)
 for attempt in range(4):
  with path.open('rb') as f:
   r=SESSION.post(url,data=f,headers={'Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)},timeout=(30,900))
  if r.status_code==201:
   notify_asset(rel,path,name); return r.json()
  if attempt==3: raise RuntimeError('Release upload failed: HTTP '+str(r.status_code))
  time.sleep(10*(attempt+1))
def json_asset(rel,name,data):
 p=WORK/name; p.write_text(json.dumps(data,indent=2)+'\n'); a=upload(rel,p,replace=True); p.unlink(); return a
def download(url,path,expected=None):
 path=pathlib.Path(path); temp=path.with_suffix(path.suffix+'.part')
 # Public artifact transport intentionally has NO repository authentication header.
 with requests.get(url,stream=True,timeout=(30,180)) as r:
  if r.status_code!=200: raise RuntimeError('Input download returned HTTP '+str(r.status_code))
  size=int(r.headers.get('Content-Length',0)); require_space(size)
  with temp.open('wb') as f:
   for b in r.iter_content(4*1024*1024):
    if b: f.write(b)
 temp.replace(path)
 if expected and sha256(path)!=expected: path.unlink(); raise RuntimeError('Input SHA-256 mismatch')
 return path
def split_upload(path,rel,prefix):
 records=[]
 with open(path,'rb') as src:
  index=1
  while True:
   p=WORK/f'{prefix}-{index:04d}'; h=hashlib.sha256(); written=0
   with p.open('wb') as dst:
    while written<PART_SIZE:
     b=src.read(min(4*1024*1024,PART_SIZE-written))
     if not b: break
     dst.write(b); h.update(b); written+=len(b)
   if not written: p.unlink(); break
   a=upload(rel,p)
   records.append({'name':p.name,'size':written,'sha256':h.hexdigest(),'url':a['browser_download_url']}); p.unlink()
   s=state(); s['stock_mirror_parts']=records if prefix=='stock-part' else s.get('stock_mirror_parts',[]); save(s)
   if prefix=='stock-part':
    manifest={'complete':False,'parts':records,'part_limit':PART_SIZE}; (ROOT/'stock-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n'); json_asset(rel,'stock-manifest.json',manifest)
   checkpoint('checkpoint: mirrored asset '+records[-1]['name']); index+=1
 return records
