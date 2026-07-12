# Critical data copy checkpoint — 2026-07-11

> Sanitized checkpoint. No private values, file contents, local hashes, or credentials are reproduced here.

## Authorization and scope

The user explicitly authorized execution of the `critical` migration profile only.

Excluded from this operation:

- `archive` profile;
- `cache` profile;
- source deletion or move;
- Git tracked-file cleanup;
- merge or monorepo import;
- deploy or Shopify mutation;
- history rewrite;
- `CURRENT_APP_STATE.md` write;
- GPT knowledge ZIP generation.

## Tool and source gates

- Safety tool checkout advanced to branch checkpoint `e7487591088f7eda269f931498bac927e6294cf4`.
- The validated safety implementation ancestor gate passed for `a6dc723fc60da7959ba110a2a614c5ff0b1566bc`.
- Canonical source checkout remained at the approved source head `69a796274de9b9fdee2418707d8dc356b7732e07`.
- The exact critical manifest was compared with the accepted final dry-run before copy.

## Copy result

- profile: `critical`;
- dry-run: **false**;
- items: **177**;
- copied: **177**;
- verified existing: **0**;
- blocked: **false**;
- errors: **0**;
- duplicate sources: **0**;
- duplicate destinations: **0**;
- source/destination SHA-256 mismatches: **0**;
- missing destination hashes: **0**;
- invalid statuses: **0**;
- sources deleted: **0**.

Classification split:

- private: **112**;
- runtime: **61**;
- secret: **4**.

Destination bucket split:

- data: **159**;
- config: **18**.

Every item finished with status `copied` and an equal source/destination SHA-256 value. The operation was copy-only and source-preserving.

## Gate decision

The approved critical copy is **COMPLETE AND HASH-VERIFIED**.

Stage 1E may now proceed to implementation of external runtime paths, legacy-read compatibility, safe examples/defaults, `.gitignore` alignment, and a separately reviewed tracked-file cleanup patch.

Still forbidden without separate approval:

- copying `archive`;
- copying `cache`;
- removing or moving source files;
- removing files from Git tracking;
- merging PR #4;
- importing into the canonical monorepo;
- deploying or mutating Shopify;
- rewriting history;
- writing `CURRENT_APP_STATE.md`;
- generating the GPT knowledge ZIP.
