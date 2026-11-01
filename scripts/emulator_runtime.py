#!/usr/bin/env python3
"""Mirror a pinned official Android 16 ARM64 runtime. No Android source compilation.
The public-build client key is read in memory from checksum-pinned upstream code;
no API key or short-lived signed artifact URL is committed, printed or persisted.
"""
import hashlib,json,re,tarfile
import requests
from common import *
API_V4='https://androidbuild-pa.googleapis.com/v4/'
CLIENT_URL='https://raw.githubusercontent.com/google/android-cuttlefish/a20c719622c527540f4b1ee82d30e3f15553d77f/base/cvd/cuttlefish/host/libs/web/android_build_api_key.cc'
CLIENT_SHA='d462ac7beee72d6e6cb6c2097c7dbdd3c408a8c5e70e43282b7dc44710c1e8ad'
BUILD='14981173'
TARGET='aosp_cf_arm64_only_phone-userdebug'
PROP_SHA='31534612266f19d3bafe551fe7f57b0a98a7c4d204c02bdd849a90e180982a59'
PINNED={
 'host':{'name':'cvd-host_package-x86_64.tar.gz','size':895741439,'md5':'d9e5fa5f168fb303af72254d1731a0e6'},
 'images':{'name':'aosp_cf_arm64_only_phone-img-14981173.zip','size':1046289693,'md5':'1369a79f8fb53fe9b3aaf13b481f4d20'}
}

def validate_properties(data):
 if hashlib.sha256(data).hexdigest()!=PROP_SHA: raise RuntimeError('Pinned emulator build.prop SHA-256 changed')
 props=dict(re.findall(r'^([^#=\n]+)=(.*)$',data.decode(),re.M))
 if props.get('ro.build.version.sdk')!='36' or props.get('ro.build.version.release')!='16' or props.get('ro.product.cpu.abi')!='arm64-v8a':
  raise RuntimeError('Emulator image must independently verify Android 16/API 36 ARM64')
 return props

class PublicBuildClient:
 def __init__(self):
  try:
   r=requests.get(CLIENT_URL,timeout=40);r.raise_for_status()
   if hashlib.sha256(r.content).hexdigest()!=CLIENT_SHA: raise RuntimeError('Pinned official public-build client source hash mismatch')
   key=re.search(r'AIza[0-9A-Za-z_-]{30,}',r.text)
   if not key: raise RuntimeError('Official public-build client key not found')
   self.headers={'X-goog-api-key':key.group()}
  except requests.RequestException: raise RuntimeError('Official public-build client source transport failure') from None
 def get(self,path,params=None):
  try:
   r=requests.get(API_V4+path,headers=self.headers,params=params,timeout=60)
   if r.status_code!=200: raise RuntimeError('Official Android Build v4 API returned HTTP '+str(r.status_code))
   return r.json()
  except (requests.RequestException,ValueError): raise RuntimeError('Official Android Build v4 metadata transport/JSON failure') from None
 def metadata(self,name):
  data=self.get('builds/'+BUILD+'/'+TARGET+'/attempts/latest/artifacts',{'pageSize':10,'nameRegexp':'^'+re.escape(name)+'$'})
  return next((a for a in data.get('artifacts',[]) if a['name']==name),None)
 def content_url(self,name):
  # Signed URL is ephemeral and stays in process memory only.
  data=self.get('builds/'+BUILD+'/'+TARGET+'/attempts/latest/artifacts/'+name+'/url')
  url=data.get('signedUrl','')
  if not url.startswith('https://'): raise RuntimeError('Official artifact API supplied no HTTPS content URL')
  return url
 def small(self,name):
  try:
   with requests.get(self.content_url(name),stream=True,timeout=(30,60)) as r:
    if r.status_code!=200: raise RuntimeError('Official small artifact returned HTTP '+str(r.status_code))
    data=bytearray()
    for b in r.iter_content(65536):
     data.extend(b)
     if len(data)>1024**2: raise RuntimeError('Unexpectedly large metadata artifact refused')
    return bytes(data)
  except requests.RequestException: raise RuntimeError('Official small artifact transport failure') from None

def md5_file(path):
 h=hashlib.md5(usedforsecurity=False)
 with path.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''): h.update(b)
 return h.hexdigest()

