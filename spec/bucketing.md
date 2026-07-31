# 決定的バケッティング — 規範仕様

このドキュメントは**規範（normative）** である。Swift / Kotlin / Go / Python / TypeScript のすべての実装はここに完全に従い、[golden-vectors.json](golden-vectors.json) を CI で検証すること。

割当の決定性が壊れると、実験結果が静かに無意味になる。バグが表に出ないので、テストで守るしかない。

## 1. アルゴリズム

```
bucket(salt, unit_id):
    input  := UTF-8( salt + ":" + unit_id )
    digest := SHA-256(input)                    # 32 bytes
    n      := uint32_big_endian(digest[0..4])   # 先頭 4 バイト
    return n mod 10000                          # 0..9999
```

### 各要素の根拠

| 要素 | 選択 | 理由 |
|---|---|---|
| ハッシュ関数 | SHA-256 | すべての言語の標準ライブラリに存在し、**実装のバリエーションがない**。MurmurHash3 は x86_32 / x86_128 / x64_128 の亜種があり、シード解釈も実装ごとに揺れる。性能差（数百 ns）はアプリ起動時に数十回呼ぶだけの用途では無関係 |
| 区切り文字 | `:` | `salt` と `unit_id` の境界を固定し、`("ab","c")` と `("a","bc")` が衝突しないようにする。**`salt` と `unit_id` に `:` を含めてはならない**（§5） |
| バイト取り出し | 先頭 4 バイト、ビッグエンディアン | 「先頭」「ビッグエンディアン」はどの言語でも曖昧さがない。リトルエンディアンだと環境依存の実装ミスを誘発する |
| バケット数 | 10000 | 0.01%（1 basis point）単位の配分ができる。10 万や 100 万にしても実務上の利得がない |
| 剰余 | `mod 10000` | §4 参照 |

## 2. バリアント割当

```
assign(experiment, unit_id):
    b   := bucket(experiment.salt, unit_id)
    cum := 0
    for each variant in experiment.variants:     # ★ 定義順を厳守
        cum += variant.weight_bp                 # basis points (out of 10000)
        if b < cum:
            return variant
    return UNASSIGNED
```

- `weight_bp` は 0..10000 の整数。**浮動小数点を使ってはならない**（丸め差で言語間の割当がずれる）。
- バリアントの走査順は**コンフィグ内の定義順**。実装が名前でソートしたりマップの反復順に依存してはならない。
- 合計が 10000 未満の場合、残りは未割当（実験対象外）。これは部分ロールアウトの表現に使う。

## 3. レイヤーとの二段階割当

```
b_layer := bucket(layer.salt,      unit_id)   # レイヤー内での位置
b_var   := bucket(experiment.salt, unit_id)   # バリアント割当
```

**2 つの salt は必ず異なる値にする。** 同一 salt を使うと、レイヤー範囲の端に配置された実験でバリアントが偏る（レイヤー範囲 [0,1000) の実験なら b_var も 0..999 にしかならず、最初のバリアントに全員入る）。

salt の構成規則:

```
layer.salt      = "layer:" + layer_key + ":" + layer_seed
experiment.salt = "exp:"   + experiment_key + ":" + experiment_seed
```

`seed` をインクリメントすると、過去の割当と統計的に独立な新しい割当が得られる（検証済み: seed 変更後も同一バリアントに残る割合は 0.5009、期待値 0.5）。再ランダム化はこの操作で行う。

## 4. 剰余バイアスについて

`2^32 mod 10000 = 7296` であるため、バケット 0..7295 はバケット 7296..9999 よりわずかに選ばれやすい。

相対的な偏りは `7296 / 2^32 ≈ 1.7 × 10⁻⁶`。

**この偏りは無視してよい。** 1 億ユーザを割り当てても偏りは期待値で 0.17 人分にしかならず、いかなる実験の検定統計量にも影響しない。棄却サンプリングによる補正は、実装を複雑にして言語間の不一致リスクを上げるだけで割に合わない。

実測での一様性検証（20 万件の合成 UUID を 100 群に分割。`tools/verify_vectors.py --distribution` で再現可能）:

