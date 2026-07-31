#!/usr/bin/env python3
"""ロードマップ項目の形式チェッカ。

roadmaps/BK-NNNN-<slug>/ 配下の日英ファイル対が、roadmaps/README.md の定める
正規スケルトンに従っていることを検証する。

このチェックは gate であって formatter ではない。違反箇所を報告して終了し、
修正は書き手に委ねる。

  usage: python3 tools/check_roadmap_format.py [--roadmaps DIR]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# --- 正規の語彙 -------------------------------------------------------------

STATUS_PAIRS = {
    "**Implemented**": "**実装済み**",
    "**Accepted, in progress**": "**可決・実装中**",
    "**Accepted**": "**可決**",
    "**Proposal**": "**提案**",
    "**Proposal (deferred)**": "**提案（保留）**",
}

# (英語フィールド, 日本語フィールド, 必須か)
FIELDS = [
    ("Proposal", "提案", True),
    ("Author", "提案者", True),
    ("Status", "状態", True),
    ("Tracking issue", "トラッキング Issue", False),
    ("Implementing PR", "実装 PR", False),
    ("Topic", "トピック", True),
    ("Related", "関連", False),
    ("Superseded by", "後継", False),
]

SECTIONS_EN = [
    "Introduction",
    "Motivation",
    "Detailed design",
    "Alternatives considered",
    "Progress",
    "References",
]
SECTIONS_JA = ["はじめに", "動機", "詳細設計", "検討した代替案", "進捗", "参考"]

# Topic は統制語彙。日英で対応する値を持つ。
TOPICS = {
    "Platform strategy": "プラットフォーム戦略",
    "Client SDK architecture": "クライアント SDK 設計",
    "Config delivery": "コンフィグ配信",
    "Assignment & determinism": "割当と決定性",
    "Data pipeline": "データ基盤",
    "Statistics & analysis": "統計と解析",
    "Operations": "運用",
}

ID_RE = re.compile(r"^BK-(\d{4}|XXXX)-([a-z0-9-]+)$")
FENCE_OPEN = "<!-- BK-METADATA -->"
FENCE_CLOSE = "<!-- /BK-METADATA -->"


class Reporter:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def fail(self, path: Path, line: int | None, message: str) -> None:
        where = f"{path}:{line}" if line else str(path)
        self.failures.append(f"{where}: {message}")


def parse_metadata(text: str, japanese: bool) -> tuple[dict[str, str], list[str], int | None]:
    """フェンスで囲まれた領域だけを読む。

    フェンスが load-bearing である理由は roadmaps/README.md に書いてある。本文中に
    同じ形の表が現れても、パーサがそれを掴まないようにするためのもの。
    """
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == FENCE_OPEN)
        end = next(i for i, ln in enumerate(lines) if ln.strip() == FENCE_CLOSE)
    except StopIteration:
        return {}, [], None

    header_key = "項目" if japanese else "Field"
    fields: dict[str, str] = {}
    order: list[str] = []
    for raw in lines[start + 1 : end]:
        m = re.match(r"^\|\s*(.+?)\s*\|\s*(.*?)\s*\|$", raw)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        if key == header_key or set(key) <= {"-", ":"}:
            continue
        fields[key] = value
        order.append(key)
    return fields, order, start + 1


def check_file(path: Path, item_id: str, slug: str, japanese: bool, rep: Reporter) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 1. 言語切替リンク
    sibling = f"{item_id}-{slug}{'.md' if japanese else '-ja.md'}"
    expected = (
        f"[English]({sibling}) · **日本語**"
        if japanese
        else f"**English** · [日本語]({sibling})"
    )
    if not lines or lines[0].strip() != expected:
        rep.fail(path, 1, f"1行目は言語切替リンクでなければならない\n    期待: {expected}\n    実際: {lines[0] if lines else '(空)'}")

    # 2. H1 タイトル（ID + 半角スペース + em ダッシュ + スペース + タイトル）
    h1 = next((ln for ln in lines if ln.startswith("# ")), None)
    if h1 is None:
        rep.fail(path, None, "H1 見出しがない")
    elif not re.match(rf"^# {re.escape(item_id)} — \S", h1):
        rep.fail(path, lines.index(h1) + 1, f"H1 は `# {item_id} — <タイトル>` の形式（U+2014 の em ダッシュ）\n    実際: {h1}")

    # 3. メタデータブロック
    fields, order, meta_line = parse_metadata(text, japanese)
    if meta_line is None:
        rep.fail(path, None, f"メタデータが {FENCE_OPEN} … {FENCE_CLOSE} で囲まれていない")
        return {}

    canonical = [(ja if japanese else en) for en, ja, _ in FIELDS]
    for en, ja, required in FIELDS:
        name = ja if japanese else en
        if required and name not in fields:
            rep.fail(path, meta_line, f"必須メタデータ `{name}` がない")
    for key in order:
        if key not in canonical:
            rep.fail(path, meta_line, f"未知のメタデータ `{key}`（正規フィールドは {', '.join(canonical)}）")
    present = [k for k in order if k in canonical]
    if present != sorted(present, key=canonical.index):
        rep.fail(path, meta_line, f"メタデータの順序が正規順と異なる\n    期待順: {' → '.join(k for k in canonical if k in present)}\n    実際　: {' → '.join(present)}")

    # 4. Status は正規語彙のいずれか
    status_key = "状態" if japanese else "Status"
    status = fields.get(status_key, "")
    valid = set(STATUS_PAIRS.values()) if japanese else set(STATUS_PAIRS)
    if status and status not in valid:
        rep.fail(path, meta_line, f"`{status_key}` が正規語彙にない: {status}\n    有効: {', '.join(sorted(valid))}")

    # 5. セクション見出し
    want = SECTIONS_JA if japanese else SECTIONS_EN
    got = [ln[3:].strip() for ln in lines if ln.startswith("## ")]
    if got != want:
        rep.fail(path, None, f"H2 セクションが正規形と一致しない\n    期待: {' / '.join(want)}\n    実際: {' / '.join(got) or '(なし)'}")

    return fields


def check_item(directory: Path, rep: Reporter) -> None:
    m = ID_RE.match(directory.name)
    if not m:
        rep.fail(directory, None, "ディレクトリ名は `BK-NNNN-<slug>` 形式（slug は [a-z0-9-]）")
        return
    item_id, slug = f"BK-{m.group(1)}", m.group(2)

    en_path = directory / f"{item_id}-{slug}.md"
    ja_path = directory / f"{item_id}-{slug}-ja.md"
    for p in (en_path, ja_path):
        if not p.exists():
            rep.fail(p, None, "対になるファイルがない（日英そろっている必要がある）")
    if not (en_path.exists() and ja_path.exists()):
        return

    en_fields = check_file(en_path, item_id, slug, japanese=False, rep=rep)
    ja_fields = check_file(ja_path, item_id, slug, japanese=True, rep=rep)

    # 6. 日英で Status が対応していること（対でしか検出できない）
    en_status, ja_status = en_fields.get("Status"), ja_fields.get("状態")
    if en_status and ja_status and STATUS_PAIRS.get(en_status) != ja_status:
        rep.fail(directory, None, f"日英の Status が対応していない: EN `{en_status}` / JA `{ja_status}`")

    # 7. Topic は統制語彙から、かつ日英で対応していること
    topic = en_fields.get("Topic")
    if topic and topic not in TOPICS:
        rep.fail(en_path, None, f"未知の Topic: {topic}\n    既知: {', '.join(sorted(TOPICS))}")
    ja_topic = ja_fields.get("トピック")
    if topic in TOPICS and ja_topic is not None and ja_topic != TOPICS[topic]:
        rep.fail(directory, None, f"日英の Topic が対応していない: EN `{topic}` / JA `{ja_topic}`（期待: `{TOPICS[topic]}`）")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--roadmaps", type=Path,
                        default=Path(__file__).resolve().parent.parent / "roadmaps")
    args = parser.parse_args()

    items = sorted(d for d in args.roadmaps.iterdir() if d.is_dir())
    if not items:
        print(f"項目が見つからない: {args.roadmaps}")
        return 1

    rep = Reporter()
    for directory in items:
        check_item(directory, rep)

    if rep.failures:
        for f in rep.failures:
            print(f"FAIL {f}")
        print(f"\n{len(rep.failures)} 件の違反（対象 {len(items)} 項目）")
        return 1

    print(f"OK — {len(items)} 項目（{len(items) * 2} ファイル）が正規形に適合")
    return 0


if __name__ == "__main__":
    sys.exit(main())
