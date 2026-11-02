"""Recover complete pinned source archives, validating every blob before extraction.

Does not install dependencies, run upstream scripts, or infer a paper revision.
Use a new report path for each attempt; failed downloads remain evidence.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request

WORK = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, help="New JSON report path relative to btp_work")
    p.add_argument("--fetch", action="store_true", help="Download and verify; without this flag inventory only")
    args = p.parse_args()
    report = (WORK / args.output).resolve()
    if not report.is_relative_to(WORK) or report.exists():
        raise SystemExit("Report must be new and inside btp_work")
    repos = json.loads((WORK / "source_review/repository_snapshot.json").read_text(encoding="utf-8-sig"))
    results = []
    for repo in repos:
        name, rev = repo["repository"], repo["commit"]
        target = (WORK / "vendor" / (name.split("/")[1] + "-" + rev)).resolve()
        assert target.is_relative_to(WORK / "vendor")
        url = f"https://codeload.github.com/{name}/tar.gz/{rev}"
        record = {"repository": name, "revision": rev, "url": url,
                  "target": target.relative_to(WORK).as_posix(), "status": "not_attempted"}
        if not args.fetch:
            record["status"] = "inventory_only"
            results.append(record)
            continue
        try:
            if target.exists():
                raise FileExistsError(f"Refusing to overwrite {target}")
            req = urllib.request.Request(url, headers={"User-Agent": "BTP-Phase00-source-audit"})
            with urllib.request.urlopen(req, timeout=20) as response:
                archive = response.read()
            expected = {x["path"]: x for x in repo["tree"] if x["type"] == "blob"}
            verified = {}
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
                for member in tar.getmembers():
                    parts = PurePosixPath(member.name).parts
                    if not parts or ".." in parts or PurePosixPath(member.name).is_absolute():
                        raise ValueError("Unsafe archive path")
                    relative = PurePosixPath(*parts[1:]).as_posix()
                    if member.isdir():
                        continue
                    if not member.isfile() or relative not in expected or relative in verified:
                        raise ValueError(f"Unexpected archive member {member.name}")
                    if expected[relative].get("mode") not in ("100644", "100755"):
                        raise ValueError(f"Unsupported Git mode for {relative}")
                    payload = tar.extractfile(member).read()
                    blob = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()
                    if blob != expected[relative]["sha"]:
                        raise ValueError(f"Git blob mismatch: {relative}")
                    verified[relative] = payload
            if set(verified) != set(expected):
                raise ValueError(f"Incomplete archive: {len(verified)} of {len(expected)} blobs")
            # No mutation of the target occurs until all expected files are verified.
            for relative, payload in verified.items():
                destination = (target / relative).resolve()
                if not destination.is_relative_to(target):
                    raise ValueError("Destination escapes target")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as f:
                    f.write(payload)
            record.update(status="verified_complete_archive", blobs=len(verified),
                          archive_sha256=hashlib.sha256(archive).hexdigest(),
                          agents_files=[s for s in verified if PurePosixPath(s).name == "AGENTS.md"],
                          git_history_available=False)
        except Exception as e:
            record.update(status="error", error_type=type(e).__name__, error=str(e))
        results.append(record)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"fetch_requested": args.fetch, "results": results}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    raise SystemExit(2 if any(r["status"] == "error" for r in results) else 0)


if __name__ == "__main__":
    main()
