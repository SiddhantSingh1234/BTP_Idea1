"""Check planning links, phase completeness, and retained source provenance.

This validates the planning artifacts, not the unimplemented research software.
"""
from pathlib import Path
from urllib.parse import unquote
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
work = Path(__file__).resolve().parents[1]
root = work.parent
issues = []
docs = []
for directory, subdirs, files in os.walk(work):
    subdirs[:] = [d for d in subdirs if d not in {".research-tools", ".compiler-tools", ".venv", ".venv-replay", "vendor", "upstream_excerpt"}]
    docs.extend(Path(directory) / name for name in files if name.endswith(".md"))
docs = sorted(docs)
links_checked = 0
for doc in docs:
    body = doc.read_text(encoding="utf-8")
    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", body):
        target = match.group(1).strip().strip("<>")
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            continue
        target_path, _, fragment = target.partition("#")
        destination = (doc.parent / unquote(target_path)).resolve() if target_path else doc
        links_checked += 1
        if not destination.exists():
            issues.append(f"Missing link from {doc.relative_to(work)}: {target}")
            continue
        if fragment and destination.suffix == ".md":
            destination_text = destination.read_text(encoding="utf-8")
            headings = re.findall(r"(?m)^#{1,6}\s+(.+)$", destination_text)
            anchors = {re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-") for heading in headings}
            if fragment not in anchors:
                issues.append(f"Missing heading from {doc.relative_to(work)}: {target}")

phases = sorted((work / "plan" / "phases").glob("*.md"))
if [p.name[:2] for p in phases] != [f"{i:02d}" for i in range(11)]:
    issues.append("Expected exactly phases 00 through 10")
phase_summary = []
for phase in phases:
    body = phase.read_text(encoding="utf-8")
    checks = body.count("- [ ]")
    if checks < 5:
        issues.append(f"Insufficient acceptance checklist in {phase.name}")
    if "## Work packages" not in body or "## Handoff" not in body or "Deliverables" not in body:
        issues.append(f"Required task/deliverable/handoff content missing in {phase.name}")
    phase_summary.append({"file": phase.relative_to(work).as_posix(), "words": len(body.split()), "acceptance_items": checks})

manifest = json.loads((work / "source_review" / "manifest.json").read_text(encoding="utf-8"))
for entry in manifest:
    source = root / entry["source"]
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != entry["sha256"]:
        issues.append(f"Source PDF changed since extraction: {entry['source']}")
    if not (work / entry["extracted"]).exists():
        issues.append(f"Missing extracted text: {entry['extracted']}")

repositories = json.loads((work / "source_review" / "repository_snapshot.json").read_text(encoding="utf-8-sig"))
rft = next(repo for repo in repositories if repo["repository"] == "ipash185/NAQC_Compiler")
upstream_tree = {item["path"]: item for item in rft["tree"]}
excerpt_root = work / "source_review" / "upstream_excerpt" / "NAQC_Compiler"
excerpt_files = sorted(p for p in excerpt_root.rglob("*") if p.is_file())
for excerpt in excerpt_files:
    relative = excerpt.relative_to(excerpt_root).as_posix()
    data = excerpt.read_bytes()
    blob_hash = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    if relative not in upstream_tree or blob_hash != upstream_tree[relative]["sha"]:
        issues.append(f"Upstream excerpt differs from pinned git blob: {relative}")

report = {
    "scope": "Planning links, phase documents, original PDF hashes and upstream excerpt integrity only; no compiler execution or research acceptance checks",
    "documents_checked": len(docs),
    "local_links_checked": links_checked,
    "phase_documents": phase_summary,
    "pdf_sources_verified": len(manifest),
    "upstream_excerpt_files_verified": len(excerpt_files),
    "issues": issues,
    "ok": not issues,
}
report_path = work / "plan" / "document_check_report.json"
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
environment = {
    "purpose": "Document extraction and planning verification only",
    "python": platform.python_version(),
    "pypdf": importlib.metadata.version("pypdf"),
    "fonttools": importlib.metadata.version("fonttools"),
    "portable_runtime_location": ".research-tools/python",
    "compiler_environment_installed": (work / ".venv" / "Scripts" / "python.exe").exists(),
}
(work / "source_review" / "preparation_environment.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
raise SystemExit(1 if issues else 0)
