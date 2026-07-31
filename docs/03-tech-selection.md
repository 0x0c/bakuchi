# 03. 技術選定

各選定は「何を最適化したか」を明示する。トレードオフのない選択は載せていない。

## 0. 前提: そもそも作るべきか

先に片付ける。**MAU 100 万未満、年間実験数 50 未満なら自前構築は割に合わない。** GrowthBook（OSS・自己ホスト可）か Firebase A/B Testing で始めるべき。判断基準の詳細は [BK-0001](../roadmaps/BK-0001-build-vs-buy/BK-0001-build-vs-buy-ja.md)。

以降は「作る」と決めた場合の設計。

---

## 1. クライアント SDK

### 選択肢

| 案 | 実装 | 長所 | 短所 |
|---|---|---|---|
| **A. ネイティブ 2 実装** | Swift + Kotlin | 各プラットフォームで自然な API。バイナリ増分最小。導入時の反対がない。デバッグが素直 | ロジックが二重化。実装差異のリスク |
| B. Kotlin Multiplatform | 共通コア + 薄いネイティブ層 | ロジック一本化。Android 側は追加コストほぼゼロ | iOS に Kotlin/Native ランタイムが載る（+1.5〜3MB）。Swift 側の API がぎこちなくなる（suspend の橋渡し、ジェネリクス非対応）。iOS チームの同意を得にくい |
| C. Rust コア + UniFFI | 共通コア + 生成バインディング | バイナリ最小、性能最良、ロジック一本化 | Rust を書ける人が要る。ビルドパイプラインが複雑（xcframework、NDK） |

### 採用: **A（ネイティブ 2 実装）+ ゴールデンベクタによる適合性テスト**

理由:

1. **共通化したい本質は「決定的割当」であり、それは数十行しかない。** SHA-256 とビッグエンディアン読みだけ。共有ライブラリで守るより、[ゴールデンベクタ](../spec/golden-vectors.json)を全実装の CI で検証するほうが直接的かつ強力。実際、本設計の策定時に Python / Node / Go の 3 実装で同一結果を確認済み。
2. **C8（バイナリサイズ）は交渉可能な要件ではない。** 「A/B テスト SDK を入れるとアプリが 3MB 増えます」は iOS チームに拒否される。導入されない SDK に価値はない。
3. 残りのロジック（キャッシュ、イベントキュー、再送）は各プラットフォームの標準機能に強く依存する部分で、共通化の利得が思ったより小さい。iOS は `URLSession` の background transfer、Android は `WorkManager` — そもそも共通化できない。

**再検討の条件（明示しておく）:** SDK が 5,000 行を超える／両実装の挙動差に起因するバグが 2 件以上出る、のいずれかで B を再評価する。

| 項目 | iOS | Android |
|---|---|---|
| 言語 | Swift 5.9+（`strict concurrency`） | Kotlin 2.0+ |
| 最低サポート | iOS 15 | API 24 |
| 配布 | Swift Package Manager（CocoaPods も併走） | Maven Central（AAR） |
| 永続化 | ファイル + Keychain（`install_id` のみ） | DataStore + EncryptedSharedPreferences |
| ネットワーク | `URLSession`（依存ゼロ） | `OkHttp`（既に大半のアプリが持っている） |
| 非同期 | `async/await` + 同期評価 API | Coroutines + 同期評価 API |
| バックグラウンド送信 | `URLSession` background configuration | `WorkManager` |

**依存ライブラリを持たないこと**を強い制約にする。ホストアプリとのバージョン衝突は SDK 導入の最大の障壁。

---

## 2. サーバサイド言語

| サービス | 言語 | 理由 |
|---|---|---|
| config-edge, event-gateway, assignment-service | **Go** | 起動が速くメモリフットプリントが小さい（オートスケール時に効く）。GC のテールレイテンシが p99 要件に合う。標準ライブラリだけで HTTP サーバが完結し依存が少ない |
| experiment-service, metric-service, config-builder | **Go** | データプレーンと同一言語にして、**割当ロジックのコードを literally 共有する**。ここが分かれると決定性の保証が難しくなる |
| stats-service, metric-aggregator | **Python 3.12** | 交渉の余地なし。`statsmodels` / `scipy` / `numpy` が要る。統計手法を Go で再実装するのは誤り |
| console | **TypeScript / Next.js** | 実験一覧・結果閲覧という典型的な CRUD + ダッシュボード。React エコシステムのグラフ資産を使う |

**なぜ Kotlin/JVM や Node をサーバに使わないか:** JVM は起動時間とメモリで config-edge の要件（急なスパイクへのオートスケール）に不利。Node はイベント取り込みの CPU バウンドな処理（検証・圧縮）でシングルスレッドがボトルネックになる。ただし**既存組織が JVM 一色なら Kotlin/Spring で統一するほうが正しい** — 言語の技術的優位より運用可能性のほうが重い。

