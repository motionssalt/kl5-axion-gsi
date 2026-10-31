#!/usr/bin/env python3
import argparse, hashlib, json, os, pathlib, re, subprocess, time
import requests
from common import *

def load_manifest(rel):
 a=asset(rel,'stock-manifest.json')
 if a:
  r=requests.get(a['browser_download_url'],timeout=45); r.raise_for_status(); return r.json()
 return {'complete':False,'parts':[]}

def import_release(url):
 # Accept exactly a GitHub Release asset, not arbitrary HTML or a shell expression.
 if not re.match(r'^https://github\.com/[^/]+/[^/]+/releases/download/[^/]+/[^/]+$',url): raise RuntimeError('Stock import must be a direct GitHub Release asset URL')
 return download(url,WORK/'stock.download')

def curl_drive(path):
 session=requests.Session(); url='https://drive.usercontent.google.com/download'
 r=session.get(url,params={'id':DRIVE_ID,'export':'download','confirm':'t'},stream=True,timeout=(30,120))
 if r.status_code!=200 or 'text/html' in r.headers.get('Content-Type',''):
  r.close(); raise RuntimeError('Drive cookie/confirm flow returned quota or confirmation page')
 # requests.Session maintains cookies across the confirmation flow. Transfer with curl,
 # with cookie file in work/ only. Never log a signed URL or cookie content.
 cookies=WORK/'drive-cookies.txt'
 with cookies.open('w') as f:
  f.write('# Netscape HTTP Cookie File\n')
  for c in session.cookies: f.write(f'{c.domain}\tTRUE\t{c.path}\tFALSE\t0\t{c.name}\t{c.value}\n')
 direct=r.url; r.close()
 try:
  p=subprocess.run(['curl','--fail','--silent','--location','--retry','3','--retry-delay','20','--cookie',str(cookies),'--max-time','5400','--output',str(path),direct],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5500)
  if p.returncode: raise RuntimeError('Drive curl transfer failed; sensitive transfer details suppressed')
 finally: cookies.unlink(missing_ok=True)

def fetch_drive(path):
 # No captured gdown/curl output goes into public Actions logs: cookie URLs may be sensitive.
 methods=[['gdown','--fuzzy',f'https://drive.google.com/file/d/{DRIVE_ID}/view','-O',str(path)],['gdown',f'https://drive.google.com/uc?id={DRIVE_ID}&export=download&confirm=t','-O',str(path)]]
 for i,cmd in enumerate(methods):
  try:
   p=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5400)
   if p.returncode==0 and path.exists() and path.stat().st_size>1024**2: return
  except subprocess.TimeoutExpired: pass
  print('Drive method',i+1,'failed; backoff, then next flow'); time.sleep(30*(i+1))
 try: curl_drive(path)
 except Exception: raise RuntimeError('All three Drive methods failed or were quota-blocked; prepared stock Release import remains available') from None
 if not path.exists() or path.stat().st_size<1024**2: raise RuntimeError('Drive response is not a firmware archive')

def mirror(stock_url=''):
 phase(2,'running','Stock mirror is the first heavy job.'); clear('initial-state-race'); disk('mirror-start'); checkpoint('state: stock mirror started')
 rel=release('stock-mirror'); manifest=load_manifest(rel)
 if manifest.get('complete'):
  available={a['name']:a for a in assets(rel)}
  if not all(p['name'] in available and available[p['name']]['size']==p['size'] and available[p['name']].get('digest')=='sha256:'+p['sha256'] for p in manifest['parts']): raise RuntimeError('Complete mirror manifest does not match server-side asset digests')
  (ROOT/'stock-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n'); clear('stock-download'); print('Complete stock mirror verified; Google Drive not contacted'); return
 require_space(9*1024**3)
 path=import_release(stock_url) if stock_url else WORK/'stock.download'
 if not stock_url: fetch_drive(path)
 # Detect HTML before spending time uploading it.
 with path.open('rb') as f: head=f.read(4096)
 if b'<html' in head.lower() or b'<!doctype html' in head.lower(): raise RuntimeError('Drive returned HTML instead of firmware')
 digest=sha256(path); size=path.stat().st_size
 parts=split_upload(path,rel,'stock-part')
 manifest={'schema':1,'complete':True,'source':'GitHub Release import' if stock_url else 'Google Drive ID '+DRIVE_ID,'size':size,'sha256':digest,'part_limit':PART_SIZE,'parts':parts,'observed_at':now(),'format_magic_hex':head[:32].hex(),'checksum_trust':'SHA-256 computed at first acquisition; no manufacturer checksum supplied'}
 (ROOT/'stock-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n'); json_asset(rel,'stock-manifest.json',manifest)
 release('stock-mirror','Stock mirror complete. Rejoin parts in numeric order and verify the manifest. Checksums establish transport integrity, not manufacturer authenticity. Do not flash this archive as system.'); path.unlink()
 clear('stock-download'); disk('mirror-complete'); notify('KL5 stock mirror complete: split assets and SHA-256 manifest published.'); checkpoint('state: stock mirror complete')

