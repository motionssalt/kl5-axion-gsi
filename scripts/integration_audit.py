#!/usr/bin/env python3
"""Trace actual cross-partition references; absence from a GSI is not a defect.
Pure static analysis. Never approves patches, invents HALs, or changes tuning.
"""
import collections, pathlib, re, xml.etree.ElementTree as ET

def logical_path(record):
 part=record['partition']; path=record['path'].lstrip('/')
 if part=='system':
  return '/'+path if path.startswith('system/') else '/system/'+path
 return '/'+part+'/'+path

def flatten(inventories):
 return [r for inv in inventories for r in inv.get('records',[])]

def property_lines(text):
 result=collections.defaultdict(list)
 for n,line in enumerate(text.splitlines(),1):
  m=re.match(r'^\s*([\w.\-]+)\s*=\s*(.*?)\s*$',line)
  if m: result[m[1]].append({'line':n,'value':m[2]})
 return result

def hal_records(records):
 output=[]
 for rec in records:
  for declaration in rec.get('hal_declarations',[]):
   try: hal=ET.fromstring(declaration)
   except ET.ParseError: continue
   interfaces=[]
   for it in hal.findall('interface'):
    interfaces.append({'name':it.findtext('name'),'instances':[x.text for x in it.findall('instance')],'regex_instances':[x.text for x in it.findall('regex-instance')]})
   output.append({'path':logical_path(rec),'sha256':rec.get('sha256'),'name':hal.findtext('name'),'format':hal.get('format','hidl'),'versions':[x.text for x in hal.findall('version')],'transport':hal.findtext('transport'),'fqnames':[x.text for x in hal.findall('fqname')],'interfaces':interfaces,'optional':hal.get('optional'),'document_kind':'compatibility-matrix' if 'compatibility_matrix' in rec['path'] else 'manifest','partition':rec['partition']})
 return output

def references(record,text):
 output=[]
 if record['path'].endswith('.rc'):
  for n,line in enumerate(text.splitlines(),1):
   m=re.match(r'^\s*import\s+(/\S+)',line)
   if m: output.append({'kind':'init-import','target':m[1],'line':n})
 if record['path'].endswith('.xml'):
  try: xml=ET.fromstring(text.lstrip('\ufeff'))
  except ET.ParseError: return output
  for node in xml.iter():
   if node.tag.lower()=='include' and node.get('href'):
    href=node.get('href')
    output.append({'kind':'xml-include','target':href if href.startswith('/') else str(pathlib.PurePosixPath(logical_path(record)).parent/href),'line':None})
 return output