---

## 3. データストア

| 用途 | 採用 | 対抗馬と却下理由 |
|---|---|---|
| 実験メタデータ | **PostgreSQL 16** | MySQL でも可。`jsonb` でのターゲティング条件保持と、排他制約でのレイヤー容量管理が効くので Postgres を選好 |
| コンフィグ配信 | **S3 + CDN**（Redis はホットキャッシュ） | DB 直読みは可用性が足りない。「静的ファイル配信」に落とすのが最も堅い |
| スティッキー割当 | **Redis**（+ DynamoDB/Postgres で永続） | 読み書きとも高頻度・小さいレコード。TTL が要る |
| イベントバス | **Kafka**（MSK / Confluent Cloud） | Kinesis も可。パーティション数の柔軟性と、Flink との接続の枯れ具合で Kafka |
| イベント分析 | **ClickHouse** | **既に BigQuery / Snowflake があるならそれを使うべき**。新規導入なら ClickHouse（列指向、実験集計のようなスキャン主体クエリで圧倒的にコスト効率が良い、自己ホスト可） |
| 生ログ保管 | **S3**（Parquet / Iceberg） | 再処理のための単一の真実。ClickHouse は再構築可能な派生データとして扱う |

**ClickHouse を選ぶときの注意:** 運用負荷は Snowflake/BigQuery より明確に高い（レプリケーション、マージ、ディスク管理）。専任の担当がいないなら DWH に載せるほうが総コストは安い。ここは組織の状況で覆る選択。

---

## 4. ストリーム処理

| 案 | 評価 |
|---|---|
| **Flink**（採用） | イベント時刻ベースのウィンドウ、**遅延到着の一級サポート**、状態を持った重複排除。C4 の要件を直接満たす |
| Kafka Streams | JVM 前提。Flink より軽量だが遅延データの扱いが弱い |
| 単純な Go コンシューマ + ClickHouse 直挿入 | **Phase 1 はこれで良い。** 重複排除は ClickHouse の `ReplacingMergeTree` に任せる。Flink は遅延データの再計算が問題化してから入れる |

Phase 1 でいきなり Flink を入れるのは過剰。運用できるチームがいる場合のみ。

---

## 5. インフラ

| 項目 | 採用 | 備考 |
|---|---|---|
| コンテナ基盤 | Kubernetes（EKS） | config-edge のみ、より単純な基盤（ECS Fargate / Cloud Run）でも良い |
| CDN | CloudFront または Fastly | `stale-if-error` と即時 purge が使えることが条件。Fastly は purge が速い（<1s）ので実験の反映時間を詰めたいなら有利 |
| CD | Argo CD（GitOps） | 実験定義そのものは DB 管理だが、**メトリクス定義は Git 管理**にして PR レビューを通す |
| 監視 | OpenTelemetry → Prometheus / Grafana / Tempo | SDK もクライアント側メトリクス（フェッチ成功率、初期化時間）を送る |
| Secrets | AWS Secrets Manager / External Secrets Operator | |
| IaC | Terraform | |

---

## 6. 選定サマリ

```
クライアント : Swift (SPM) / Kotlin (AAR) — 依存ゼロ、ゴールデンベクタで同一性を担保
データプレーン: Go — config-edge / event-gateway / assignment-service
コントロール  : Go（experiment / metric / builder）+ Next.js（console）
解析         : Python + FastAPI（stats）、Flink or Go consumer（stream）
ストア       : PostgreSQL / Redis / Kafka / ClickHouse / S3
配信         : S3 + CDN（不変オブジェクト + ポインタ差し替え）
```

## 7. 意図的に採らなかったもの

| 不採用 | 理由 |
|---|---|
| GraphQL（SDK 対向） | CDN でキャッシュできない。コンフィグ配信は単一 GET が正解 |
| WebSocket / SSE でのコンフィグ push | モバイルで常時接続を維持するのはバッテリーと接続管理のコストが見合わない。次回起動反映で十分（[BK-0005](../roadmaps/BK-0005-session-sealed-config/BK-0005-session-sealed-config-ja.md)） |
| サーバサイド評価を主経路にする | [BK-0002](../roadmaps/BK-0002-local-evaluation/BK-0002-local-evaluation-ja.md) |
| Firebase Remote Config を配信層に流用 | 配信だけは楽になるが、レイヤー排他・スティッキー割当・曝露ログの整合が自前実装になり、結局二重管理になる |
| gRPC-Web / Connect（SDK 対向） | モバイルで HTTP/JSON 以上の利得が薄く、CDN 互換性を失う |
| exactly-once セマンティクス | at-least-once + `event_id` 冪等排除で十分。コストが見合わない |
