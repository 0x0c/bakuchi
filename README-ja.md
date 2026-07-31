[English](README.md) · **日本語**

# bakuchi — iOS / Android 両対応 A/B テストプラットフォーム 設計

モバイル（iOS / Android）を第一級市民として扱う、実験プラットフォームの技術選定と設計。
フィーチャーフラグ配信・被験者割当・イベント収集・統計解析までを一気通貫で扱う。

## ロードマップの一覧ページ

BK 項目の一覧: **https://0x0c.github.io/bakuchi/**

[roadmaps/](roadmaps/) の各項目を、可決 / 提案 / 提案（保留）という状態ごとに束ねて採番順に並べる。
タイトル・状態・トピック・関連は各項目の BK-METADATA が出典で、フェーズは項目の「作業」節が
明記しているものだけを引く。日英どちらの版へも 1 クリックで飛べる。
ソースは [site/](site/)、`main` への push で GitHub Actions が自動デプロイする
（[.github/workflows/pages.yml](.github/workflows/pages.yml)）。ビルドステップはなく、
素の HTML / CSS / ES モジュールで完結する。ローカルで見るには任意の静的サーバを使う
（`python3 -m http.server --directory site`）。ES モジュールを読むため `file://` では動かない。

初回のみ、リポジトリ設定 → Pages → Build and deployment → Source を **GitHub Actions**
にする必要がある。`GITHUB_TOKEN` では Pages サイトそのものを作成できないため、
この一手だけはワークフローから自動化できない。

## ドキュメント構成

| ドキュメント | 内容 |
|---|---|
| [docs/01-requirements-ja.md](docs/01-requirements-ja.md) | 要求仕様。**モバイル固有の制約**（アプリのリリースサイクル、オフライン、遅延到着）はここが起点 |
| [docs/02-architecture-ja.md](docs/02-architecture-ja.md) | 全体アーキテクチャ、サービス分割、シーケンス |
| [docs/03-tech-selection-ja.md](docs/03-tech-selection-ja.md) | 技術選定と比較表、採用理由 |
| [docs/04-client-sdk-ja.md](docs/04-client-sdk-ja.md) | iOS / Android SDK 設計（API、評価モデル、ライフサイクル） |
| [docs/05-services-ja.md](docs/05-services-ja.md) | 各マイクロサービスの責務・API・データモデル |
| [docs/06-data-pipeline-ja.md](docs/06-data-pipeline-ja.md) | イベント基盤、遅延到着データ、時刻補正 |
| [docs/07-statistics-ja.md](docs/07-statistics-ja.md) | 統計設計（SRM、CUPED、逐次検定、多重比較） |
| [docs/08-operations-ja.md](docs/08-operations-ja.md) | SLO、リリース、ロールバック、プライバシー |
| [docs/09-roadmap-ja.md](docs/09-roadmap-ja.md) | 段階的な構築計画 |

各ドキュメントは日英の両方に置いている。英語版が接尾辞のないファイル名、日本語版が `-ja` を
付けたファイル名で、[docs/01-requirements.md](docs/01-requirements.md) と
[docs/01-requirements-ja.md](docs/01-requirements-ja.md) は同一文書の 2 言語版にあたる。
どちらか一方が他方の要約ではなく、どちらを読んでも議論の全体が得られる。

## ロードマップ（設計判断の記録）

主要な設計判断と、未決着の論点は、採番された **BK 項目**として [roadmaps/](roadmaps/) に日英両方で
置いています。書式と追加手順は [roadmaps/README-ja.md](roadmaps/README-ja.md) にあります。
最新の一覧は上記の[ロードマップの一覧ページ](#ロードマップの一覧ページ)、または
`python3 tools/roadmap_query.py --status "Proposal"` で引けます。

## 仕様（実装が従う規範）

| ファイル | 内容 |
|---|---|
| [spec/bucketing-ja.md](spec/bucketing-ja.md) | 決定的バケッティングアルゴリズムの規範仕様 |
| [spec/golden-vectors.json](spec/golden-vectors.json) | 全 SDK が再現すべきゴールデンベクタ |
| [spec/config-bundle.schema.json](spec/config-bundle.schema.json) | 配信コンフィグの JSON Schema |
| [spec/event.schema.json](spec/event.schema.json) | イベントスキーマ |
| [tools/verify_vectors.py](tools/verify_vectors.py) | ゴールデンベクタ適合性チェッカ |

## ツールとエージェント

```bash
./tools/check.sh          # 決定的な検証ゲート（ベクタ・ロードマップ形式・JSON・textlint）
```

| ファイル | 内容 |
|---|---|
| [tools/check.sh](tools/check.sh) | すべてのゲートをまとめて実行する |
| [tools/check_roadmap_format.py](tools/check_roadmap_format.py) | ロードマップ項目の正規形チェッカ |
| [tools/new_roadmap_item.py](tools/new_roadmap_item.py) | 項目の雛形生成と ID 採番 |
| [tools/roadmap_query.py](tools/roadmap_query.py) | Status によるロードマップの絞り込み |
| [.agent-workflows/](.agent-workflows/) | エージェント向けワークフロー（文章規範、起票、実装、レビュー追従） |
| [.claude/skills/](.claude/skills/) | 上記への Claude Code アダプタ |

ワークフローと文章規範は [Bajutsu](https://github.com/bajutsu-e2e/bajutsu) から Apache License 2.0
のもとで借用し、bakuchi 向けに改変しています。帰属表示は
[.agent-workflows/NOTICE](.agent-workflows/NOTICE) にあります。

## 設計の要点（3行）

1. **端末内評価（local evaluation）** — 割当をサーバに問い合わせない。コンフィグを丸ごと配信し端末で決める。ネットワーク遅延ゼロ・オフライン動作・障害時も既存挙動を維持。
2. **セッション内シール（session-sealed）** — 起動時に確定した割当をセッション中は変えない。画面ごとに UI が変わる事故を構造的に排除する。
3. **決定性の一点管理** — 割当は `SHA-256(salt + ":" + unit_id)` のみに依存。Swift / Kotlin / Go / Python の全実装が同一のゴールデンベクタで CI 検証される。

## 前提と適用範囲

- 想定規模: MAU 100 万〜1000 万、同時実行実験 50〜200、イベント 10 億件/日 程度まで単一構成でスケールする想定。
- これ未満の規模では自前構築は割に合わない。[BK-0001](roadmaps/BK-0001-build-vs-buy/BK-0001-build-vs-buy-ja.md) に判断基準と SaaS/OSS 採用の推奨を記載。
- 本リポジトリは設計ドキュメントであり、実装は含まない（[docs/09-roadmap-ja.md](docs/09-roadmap-ja.md) の Phase 1 から着手する）。
