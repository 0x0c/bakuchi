**English** · [日本語](README-ja.md)

# bakuchi — an A/B testing platform designed for iOS and Android

bakuchi is the technology selection and design for an experimentation platform that treats mobile as
a first-class citizen. The design covers the whole path end to end: delivering feature flags,
assigning subjects to variants, collecting events, and analyzing the result statistically.

## The roadmap page

**https://0x0c.github.io/bakuchi/** (Japanese: https://0x0c.github.io/bakuchi/ja/)

Every BK item on one board. Three ways to read it — cards, a table, and a map of how the items
relate — with filters by status and topic, and a search over ID, title, topic, and status.

**The page is generated from [roadmaps/](roadmaps/).** Titles, statuses, topics, relations, and the
progress checkboxes are all read from the item files themselves. Nothing is copied by hand, so the
page cannot drift from the roadmap it describes. The output is not tracked in git (`site/` is in
`.gitignore`); [tools/build_roadmap_site.py](tools/build_roadmap_site.py) rebuilds it on every
deploy.

```sh
python3 tools/build_roadmap_site.py     # write site/
python3 -m http.server --directory site # read it
```

[tools/check.sh](tools/check.sh) runs the generator and throws the output away. An unknown Status,
or a progress section whose item count differs between the two languages, fails at that gate rather
than at deploy time.

A push to `main` builds and deploys through GitHub Actions
([.github/workflows/pages.yml](.github/workflows/pages.yml)). Once, before the first deploy, set
Settings → Pages → Build and deployment → Source to **GitHub Actions**. `GITHUB_TOKEN` cannot create
the Pages site itself, so that one step is done by a person.

One setting must be made by hand the first time: repository settings → Pages → Build and
deployment → Source must be set to **GitHub Actions**. A workflow cannot automate that one step,
because `GITHUB_TOKEN` cannot create the Pages site itself.

## The documents

| Document | Contents |
|---|---|
| [docs/01-requirements.md](docs/01-requirements.md) | The requirements. The **mobile-specific constraints** — app release cycles, offline operation, late-arriving events — start here |
| [docs/02-architecture.md](docs/02-architecture.md) | The overall architecture, the service split, and the sequences |
| [docs/03-tech-selection.md](docs/03-tech-selection.md) | Technology selection, the comparisons, and the reasoning behind each choice |
| [docs/04-client-sdk.md](docs/04-client-sdk.md) | The iOS and Android SDK design: the API, the evaluation model, and the lifecycle |
| [docs/05-services.md](docs/05-services.md) | Each microservice's responsibility, API, and data model |
| [docs/06-data-pipeline.md](docs/06-data-pipeline.md) | The event pipeline, late-arriving data, and clock correction |
| [docs/07-statistics.md](docs/07-statistics.md) | The statistical design: sample ratio mismatch, CUPED, sequential testing, and multiple comparisons |
| [docs/08-operations.md](docs/08-operations.md) | Service level objectives, releases, rollback, and privacy |
| [docs/09-roadmap.md](docs/09-roadmap.md) | The phased build plan |

Every document exists in English and Japanese. The English file carries the plain name and the
Japanese file the `-ja` suffix, so [docs/01-requirements.md](docs/01-requirements.md) and
[docs/01-requirements-ja.md](docs/01-requirements-ja.md) are the same document in two languages.
Neither is a summary of the other.

## The roadmap as a record of decisions

Each major design decision, and each question still open, lives in [roadmaps/](roadmaps/) as a
numbered **BK item** written in both languages. The format and the procedure for adding an item are
in [roadmaps/README.md](roadmaps/README.md).

