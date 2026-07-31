/**
 * ロードマップ一覧の単一の情報源。
 *
 * title / status / topic / related は各 BK 項目の BK-METADATA ブロックが出典。
 * phase は各項目の「作業」節が明記しているものだけを引く。明記のない項目は
 * null のままにする（推測で埋めない）。
 *
 * 出典: roadmaps 配下の各 BK 項目（日本語版は -ja.md、英語版は .md）。
 */

export const ITEMS = [
  {
    id: 'BK-0001',
    dir: 'BK-0001-build-vs-buy',
    title: '自前構築か既製品か',
    status: 'accepted',
    topic: 'プラットフォーム戦略',
    phase: 'Phase 0',
    related: [],
  },
  {
    id: 'BK-0002',
    dir: 'BK-0002-local-evaluation',
    title: '割当をサーバではなく端末内で評価する',
    status: 'accepted',
    topic: 'コンフィグ配信',
    phase: 'Phase 1',
    note: 'assignment-service は Phase 2',
    related: ['BK-0005', 'BK-0008'],
  },
  {
    id: 'BK-0003',
    dir: 'BK-0003-native-sdks',
    title: 'ネイティブ 2 実装の SDK を、ゴールデンベクタで担保する',
    status: 'accepted',
    topic: 'クライアント SDK 設計',
    phase: 'Phase 1',
    related: ['BK-0007'],
  },
  {
    id: 'BK-0004',
    dir: 'BK-0004-bucketing-hash',
    title: '決定的バケッティングに SHA-256 を用いる',
    status: 'accepted',
    topic: '割当と決定性',
    phase: 'Phase 1',
    related: ['BK-0003'],
  },
  {
    id: 'BK-0005',
    dir: 'BK-0005-session-sealed-config',
    title: 'コンフィグをセッション内でシールし、更新は次回起動から適用する',
    status: 'accepted',
    topic: 'クライアント SDK 設計',
    phase: 'Phase 1',
    related: ['BK-0002'],
  },
  {
    id: 'BK-0006',
    dir: 'BK-0006-event-warehouse-selection',
    title: 'ClickHouse と既存データウェアハウスのどちらを採るか',
    status: 'proposed',
    topic: 'データ基盤',
    phase: 'Phase 0',
    note: 'Phase 0 のチェックリスト項目そのもの',
    related: ['BK-0001'],
  },
  {
    id: 'BK-0007',
    dir: 'BK-0007-revisit-kmp-shared-core',
    title: '共有 Kotlin Multiplatform コアの再評価',
    status: 'deferred',
    topic: 'クライアント SDK 設計',
    phase: null,
    note: '3 つの引き金のいずれかが引かれるまで着手しない',
    related: ['BK-0003'],
  },
  {
    id: 'BK-0008',
    dir: 'BK-0008-config-bundle-signing',
    title: 'コンフィグバンドルに Ed25519 署名を付ける',
    status: 'proposed',
    topic: 'コンフィグ配信',
    phase: null,
    related: ['BK-0002'],
  },
  {
    id: 'BK-0009',
    dir: 'BK-0009-flink-late-data',
    title: '遅延到着イベントの再処理に Flink を導入する',
    status: 'deferred',
    topic: 'データ基盤',
    phase: 'Phase 3',
    note: 'Phase 1 では単純なコンシューマを出荷する',
    related: ['BK-0006'],
  },
];

/** 状態は色だけで伝えない。必ずアイコンとラベルの組で出す。 */
export const STATUS = {
  accepted: { label: '可決', icon: 'check' },
  proposed: { label: '提案', icon: 'open' },
  deferred: { label: '提案（保留）', icon: 'pause' },
};

/** 一覧の並び順。BK-METADATA の状態表記に対応する。 */
export const STATUS_ORDER = ['accepted', 'proposed', 'deferred'];

export const DOCS = [
  { file: 'docs/09-roadmap-ja.md', title: '09. ロードマップ', desc: '段階的構築計画（Phase 0〜4）' },
  { file: 'roadmaps/README-ja.md', title: 'BK 項目の書式', desc: '追加手順と正規形' },
  { file: 'docs/01-requirements-ja.md', title: '01. 要求仕様', desc: 'モバイル固有の制約が起点' },
  { file: 'docs/02-architecture-ja.md', title: '02. アーキテクチャ', desc: '3 平面の分割とシーケンス' },
  { file: 'docs/03-tech-selection-ja.md', title: '03. 技術選定', desc: '比較表と採用理由' },
  { file: 'docs/04-client-sdk-ja.md', title: '04. クライアント SDK', desc: 'API と評価モデル' },
  { file: 'docs/05-services-ja.md', title: '05. サービス', desc: '責務・API・データモデル' },
  { file: 'docs/06-data-pipeline-ja.md', title: '06. データパイプライン', desc: '遅延到着データと時刻補正' },
  { file: 'docs/07-statistics-ja.md', title: '07. 統計設計', desc: 'SRM、CUPED、逐次検定' },
  { file: 'docs/08-operations-ja.md', title: '08. 運用', desc: 'SLO、リリース、ロールバック' },
  { file: 'spec/bucketing-ja.md', title: 'spec: バケッティング', desc: '決定的割当の規範仕様' },
  { file: 'spec/golden-vectors.json', title: 'spec: ゴールデンベクタ', desc: '全 SDK が再現すべき値' },
];

export const REPO_URL = 'https://github.com/0x0c/bakuchi';
export const BLOB_BASE = `${REPO_URL}/blob/main/`;
