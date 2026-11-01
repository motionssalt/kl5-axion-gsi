#!/usr/bin/env python3
"""Selective, evidence-only stock and GSI audit. Never auto-copies vendor binaries."""
import fnmatch, gzip, io, json, lzma, pathlib, re, shutil, subprocess, tarfile, zipfile
from common import *
from images import *
CATEGORIES={
 'vintf':r'(vintf/|compatibility_matrix|manifest.*\.xml$)',
 'init':r'(\.rc$|ueventd|fstab|init\.)',
 'props':r'(build\.prop$|default\.prop$|prop\.default$|\.prop$)',
 'media':r'(media_codecs|media_profiles|codec2|omx|stagefright|vcodec|video)',
 'camera':r'(camera|camsensor|imgsensor)',
 'fingerprint':r'(fingerprint|biometric|goodix|fpc)',
 'usb_otg':r'(usb|typec|type-c|rt.pd|otg)',
 'audio':r'(audio|mixer|sound|tinyalsa)',
 'sensors':r'(sensor|gyroscope|accelerometer)',
 'gnss':r'(gnss|gps|agps)', 'nfc':r'(nfc|pn54|pn55)',
 'bluetooth':r'(bluetooth|btconfig|bt_stack)', 'wifi':r'(wifi|wlan|wpa_|hostapd)',
 'telephony_ims':r'(ril|telephony|ims|volte|radio|modem)',
 'display':r'(display|graphics|composer|refresh|hdr|color)',
 'power_thermal_charging':r'(power|thermal|charg|battery)',
 'vibrator_lights':r'(vibrat|lights|led)',
 'overlays':r'(^|/)(overlay|overlays)/',
 'permissions_sysconfig':r'(permissions/|sysconfig/)',
 'selinux':r'(selinux/|sepolicy|contexts|\.cil$)',
 'hardware_apps':r'(ims|camera|fingerprint|biometric|engineermode|hardware|usb|nfc).*\.apk$'
}
AUDIT_VERSION=2

def stock_release_tag():
 manifest=json.loads((ROOT/'stock-manifest.json').read_text())
 return 'audit-stock-'+manifest.get('sha256','unknown')[:12]+'-v2'

def base_release_tag():
 return 'audit-base-'+state()['base_input']['sha256'][:12]+'-v2'

def select_super(z):
 # SP Flash Tool scatter references the super next to it, not optional Open/ images.
 candidates=[i for i in z.infolist() if re.search(r'(^|/)super(?:_a)?\.img$',i.filename,re.I)]
 scatter_dirs={str(pathlib.PurePosixPath(i.filename).parent) for i in z.infolist() if re.search(r'scatter.*\.txt$',i.filename,re.I)}
 return sorted(candidates,key=lambda i:(str(pathlib.PurePosixPath(i.filename).parent) not in scatter_dirs,len(pathlib.PurePosixPath(i.filename).parts),-i.file_size,i.filename))

TEXT_SUFFIX=('.xml','.rc','.prop','.cil','.conf','.cfg','.ini','.json','.txt','_contexts','.te')

