/**
 * ロードマップの単一の情報源。
 * 出典: docs/09-roadmap-ja.md — 内容を変えるときは両方を同時に更新する。
 *
 * weeks: ガントの座標（週）。
 *   minStart / minEnd = 最短シナリオ、maxStart / maxEnd = 最長シナリオ。
 *   open: true は「継続」（終端を持たない）、tentative: true は「候補」（要否未定）。
 */

export const AXIS_END = 24; // 週。これ以降は「継続」帯として扱う
export const AXIS_TICKS = [0, 4, 8, 12, 16, 20, 24];

export const PHASES = [
  {
    id: 0,
    label: 'Phase 0',
    title: '検証',
    duration: '2 週間',
    weeks: { minStart: 0, minEnd: 2, maxStart: 0, maxEnd: 2 },
    goal: '作る前に確かめる。',
    lead: '作る前に確かめる。',
    items: [
      {
        area: 'チェックリスト',
        rows: [
          'ADR-0001 の判断基準に照らし、本当に自前構築すべきか結論を出す',
          '既存の DWH（BigQuery / Snowflake）の有無を確認 → あれば ClickHouse を採用しない',
          '想定イベント量とコストの試算',
          'iOS / Android チームに SDK のサイズ・起動時間予算を提示して合意を取る',
          'バケッティングアルゴリズムを spec/ の通りに実装し、ゴールデンベクタで 4 言語一致を確認',
        ],
      },
    ],
    layout: 'checklist',
    callout: {
      kind: 'note',
      text: 'Phase 0 の成果物が「作らない」という結論でも、それは成功。',
    },
  },
  {
    id: 1,
    label: 'Phase 1',
    title: 'フィーチャーフラグ配信',
    duration: '6〜8 週間',
    weeks: { minStart: 2, minEnd: 8, maxStart: 2, maxEnd: 10 },
    goal: '実験ではなく、安全なフラグ配信を先に確立する。',
    lead: '統計より先に、配信の信頼性を作る。',
    layout: 'table',
    items: [
      {
        area: 'SDK',
        detail:
          'iOS / Android。同期評価、ローカルキャッシュ、バンドルデフォルト、曝露イベント、デバッグメニュー',
      },
      { area: '配信', detail: 'config-edge + S3 + CDN。不変オブジェクト + ポインタ差し替え' },
      {
        area: '制御',
        detail:
          'experiment-service / metric-service / config-builder / console を単一デプロイ単位で',
      },
      {
        area: 'イベント',
        detail:
          'event-gateway → Kafka → Go の単純コンシューマ → ClickHouse（Flink はまだ入れない）',
      },
      { area: '解析', detail: '既存の BI / DWH で手動集計。専用の stats-service はまだ作らない' },
    ],
    canDo: '段階的ロールアウト、キルスイッチ、A/B の割当と曝露記録。結果の判定は手動 SQL。',
    wontDo: '統計エンジン、レイヤー排他（1 レイヤーのみ）、スティッキー割当、サーバ側実験。',
    done: '本番で 1 つの実験を最後まで回し、手動で結論を出せた。',
  },
  {
    id: 2,
    label: 'Phase 2',
    title: '実験プラットフォーム化',
    duration: '8〜10 週間',
    weeks: { minStart: 8, minEnd: 16, maxStart: 10, maxEnd: 20 },
    goal: '統計判定を自動化し、PM が自力で実験を回せるようにする。',
    layout: 'table',
    items: [
      { area: '統計', detail: 'stats-service。Welch t 検定、比率、デルタ法、信頼区間' },
      { area: '診断', detail: 'SRM 検定を結果表示のハードゲートに、事前 A/A チェック' },
      { area: '設計支援', detail: 'サンプルサイズ計算、所要日数の事前提示' },
      { area: '排他', detail: 'レイヤーによる相互排他（DB の EXCLUDE 制約）' },
      {
        area: '安全装置',
        detail: 'guardrail-watcher による自動停止。リテンションを全実験の必須ガードレールに',
      },
      { area: '品質', detail: '常時 A/A 実験 2 本。データ品質モニタリング' },
      { area: 'サーバ側', detail: 'assignment-service + abkit-go 埋め込みライブラリ' },
    ],
    done:
      'PM がエンジニアの手を借りずに実験を作成・開始・判定できる。A/A の偽陽性率が名目水準に収まっている。',
  },
  {
    id: 3,
    label: 'Phase 3',
    title: '精度と規模',
    duration: '継続',
    weeks: { minStart: 16, minEnd: AXIS_END, maxStart: 20, maxEnd: AXIS_END, open: true },
    goal: '実験のスループットと検出力を上げる。',
    layout: 'table',
    items: [
      { area: '分散削減', detail: 'CUPED。既存ユーザセグメントに適用' },
      { area: '逐次検定', detail: 'mSPRT による always-valid CI。ダッシュボードの既定表示に' },
      { area: '多重比較', detail: 'Benjamini-Hochberg、Dunnett' },
      { area: '遅延データ', detail: 'Flink 導入。ウォーターマークベースの再計算' },
      { area: '分位点', detail: 't-digest によるレイテンシメトリクス' },
      { area: '高度な解析', detail: '新奇性効果検出、異質処理効果（HTE）、クラスタランダム化' },
      { area: '運用', detail: 'フラグ棚卸しの自動化、静的解析による未使用フラグ検出' },
      { area: 'ホールドバック', detail: '全実験からの恒常的除外群による累積効果測定' },
    ],
  },
  {
    id: 4,
    label: 'Phase 4 以降',
    title: '候補',
    duration: '要否は Phase 3 の実績で判断',
    weeks: { minStart: 20, minEnd: AXIS_END, maxStart: 20, maxEnd: AXIS_END, tentative: true },
    goal: '要否は Phase 3 の実績で判断する。確定した計画ではない。',
    layout: 'list',
    items: [
      {
        text: '多腕バンディット（探索と活用の自動最適化）',
        note:
          '実験文化が成熟する前に入れると、なぜ勝ったか分からない意思決定が増えるため優先度は低い',
      },
      { text: 'パーソナライゼーション（セグメント別に最適バリアントを自動選択）' },
      { text: '因果推論の拡張（観察データからの効果推定、切替回帰デザイン）' },
      { text: '実験結果のメタ分析（過去実験の効果量分布から事前分布を構築）' },
    ],
  },
];

