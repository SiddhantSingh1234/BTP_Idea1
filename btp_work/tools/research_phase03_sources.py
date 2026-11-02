"""Phase 03 only: retain primary source evidence; never execute artifact code."""
from pathlib import Path
import hashlib, json, sys, urllib.request, zipfile, datetime
ROOT=Path('btp_work').resolve()
sys.path.insert(0,str(ROOT/'.phase03-tools'))
import pypdfium2 as pdfium
out=ROOT/'runs/phase_03/research'
out.mkdir(parents=True,exist_ok=True)
manifest={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pdf_renderer':'pypdfium2 5.14.0','rendered':[]}
for name,pages in [('4_ISCA59077.2024.00030.pdf',[6,7,11]),('2_ZAP_Zoned_Architecture_and_Performant_Compiler_for_Field-Programmable_Atom_Array.pdf',[5]),('3_DasAtom_A_Divide-and-Shuttle_Atom_Approach_to_Quantum_Circuit_Transformation.pdf',[7])]:
    path=ROOT.parent/'Papers'/name
    pdf=pdfium.PdfDocument(str(path))
    for page in pages:
        dest=out/(name.split('_')[0]+'_page_'+str(page)+'.png')
        if not dest.exists(): pdf[page-1].render(scale=2).to_pil().save(dest)
        manifest['rendered'].append({'source':str(path.relative_to(ROOT.parent)),'page':page,'pdf_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'image':str(dest.relative_to(ROOT))})
url='https://zenodo.org/api/records/10995324'
record=json.load(urllib.request.urlopen(url,timeout=30))
(out/'zenodo_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
f=record['files'][0]
archive=out/f['key']
if not archive.exists():
    with urllib.request.urlopen(f['links']['self'],timeout=45) as src, archive.open('wb') as dst:
        while block:=src.read(1024*1024): dst.write(block)
raw=archive.read_bytes()
assert 'md5:'+hashlib.md5(raw).hexdigest()==f['checksum']
manifest['artifact']={'record':url,'archive':str(archive.relative_to(ROOT)),'md5':f['checksum'],'sha256':hashlib.sha256(raw).hexdigest(),'files':[]}
ref=ROOT/'source_review/phase03_atomique'
with zipfile.ZipFile(archive) as z:
    for info in z.infolist():
        p=Path(info.filename)
        if info.is_dir() or not (p.suffix in ['.py','.yaml','.yml'] or p.name.lower() in ['license','license.txt','readme.md']):continue
        if '__pycache__' in p.parts or '.git' in p.parts:continue
        dest=(ref/p).resolve()
        if not dest.is_relative_to(ref.resolve()):raise ValueError('unsafe archive path')
        content=z.read(info)
        if dest.exists():assert dest.read_bytes()==content
        else:
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content)
        manifest['artifact']['files'].append({'path':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(content).hexdigest()})
(out/'research_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'rendered':len(manifest['rendered']),'source_files':len(manifest['artifact']['files']),'artifact_sha256':manifest['artifact']['sha256']}))