#!/usr/bin/env bash
# 決定的な検証ゲート。緑ならマージ可、赤ならマージ不可。
#
# 判定するのは機械的に判定できるものだけ。散文の明晰さや論証の順序は
# レビュー時の人間の判断に委ねる（.agent-workflows/document-writing/workflow.md）。
set -uo pipefail

cd "$(dirname "$0")/.."

failed=0
run () {
  local name="$1"; shift
  printf '\n\033[1m==> %s\033[0m\n' "$name"
  if "$@"; then
    return 0
  fi
  printf '\033[31mFAILED: %s\033[0m\n' "$name"
  failed=1
}

run "決定性: バケッティングのゴールデンベクタ" \
  python3 tools/verify_vectors.py --distribution

run "形式: ロードマップ項目の正規形" \
  python3 tools/check_roadmap_format.py

# ページは roadmaps/ から生成する。生成器が読めない項目（未知の Status、日英で
# 食い違う進捗の件数）は、デプロイではなくここで落とす。出力は捨てる。
run "生成: ロードマップサイト" \
  python3 tools/build_roadmap_site.py --out "$(mktemp -d)"

run "整合性: 仕様ファイルの JSON" \
  python3 -c '
import json, glob, sys
bad = 0
for f in sorted(glob.glob("spec/*.json")):
    try:
        json.load(open(f, encoding="utf-8"))
        print(f"OK   {f}")
    except Exception as e:
        print(f"FAIL {f}: {e}"); bad = 1
sys.exit(bad)
'

# textlint は node と、一度の `npm ci` が必要。未導入ならスキップし、その旨を明示する。
#
# 言語ごとに config を分けて 2 回走らせる。1 つの config に overrides を書く方法は
# 採れない: textlint は overrides.files を config ファイル自身のディレクトリ基準で
# 照合するため、リポジトリ側のファイルには一致せず、日本語ルールが「静かに 1 つも
# 走らない」状態になる。緑に見えて何も検査していない状態が最も危ないため、
# 対象ファイルを明示して 2 回呼ぶ。
TEXTLINT_DIR=.agent-workflows/document-writing/textlint

# ゲートの対象は、この文章規範のもとで書かれた文書にかぎる。docs/ の英語版は規範のもとで
# 書いたので対象に含める。日本語版は規範を導入する前に書いたもので、まだ適合していない
# （30 件の指摘）。適合していない文書を対象に含めるとゲートが恒常的に赤くなり、ゲートとして
# 機能しなくなるため、日本語版は対象外にしてある。移行は roadmaps/README.md の Unsorted ideas
# に項目として積んである。
#
# spec/ は規範の適用範囲そのものの外にある。要求を述べる規範仕様であって議論を組み立てる
# 散文ではないため（.agent-workflows/document-writing/workflow.md の Scope を参照）。
ja_files () {
  find roadmaps -name '*-ja.md'
  echo README-ja.md
}
en_files () {
  find roadmaps -name 'BK-*.md' ! -name '*-ja.md'
  find docs -name '0*.md' ! -name '*-ja.md'
  echo roadmaps/README.md
  echo README.md
}

printf '\n\033[1m==> 文章: textlint\033[0m\n'
if [ -d "$TEXTLINT_DIR/node_modules" ]; then
  for lang in ja en; do
    printf -- '--- %s ---\n' "$lang"
    # shellcheck disable=SC2046
    if npx --prefix "$TEXTLINT_DIR" textlint \
        --config "$TEXTLINT_DIR/.textlintrc.${lang}.json" $("${lang}_files"); then
      echo "OK"
    else
      printf '\033[31mFAILED: textlint (%s)\033[0m\n' "$lang"
      failed=1
    fi
  done
elif [ -n "${CHECK_REQUIRE_TEXTLINT:-}" ]; then
  # CI ではスキップを許さない。検査していないのに緑になる状態は、赤より危ない。
  printf '\033[31mFAILED: textlint が未セットアップ（CHECK_REQUIRE_TEXTLINT が設定されている）\033[0m\n'
  printf '  npm --prefix %s ci --ignore-scripts\n' "$TEXTLINT_DIR"
  failed=1
else
  printf '\033[33mSKIPPED\033[0m — 未セットアップ。次を一度実行すること:\n'
  printf '  npm --prefix %s ci --ignore-scripts\n' "$TEXTLINT_DIR"
  printf '  （CHECK_REQUIRE_TEXTLINT=1 を設定すると、スキップを失敗として扱う。CI はそうしている）\n'
fi

printf '\n'
if [ "$failed" -eq 0 ]; then
  printf '\033[32mすべてのゲートが緑\033[0m\n'
else
  printf '\033[31m赤いゲートがある\033[0m\n'
fi
exit "$failed"
