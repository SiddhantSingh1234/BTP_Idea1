"""Resolve both public default-branch heads and preserve the exact responses."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.request

WORK = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    out = (WORK / args.out).resolve()
    if not out.is_relative_to(WORK) or out.exists():
        raise SystemExit("Use a new directory under btp_work")
    out.mkdir(parents=True)
    rows = []
    for name in ["ipash185/NAQC_Compiler", "Huangyunqi/DasAtom"]:
        row = {"repository": name, "source_url": "https://github.com/" + name,
               "checked_utc": datetime.now(timezone.utc).isoformat()}
        url = "https://api.github.com/repos/" + name + "/commits?per_page=1"
        row["query_url"] = url
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BTP-baseline-audit"})
            with urllib.request.urlopen(req, timeout=25) as response:
                payload = response.read()
            (out / (name.split("/")[1] + "_head.json")).write_bytes(payload)
            head = json.loads(payload)[0]
            row.update(status="ok", commit=head["sha"], commit_url=head["html_url"],
                commit_date=head["commit"]["committer"]["date"], message=head["commit"]["message"],
                local_working_tree_present=(WORK / "vendor" / (name.split("/")[1] + "-" + head["sha"])).exists())
        except Exception as e:
            row.update(status="error", error=str(e))
        rows.append(row)
    (out / "latest_sources.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rows, indent=2))
    raise SystemExit(0 if all(r["status"] == "ok" for r in rows) else 2)


if __name__ == "__main__":
    main()
