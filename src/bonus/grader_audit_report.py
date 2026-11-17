"""Write reports/bonus_grader_audit.json from a real run of the relations (B7).

    python -m bonus.grader_audit_report --out reports/bonus_grader_audit.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bonus.grader_relations import audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="reports/bonus_grader_audit.json")
    args = parser.parse_args(argv)
    result = audit()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    relations = list(next(iter(result["matrix"].values())))
    print(f"{'variant':<10} " + " ".join(f"{r[:28]:<28}" for r in relations))
    for variant, row in result["matrix"].items():
        cells = []
        for relation in relations:
            cell = row[relation]
            cells.append(f"{'holds' if cell['holds'] else 'DEVIATES ' + str(len(cell['violations'])) + ' metric(s)':<28}")
        print(f"{variant:<10} " + " ".join(cells))
    print("delay relation:", result["delay_relation"])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