```
χ²(df=99) = 88.68     （期待値 ≈ 99、5% 棄却限界 ≈ 123.2）
50/50 分割: control 25,029 / treatment 24,971
```

## 5. 実装上の必須要件

| 要件 | 理由 |
|---|---|
| 入力は必ず **UTF-8** バイト列として扱う | Swift の `String.utf8`、Kotlin の `toByteArray(Charsets.UTF_8)` を明示する。プラットフォーム既定エンコーディングに依存しない |
| `salt` / `unit_id` に `:` を含めない | 境界の曖昧性を排除する。実験キーは `[a-z0-9_]+` に制限し、`unit_id` は生成時に検証する |
| `unit_id` の正規化をしない | 大文字小文字変換・トリムなどを勝手に行わない。サーバとクライアントで正規化が食い違うと割当がずれる |
| 空文字列の `unit_id` を許容する | クラッシュしてはならない。ゴールデンベクタに含まれている |
| 非 ASCII の `unit_id` を許容する | 同上。UTF-8 として一貫して扱えば問題ない |
| 32 ビット環境でのオーバーフロー | `uint32` として扱う。符号付き 32 ビット整数に読むと負値になり `mod` の結果が言語ごとに変わる（C 系は負、Python は正）。**必ず符号なしで扱う** |

最後の項目が最も事故りやすい。Java / Kotlin には符号なし 32 ビット整数がないため、`ByteBuffer.getInt()` の結果を `.toLong() and 0xFFFFFFFFL` で符号なしに変換する必要がある。

## 6. 参照実装

### Kotlin

```kotlin
import java.security.MessageDigest

object Bucketing {
    const val TOTAL_BUCKETS = 10_000

    fun bucket(salt: String, unitId: String): Int {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest("$salt:$unitId".toByteArray(Charsets.UTF_8))
        // 先頭 4 バイトをビッグエンディアンの符号なし 32bit として読む
        val n = ((digest[0].toLong() and 0xFF) shl 24) or
                ((digest[1].toLong() and 0xFF) shl 16) or
                ((digest[2].toLong() and 0xFF) shl 8)  or
                 (digest[3].toLong() and 0xFF)
        return (n % TOTAL_BUCKETS).toInt()
    }
}
```

### Swift

```swift
import CryptoKit

enum Bucketing {
    static let totalBuckets: UInt32 = 10_000

    static func bucket(salt: String, unitID: String) -> Int {
        let digest = SHA256.hash(data: Data("\(salt):\(unitID)".utf8))
        let bytes = Array(digest.prefix(4))
        let n = (UInt32(bytes[0]) << 24) | (UInt32(bytes[1]) << 16)
              | (UInt32(bytes[2]) << 8)  |  UInt32(bytes[3])
        return Int(n % totalBuckets)
    }
}
```

### Go

```go
func Bucket(salt, unitID string) int {
    h := sha256.Sum256([]byte(salt + ":" + unitID))
    return int(binary.BigEndian.Uint32(h[:4]) % 10000)
}
```

### Python

```python
import hashlib, struct

TOTAL_BUCKETS = 10_000

def bucket(salt: str, unit_id: str) -> int:
    digest = hashlib.sha256(f"{salt}:{unit_id}".encode("utf-8")).digest()
    return struct.unpack(">I", digest[:4])[0] % TOTAL_BUCKETS
```

## 7. 適合性テスト

すべての実装は [golden-vectors.json](golden-vectors.json) の全ベクタを再現しなければならない。

- 24 個の `bucket_vectors`（3 salt × 8 unit_id。空文字列・非 ASCII・128 文字の長い ID を含む）
- 15 個の `assignment_vectors`（50/50、33/33/34、90/10 の 3 配分）

各ベクタは `sha256_prefix_hex` と `uint32_be` も持っているので、**不一致時にどの段階で壊れているかが特定できる**。ハッシュが合っているのにバケットが合わなければ剰余か符号の扱い、ハッシュが合わなければエンコーディングか区切り文字。

検証ツール: [../tools/verify_vectors.py](../tools/verify_vectors.py)

CI での実行は必須とし、不一致の場合はマージをブロックする。実体は [`.github/workflows/check.yml`](../.github/workflows/check.yml) で、[`tools/check.sh`](../tools/check.sh) を走らせている。
