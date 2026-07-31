# bakuchi — iOS / Android 両対応 A/B テストプラットフォーム 設計

モバイル（iOS / Android）を第一級市民として扱う、実験プラットフォームの技術選定と設計。
フィーチャーフラグ配信・被験者割当・イベント収集・統計解析までを一気通貫で扱う。

## ロードマップ（Web）

段階的構築計画を可視化したページ: **https://0x0c.github.io/bakuchi/**

[docs/09-roadmap.md](docs/09-roadmap.md) を出典に、フェーズのタイムライン（最短・最長の幅つき）、
各フェーズの成果物と「意図的にやらないこと」、領域ごとのケイパビリティ導入マップを表示する。
ソースは [site/](site/)、`main` への push で GitHub Actions が自動デプロイする
（[.github/workflows/pages.yml](.github/workflows/pages.yml)）。

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
| [docs/adr/](docs/adr/) | 主要な意思決定記録（ADR） |

## 仕様（実装が従う規範）

| ファイル | 内容 |
|---|---|
| [spec/bucketing.md](spec/bucketing.md) | 決定的バケッティングアルゴリズムの規範仕様 |
| [spec/golden-vectors.json](spec/golden-vectors.json) | 全 SDK が再現すべきゴールデンベクタ |
| [spec/config-bundle.schema.json](spec/config-bundle.schema.json) | 配信コンフィグの JSON Schema |
| [spec/event.schema.json](spec/event.schema.json) | イベントスキーマ |
| [tools/verify_vectors.py](tools/verify_vectors.py) | ゴールデンベクタ適合性チェッカ |

## 設計の要点（3行）

1. **端末内評価（local evaluation）** — 割当をサーバに問い合わせない。コンフィグを丸ごと配信し端末で決める。ネットワーク遅延ゼロ・オフライン動作・障害時も既存挙動を維持。
2. **セッション内シール（session-sealed）** — 起動時に確定した割当をセッション中は変えない。画面ごとに UI が変わる事故を構造的に排除する。
3. **決定性の一点管理** — 割当は `SHA-256(salt + ":" + unit_id)` のみに依存。Swift / Kotlin / Go / Python の全実装が同一のゴールデンベクタで CI 検証される。

## 前提と適用範囲

- 想定規模: MAU 100 万〜1000 万、同時実行実験 50〜200、イベント 10 億件/日 程度まで単一構成でスケールする想定。
- これ未満の規模では自前構築は割に合わない。[ADR-0001](docs/adr/0001-build-vs-buy.md) に判断基準と SaaS/OSS 採用の推奨を記載。
- 本リポジトリは設計ドキュメントであり、実装は含まない（[docs/09-roadmap.md](docs/09-roadmap.md) の Phase 1 から着手する）。