def base(url=''):
 phase(2,'running','Mirroring base GSI independently of stock availability.'); disk('base-start')
 url=url or state().get('base_input',{}).get('url') or BASE_URL
 if not re.match(r'^https://github\.com/[^/]+/[^/]+/releases/download/[^/]+/[^/]+\.img\.xz$',url): raise RuntimeError('Base must be an HTTPS GitHub Release .img.xz asset')
 owner,repo,tag,name=url.split('/')[3],url.split('/')[4],url.split('/')[7],url.split('/')[8]
 upstream=api('GET',f'/repos/{owner}/{repo}/releases/tags/{urllib.parse.unquote(tag)}')
 source=next(a for a in upstream['assets'] if a['name']==urllib.parse.unquote(name))
 digest=(source.get('digest') or '').removeprefix('sha256:')
 if url==BASE_URL and digest and digest!=BASE_SHA: raise RuntimeError('Original upstream asset changed from pinned checksum')
 digest=digest or (BASE_SHA if url==BASE_URL else None)
 tag='inputs-'+hashlib.sha256(url.encode()).hexdigest()[:12]; rel=release(tag)
 existing=asset(rel,'base-manifest.json')
 if existing:
  r=requests.get(existing['browser_download_url'],timeout=45); r.raise_for_status(); manifest=r.json()
  mirrored={a['name']:a for a in assets(rel)}
  if not all(p['name'] in mirrored and mirrored[p['name']].get('digest')=='sha256:'+p['sha256'] for p in manifest['parts']): raise RuntimeError('Base mirror digest mismatch')
 else:
  recovered=asset(rel,'base-part-0001')
  if digest and source['size']<=PART_SIZE and recovered and recovered['size']==source['size'] and recovered.get('digest')=='sha256:'+digest:
   # Recover metadata after interruption between asset upload and manifest commit.
   records=[{'name':recovered['name'],'size':recovered['size'],'sha256':digest,'url':recovered['browser_download_url']}]
   manifest={'schema':1,'url':url,'release':tag,'sha256':digest,'size':source['size'],'parts':records,'upstream_digest':source.get('digest'),'asset_updated_at':source['updated_at']}
   json_asset(rel,'base-manifest.json',manifest)
   decision('Recovered interrupted base mirror manifest from matching upstream and Release server-side SHA-256; avoided re-downloading 1.3 GB input.')
  else:
   path=download(url,WORK/'base.img.xz',digest); size=path.stat().st_size
   records=split_upload(path,rel,'base-part')
   manifest={'schema':1,'url':url,'release':tag,'sha256':sha256(path),'size':size,'parts':records,'upstream_digest':source.get('digest'),'asset_updated_at':source['updated_at']}
   json_asset(rel,'base-manifest.json',manifest); path.unlink()
 s=state(); s['base_input']=manifest; save(s); clear('base-download')
 phase(2,'done' if (ROOT/'stock-manifest.json').exists() and json.loads((ROOT/'stock-manifest.json').read_text()).get('complete') else 'blocked','Base mirrored with verified SHA-256; stock availability recorded separately.',[rel['html_url']]); notify('KL5 base GSI mirrored and checksummed; stock audit status tracked separately.'); checkpoint('state: base input mirrored')

if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('stage',choices=['stock','base']); p.add_argument('--url',default=''); a=p.parse_args()
 try:
  (mirror if a.stage=='stock' else base)(a.url)
 except Exception as e:
  key='stock-download' if a.stage=='stock' else 'base-download'
  blocker(key,str(e),2); phase(2,'blocked',str(e)); notify('KL5 input phase blocked: '+str(e)); checkpoint('state: input stage blocked')
  # A quota block must not prevent independent base analysis.
 finally:
  with open(os.getenv('GITHUB_OUTPUT',os.devnull),'a') as f:
   ready=(ROOT/'stock-manifest.json').exists() and json.loads((ROOT/'stock-manifest.json').read_text()).get('complete',False) if a.stage=='stock' else bool(state().get('base_input'))
   f.write('ready='+str(bool(ready)).lower()+'\n')
