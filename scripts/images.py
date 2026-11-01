#!/usr/bin/env python3
"""Bounded Release range reader, streaming sparse decoder, read-only mount."""
import contextlib, hashlib, io, json, os, pathlib, shutil, struct, subprocess
import requests, time
from common import *

class MultipartRemote(io.RawIOBase):
 def __init__(self,parts,block=4*1024**2):
  self.parts=parts; self.offsets=[]; self.length=0; self.pos=0; self.block=block; self.cache={}; self.transport=requests.Session(); self.object_urls={}
  for p in parts: self.offsets.append(self.length); self.length+=p['size']
 def readable(self): return True
 def seekable(self): return True
 def tell(self): return self.pos
 def seek(self,offset,whence=0):
  p=offset if whence==0 else self.pos+offset if whence==1 else self.length+offset
  if p<0: raise ValueError('Negative seek')
  self.pos=p; return p
 def read(self,size=-1):
  if size<0: size=self.length-self.pos
  if size>64*1024**2: raise RuntimeError('Unbounded archive read prevented')
  chunks=[]
  while size>0 and self.pos<self.length:
   i=max(j for j,o in enumerate(self.offsets) if o<=self.pos)
   local=self.pos-self.offsets[i]; block=local//self.block; key=(i,block)
   if key not in self.cache:
    start=block*self.block; end=min(start+self.block,self.parts[i]['size'])-1
    data=None
    for attempt in range(3):
     try:
      url=self.object_urls.get(i,self.parts[i]['url'])
      with self.transport.get(url,headers={'Range':f'bytes={start}-{end}'},stream=True,timeout=(30,180)) as r:
       if r.status_code in [401,403] and i in self.object_urls:
        self.object_urls.pop(i,None);continue
       if r.status_code>=500:raise requests.RequestException('temporary Release transport failure')
       if r.status_code!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{end}/{self.parts[i]["size"]}':raise RuntimeError('Release host did not honor exact bounded HTTP Range/total length')
       collected=bytearray()
       for chunk in r.iter_content(1024*1024):
        collected.extend(chunk)
        if len(collected)>end-start+1:raise RuntimeError('Release range body exceeded requested bound')
       if len(collected)!=end-start+1:raise requests.RequestException('truncated Release range')
       data=bytes(collected)
       # Cache the final signed object URL in RAM only, never in state/logs.
       final=getattr(r,'url',None)
       if final and final.startswith('https://'):self.object_urls[i]=final
      break
     except requests.RequestException:
      if attempt==2:raise RuntimeError('Release range transport failed after bounded retries; signed URL suppressed') from None
      time.sleep(2**attempt)
    if data is None:raise RuntimeError('Release signed object URL expired; canonical URL refresh did not succeed')
    self.cache[key]=data
    while len(self.cache)>4: self.cache.pop(next(iter(self.cache)))
   data=self.cache[key]; begin=local%self.block; n=min(size,len(data)-begin,self.length-self.pos)
   chunks.append(data[begin:begin+n]); self.pos+=n; size-=n
  return b''.join(chunks)
 def close(self):
  self.cache.clear();self.object_urls.clear();self.transport.close();super().close()
 def readinto(self,b):
  data=self.read(len(b)); b[:len(data)]=data; return len(data)

def exact(src,n):
 b=bytearray()
 while len(b)<n:
  q=src.read(n-len(b))
  if not q: raise RuntimeError('Truncated partition stream')
  b.extend(q)
 return bytes(b)

def raw_from_stream(src,dest):
 """Expand Android sparse chunks directly into a sparse host file (no second image)."""
 header=src.read(28)
 if len(header)<28: raise RuntimeError('Image is too small')
 count=0
 with open(dest,'wb') as out:
  if struct.unpack('<I',header[:4])[0]!=0xed26ff3a:
   out.write(header)
   while True:
    b=src.read(4*1024**2)
    if not b: break
    if shutil.disk_usage(WORK).free<len(b)+512*1024**2: raise RuntimeError('Disk safety threshold reached while streaming image')
    out.write(b); count+=len(b)
   return False
  magic,major,minor,fh,ch,bs,blocks,nchunks,crc=struct.unpack('<IHHHHIIII',header)
  if major!=1 or fh<28 or ch<12 or bs<4 or bs>1024**2: raise RuntimeError('Unsupported sparse format')
  if fh>28: exact(src,fh-28)
  for _ in range(nchunks):
   hdr=exact(src,ch); typ,_,n,total=struct.unpack('<HHII',hdr[:12]); size=n*bs; payload=total-ch
   if typ==0xcac1:
    if payload!=size: raise RuntimeError('Invalid sparse RAW chunk')
    while size:
     k=min(size,4*1024**2); require_space(k); out.write(exact(src,k)); size-=k
   elif typ==0xcac2:
    if payload!=4: raise RuntimeError('Invalid sparse FILL chunk')
    pat=exact(src,4)
    if pat==b'\0'*4: out.seek(size,1)
    else:
     buf=pat*(1024**2//4)
     while size:
      k=min(size,len(buf)); require_space(k); out.write(buf[:k]); size-=k
   elif typ==0xcac3:
    if payload!=0: raise RuntimeError('Invalid sparse DONT_CARE chunk')
    out.seek(size,1)
   elif typ==0xcac4:
    if payload!=4 or n!=0: raise RuntimeError('Invalid sparse checksum chunk')
    exact(src,4)
   else: raise RuntimeError('Unknown sparse chunk type')
   count+=n*bs
  if count!=blocks*bs: raise RuntimeError('Sparse block count mismatch')
  out.truncate(blocks*bs)
 return True

def filesystem(path):
 with open(path,'rb') as f:
  f.seek(1024); magic=f.read(4)
  if magic==b'\xe2\xe1\xf5\xe0': return 'erofs'
  f.seek(1080)
  if f.read(2)==b'\x53\xef': return 'ext4'
 raise RuntimeError('Image is neither raw ext4 nor EROFS')

@contextlib.contextmanager
def readonly_mount(image):
 fs=filesystem(image); mount=WORK/'mnt'; mount.mkdir(exist_ok=True)
 opts='loop,ro,nosuid,nodev,noexec'+(',noload' if fs=='ext4' else '')
 subprocess.run(['sudo','mount','-t',fs,'-o',opts,str(image),str(mount)],check=True)
 try: yield mount,fs
 finally: subprocess.run(['sudo','umount',str(mount)],check=True)

def tool_lpunpack():
 sha='600d1cab2fc7de5127fb287f4e2791718db54efb1102d0f365db0d3ec1ccf62e'
 p=WORK/'lpunpack.py'
 if not p.exists(): download('https://raw.githubusercontent.com/unix3dgforce/lpunpack/c59b8f3b069c5a8aa438a049fa4a091177172434/lpunpack.py',p,sha)
 return p
