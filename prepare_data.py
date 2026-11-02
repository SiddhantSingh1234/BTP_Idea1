"""Restore archived data within this repository; never overwrite differing files."""
from pathlib import Path
import hashlib,json,zipfile,shutil
ROOT=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 m=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_text());restored=0
 for archive in m['archives']:
  q=ROOT/archive['path']
  if sha(q)!=archive['sha256']:raise ValueError('Archive checksum mismatch: '+str(q))
  with zipfile.ZipFile(q) as z:
   expected={r['path']:r for r in archive['members']}
   if set(z.namelist())!=set(expected):raise ValueError('Unexpected archive entries')
   for member in z.infolist():
    target=(ROOT/member.filename).resolve()
    if not target.is_relative_to(ROOT):raise ValueError('Archive path escapes repository')
    if target.exists():
     if not target.is_file() or sha(target)!=expected[member.filename]['sha256']:
      raise ValueError('Refusing to overwrite changed file: '+str(target))
     continue
    target.parent.mkdir(parents=True,exist_ok=True)
    with z.open(member) as source,target.open('xb') as dest:shutil.copyfileobj(source,dest)
    if sha(target)!=expected[member.filename]['sha256']:raise ValueError('Extracted checksum mismatch')
    restored+=1
 print(json.dumps({'restored_files':restored,'repository':str(ROOT)}))
if __name__=='__main__':main()
