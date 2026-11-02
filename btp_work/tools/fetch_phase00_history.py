"""Read bounded public GitHub history/branch metadata; never modify source trees."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

WORK = Path(__file__).resolve().parents[1]
RFT = "ipash185/NAQC_Compiler"
DAS = "Huangyunqi/DasAtom"
PIN = "3d1f09233c2acd357fd9fbfad1b5300a921d301a"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    out = (WORK / args.out).resolve()
    if not out.is_relative_to(WORK) or out.exists():
        raise SystemExit("Use a new directory under btp_work")
    out.mkdir(parents=True)
    records = []

    def get(name, endpoint):
        url = "https://api.github.com/repos/" + endpoint
        record = {"url": url, "file": name + ".json"}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BTP-Phase00-audit", "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read()
                record["next_page_link"] = r.headers.get("Link")
            (out / record["file"]).write_bytes(body)
            record.update(status="ok", sha256=hashlib.sha256(body).hexdigest())
            data = json.loads(body)
        except Exception as e:
            record.update(status="error", error=str(e))
            data = None
        records.append(record)
        return data

    commits = get("rft_commits", f"{RFT}/commits?sha={PIN}&per_page=100")
    get("rft_branches", f"{RFT}/branches?per_page=100")
    get("rft_tags", f"{RFT}/tags?per_page=100")
    get("rft_current_head", f"{RFT}/commits?per_page=1")
    history = get("dasatom_helper_history", f"{DAS}/commits?path=DasAtom_fun.py&per_page=100")
    helper_matches = []
    if isinstance(history, list):
        for i, item in enumerate(history[:20]):
            tree = get(f"dasatom_root_{i:02}", f"{DAS}/git/trees/{item['commit']['tree']['sha']}")
            if tree:
                files = {x["path"]: x["sha"] for x in tree.get("tree", [])}
                helper_matches.append({"commit": item["sha"], "date": item["commit"]["committer"]["date"],
                    "helper_blob": files.get("DasAtom_fun.py"),
                    "matches_embedded_helper": files.get("DasAtom_fun.py") == "e0b021f0f8f38ebb7e2be5c240b264b75e247606"})
    result = {"records": records, "rft_commit_count_returned": len(commits) if isinstance(commits, list) else None,
        "rft_commits": [{"sha": c["sha"], "date": c["commit"]["committer"]["date"],
                         "message": c["commit"]["message"]} for c in commits] if isinstance(commits, list) else [],
        "embedded_helper_history_search": helper_matches,
        "limits": "At most 100 RFT commits and 20 DasAtom helper-changing root trees; not a complete Git checkout",
        "paper_revision_resolved": False}
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"requests": len(records), "errors": sum(r["status"] != "ok" for r in records),
        "rft_commits": result["rft_commit_count_returned"], "embedded_helper_matches": [x for x in helper_matches if x["matches_embedded_helper"]]}, indent=2))


if __name__ == "__main__":
    main()
