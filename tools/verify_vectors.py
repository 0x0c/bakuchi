#!/usr/bin/env python3
"""ゴールデンベクタ適合性チェッカ。

spec/bucketing.md の参照実装が spec/golden-vectors.json を再現することを検証する。
各 SDK（Swift / Kotlin / Go / TypeScript）は同等のテストを自身の CI に持ち、
不一致の場合はマージをブロックすること。

  usage: python3 tools/verify_vectors.py [--vectors PATH] [--distribution]
"""

import argparse
import hashlib
import json
import struct
import sys
import uuid
from collections import Counter
from pathlib import Path

TOTAL_BUCKETS = 10_000


def bucket(salt: str, unit_id: str) -> int:
    """spec/bucketing.md §1 の規範実装。"""
    digest = hashlib.sha256(f"{salt}:{unit_id}".encode("utf-8")).digest()
    return struct.unpack(">I", digest[:4])[0] % TOTAL_BUCKETS


def assign(salt: str, unit_id: str, splits) -> str:
    """spec/bucketing.md §2 の規範実装。splits は [[name, weight_bp], ...] で定義順を保つ。"""
    b = bucket(salt, unit_id)
    cumulative = 0
    for name, weight_bp in splits:
        cumulative += weight_bp
        if b < cumulative:
            return name
    return "__unassigned__"


def verify(vectors: dict) -> int:
    failures = 0

    for v in vectors["bucket_vectors"]:
        digest = hashlib.sha256(f"{v['salt']}:{v['unit_id']}".encode("utf-8")).digest()
        prefix_hex = digest[:4].hex()
        n = struct.unpack(">I", digest[:4])[0]
        got = bucket(v["salt"], v["unit_id"])

        # 段階ごとに照合し、不一致がどこで生じたかを特定できるようにする
        if prefix_hex != v["sha256_prefix_hex"]:
            print(f"FAIL [hash]   salt={v['salt']!r} unit={v['unit_id']!r} "
                  f"expected={v['sha256_prefix_hex']} got={prefix_hex}")
            print("  → UTF-8 エンコーディングか区切り文字 ':' の扱いを確認")
            failures += 1
        elif n != v["uint32_be"]:
            print(f"FAIL [uint32] salt={v['salt']!r} unit={v['unit_id']!r} "
                  f"expected={v['uint32_be']} got={n}")
            print("  → ビッグエンディアン読み、または符号付き整数として読んでいないか確認")
            failures += 1
        elif got != v["bucket"]:
            print(f"FAIL [bucket] salt={v['salt']!r} unit={v['unit_id']!r} "
                  f"expected={v['bucket']} got={got}")
            print("  → 剰余演算、または負値の扱いを確認")
            failures += 1

    for a in vectors["assignment_vectors"]:
        got = assign(a["salt"], a["unit_id"], a["splits"])
        if got != a["variant"]:
            print(f"FAIL [assign] case={a['case']} unit={a['unit_id']!r} "
                  f"bucket={a['bucket']} expected={a['variant']} got={got}")
            print("  → バリアントの走査順（定義順を厳守）と累積レンジの境界条件を確認")
            failures += 1

    n_bucket = len(vectors["bucket_vectors"])
    n_assign = len(vectors["assignment_vectors"])
    if failures == 0:
        print(f"OK — {n_bucket} bucket vectors, {n_assign} assignment vectors すべて一致")
    else:
        print(f"\n{failures} 件の不一致（対象: {n_bucket + n_assign} ベクタ）")
    return failures


def check_distribution(n: int = 200_000, groups: int = 100) -> int:
    """一様性の χ² 検定。spec/bucketing.md §4 の数値を再現する。"""
    import random

    random.seed(42)
    ids = [str(uuid.UUID(int=random.getrandbits(128))) for _ in range(n)]

    counts = Counter(bucket("exp:checkout_button_v2:1", i) * groups // TOTAL_BUCKETS for i in ids)
    expected = n / groups
    chi2 = sum((counts[g] - expected) ** 2 / expected for g in range(groups))

    # df=99 の 0.1% 棄却限界（両裾で異常を検出する。小さすぎる値も不自然）
    lo, hi = 54.2, 148.2
    ok = lo < chi2 < hi
    print(f"{'OK' if ok else 'FAIL'} — 一様性: chi2(df={groups - 1}) = {chi2:.2f} "
          f"(期待 ≈ {groups - 1}, 許容 {lo}–{hi})")

    # seed 変更による再ランダム化の独立性
    a = [assign("exp:x:1", i, [["control", 5000], ["treatment", 5000]]) for i in ids[:50_000]]
    b = [assign("exp:x:2", i, [["control", 5000], ["treatment", 5000]]) for i in ids[:50_000]]
    same_rate = sum(1 for x, y in zip(a, b) if x == y) / len(a)
    indep_ok = 0.49 < same_rate < 0.51
    print(f"{'OK' if indep_ok else 'FAIL'} — 再ランダム化の独立性: "
          f"seed 変更後も同一バリアントの割合 = {same_rate:.4f} (期待 ≈ 0.5)")

    balance = Counter(a)
    print(f"OK — 50/50 分割: {dict(balance)}")

    return 0 if (ok and indep_ok) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vectors", type=Path,
                        default=Path(__file__).resolve().parent.parent / "spec" / "golden-vectors.json")
    parser.add_argument("--distribution", action="store_true",
                        help="一様性と独立性の統計的検証も実行する（数秒かかる）")
    args = parser.parse_args()

    vectors = json.loads(args.vectors.read_text(encoding="utf-8"))
    failures = verify(vectors)

    if args.distribution:
        print()
        failures += check_distribution()

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