def ensure_runtime():
 tag='emulator-runtime-'+BUILD+'-x86-host'
 rel=release(tag,'Pinned official Android 16/API 36 ARM64 Cuttlefish host and image set, build '+BUILD+'. Files acquired from official Android Build v4 API, checked against upstream MD5 and re-pinned with SHA-256. Runtime fixtures only; NOT a KL5 ROM or boot proof.')
 existing=asset(rel,'emulator-runtime.json')
 if existing:
  p=download(existing['browser_download_url'],WORK/'runtime-existing.json')
  try: config=json.loads(p.read_text())
  finally:p.unlink(missing_ok=True)
  if config.get('build_id')!=BUILD or config.get('properties_sha256')!=PROP_SHA or config.get('api_level')!=36 or config.get('architecture')!='arm64': raise RuntimeError('Existing emulator runtime manifest failed version pin validation')
  for key in PINNED:
   a=asset(rel,PINNED[key]['name'])
   if not a or a.get('digest')!='sha256:'+config[key+'_sha256']: raise RuntimeError('Existing emulator runtime Release digest mismatch')
  (ROOT/'docs/EMULATOR_ARTIFACTS.json').write_text(json.dumps(config,indent=2)+'\n')
  clear('emulator-artifact-pin');checkpoint('test: recover mirrored Android 16 runtime pins');return config
 client=PublicBuildClient()
 data=client.small('build.prop');props=validate_properties(data)
 prop=WORK/'runtime-build.prop';prop.write_bytes(data);upload(rel,prop,replace=True);prop.unlink()
 config={'api_level':36,'architecture':'arm64','host_architecture':'x86_64','build_id':BUILD,'target':TARGET,'source_branch':'aosp-android-latest-release','properties_sha256':PROP_SHA,'sdk_full':props.get('ro.build.version.sdk_full'),'estimated_unpacked_bytes':12*1024**3,'virtualization':'qemu_cli TCG ARM64 guest on x86_64 host','source':API_V4,'client_source':CLIENT_URL,'client_source_sha256':CLIENT_SHA,'status':'Pinned runtime; NOT emulator boot or hardware proof.'}
 for key,pinned in PINNED.items():
  meta=client.metadata(pinned['name'])
  if not meta or meta.get('md5')!=pinned['md5'] or int(meta.get('size',-1))!=pinned['size']: raise RuntimeError('Official emulator artifact metadata changed for '+key)
  a=asset(rel,pinned['name'])
  if not a:
   notify('KL5 emulator runtime '+key+' mirroring started: Android 16 build '+BUILD+'. No boot success yet.')
   p=WORK/pinned['name']
   try:
    try:download(client.content_url(pinned['name']),p)
    except requests.RequestException:raise RuntimeError('Official '+key+' artifact transport failure; signed URL suppressed') from None
    if p.stat().st_size!=pinned['size'] or md5_file(p)!=pinned['md5']:raise RuntimeError('Official emulator '+key+' MD5/size mismatch')
    digest=sha256(p);a=upload(rel,p)
    if a.get('digest')!='sha256:'+digest:raise RuntimeError('Mirrored emulator '+key+' SHA-256 mismatch')
   finally:p.unlink(missing_ok=True)
  digest=a.get('digest','')
  if not digest.startswith('sha256:') or a['size']!=pinned['size']:raise RuntimeError('Emulator mirrored asset lacks SHA-256/size evidence')
  config[key+'_url']=a['browser_download_url'];config[key+'_sha256']=digest[7:];config[key+'_upstream_md5']=pinned['md5']
  json_asset(rel,'emulator-runtime-partial.json',config)
  checkpoint('test: mirrored emulator runtime '+key)
 json_asset(rel,'emulator-runtime.json',config)
 (ROOT/'docs/EMULATOR_ARTIFACTS.json').write_text(json.dumps(config,indent=2)+'\n')
 decision('Corrected emulator discovery to official Android Build v4 public API. Latest build 16644040 is API 37 and rejected. Pin matched build 14981173 verified as Android 16/API 36.1 ARM64. Use matching x86_64 host package on free x86 runner for the explicit QEMU TCG ARM64 guest path, avoiding unsupported native ARM64 KVM fallback. Public client key and temporary artifact URLs remain process-only.')
 clear('emulator-artifact-pin');checkpoint('test: persist verified Android 16 ARM64 runtime mirror pins')
 notify('KL5 Android 16 ARM64 emulator runtime mirrored and SHA-256 pinned: '+rel['html_url']+'. Boot/UI still unverified.')
 return config

if __name__=='__main__':ensure_runtime()
