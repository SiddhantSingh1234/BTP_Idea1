"""Extract only Papers/ PDFs and the proposal PDF; preserve page boundaries."""
from pathlib import Path
import hashlib
import json
from pypdf import PdfReader

root = Path(__file__).resolve().parents[2]
output = root / "btp_work" / "source_review" / "extracted"
output.mkdir(parents=True, exist_ok=True)
sources = sorted((root / "Papers").glob("*.pdf"))
sources += [root / "Proposal" / "BTP_Research_Proposal.pdf"]
manifest = []
for source in sources:
    reader = PdfReader(source)
    pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
    target = output / (source.stem + ".txt")
    target.write_text("\n\n".join(f"=== PDF PAGE {i + 1} ===\n{text}" for i, text in enumerate(pages)), encoding="utf-8")
    links = sorted({str(a.get_object().get("/A", {}).get("/URI")) for page in reader.pages for a in page.get("/Annots", []) if a.get_object().get("/A", {}).get("/URI")})
    manifest.append({"source": source.relative_to(root).as_posix(), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "pages": len(pages), "extracted": target.relative_to(root / "btp_work").as_posix(), "links": links})
    print(f"{source.name}: {len(pages)} pages, {sum(map(len, pages))} characters")
(output.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
