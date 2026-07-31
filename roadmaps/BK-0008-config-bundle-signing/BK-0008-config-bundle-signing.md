**English** · [日本語](BK-0008-config-bundle-signing-ja.md)

# BK-0008 — Sign the configuration bundle with Ed25519

<!-- BK-METADATA -->
| Field | Value |
|---|---|
| Proposal | [BK-0008](BK-0008-config-bundle-signing.md) |
| Author | [@0x0c](https://github.com/0x0c) |
| Status | **Proposal** |
| Tracking issue | [Search](https://github.com/0x0c/bakuchi/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+%22BK-0008%22) |
| Topic | Config delivery |
| Related | [BK-0002](../BK-0002-local-evaluation/BK-0002-local-evaluation.md) |
<!-- /BK-METADATA -->

## Introduction

The configuration bundle is delivered over HTTPS through a content delivery network. The client SDK
design in [`docs/04-client-sdk.md`](../../docs/04-client-sdk.md) records signature verification as
"optional but recommended", which is not a decision. This item proposes making it mandatory: the
build service signs every bundle with Ed25519, and the SDK verifies the signature against a public
key compiled into the app.

## Motivation

Under [BK-0002](../BK-0002-local-evaluation/BK-0002-local-evaluation.md) the bundle does not merely
describe an experiment — **it decides what code the app runs.** A tampered bundle can enable a
feature that was never released, disable a safety check, or route users into a variant that the
platform never published. The blast radius of a forged bundle is the blast radius of a bad release,
without the release.

Transport security alone does not close that gap in practice. Corporate mobile device management
routinely installs a root certificate and inspects TLS traffic, so a middlebox that can rewrite
responses exists on real user devices, placed there legitimately. A signature verified against a
key in the binary is checked end to end, by the party that has to trust the result, which is why it
holds where transport security does not.

The cost is small and one-sided. Ed25519 verification takes well under a millisecond, the signature
adds 64 bytes, and both platforms provide the primitive in their standard cryptography framework —
so the no-dependency constraint from
[BK-0003](../BK-0003-native-sdks/BK-0003-native-sdks.md) is not strained.

## Detailed design

### Signing

`config-builder` signs each bundle after compiling it. The signature covers the canonical
serialization of the bundle with the `signature` field removed, so that verification is
well-defined regardless of key ordering or whitespace. The signature travels in the bundle's
`signature` field, base64-encoded, as
[`spec/config-bundle.schema.json`](../../spec/config-bundle.schema.json) already reserves.

The private key lives in the secrets manager and is reachable only by `config-builder`. No human
holds it, and no other service can sign.

### Verification

The SDK verifies before a bundle is accepted, and the check sits alongside the existing validation
steps: schema conformance, and the requirement that `config_version` be newer than the one held.
A bundle that fails verification is discarded and the previous configuration is kept, which is the
same path already taken for a corrupt or truncated bundle. Verification failure is therefore not a
new failure mode; it reuses one that
[BK-0005](../BK-0005-session-sealed-config/BK-0005-session-sealed-config.md) already requires the
SDK to handle.

The SDK reports a verification failure as a health metric. A rise in that metric across many
devices is a signal worth paging on, since it means either a signing defect or an actual attempt at
tampering.

### Key rotation

**The app embeds two public keys,** and a bundle verifies when it matches either. Rotating a key is
then possible without stranding old app versions: publish an app version carrying both the current
and the next key, wait for adoption, then switch signing to the next key.

Rotation is what makes the scheme survivable. Without two slots, a compromised key would require an
app release before any new configuration could be delivered — during which the kill switch, the
platform's only emergency stop, would be unusable. Designing the rotation path now is what keeps
that scenario from being unrecoverable.

## Alternatives considered

- **Rely on HTTPS alone.** The status quo, and rejected because TLS inspection by device management
  is a real configuration on real devices, so a rewriting middlebox is a realistic position rather
  than a hypothetical one.
- **Certificate pinning instead of signing.** Rejected because pinning protects the transport rather
  than the artifact: it does not detect a bundle that was altered before it reached the content
  delivery network, and it breaks legitimately when certificates are rotated.
- **A message authentication code with a shared secret.** Rejected because the secret would have to
  ship inside the app, where anyone can extract it and forge a bundle. Asymmetric signing is what
  makes a client-side check meaningful.
- **Sign only in release builds.** Rejected because a check that does not run in development is a
  check that has not been tested when it matters. The staging environment signs with its own key.

## Progress

- [ ] Ed25519 signing in `config-builder`, with the key held in the secrets manager.
- [ ] Verification in both SDKs, with two embedded public-key slots.
- [ ] Verification-failure health metric, and an alert on a cross-device rise.
- [ ] A documented rotation runbook, exercised once before the scheme is relied upon.

## References

- [`docs/04-client-sdk.md`](../../docs/04-client-sdk.md) — configuration fetching and validation,
  where verification is listed as optional today.
- [`spec/config-bundle.schema.json`](../../spec/config-bundle.schema.json) — the `signature` field
  this item fills in.
- [`docs/08-operations.md`](../../docs/08-operations.md) — the security posture, where tampering is
  listed as a threat.
- [BK-0002](../BK-0002-local-evaluation/BK-0002-local-evaluation.md) — why the bundle decides app
  behavior at all.
