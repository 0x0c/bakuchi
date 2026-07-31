# bakuchi — iOS / Android 両対応 A/B テストプラットフォーム 設計

モバイル（iOS / Android）を第一級市民として扱う、実験プラットフォームの技術選定と設計。
フィーチャーフラグ配信・被験者割当・イベント収集・統計解析までを一気通貫で扱う。

## ロードマップ（Web）

段階的な構築計画を可視化したページ: **https://0x0c.github.io/bakuchi/**

[docs/09-roadmap.md](docs/09-roadmap.md) を出典に、フェーズのタイムライン（最短・最長の幅つき）、
各フェーズの成果物と「意図的にやらないこと」、領域ごとのケイパビリティ導入マップを表示する。
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
| [docs/01-requirements.md](docs/01-requirements.md) | 要求仕様。**モバイル固有の制約**（アプリのリリースサイクル、オフライン、遅延到着）はここが起点 |
| [docs/02-architecture.md](docs/02-architecture.md) | 全体アーキテクチャ、サービス分割、シーケンス |
| [docs/03-tech-selection.md](docs/03-tech-selection.md) | 技術選定と比較表、採用理由 |
| [docs/04-client-sdk.md](docs/04-client-sdk.md) | iOS / Android SDK 設計（API、評価モデル、ライフサイクル） |
| [docs/05-services.md](docs/05-services.md) | 各マイクロサービスの責務・API・データモデル |
| [docs/06-data-pipeline.md](docs/06-data-pipeline.md) | イベント基盤、遅延到着データ、時刻補正 |
| [docs/07-statistics.md](docs/07-statistics.md) | 統計設計（SRM、CUPED、逐次検定、多重比較） |
| [docs/08-operations.md](docs/08-operations.md) | SLO、リリース、ロールバック、プライバシー |
| [docs/09-roadmap.md](docs/09-roadmap.md) | 段階的な構築計画 |

## ロードマップ（設計判断の記録）

主要な設計判断と、未決着の論点は、採番された **BK 項目**として [roadmaps/](roadmaps/) に日英両方で
置いています。書式と追加手順は [roadmaps/README-ja.md](roadmaps/README-ja.md) にあります。

| ID | 項目 | Status |
|---|---|---|
| [BK-0001](roadmaps/BK-0001-build-vs-buy/BK-0001-build-vs-buy-ja.md) | 自前構築か既製品か | 可決 |
| [BK-0002](roadmaps/BK-0002-local-evaluation/BK-0002-local-evaluation-ja.md) | 割当をサーバではなく端末内で評価する | 可決 |
| [BK-0003](roadmaps/BK-0003-native-sdks/BK-0003-native-sdks-ja.md) | ネイティブ 2 実装の SDK を、ゴールデンベクタで担保する | 可決 |
| [BK-0004](roadmaps/BK-0004-bucketing-hash/BK-0004-bucketing-hash-ja.md) | 決定的バケッティングに SHA-256 を用いる | 可決 |
| [BK-0005](roadmaps/BK-0005-session-sealed-config/BK-0005-session-sealed-config-ja.md) | コンフィグをセッション内でシールする | 可決 |
| [BK-0006](roadmaps/BK-0006-event-warehouse-selection/BK-0006-event-warehouse-selection-ja.md) | ClickHouse と既存 DWH のどちらを採るか | 提案 |
| [BK-0007](roadmaps/BK-0007-revisit-kmp-shared-core/BK-0007-revisit-kmp-shared-core-ja.md) | 共有 Kotlin Multiplatform コアの再評価 | 提案（保留） |
| [BK-0008](roadmaps/BK-0008-config-bundle-signing/BK-0008-config-bundle-signing-ja.md) | コンフィグバンドルの Ed25519 署名 | 提案 |
| [BK-0009](roadmaps/BK-0009-flink-late-data/BK-0009-flink-late-data-ja.md) | 遅延到着イベントの再処理に Flink を導入する | 提案（保留） |

一覧は `python3 tools/roadmap_query.py --status "Proposal"` でも引けます。

## 仕様（実装が従う規範）

| ファイル | 内容 |
|---|---|
| [spec/bucketing.md](spec/bucketing.md) | 決定的バケッティングアルゴリズムの規範仕様 |
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
- 本リポジトリは設計ドキュメントであり、実装は含まない（[docs/09-roadmap.md](docs/09-roadmap.md) の Phase 1 から着手する）。
