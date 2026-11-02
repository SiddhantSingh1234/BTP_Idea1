"""Print bounded source excerpts for review, without touching original files."""
from pathlib import Path
import re

folder = Path(__file__).resolve().parents[1] / "source_review" / "extracted"
for name in ["1_2607.20616v2.txt", "5_3658617.3697778.txt", "6_Schmid_2024_Quantum_Sci._Technol._9_033001.txt"]:
    text = (folder / name).read_text(encoding="utf-8")
    print("\nFILE:", name, "\nOPENING:\n", text[:6500])
    hits = list(re.finditer(r"(?im)^.*(?:CONCLUSION|Conclusion|conclusion|Future directions|future directions).*$", text))
    for hit in hits[-2:]:
        print("\nCONCLUSION CONTEXT:\n", text[max(0, hit.start() - 150):hit.end() + 4500])