def analyze(stock,base,stocktext,basetext):
 sr=flatten(stock); br=flatten(base)
 stockpaths={logical_path(r):r for r in sr}
 # A GSI supplies system, including its embedded product/system_ext trees. Stock
 # vendor/odm stay on-device. Stock product/system_ext are separately reported:
 # actual mount topology must be confirmed, not assumed overwritten by system.
 basepaths={logical_path(r):r for r in br}
 retained={p:r for p,r in stockpaths.items() if r['partition'] in ['vendor','odm']}
 combined={**retained,**basepaths}
 result={'schema':1,'scope':'Static reference candidates only. No runtime causality, checkvintf, codec enumeration, SELinux decision or hardware verification.','retained_partitions':['vendor','odm'],'mount_topology_warning':'Stock product/system_ext may be separate logical mounts. Read /proc/mounts on-device before choosing a system-side target.','references':[],'duplicate_properties':[],'hal_declarations':{'stock':hal_records(sr),'base':hal_records(br)},'native_dependencies':[],'priority_findings':[]}
 for rec in sr:
  content=stocktext.get(rec.get('evidence_file',''))
  if content is None: continue
  for ref in references(rec,content):
   target=ref['target']; dynamic='$' in target or '*' in target
   ref.update({'source':logical_path(rec),'source_partition':rec['partition'],'source_sha256':rec.get('sha256'),'stock_target':target in stockpaths,'base_target':target in basepaths,'retained_vendor_target':target in retained})
   ref['assessment']='dynamic-reference-not-resolved' if dynamic else 'satisfied-by-base-or-retained-vendor' if target in combined else 'stock-system-side-target-absent-in-gsi' if target in stockpaths else 'not-in-selective-inventory-not-proof-of-absence'
   result['references'].append(ref)
  if rec['path'].endswith('.prop'):
   for prop,lines in property_lines(content).items():
    if len({x['value'] for x in lines})>1:
     result['duplicate_properties'].append({'source':logical_path(rec),'property':prop,'values':lines,'warning':'Conflicting lines in one stock property file. Effective value depends on init loading; do not select the final line blindly.'})
 # Resolve by ELF class and SONAME, not just basename across 32/64-bit namespaces.
 libs=collections.defaultdict(list)
 for r in list(retained.values())+br:
  if r['path'].endswith('.so') and r.get('elf_class'):
   for name in set(r.get('soname',[])+[pathlib.PurePosixPath(r['path']).name]):libs[(name,r['elf_class'])].append(logical_path(r))
 for rec in sr:
  if rec['partition'] not in ['vendor','odm'] or not rec.get('needed'): continue
  if not any(c in rec.get('categories',[]) for c in ['media','camera','fingerprint','usb_otg','telephony_ims']): continue
  entries=[]
  for needed in rec['needed']:
   providers=libs.get((needed,rec.get('elf_class')),[])
   if not providers:entries.append({'soname':needed,'elf_class':rec.get('elf_class'),'assessment':'not-resolved-by-inventory; inspect VNDK/APEX and linker namespace before copying'})
  if entries:result['native_dependencies'].append({'consumer':logical_path(rec),'sha256':rec.get('sha256'),'unresolved':entries})
 for category,words in [('media',['android.hardware.media.c2','android.hardware.media.omx']),('fingerprint',['android.hardware.biometrics.fingerprint']),('usb_otg',['android.hardware.usb'])]:
  hals=[h for h in result['hal_declarations']['stock'] if h['name'] in words and h['document_kind']=='manifest' and h['partition'] in ['vendor','odm']]
  result['priority_findings'].append({'category':category,'stock_hals':hals,'conclusion':'Vendor/odm provider manifest declaration exists; compatibility-matrix requirements and system software services are not counted as hardware providers. Do not duplicate device HALs into framework VINTF. Service startup, binder connection and framework logs still required.' if hals else 'No matching vendor/odm provider manifest declaration in selective inventory; matrix requirements are not evidence of a provider. Review coverage before treating absent.'})
 c2=[]
 for rec in sr:
  if pathlib.PurePosixPath(rec['path']).name!='media_codecs_c2.xml':continue
  try:xml=ET.fromstring(stocktext.get(rec.get('evidence_file',''),'').lstrip('\ufeff'))
  except ET.ParseError:continue
  for codec in xml.iter('MediaCodec'):
   if (codec.get('name') or '').startswith('c2.mtk.'):
    c2.append({'name':codec.get('name'),'type':codec.get('type'),'limits':[dict(x.attrib) for x in codec.findall('Limit') if x.get('name') in ['size','alignment','block-size']],'source':logical_path(rec)})
 result['mediatek_codec_declarations']=c2
 result['priority_findings'].append({'category':'media','conclusion':'Stock XML advertises MediaTek hardware video codecs. Existing vendor configuration alone does not prove registration or encoding; do not override base software limits, codec ranking, or performance properties.','hardware_codecs_declared':len(c2)})
 return result

def markdown(result):
 text='# Cross-partition integration findings\n\n'+result['scope']+'\n\n'+result['mount_topology_warning']+'\n\n## Prioritized hardware wiring\n\n'
 for row in result['priority_findings']:
  text+='### '+row['category']+'\n\n'+row['conclusion']+'\n\n'
  for hal in row.get('stock_hals',[]):text+='- `'+str(hal['name'])+'` '+', '.join(hal['versions'])+' — `'+hal['path']+'`\n'
 text+='\n## Explicit imports/includes not supplied by the GSI\n\n'
 for ref in result['references']:
  if ref['assessment']=='stock-system-side-target-absent-in-gsi':text+='- `'+ref['source']+'` → `'+ref['target']+'` (mount topology and init action semantics need review)\n'
 text+='\n## Conflicting stock property values\n\n'
 for prop in result['duplicate_properties']:text+='- `'+prop['source']+'`: `'+prop['property']+'`: '+', '.join('line '+str(x['line'])+' = '+x['value'] for x in prop['values'])+'. Never infer active API level from last-value parsing.\n'
 text+='\nFull HAL declarations, architecture-aware unresolved ELF candidates, codec limits and exact reference hashes are in `integration.json`. APEX-contained libraries and runtime linker namespaces are not yet fully inventoried. No compatibility patches are approved by this report.\n'
 return text
