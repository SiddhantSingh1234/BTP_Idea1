"""Verify repository integrity with the Python standard library."""
from pathlib import Path
import argparse,hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent
def sha_stream(f):
 h=hashlib.sha256()
 for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--extracted',action='store_true');a=p.parse_args()
 m=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_text());errors=[];checked=0
 for r in m['files']+m['support_files']+m['archives']:
  q=ROOT/r['path']
  if not q.is_file():errors.append('missing: '+r['path']);continue
  with q.open('rb') as f:actual=sha_stream(f)
  if actual!=r['sha256']:errors.append('changed: '+r['path'])
  checked+=1
 for archive in m['archives']:
  with zipfile.ZipFile(ROOT/archive['path']) as z:
   for r in archive['members']:
    with z.open(r['path']) as f:actual=sha_stream(f)
    if actual!=r['sha256']:errors.append('archive member changed: '+r['path'])
    if a.extracted:
     q=ROOT/r['path']
     if not q.is_file():errors.append('not extracted: '+r['path'])
     else:
      with q.open('rb') as f:actual=sha_stream(f)
      if actual!=r['sha256']:errors.append('extracted member changed: '+r['path'])
    checked+=1
 print(json.dumps({'passed':not errors,'checked_files_and_archive_members':checked,'errors':errors},indent=2))
 return 1 if errors else 0
if __name__=='__main__':raise SystemExit(main())