| ID | Item | Status |
|---|---|---|
| [BK-0001](roadmaps/BK-0001-build-vs-buy/BK-0001-build-vs-buy.md) | Build or buy the experimentation platform | Accepted |
| [BK-0002](roadmaps/BK-0002-local-evaluation/BK-0002-local-evaluation.md) | Evaluate assignment on the device rather than on the server | Accepted |
| [BK-0003](roadmaps/BK-0003-native-sdks/BK-0003-native-sdks.md) | Two native SDK implementations, held together by golden vectors | Accepted |
| [BK-0004](roadmaps/BK-0004-bucketing-hash/BK-0004-bucketing-hash.md) | Use SHA-256 for deterministic bucketing | Accepted |
| [BK-0005](roadmaps/BK-0005-session-sealed-config/BK-0005-session-sealed-config.md) | Seal the configuration for the whole session | Accepted |
| [BK-0006](roadmaps/BK-0006-event-warehouse-selection/BK-0006-event-warehouse-selection.md) | ClickHouse or an existing data warehouse | Proposal |
| [BK-0007](roadmaps/BK-0007-revisit-kmp-shared-core/BK-0007-revisit-kmp-shared-core.md) | Revisit a shared Kotlin Multiplatform core | Proposal (deferred) |
| [BK-0008](roadmaps/BK-0008-config-bundle-signing/BK-0008-config-bundle-signing.md) | Sign the configuration bundle with Ed25519 | Proposal |
| [BK-0009](roadmaps/BK-0009-flink-late-data/BK-0009-flink-late-data.md) | Adopt Flink to reprocess late-arriving events | Proposal (deferred) |

The same list can be queried with `python3 tools/roadmap_query.py --status "Proposal"`.

## The specifications an implementation must satisfy

| File | Contents |
|---|---|
| [spec/bucketing.md](spec/bucketing.md) | The normative specification of the deterministic bucketing algorithm |
| [spec/golden-vectors.json](spec/golden-vectors.json) | The golden vectors every SDK must reproduce |
| [spec/config-bundle.schema.json](spec/config-bundle.schema.json) | The JSON Schema for the delivered configuration |
| [spec/event.schema.json](spec/event.schema.json) | The event schema |
| [tools/verify_vectors.py](tools/verify_vectors.py) | The golden-vector conformance checker |

## Tools and agents

```bash
./tools/check.sh          # the deterministic gates: vectors, roadmap format, JSON, textlint
```

| File | Contents |
|---|---|
| [tools/check.sh](tools/check.sh) | Runs every gate in one command |
| [tools/check_roadmap_format.py](tools/check_roadmap_format.py) | The canonical-form checker for roadmap items |
| [tools/new_roadmap_item.py](tools/new_roadmap_item.py) | Scaffolds an item and allocates its number |
| [tools/roadmap_query.py](tools/roadmap_query.py) | Filters the roadmap by `Status` |
| [.agent-workflows/](.agent-workflows/) | Workflows for agents: the prose norm, proposing, implementing, and following up on review |
| [.claude/skills/](.claude/skills/) | The Claude Code adapters for those workflows |

The workflows and the prose norm are borrowed from
[Bajutsu](https://github.com/bajutsu-e2e/bajutsu) under the Apache License 2.0 and adapted for
bakuchi. The attribution is in [.agent-workflows/NOTICE](.agent-workflows/NOTICE).

## The design in three lines

1. **Local evaluation.** The device never asks a server which variant a user gets. The whole
   configuration is delivered, and the device decides — which means no network latency, offline
   operation, and unchanged behavior during an outage.
2. **Session-sealed configuration.** The assignment fixed at startup does not change for the rest of
   the session, which structurally rules out a user interface that shifts from screen to screen.
3. **One place where determinism lives.** An assignment depends on `SHA-256(salt + ":" + unit_id)`
   and nothing else, and every implementation — Swift, Kotlin, Go, and Python — is verified in
   continuous integration against the same golden vectors.

## Assumptions and scope

- The design targets 1 to 10 million monthly active users, 50 to 200 concurrent experiments, and
  event volume up to roughly a billion events per day on a single deployment.
- Below that scale, building this platform does not pay for itself.
  [BK-0001](roadmaps/BK-0001-build-vs-buy/BK-0001-build-vs-buy.md) records the criteria for that
  judgment and recommends the software-as-a-service and open-source products to adopt instead.
- This repository holds design documents and no implementation. Building starts at Phase 1 of
  [docs/09-roadmap.md](docs/09-roadmap.md).
