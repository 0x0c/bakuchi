#!/usr/bin/env python3
"""ロードマップ項目を Status で絞り込んで一覧する。

読み取り専用。各項目のメタデータブロックだけを読み、ネットワークにも LLM にも
依存しない。roadmap-filter ワークフローが使う。

  usage: python3 tools/roadmap_query.py --status "Proposal" [--topic "Data pipeline"] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_roadmap_format import STATUS_PAIRS, parse_metadata  # noqa: E402

ROADMAPS = Path(__file__).resolve().parent.parent / "roadmaps"


def collect() -> list[dict[str, str]]:
    items = []
    for directory in sorted(ROADMAPS.iterdir()):
        if not directory.is_dir():
            continue
        m = re.match(r"^BK-(\d{4}|XXXX)-(.+)$", directory.name)
        if not m:
            continue
        path = directory / f"BK-{m.group(1)}-{m.group(2)}.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        fields, _, _ = parse_metadata(text, japanese=False)
        title = ""
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].split("—", 1)[-1].strip()
                break
        items.append({
            "id": f"BK-{m.group(1)}",
            "title": title,
            "status": fields.get("Status", "").strip("*"),
            "topic": fields.get("Topic", ""),
            "path": str(path.relative_to(ROADMAPS.parent)),
        })
    return items


def main() -> int:
    valid = [s.strip("*") for s in STATUS_PAIRS]
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", help=f"絞り込む Status。有効: {', '.join(valid)}")
    parser.add_argument("--topic", help="絞り込む Topic")
    parser.add_argument("--json", action="store_true", help="JSON で出力する")
    args = parser.parse_args()

    if args.status and args.status.lower() not in {v.lower() for v in valid}:
        print(f"未知の Status: {args.status}\n有効: {', '.join(valid)}", file=sys.stderr)
        return 1

    items = collect()
    if args.status:
        items = [i for i in items if i["status"].lower() == args.status.lower()]
    if args.topic:
        items = [i for i in items if i["topic"].lower() == args.topic.lower()]
    items.sort(key=lambda i: (i["topic"], i["id"]))

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0

    if not items:
        print("該当なし")
        return 0

    print("| ID | Item | Topic | Path |")
    print("|---|---|---|---|")
    for i in items:
        print(f"| {i['id']} | {i['title']} | {i['topic']} | `{i['path']}` |")
    print(f"\n{len(items)} 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