def inspect_tree(root,partition,output):
 evidence=output/'files'/partition; evidence.mkdir(parents=True,exist_ok=True)
 records=[]; errors=[]; text_total=0
 for dirpath,dirs,files in os.walk(root,followlinks=False):
  # Do not follow a filesystem symlink outside the partition.
  dirs[:]=[d for d in dirs if not (pathlib.Path(dirpath)/d).is_symlink()]
  for name in files:
   p=pathlib.Path(dirpath)/name; rel=p.relative_to(root).as_posix(); cats=[k for k,v in CATEGORIES.items() if re.search(v,rel,re.I)]
   if not cats and not name.endswith('.so'): continue
   try:
    st=p.lstat(); rec={'partition':partition,'path':rel,'size':st.st_size,'mode':oct(st.st_mode&0o7777),'uid':st.st_uid,'gid':st.st_gid,'categories':cats}
    if p.is_symlink(): rec['symlink']=os.readlink(p); records.append(rec); continue
    rec['sha256']=sha256(p)
    try: rec['selinux']=os.getxattr(p,'security.selinux').rstrip(b'\0').decode()
    except OSError: pass
    if name.endswith(TEXT_SUFFIX) or 'contexts' in name or name in ['fstab','ueventd.rc']:
     if st.st_size<=4*1024**2 and text_total+st.st_size<128*1024**2:
      b=p.read_bytes(); text=b.decode('utf-8',errors='replace')
      target=evidence/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(b)
      rec['evidence_file']=str(target.relative_to(output)); text_total+=len(b)
      if name.endswith('.prop') or name=='prop.default': rec['properties']={m.group(1):m.group(2) for m in re.finditer(r'^\s*([\w.\-]+)\s*=([^\n]*)',text,re.M)}
      if 'vintf' in cats:
       try:
        import xml.etree.ElementTree as ET
        xml=ET.fromstring(text); rec['hal_declarations']=[ET.tostring(h,encoding='unicode') for h in xml.findall('.//hal')]
       except ET.ParseError: rec['parse_error']='XML parse failed'
     else: rec['extraction_skipped']='Text evidence budget exceeded'
    if name.endswith('.so') or '/hw/' in rel:
     r=subprocess.run(['readelf','-d',str(p)],capture_output=True,text=True,timeout=15)
     rec['needed']=re.findall(r'\(NEEDED\).*?\[(.*?)\]',r.stdout); rec['soname']=re.findall(r'\(SONAME\).*?\[(.*?)\]',r.stdout)
    if name.endswith('.apk') and ('overlays' in cats or 'hardware_apps' in cats) and shutil.which('aapt'):
     r=subprocess.run(['aapt','dump','badging',str(p)],capture_output=True,text=True,timeout=30)
     rec['apk_badging']=r.stdout[:16000]
     if 'overlays' in cats:
      r=subprocess.run(['aapt','dump','--values','resources',str(p)],capture_output=True,text=True,timeout=60)
      target=evidence/(rel+'.resources.txt'); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(r.stdout[:4*1024**2]); rec['resource_dump']=str(target.relative_to(output))
    records.append(rec)
   except (OSError,subprocess.TimeoutExpired) as e: errors.append({'path':rel,'error':type(e).__name__})
 return {'partition':partition,'records':records,'errors':errors,'text_bytes':text_total}

