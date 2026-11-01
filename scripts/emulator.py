#!/usr/bin/env python3
"""ARM64 Cuttlefish harness. Only real ADB evidence can mark a boot passed."""
import argparse, json, lzma, os, pathlib, platform, re, shutil, subprocess, tarfile, time, zipfile
import requests
from common import *
from images import raw_from_stream
from emulator_system import expected_identity,supported_flags,system_args

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
 from emulator_runtime import ensure_runtime
 return ensure_runtime()

def unpack(path,dest):
 dest=dest.resolve(); dest.mkdir(exist_ok=True)
 def valid(name): return (dest/name).resolve().is_relative_to(dest)
 if zipfile.is_zipfile(path):
  with zipfile.ZipFile(path) as z:
   for m in z.infolist():
    if not valid(m.filename): raise RuntimeError('Unsafe emulator ZIP path')
    if (m.external_attr>>16)&0o170000==0o120000: raise RuntimeError('Symlink in emulator ZIP refused')
   z.extractall(dest)
   # zipfile does not preserve executable mode bits; image ZIPs may include tools.
   for m in z.infolist():
    mode=(m.external_attr>>16)&0o777
    if mode and not m.is_dir(): (dest/m.filename).chmod(mode)
 else:
  with tarfile.open(path) as tf:
   for m in tf:
    if not valid(m.name) or m.isdev() or m.isfifo(): raise RuntimeError('Unsafe emulator tar entry')
    if m.issym() or m.islnk():
     target=(dest/m.linkname) if m.islnk() else (dest/m.name).parent/m.linkname
     if pathlib.PurePosixPath(m.linkname).is_absolute() or not target.resolve().is_relative_to(dest): raise RuntimeError('Escaping emulator archive link refused')
   try: tf.extractall(dest,filter='data')
   except TypeError: tf.extractall(dest)

def adb(cmd,timeout=30):
 return subprocess.run([str(WORK/'cvd/bin/adb'),'-s','127.0.0.1:6520']+cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)

def collect_boot(label,image,config):
 cvd=WORK/'cvd'; launch=cvd/'bin/launch_cvd'; evidence=WORK/('emulator-'+label); evidence.mkdir(exist_ok=True)
 kvm=pathlib.Path('/dev/kvm').exists() and platform.machine() in ['aarch64','arm64']
 env=os.environ.copy(); env['HOME']=str(cvd)
 # QEMU TCG is explicit when KVM unavailable; still bounded by the Actions job timeout.
 flags=supported_flags(cvd,env)
 args=[str(launch),'--daemon','--resume=false','--system_image_dir='+str(cvd),'--start_webrtc=false','--gpu_mode=guest_swiftshader','--report_anonymous_usage_stats=n']
 args+=system_args(cvd,image,evidence,flags,env)
 if not kvm:
  args+=['--vm_manager=qemu_cli','--cpus=2','--memory_mb=4096']
  if '<name>enable_kvm</name>' in flags: args+=['--enable_kvm=false']
  elif platform.machine() in ['aarch64','arm64']:
   (evidence/'tcg-prerequisite.txt').write_text('No /dev/kvm; this Cuttlefish package does not expose enable_kvm. Native ARM64 Linux QEMU manager may hardcode KVM. Boot must fail honestly if software fallback is unavailable.\n')
 completed=False; boot_budget=3600 if kvm else 7200; deadline=time.monotonic()+boot_budget
 if '<name>boot_timeout</name>' in flags: args+=['--boot_timeout='+str(boot_budget)]
 (evidence/'launcher-budget.json').write_text(json.dumps({'boot_budget_seconds':boot_budget,'launcher_timeout_seconds':boot_budget+60,'kvm':kvm,'note':'TCG ARM64 boot may be slow; a 300-second launcher cutoff is insufficient.'},indent=2)+'\n')
 try:
  try: r=subprocess.run(args,cwd=cvd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=boot_budget+60)
  except subprocess.TimeoutExpired as exc:
   (evidence/'launcher.log').write_bytes(exc.stdout or b'Launcher timed out')
   raise RuntimeError('Cuttlefish launcher timed out; partial launcher log retained') from None
  (evidence/'launcher.log').write_bytes(r.stdout)
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
  actual_fingerprint=adb(['shell','getprop','ro.system.build.fingerprint']).stdout.decode(errors='replace').strip()
  architecture=adb(['shell','uname','-m']).stdout.decode(errors='replace').strip()
  sdk=adb(['shell','getprop','ro.system.build.version.sdk']).stdout.decode(errors='replace').strip()
  identity={'expected_system_fingerprint':expected_identity(),'observed_system_fingerprint':actual_fingerprint,'guest_architecture':architecture,'guest_system_sdk':sdk}
  (evidence/'guest-identity.json').write_text(json.dumps(identity,indent=2)+'\n')
  if actual_fingerprint!=identity['expected_system_fingerprint'] or architecture not in ['aarch64','arm64'] or sdk!='36':raise RuntimeError('Booted guest identity/API/architecture does not match the intended AxionOS ARM64 GSI; generic AOSP boot rejected')
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
  try: subprocess.run([str(cvd/'bin/stop_cvd')],cwd=cvd,env=env,capture_output=True,timeout=120)
  except (OSError,subprocess.TimeoutExpired): (evidence/'stop-warning.txt').write_text('stop_cvd failed or timed out; CI runner teardown remains the cleanup boundary.\n')
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
 config=discover()
 host=config.get('host_architecture','arm64')
 actual='arm64' if platform.machine() in ['aarch64','arm64'] else platform.machine()
 if host!=actual: raise RuntimeError('Pinned emulator host architecture does not match runner; ARM64 guest must not be substituted')
 require_space(config.get('estimated_unpacked_bytes',12*1024**3))
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
   (WORK/'runtime-test-super.img').unlink(missing_ok=True)
   (WORK/'runtime-test-vbmeta.img').unlink(missing_ok=True)
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