/** 領域ごとに「どのフェーズで何が入るか」。空欄はそのフェーズで触らない領域。 */
export const CAPABILITIES = [
  {
    area: '意思決定',
    cells: { 0: 'build vs buy の結論、コスト試算' },
  },
  {
    area: 'クライアント SDK',
    cells: {
      0: 'ゴールデンベクタで 4 言語一致',
      1: 'iOS / Android。同期評価・ローカルキャッシュ',
    },
  },
  { area: 'コンフィグ配信', cells: { 1: 'config-edge + S3 + CDN' } },
  {
    area: 'コントロールプレーン',
    cells: { 1: 'experiment / metric / config-builder / console' },
  },
  {
    area: 'イベント基盤',
    cells: {
      1: 'Kafka → Go コンシューマ → ClickHouse',
      3: 'Flink。ウォーターマーク再計算',
    },
  },
  {
    area: '統計判定',
    cells: {
      1: '既存 BI / DWH で手動集計',
      2: 'stats-service。Welch t 検定・デルタ法',
      3: 'mSPRT、Benjamini-Hochberg、Dunnett',
    },
  },
  { area: '実験診断', cells: { 2: 'SRM ハードゲート、事前 A/A' } },
  { area: '排他制御', cells: { 2: 'レイヤー相互排他（EXCLUDE 制約）' } },
  { area: '自動安全装置', cells: { 2: 'guardrail-watcher による自動停止' } },
  { area: 'サーバ側実験', cells: { 2: 'assignment-service + abkit-go' } },
  { area: '分散削減・高度な解析', cells: { 3: 'CUPED、HTE、ホールドバック' } },
  { area: 'フラグ運用', cells: { 3: '棚卸し自動化、未使用フラグの静的解析' } },
];

export const RISKS = [
  {
    risk: 'SDK が iOS / Android チームに採用されない',
    mitigation:
      'Phase 0 でサイズ・起動時間の予算を合意。SDK 開発に両チームのメンバーを入れる',
    phase: 0,
  },
  {
    risk: '統計を誰も理解せず結果が誤読される',
    mitigation:
      'Phase 2 で SRM ハードゲートと「有意差なし ≠ 差がない」の明示を実装に組み込む。ドキュメントに頼らない',
    phase: 2,
  },
  {
    risk: 'Phase 1 で作り込みすぎる',
    mitigation: '「統計エンジンを作らない」を明示的な制約として守る',
    phase: 1,
  },
  {
    risk: 'ClickHouse の運用負荷',
    mitigation: '既存 DWH があるならそれを使う。Phase 0 で判断する',
    phase: 0,
  },
  {
    risk: '実験が回らず基盤が塩漬けになる',
    mitigation:
      'Phase 1 完了条件を「実験を 1 本完走」にしてある。技術的完成ではなく利用を完了条件にする',
    phase: 1,
  },
];

export const DOCS = [
  { file: 'docs/01-requirements-ja.md', title: '01. 要求仕様', desc: 'モバイル固有の制約が起点' },
  { file: 'docs/02-architecture-ja.md', title: '02. アーキテクチャ', desc: '3 平面の分割とシーケンス' },
  { file: 'docs/03-tech-selection-ja.md', title: '03. 技術選定', desc: '比較表と採用理由' },
  { file: 'docs/04-client-sdk-ja.md', title: '04. クライアント SDK', desc: 'iOS / Android の API と評価モデル' },
  { file: 'docs/05-services-ja.md', title: '05. サービス', desc: '責務・API・データモデル' },
  { file: 'docs/06-data-pipeline-ja.md', title: '06. データパイプライン', desc: '遅延到着データと時刻補正' },
  { file: 'docs/07-statistics-ja.md', title: '07. 統計設計', desc: 'SRM、CUPED、逐次検定、多重比較' },
  { file: 'docs/08-operations-ja.md', title: '08. 運用', desc: 'SLO、リリース、ロールバック' },
  { file: 'docs/09-roadmap-ja.md', title: '09. ロードマップ', desc: 'このページの出典' },
  { file: 'docs/adr/', title: 'ADR', desc: '主要な意思決定記録' },
  { file: 'spec/bucketing-ja.md', title: 'spec: バケッティング', desc: '決定的割当の規範仕様' },
  { file: 'spec/golden-vectors.json', title: 'spec: ゴールデンベクタ', desc: '全 SDK が再現すべき値' },
];

export const REPO_URL = 'https://github.com/0x0c/bakuchi';
export const BLOB_BASE = `${REPO_URL}/blob/main/`;
