# Local migration analysis — 2026-07-11

Repository package: `eagleblastmusic-lgtm/gicleeapp`

Branch: `gpt-work/repo-safety-foundation`

Inputs reviewed locally by the user and supplied for analysis:

- `gicleeapp-tracked-tree.json`
- `gicleeapp-migration-dry-run.json`
- `gicleeapp-snapshot-dry-run.json`

## Safety status

**FIRST LOCAL ANALYSIS COMPLETE / SECOND DRY-RUN REQUIRED / COPY NOT AUTHORIZED**

The supplied migration report is a dry-run. Every item has status `planned`; no file was copied and no destination hash exists yet. The report is not blocked, contains no execution error and contains no duplicate destination path.

## Original local migration plan

Total items: **427**

| Classification | Count | Proposed handling |
|---|---:|---|
| SECRET | 4 | mandatory preservation in config storage |
| PRIVATE | 80 | mandatory preservation in data storage |
| RUNTIME | 82 | split between active state/config and optional logs |
| BACKUP | 244 | archive, not active runtime storage |
| CACHE | 17 | regenerable; do not copy by default |

Destination buckets:

| Bucket | Count |
|---|---:|
| backups | 244 |
| data | 125 |
| logs | 50 |
| config | 8 |

Tracked versus untracked discovery:

- tracked migration-eligible paths: **252**;
- additional untracked candidates: **175**.

## Preservation tiers from the first report

### Tier A — mandatory preservation: 116 items

- 4 secrets/local credentials;
- 80 private/accounting/authored files;
- 28 runtime data files;
- 4 runtime configuration files.

This tier includes credentials, invoices and sales data, KPiR exports, authored notes, Home/collaboration state and essential application configuration.

### Tier B — optional historical archive: 294 items

- 244 backups;
- 50 log/performance files.

This tier should be copied to archive/log storage only after a retention decision. It must not remain in source directories or Git.

### Tier C — regenerable: 17 items

- caches and local databases classified as regenerable.

The default recommendation is not to migrate this tier unless a component-specific review proves that a file is expensive or impossible to regenerate.

## Important policy gaps found

The original snapshot had zero content blockers, but path review showed that several mutable or private files were still passing as `SOURCE`. The policy has been tightened for:

- DNR and KPiR records/settings;
- invoice event history;
- prompt database context media and authored prompts;
- planner entries;
- processed client orders;
- Segregator Plików tiles;
- AI title/description drafts;
- tasks and reminders;
- Add Image marks/history/preferences;
- social-media queue/config/state;
- local page/site settings;
- launcher shortcuts/categories;
- performance reports and `_push_live.log`;
- `.shopify/**` generated state;
- `print_optimize/data/ww_pairs/**` generated artifacts.

Policy precedence was corrected so generated paths such as `.pytest_cache`, `node_modules/.cache`, backup `.gitkeep` markers and `.shopify` state are not incorrectly proposed for migration as cache/backup data.

## Migration profiles added

Copy execution now requires one explicit non-aggregate profile:

- `critical` — secrets, private data and active runtime/config;
- `archive` — backups, logs and performance reports;
- `cache` — regenerable cache only;
- `all` — permitted for dry-run only.

`--copy --profile all` is blocked before destination resolution or directory creation.

## Remote validation after policy tightening

GitHub Actions result after the policy and profile changes:

- Security / push workflow tests: **PASS**;
- Repository safety discovery: **PASS**;
- tracked files: **1424**;
- source: **1320**;
- examples: **4**;
- runtime: **42**;
- private: **17**;
- backups: **36**;
- cache: **2**;
- secret/local config: **1**;
- generated: **2**;
- blocker findings: **103**;
- migration dry-run items: **98**;
- migration profile: `all`;
- migration blocked: **NO**.

The higher migration count and lower SOURCE count are expected: paths previously misclassified as source are now excluded and preserved through migration policy.

## Consequence

The original 427-item report is not the final migration manifest. It remains valid evidence of the first local discovery, but the tightened policy and explicit profiles require a second local dry-run before any copy operation.

Expected effects of the second local run:

- more true user/runtime paths will be excluded from the source snapshot and added to migration review;
- generated `.pytest_cache`, `node_modules/.cache`, `.shopify`, `ww_pairs` and backup marker files will no longer be migration candidates;
- previously unclassified performance reports will be consistently treated as optional logs;
- the snapshot included-file count will decrease;
- reports will include a `profile` field;
- zero content blockers alone will no longer be treated as proof that all included paths are source code.

## Required next validation

1. update the detached tool worktree to the latest branch head;
2. rerun the same copy-free validation script;
3. preserve the new JSON reports outside Git;
4. compare old/new migration counts and included paths;
5. review `critical` destinations for conflicts;
6. only after approval, execute a copy-only `critical` migration with SHA-256 verification;
7. `archive` copy is a separate decision;
8. `cache` remains un-copied by default.

## Explicit boundaries

- no `--copy` yet;
- no destination file creation;
- no `git rm` or `git rm --cached`;
- no stale staging deletion;
- no merge/import/deploy;
- no history rewrite;
- no publication of reports containing local paths or private filenames.
