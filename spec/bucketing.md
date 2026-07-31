**English** · [日本語](bucketing-ja.md)

# Deterministic bucketing — normative specification

This document is **normative**. Every implementation — Swift, Kotlin, Go, Python, and TypeScript —
follows it exactly and verifies [golden-vectors.json](golden-vectors.json) in continuous
integration.

When determinism in assignment breaks, experiment results quietly become meaningless. The bug never
surfaces on its own, so tests are the only defense.

## 1. The algorithm

```
bucket(salt, unit_id):
    input  := UTF-8( salt + ":" + unit_id )
    digest := SHA-256(input)                    # 32 bytes
    n      := uint32_big_endian(digest[0..4])   # the leading 4 bytes
    return n mod 10000                          # 0..9999
```

### The reasoning behind each element

| Element | Choice | Reason |
|---|---|---|
| Hash function | SHA-256 | It exists in every language's standard library and **has no implementation variants**. MurmurHash3 has x86_32, x86_128, and x64_128 variants, and implementations interpret its seed differently. The performance difference of a few hundred nanoseconds is irrelevant for a function called a few dozen times at app startup |
| Separator | `:` | It fixes the boundary between `salt` and `unit_id` so that `("ab","c")` and `("a","bc")` cannot collide. **Neither `salt` nor `unit_id` may contain `:`** (§5) |
| Byte extraction | The leading 4 bytes, big-endian | "Leading" and "big-endian" are unambiguous in every language. Little-endian invites platform-dependent implementation mistakes |
| Bucket count | 10000 | It allows allocation in units of 0.01%, one basis point. Raising it to 100,000 or a million buys nothing in practice |
| Modulo | `mod 10000` | See §4 |

## 2. Variant assignment

```
assign(experiment, unit_id):
    b   := bucket(experiment.salt, unit_id)
    cum := 0
    for each variant in experiment.variants:     # ★ definition order, strictly
        cum += variant.weight_bp                 # basis points (out of 10000)
        if b < cum:
            return variant
    return UNASSIGNED
```

- `weight_bp` is an integer from 0 to 10000. **Floating point must not be used**, because rounding differences shift assignment between languages.
- Variants are walked in **the order they appear in the configuration**. An implementation must not sort by name or depend on a map's iteration order.
- When the weights sum to less than 10000, the remainder is unassigned and outside the experiment. That is how a partial rollout is expressed.

## 3. Two-stage assignment with layers

```
b_layer := bucket(layer.salt,      unit_id)   # the position within the layer
b_var   := bucket(experiment.salt, unit_id)   # the variant assignment
```

**The two salts must always differ.** With one salt, variants skew for an experiment placed at the
edge of a layer: an experiment on the layer range [0,1000) would only ever see `b_var` values of 0
to 999, putting every subject in the first variant.

The rule for composing a salt:

```
layer.salt      = "layer:" + layer_key + ":" + layer_seed
experiment.salt = "exp:"   + experiment_key + ":" + experiment_seed
```

Incrementing `seed` yields a new assignment statistically independent of the previous one — verified:
after a seed change, the share of subjects remaining in the same variant was 0.5009 against an
expected 0.5. Re-randomization is performed through that operation.

## 4. On modulo bias

Because `2^32 mod 10000 = 7296`, buckets 0 through 7295 are marginally more likely than buckets 7296
through 9999.

The relative bias is `7296 / 2^32 ≈ 1.7 × 10⁻⁶`.

**The bias can be ignored.** Assigning 100 million users skews the expectation by 0.17 of a user,
which cannot affect the test statistic of any experiment. Correcting it with rejection sampling
would only complicate the implementations and raise the risk of disagreement between languages.

Uniformity as measured — 200,000 synthetic UUIDs split into 100 groups, reproducible with
`tools/verify_vectors.py --distribution`:

```
χ²(df=99) = 88.68     (expected ≈ 99, the 5% critical value ≈ 123.2)
a 50/50 split: control 25,029 / treatment 24,971
```

## 5. Mandatory requirements on an implementation

| Requirement | Reason |
|---|---|
| Treat the input as **UTF-8** bytes, always | State it explicitly with Swift's `String.utf8` and Kotlin's `toByteArray(Charsets.UTF_8)`, rather than depending on the platform's default encoding |
| Never allow `:` in `salt` or `unit_id` | It removes any ambiguity about the boundary. Experiment keys are restricted to `[a-z0-9_]+`, and `unit_id` is validated when generated |
| Never normalize `unit_id` | Do not silently change case or trim whitespace. Assignment diverges when the server and the client normalize differently |
| Accept an empty `unit_id` | It must not crash. The golden vectors include this case |
| Accept a non-ASCII `unit_id` | The same. Handled consistently as UTF-8, it presents no problem |
| Overflow on 32-bit platforms | Treat the value as `uint32`. Reading it into a signed 32-bit integer produces a negative number, and the result of `mod` then varies by language — negative in the C family, positive in Python. **Always treat it as unsigned** |

The last requirement causes the most accidents. Java and Kotlin have no unsigned 32-bit integer, so
the result of `ByteBuffer.getInt()` must be converted with `.toLong() and 0xFFFFFFFFL`.

## 6. Reference implementations

### Kotlin

```kotlin
import java.security.MessageDigest

object Bucketing {
    const val TOTAL_BUCKETS = 10_000

    fun bucket(salt: String, unitId: String): Int {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest("$salt:$unitId".toByteArray(Charsets.UTF_8))
        // read the leading 4 bytes as a big-endian unsigned 32-bit integer
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

## 7. Conformance tests

Every implementation must reproduce every vector in [golden-vectors.json](golden-vectors.json).

- 24 `bucket_vectors` (3 salts × 8 unit identifiers, including an empty string, a non-ASCII string, and a 128-character identifier)
- 15 `assignment_vectors` (three allocations: 50/50, 33/33/34, and 90/10)

Each vector also carries `sha256_prefix_hex` and `uint32_be`, which **identifies the stage that
broke when a vector fails**. A matching hash with a mismatched bucket points at the modulo or the
sign handling; a mismatched hash points at the encoding or the separator.

The verification tool is [../tools/verify_vectors.py](../tools/verify_vectors.py).

Running it in continuous integration is mandatory, and a mismatch blocks the merge. The job lives in
[`.github/workflows/check.yml`](../.github/workflows/check.yml) and runs
[`tools/check.sh`](../tools/check.sh).
