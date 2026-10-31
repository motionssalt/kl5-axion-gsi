#!/usr/bin/env python3
"""ARM64 Cuttlefish harness. Only real ADB evidence can mark a boot passed."""
import argparse, json, lzma, os, pathlib, platform, re, shutil, subprocess, tarfile, time, zipfile
import requests
from common import *
from images import raw_from_stream

# Pin a matched Android 16 device-image/host pair, NEVER mix latest host and old images.
# Public Android build API v3 returned 403 during provisioning; v4 discovery is attempted.
def discover():
 explicit=ROOT/'docs/EMULATOR_ARTIFACTS.json'
 if explicit.exists():
  config=json.loads(explicit.read_text())
  if config.get('host_url') and config.get('images_url'):
   if config.get('api_level')!=36 or config.get('architecture')!='arm64': raise RuntimeError('Emulator must be Android 16/API 36 ARM64')
   if not config.get('host_sha256') or not config.get('images_sha256') or not config.get('build_id'): raise RuntimeError('Matching host/image build ID and SHA-256 are mandatory')
   return config
 attempts=[]
 # Discover only; do not download unmatched artifacts or silently use x86 system images.
 for endpoint in ['https://androidbuildinternal.googleapis.com/android/internal/build/v4/builds','https://www.googleapis.com/android/internal/build/v3/builds']:
  try:
   r=requests.get(endpoint,params={'branch':'aosp-android16-release','target':'aosp_cf_arm64_only_phone-userdebug','maxResults':1,'buildAttemptStatus':'complete','successful':'true'},timeout=30)
   attempts.append({'endpoint':endpoint,'http_status':r.status_code,'body_excerpt':r.text[:1000]})
  except requests.RequestException: attempts.append({'endpoint':endpoint,'error':'transport failure'})
 (ROOT/'docs/emulator-discovery.json').write_text(json.dumps(attempts,indent=2)+'\n')
 raise RuntimeError('No pinned, matching Android 16 ARM64 Cuttlefish host/image artifacts. Public discovery status saved; no emulator success fabricated. Configure EMULATOR_ARTIFACTS.json with public matched artifacts and hashes.')

def unpack(path,dest):
 dest=dest.resolve(); dest.mkdir(exist_ok=True)
 def valid(name): return (dest/name).resolve().is_relative_to(dest)
 if zipfile.is_zipfile(path):
  with zipfile.ZipFile(path) as z:
   for m in z.infolist():
    if not valid(m.filename): raise RuntimeError('Unsafe emulator ZIP path')
    if (m.external_attr>>16)&0o170000==0o120000: raise RuntimeError('Symlink in emulator ZIP refused')
   z.extractall(dest)
 else:
  with tarfile.open(path) as tf:
   for m in tf:
    if not valid(m.name) or m.isdev() or m.isfifo() or m.issym() or m.islnk(): raise RuntimeError('Unsafe emulator tar entry')
   tf.extractall(dest,filter='data')

def adb(cmd,timeout=30):
 return subprocess.run([str(WORK/'cvd/bin/adb'),'-s','127.0.0.1:6520']+cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)