def publish_partition(partition,path,scope,rel):
 name=f'{scope}-{partition}-audit.tar.gz'; existing=asset(rel,name)
 if existing: print('Already audited:',partition); return
 out=WORK/'audit-fragment'; shutil.rmtree(out,ignore_errors=True); out.mkdir()
 with readonly_mount(path) as (mnt,fs):
  # Android props/init can be 0600 root-owned. Do not chmod/chown stock partitions.
  # Privilege ONLY this read-only inventory subprocess; no secrets are passed to sudo.
  subprocess.run(['sudo','python3',str(ROOT/'scripts/audit.py'),'inspect',str(mnt),partition,str(out)],check=True,timeout=2400)
  subprocess.run(['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(out)],check=True)
  result=json.loads((out/'inventory.json').read_text())
 result['audit_version']=AUDIT_VERSION
 result['filesystem']=fs; result['image_sha256']=sha256(path)
 (out/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
 archive=WORK/name
 with tarfile.open(archive,'w:gz') as tf:
  for f in out.rglob('*'):
   if f.is_file(): tf.add(f,arcname=str(f.relative_to(out)),recursive=False)
 upload(rel,archive); archive.unlink(); shutil.rmtree(out)
 s=state(); s.setdefault('audit_fragments',{}).setdefault(scope,{})[partition]={'asset':name,'release':rel['tag_name'],'records':len(result['records']),'errors':len(result['errors']),'filesystem':fs}
 save(s); checkpoint('audit: '+scope+' '+partition+' evidence checkpoint')

def archive_stock():
 manifest=json.loads((ROOT/'stock-manifest.json').read_text())
 if not manifest.get('complete'): raise RuntimeError('Stock mirror is incomplete')
 remote=MultipartRemote(manifest['parts']); head=remote.read(512); remote.seek(0)
 if not head.startswith(b'PK'):
  kind='7z' if head.startswith(b'7z') else 'RAR' if head.startswith(b'Rar!') else 'payload/raw/unknown'
  raise RuntimeError('Detected '+kind+' stock container; this extractor requires ZIP with direct partition images or super.img. No full unpack fallback attempted.')
 return remote,zipfile.ZipFile(remote)

def super_audit(z,entry,rel):
 superpath=WORK/'super.raw.img'; tool=tool_lpunpack()
 with z.open(entry) as src: raw_from_stream(src,superpath)
 info=WORK/'super-metadata.txt'
 r=subprocess.run(['python3',str(tool),'--info',str(superpath)],capture_output=True,text=True,timeout=300)
 info.write_text(r.stdout+'\n'+r.stderr); upload(rel,info,replace=True)
 # Per-partition extraction is strictly sequential; never unpack the whole super.
 for partition in ['vendor','odm','product','system_ext','system']:
  if asset(rel,f'stock-{partition}-audit.tar.gz'): continue
  found=False
  for name in [partition+'_a',partition]:
   out=WORK/'lp'; out.mkdir(exist_ok=True); require_space(3*1024**3 if partition!='system' else 5*1024**3)
   p=subprocess.run(['python3',str(tool),'-p',name,str(superpath),str(out)],capture_output=True,text=True,timeout=1200)
   candidates=list(out.glob('*.img'))
   if p.returncode==0 and candidates:
    image=candidates[0]; publish_partition(partition,image,'stock',rel); image.unlink(); found=True; break
   shutil.rmtree(out,ignore_errors=True)
  if not found: decision('Stock logical partition '+partition+' was not extractable/present; audit coverage records the gap, not compatibility.')
 superpath.unlink()

def stock():
 phase(3,'running','Selective stock extraction and read-only filesystem audit.'); disk('stock-audit-start'); checkpoint('state: stock audit started')
 rel=release(stock_release_tag()); remote,z=archive_stock()
 names=z.namelist(); listing=WORK/'stock-archive-inventory.json'; listing.write_text(json.dumps([{'name':i.filename,'size':i.file_size,'compressed':i.compress_size} for i in z.infolist()],indent=2)); upload(rel,listing,replace=True)
 # Small headers/scatter metadata first; no writable mounting or boot patching.
 headers={}
 for i in z.infolist():
  if re.search(r'(scatter.*\.txt|android.*\.txt|vbmeta.*\.img|vendor_boot.*\.img|boot.*\.img)$',i.filename,re.I):
   with z.open(i) as f: head=f.read(min(i.file_size,128*1024))
   headers[i.filename]={'size':i.file_size,'header_hex':head[:2048].hex(),'header_sha256':hashlib.sha256(head).hexdigest()}
   if i.filename.lower().endswith('.txt'): headers[i.filename]['text']=head.decode(errors='replace')
 json_asset(rel,'stock-boot-and-scatter.json',headers)
 direct={}
 for partition in ['vendor','odm','product','system_ext','system']:
  matches=[i for i in z.infolist() if re.search(r'(^|/)'+partition+r'(?:_a)?\.img$',i.filename,re.I)]
  if matches: direct[partition]=matches[0]
 for partition,entry in direct.items():
  if asset(rel,f'stock-{partition}-audit.tar.gz'): continue
  require_space(min(entry.file_size,5*1024**3)); path=WORK/(partition+'.img')
  try:
   with z.open(entry) as src: raw_from_stream(src,path)
   publish_partition(partition,path,'stock',rel)
  finally: path.unlink(missing_ok=True)
 superentries=select_super(z)
 if superentries:
  decision('Canonical stock super selected by scatter-directory proximity: '+superentries[0].filename+'. Alternate Open/super is not assumed equivalent.')
  json_asset(rel,'stock-selected-super.json',{'selected':superentries[0].filename,'alternatives':[i.filename for i in superentries[1:]],'audit_version':AUDIT_VERSION})
 if superentries and not all(asset(rel,f'stock-{p}-audit.tar.gz') for p in ['vendor','product','system_ext']): super_audit(z,superentries[0],rel)
 if not direct and not superentries:
  payload=any(n.endswith('payload.bin') for n in names)
  raise RuntimeError('OTA payload.bin detected; delta/full payload extraction is not yet implemented safely.' if payload else 'No supported direct partition images or super.img in ZIP; inspect archive inventory in audit-stock Release.')
 z.close(); remote.close(); clear('stock-audit'); checkpoint('state: stock audit fragments published')

def base():
 manifest=state().get('base_input')
 if not manifest: raise RuntimeError('Base input is not mirrored yet')
 rel=release(base_release_tag())
 if asset(rel,'base-system-audit.tar.gz'): print('Base audit already exists'); return
 remote=MultipartRemote(manifest['parts']); path=WORK/'base.raw.img'
 try:
  with lzma.LZMAFile(remote) as src: sparse=raw_from_stream(src,path)
  fs=filesystem(path); s=state(); s['base_image']={'filesystem':fs,'original_sparse':sparse,'raw_size':path.stat().st_size,'sha256':sha256(path)}; save(s)
  publish_partition('system',path,'base',rel); clear('base-audit')
 finally: path.unlink(missing_ok=True); remote.close()

def collect(scope):
 inventories=[]; evidence={}
 fragments={}
 # Assets may have completed just before a runner died prior to its state commit.
 base_input=state().get('base_input',{})
 known_tag=stock_release_tag() if scope=='stock' else base_release_tag() if base_input else ''
 if scope=='stock' or base_input:
  known=release(known_tag)
  for a in assets(known):
   match=re.fullmatch(re.escape(scope)+r'-(vendor|odm|product|system_ext|system)-audit\.tar\.gz',a['name'])
   if match and match[1] not in fragments: fragments[match[1]]={'asset':a['name'],'release':known_tag}
 for partition,item in fragments.items():
  rel=release(item['release']); a=asset(rel,item['asset']); p=download(a['browser_download_url'],WORK/item['asset'])
  with tarfile.open(p,'r:gz') as tf:
   for member in tf:
    if not member.isfile(): continue
    if member.name=='inventory.json':
     inventory=json.load(tf.extractfile(member)); inventories.append(inventory)
     s=state(); s.setdefault('audit_fragments',{}).setdefault(scope,{})[partition]={'asset':item['asset'],'release':item['release'],'records':len(inventory['records']),'errors':len(inventory['errors']),'filesystem':inventory['filesystem']}; save(s)
    elif member.size<=4*1024**2 and member.name.startswith('files/'):
     evidence[member.name]=tf.extractfile(member).read().decode(errors='replace')
  p.unlink()
 return inventories,evidence

def summarize():
 stockinv,stocktext=collect('stock'); baseinv,basetext=collect('base')
 records=[r for inv in stockinv for r in inv['records']]; base_records=[r for inv in baseinv for r in inv['records']]
 baselibs={pathlib.PurePosixPath(r['path']).name for r in base_records if r['path'].endswith('.so')}
 stocklibs={pathlib.PurePosixPath(r['path']).name for r in records if r['path'].endswith('.so')}
 missing_deps=sorted({dep for r in records for dep in r.get('needed',[]) if dep not in stocklibs and dep not in baselibs})
 # Dependency gaps are candidates, not proof: linker namespace/export restrictions need device logs.
 coverage={k:{'stock_files':sum(k in r['categories'] for r in records),'base_files':sum(k in r['categories'] for r in base_records),'status':'inventoried; not hardware tested' if any(k in r['categories'] for r in records) else 'not found in extracted partitions; not proof of absence'} for k in CATEGORIES}
 gaps=[]
 for n,cat in enumerate(['media','camera','fingerprint','usb_otg']+[k for k in CATEGORIES if k not in ['media','camera','fingerprint','usb_otg']]):
  candidates=[{'partition':r['partition'],'path':r['path'],'sha256':r.get('sha256')} for r in records if cat in r['categories'] and not any(b['sha256']==r.get('sha256') for b in base_records)]
  gaps.append({'rank':n+1,'category':cat,'status':'needs device/framework linkage evidence; no blind vendor-file copying','stock_different_or_absent_in_base':candidates,'caveat':'Stock vendor/odm remain on device. Their absence inside GSI is not itself a defect.'})
 result={'schema':1,'stock_partitions':[x['partition'] for x in stockinv],'base_partitions':[x['partition'] for x in baseinv],'coverage':coverage,'stock':stockinv,'base':baseinv,'gap_list':gaps,'unresolved_sonames_candidates':missing_deps,'verification':'Static audit only; no hardware or emulator boot claim.','limitations':['Binary SELinux policy rules are not decompiled; contexts/CIL only when present.','VINTF XML inventory is not checkvintf proof.','Framework overlay resources decoded only when aapt succeeds.','Differences do not justify overriding stock vendor configs or base performance settings.']}
 (ROOT/'docs/audit.json').write_text(json.dumps(result,indent=2)+'\n')
 text='# KL5 stock versus GSI audit\n\nStatic evidence only. Missing vendor files inside a GSI are NOT automatically gaps: the stock vendor stays on the device.\n\n'
 text+='Stock partitions: '+(', '.join(result['stock_partitions']) or 'none')+'\n\nBase partitions: '+(', '.join(result['base_partitions']) or 'none')+'\n\n## Coverage\n\n| Area | Stock files | Base files |\n|---|---:|---:|\n'
 for k,v in coverage.items(): text+=f'| {k} | {v["stock_files"]} | {v["base_files"]} |\n'
 text+='\n## Ranked candidates\n\nVideo/camera, fingerprint and USB/OTG are first. Full details and exact stock paths/hashes are in audit.json and per-partition Release archives. Every candidate still needs proof of framework, linker, property, VINTF or SELinux mismatch. No speculative binary/manifest transplant is performed.\n\n## ELF dependency candidates\n\n'+', '.join(missing_deps)+'\n\n## Limitations\n\n'+'\n'.join('- '+x for x in result['limitations'])+'\n'
 (ROOT/'docs/AUDIT.md').write_text(text)
 complete=all(p in result['stock_partitions'] for p in ['vendor','product','system_ext']) and bool(baseinv) and not any(inv['errors'] for inv in stockinv+baseinv)
 if complete: clear('audit-coverage')
 if stockinv: clear('stock-audit')
 if baseinv and not any(inv['errors'] for inv in baseinv): clear('base-audit')
 phase(3,'done' if complete else 'blocked','Static inventory produced; see explicit coverage limits. Hardware equivalence is not established.',['docs/audit.json','docs/AUDIT.md'])
 if not complete: blocker('audit-coverage','Required stock partitions and/or base inventory remain incomplete.',3)
 rel=release('audit-report'); upload(rel,ROOT/'docs/audit.json',replace=True); upload(rel,ROOT/'docs/AUDIT.md',replace=True)
 clear('audit-summary'); notify('KL5 static audit report published. Compatibility candidates are not verified fixes.'); checkpoint('audit: ranked gaps and coverage report')

if __name__=='__main__':
 import sys
 stage=sys.argv[1]
 if stage=='inspect':
  out=pathlib.Path(sys.argv[4]); result=inspect_tree(pathlib.Path(sys.argv[2]),sys.argv[3],out)
  (out/'inventory.json').write_text(json.dumps(result,indent=2)+'\n'); sys.exit(0)
 try: {'stock':stock,'base':base,'summary':summarize}[stage]()
 except Exception as e:
  blocker(stage+'-audit',str(e),3); phase(3,'blocked',str(e)); notify('KL5 '+stage+' audit blocked: '+str(e)); checkpoint('state: audit blocker recorded')
