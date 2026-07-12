# Local repository-safety validation — 2026-07-11

Repository package: `eagleblastmusic-lgtm/gicleeapp`

Branch: `gpt-work/repo-safety-foundation`

Validated tool checkout: detached worktree at `1d4e2fff9d53630d4d41baf11c0ba6e8b6be6413`

Canonical scan root: `C:\Strona\pusty\cursor-api`

Staging root: `C:\Strona\_gicleeapp_staging`

## Safety result

**FIRST LOCAL DRY-RUN COMPLETE / NO MUTATION PERFORMED / SUPERSEDED BY POLICY UPDATE**

The runbook completed through tests, compilation, tracked-tree audit, migration discovery and allowlist snapshot planning.

No data was copied, moved, overwritten or deleted. No Git mutation, merge, push or Shopify deploy was performed.

The reports exposed policy gaps that have since been fixed on the branch. Therefore these figures remain historical evidence of the first dry-run, not the final migration manifest.

## Automated validation

- focused repository-safety tests: **53 PASS**;
- compileall: **PASS**;
- tracked-tree audit: completed with expected non-zero result because prohibited tracked runtime/private files still exist;
- migration discovery: **completed, blocked = NO, dry-run only**;
- snapshot planning: **completed, blockers = 0**.

## Canonical tracked-tree result

- tracked files: **1587**;
- blocker findings: **257**;
- warnings: **0**;
- source: **1332**;
- examples: **1**;
- backups: **217**;
- runtime: **28**;
- private: **4**;
- cache: **2**;
- secret/local config: **1**;
- generated: **2**.

The classification counts imply **254 unique prohibited tracked paths**. The finding count is three higher because `10.0.0` has both a generated-artifact and dedicated accidental-artifact finding, while two private structured-data files also receive PII findings.

## Local migration discovery

- migration items: **427**;
- blocked: **NO**;
- mode: **DRY-RUN**;
- tracked migration-eligible paths inferred from the audit: **252**;
- additional untracked migration candidates: **175**;
- duplicate destination paths: **0**.

The local discovery is materially larger than the original remote GitHub snapshot. It includes, among other things:

- `.env`, `.npmrc` and `.shopify_session.json`;
- GPT integration and KPiR local settings;
- activity logs and performance reports;
- caches and local databases;
- invoice, sales and KPiR documents/exports;
- many component backups;
- Home variants `home1` through `home12`;
- collaboration variant state.

No copy is authorized from this report. The original 427 candidates were grouped as:

- 116 mandatory/critical;
- 294 optional archive/log;
- 17 regenerable cache.

## Allowlist snapshot plan

- source Git SHA: `69a796274de9b9fdee2418707d8dc356b7732e07`;
- application version: `1.54.2`;
- included source files: **1482**;
- skipped paths: **8369**;
- stale tracked staging paths retained for review: **65**;
- protected staging paths: **8**;
- blockers: **0**;
- deterministic tree SHA-256: `e8050e3dfaf33cf189929eac68133d489001865dc9cfeae883e44af6a4319477`.

The zero content blockers did not prove that every included path was true source code. Manual path review found mutable/private files still classified as SOURCE, which triggered the policy tightening documented in `LOCAL_MIGRATION_ANALYSIS_2026-07-11.md`.

## Follow-up changes after the first dry-run

- tightened private/runtime/generated path rules;
- corrected generated precedence ahead of cache/backup rules;
- added explicit migration profiles: `critical`, `archive`, `cache`, `all`;
- blocked `--copy --profile all`;
- fixed PowerShell 5.1 default ToolRoot resolution;
- added profile, policy and runbook regression tests;
- validated the updated code in GitHub Actions.

## Decision

Stage 1A–1D first local evidence is complete.

Stage 1E remains blocked. A second local dry-run with the updated branch is required before copying or untracking anything.

## Explicit boundaries

- no migration `--copy` yet;
- no tracked-file removal;
- no stale staging deletion;
- no import into `gicleeart`;
- no PR merge;
- no Shopify deploy;
- no history rewrite;
- no `CURRENT_APP_STATE.md` update;
- no GPT ZIP generation.
