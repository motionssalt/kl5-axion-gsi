import io,json,pathlib,re,sys,unittest,zipfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from images import MultipartRemote

class Response:
 def __init__(self,data,start,end,status=206): self.data=data;self.status_code=status;self.headers={'Content-Range':f'bytes {start}-{end}/{len(data)}'};self.start=start;self.end=end
 def __enter__(self): return self
 def __exit__(self,*args): pass
 def iter_content(self,n): yield self.data[self.start:self.end+1]

class RangeTests(unittest.TestCase):
 def test_cross_part_zip(self):
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z: z.writestr('vendor/etc/test.xml','<manifest/>');z.writestr('product/build.prop','ro.build.version.sdk=34\n')
  data=buf.getvalue(); chunks=[data[:91],data[91:181],data[181:]];parts=[{'size':len(c),'url':'https://example.test/'+str(i)} for i,c in enumerate(chunks)]
  def request(url,headers,**kwargs):
   index=int(url.rsplit('/',1)[1]);start,end=map(int,re.fullmatch(r'bytes=(\d+)-(\d+)',headers['Range']).groups());return Response(chunks[index],start,end)
  with patch('images.requests.get',side_effect=request):
   remote=MultipartRemote(parts,block=32)
   self.assertEqual(remote.read(100),data[:100]);remote.seek(-9,2);self.assertEqual(remote.read(),data[-9:]);remote.seek(0)
   with zipfile.ZipFile(remote) as z:self.assertEqual(z.read('vendor/etc/test.xml'),b'<manifest/>')
 def test_unbounded_http_refused(self):
  parts=[{'size':5,'url':'https://example.test'}]
  with patch('images.requests.get',return_value=Response(b'12345',0,4,status=200)):
   with self.assertRaises(RuntimeError):MultipartRemote(parts).read(1)
 def test_negative_seek(self):
  r=MultipartRemote([{'size':1,'url':'https://example.test'}])
  with self.assertRaises(ValueError):r.seek(-1)

if __name__=='__main__':unittest.main()