def collect_boot(label,image,config):
 cvd=WORK/'cvd'; launch=cvd/'bin/launch_cvd'; evidence=WORK/('emulator-'+label); evidence.mkdir(exist_ok=True)
 kvm=pathlib.Path('/dev/kvm').exists()
 env=os.environ.copy(); env['HOME']=str(cvd)
 # QEMU TCG is explicit when KVM unavailable; still bounded by the Actions job timeout.
 args=[str(launch),'--daemon','--resume=false','--system_image='+str(image),'--start_webrtc=false','--gpu_mode=guest_swiftshader','--report_anonymous_usage_stats=n']
 if not kvm: args+=['--vm_manager=qemu_cli','--enable_kvm=false']
 r=subprocess.run(args,cwd=cvd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
 (evidence/'launcher.log').write_bytes(r.stdout)
 completed=False; deadline=time.monotonic()+(3600 if kvm else 7200)
 try:
  if r.returncode!=0: raise RuntimeError('Cuttlefish launcher failed; see launcher log')
  while time.monotonic()<deadline:
   try:
    subprocess.run([str(cvd/'bin/adb'),'connect','127.0.0.1:6520'],capture_output=True,timeout=20)
    p=adb(['shell','getprop','sys.boot_completed'])
    if p.returncode==0 and p.stdout.strip()==b'1': completed=True; break
   except subprocess.TimeoutExpired: pass
   time.sleep(20)
  (evidence/'logcat.txt').write_bytes(adb(['logcat','-b','all','-d','-t','8000'],timeout=120).stdout)
  (evidence/'properties.txt').write_bytes(adb(['shell','getprop']).stdout)
  (evidence/'kernel.txt').write_bytes(adb(['shell','dmesg']).stdout)
  if not completed: raise RuntimeError('sys.boot_completed=1 was not observed before timeout')
  adb(['shell','input','keyevent','KEYCODE_WAKEUP']); adb(['shell','wm','dismiss-keyguard']); adb(['shell','input','keyevent','KEYCODE_HOME']); time.sleep(5)
  screenshots=[('home',[]),('about',['am','start','-a','android.settings.DEVICE_INFO_SETTINGS']),('settings',['am','start','-a','android.settings.SETTINGS']),('quick-settings',['cmd','statusbar','expand-settings'])]
  for name,command in screenshots:
   if command:
    p=adb(['shell']+command)
    if p.returncode!=0 or b'Error:' in p.stdout: raise RuntimeError('Failed to navigate emulator UI: '+name)
   time.sleep(4); p=adb(['exec-out','screencap','-p'],timeout=60)
   if p.returncode!=0 or not p.stdout.startswith(b'\x89PNG\r\n\x1a\n'): raise RuntimeError('No valid screenshot for '+name)
   (evidence/(name+'.png')).write_bytes(p.stdout)
  # UI navigation logs and XML evidence support the screenshot labels.
  adb(['shell','uiautomator','dump','/sdcard/kl5-ui.xml'],timeout=60)
  (evidence/'ui-hierarchy.xml').write_bytes(adb(['exec-out','cat','/sdcard/kl5-ui.xml']).stdout)
  return {'boot_completed':True,'screenshots':[x[0]+'.png' for x in screenshots],'kvm':kvm,'scope':'Emulator proves boot and UI ONLY. MediaTek video/camera/fingerprint/OTG unverified.'},evidence
 finally:
  subprocess.run([str(cvd/'bin/stop_cvd')],cwd=cvd,env=env,capture_output=True,timeout=120)
  # Collect host/device logs, not just logcat. Limit individual files.
  for source in cvd.glob('cuttlefish*/instances/*/logs/*'):
   if source.is_file() and source.stat().st_size<16*1024**2: shutil.copy2(source,evidence/('host-'+source.name))

def image_from_parts(manifest,path):
 packed=WORK/'emulator-system.img.xz'
 with packed.open('wb') as dst:
  for part in manifest['parts']:
   p=download(part['url'],WORK/part['name'],part['sha256'])
   with p.open('rb') as src: shutil.copyfileobj(src,dst,4*1024**2)
   p.unlink()
 if sha256(packed)!=manifest['sha256']: raise RuntimeError('Emulator input checksum mismatch')
 with lzma.open(packed) as src: raw_from_stream(src,path)
 packed.unlink()

def run():
 phase(5,'running','Preparing real ARM64 emulator prerequisites.'); checkpoint('state: emulator prerequisite validation')
 if platform.machine() not in ['aarch64','arm64']: raise RuntimeError('ARM64 image requires native ARM64 host or explicit emulated machine; no architecture substitution allowed')
 config=discover(); require_space(config.get('estimated_unpacked_bytes',12*1024**3))
 cvd=WORK/'cvd'; cvd.mkdir(exist_ok=True)
 for key in ['host','images']:
  p=download(config[key+'_url'],WORK/(key+'.archive'),config[key+'_sha256']); unpack(p,cvd); p.unlink()
 # Host runtime packages are installed from signed Artifact Registry by workflow setup.
 base=state().get('base_input')
 if not base: raise RuntimeError('Base GSI unavailable')
 results={}; testrel=release('emulator-evidence','Actual emulator evidence only. No MediaTek hardware claim. Failed runs also publish logs.'); image=WORK/'emulator-system.img'
 for label,manifest in [('base',base),('candidate',state().get('candidate'))]:
  if not manifest: continue
  evidence=WORK/('emulator-'+label)
  try:
   image_from_parts(manifest,image); result,evidence=collect_boot(label,image,config); result['image_sha256']=manifest['sha256']; results[label]=result
  except Exception as e:
   results[label]={'boot_completed':False,'error':str(e),'scope':'No hardware claim.'}
  finally:
   image.unlink(missing_ok=True)
   if evidence.exists():
    for p in evidence.iterdir():
     if p.is_file(): upload(testrel,p,name=label+'-'+p.name,replace=True)
   json_asset(testrel,'boot-results.json',results)
   s=state(); s['emulator']=results; save(s); checkpoint('test: '+label+' emulator evidence')
 if results.get('candidate',{}).get('boot_completed'):
  phase(5,'done','Patched ARM64 image boot_completed=1 and UI screenshots captured. Emulator ONLY.'); clear('emulator')
 else:
  raise RuntimeError('Patched image did not achieve verified emulator boot (or no candidate exists); base result is not a patched-image pass')
 notify('KL5 patched emulator boot/UI verified. MediaTek hardware still requires physical-device tests.'); checkpoint('state: emulator stage complete')

if __name__=='__main__':
 try: run()
 except Exception as e:
  blocker('emulator',str(e),5); phase(5,'blocked',str(e)); notify('KL5 emulator stage blocked: '+str(e)); checkpoint('state: emulator blocker')
