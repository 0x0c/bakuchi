#!/usr/bin/env python3
"""ロードマップ項目の雛形生成と ID 採番。

項目は BK-XXXX というプレースホルダで起票し、番号は最後にまとめて割り当てる。
起票時に番号を自分で決めると、並行して起票された項目と衝突するため。

  雛形生成: python3 tools/new_roadmap_item.py --slug <slug> --title "<title>" --topic "<topic>"
  番号割当: python3 tools/new_roadmap_item.py --allocate
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_roadmap_format import STATUS_PAIRS, TOPICS  # noqa: E402

ROADMAPS = Path(__file__).resolve().parent.parent / "roadmaps"
ISSUE_SEARCH = (
    "https://github.com/0x0c/bakuchi/issues"
    "?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+%22{id}%22"
)

TEMPLATE_EN = """\
**English** · [日本語]({id}-{slug}-ja.md)

# {id} — {title}

<!-- BK-METADATA -->
| Field | Value |
|---|---|
| Proposal | [{id}]({id}-{slug}.md) |
| Author | [@{handle}](https://github.com/{handle}) |
| Status | {status} |
| Tracking issue | [Search]({issue}) |
| Topic | {topic} |
<!-- /BK-METADATA -->

## Introduction

TBD

## Motivation

TBD

## Detailed design

TBD

## Alternatives considered

TBD

## Progress

TBD

## References

TBD
"""

TEMPLATE_JA = """\
[English]({id}-{slug}.md) · **日本語**

# {id} — {title_ja}

<!-- BK-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [{id}]({id}-{slug}-ja.md) |
| 提案者 | [@{handle}](https://github.com/{handle}) |
| 状態 | {status_ja} |
| トラッキング Issue | [検索]({issue}) |
| トピック | {topic_ja} |
<!-- /BK-METADATA -->

## はじめに

TBD

## 動機

TBD

## 詳細設計

TBD

## 検討した代替案

TBD

## 進捗

TBD

## 参考

TBD
"""


def default_handle() -> str:
    try:
        url = subprocess.run(["git", "config", "--get", "remote.origin.url"],
                             capture_output=True, text=True, check=False).stdout.strip()
        m = re.search(r"[:/]([^/]+)/[^/]+?(?:\.git)?$", url)
        if m:
            return m.group(1)
    except OSError:
        pass
    return "your-handle"


def scaffold(args: argparse.Namespace) -> int:
    if not re.fullmatch(r"[a-z0-9-]+", args.slug):
        print(f"slug は [a-z0-9-] のみ: {args.slug}")
        return 1
    if args.topic not in TOPICS:
        print(f"未知の Topic: {args.topic}\n既知: {', '.join(sorted(TOPICS))}")
        return 1
    status_en = f"**{args.status}**"
    if status_en not in STATUS_PAIRS:
        print(f"未知の Status: {args.status}\n有効: {', '.join(s.strip('*') for s in STATUS_PAIRS)}")
        return 1

    directory = ROADMAPS / f"BK-XXXX-{args.slug}"
    if directory.exists():
        print(f"既に存在する: {directory}\n先に --allocate で番号を割り当てること")
        return 1
    directory.mkdir(parents=True)

    fields = dict(
        id="BK-XXXX", slug=args.slug, title=args.title,
        title_ja=args.title_ja or args.title,
        handle=args.handle or default_handle(),
        status=status_en, status_ja=STATUS_PAIRS[status_en],
        topic=args.topic, topic_ja=TOPICS[args.topic],
        issue=ISSUE_SEARCH.format(id="BK-XXXX"),
    )
    (directory / f"BK-XXXX-{args.slug}.md").write_text(TEMPLATE_EN.format(**fields), encoding="utf-8")
    (directory / f"BK-XXXX-{args.slug}-ja.md").write_text(TEMPLATE_JA.format(**fields), encoding="utf-8")

    print(f"作成: {directory.relative_to(ROADMAPS.parent)}/")
    print("  TBD を埋めたあと、`--allocate` で番号を割り当てる。")
    print("  BK-XXXX を項目のディレクトリの外に書かないこと（割当時に書き換えられない）。")
    return 0


def allocate(_: argparse.Namespace) -> int:
    placeholders = sorted(d for d in ROADMAPS.iterdir()
                          if d.is_dir() and d.name.startswith("BK-XXXX-"))
    if not placeholders:
        print("BK-XXXX の項目がない")
        return 0

    used = [int(m.group(1)) for d in ROADMAPS.iterdir()
            if (m := re.match(r"^BK-(\d{4})-", d.name))]
    next_id = max(used, default=0) + 1

    for directory in placeholders:
        slug = directory.name[len("BK-XXXX-"):]
        new_id = f"BK-{next_id:04d}"
        for suffix in (".md", "-ja.md"):
            src = directory / f"BK-XXXX-{slug}{suffix}"
            text = src.read_text(encoding="utf-8")
            # 発行元の検索 URL は %22 で囲まれているため、素の置換で両方に効く
            text = text.replace("BK-XXXX", new_id)
            src.write_text(text, encoding="utf-8")
            src.rename(directory / f"{new_id}-{slug}{suffix}")
        directory.rename(ROADMAPS / f"{new_id}-{slug}")
        print(f"割当: BK-XXXX-{slug} → {new_id}-{slug}")
        next_id += 1

    print("\n項目ディレクトリの外に BK-XXXX が残っていないか確認すること:")
    print("  grep -rn 'BK-XXXX' --exclude-dir=.git .")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--allocate", action="store_true", help="BK-XXXX に実番号を割り当てる")
    parser.add_argument("--slug", help="ディレクトリ名に使う slug（[a-z0-9-]）")
    parser.add_argument("--title", help="英語タイトル")
    parser.add_argument("--title-ja", help="日本語タイトル（省略時は英語タイトル）")
    parser.add_argument("--topic", help=f"Topic。既知: {', '.join(sorted(TOPICS))}")
    parser.add_argument("--status", default="Proposal",
                        help="Status（既定: Proposal）")
    parser.add_argument("--handle", help="GitHub ハンドル（省略時は origin から推定）")
    args = parser.parse_args()

    if args.allocate:
        return allocate(args)
    if not (args.slug and args.title and args.topic):
        parser.error("--slug / --title / --topic は必須（または --allocate）")
    return scaffold(args)


if __name__ == "__main__":
    sys.exit(main())
