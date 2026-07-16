# Security policy

## Supported code

Security fixes are applied to the current `master` branch and the current desktop application version. Historical branches, archived snapshots, generated knowledge ZIPs, and superseded pull requests are not supported release lines.

## Reporting a vulnerability

Do not open a public issue containing credentials, session data, customer information, private store data, or a working exploit.

Use a private GitHub Security Advisory for this repository when that feature is available. Otherwise contact the repository owner through an existing private channel and include only the minimum information needed to reproduce the problem.

A useful report contains:

- the affected commit or version;
- the affected component, file, or workflow;
- reproduction steps that do not expose real credentials or customer data;
- the expected and observed behavior;
- an impact assessment;
- a proposed mitigation when known.

## Secrets and local credentials

The following are local-only and must never be committed, attached to issues, copied into logs, or included in generated knowledge archives:

- `.env` and environment-specific `.env.*` files;
- `.shopify_session.json`;
- `.shopify-store-password.local`;
- Shopify access tokens, session cookies, API secrets, store passwords, and deployment credentials;
- customer, order, accounting, and other private business exports.

Examples and documentation must use placeholders. Redaction must remove both values and reusable identifiers when those identifiers could expose a private store or account.

## Repository and automation boundaries

- Work is performed on task branches and reviewed through pull requests.
- `master` is not edited directly.
- Force-push, history rewriting, destructive cleanup, and automatic conflict resolution are not part of the normal workflow.
- Shopify deploys, live-theme mutations, data migrations, releases, tags, and package publication require a separate explicit decision.
- CI artifacts and logs must not contain secrets or private runtime state.
- Runtime-writable state, cache, logs, backups, and session files must live outside source-controlled application directories.

## Suspected secret exposure

When a secret may have been exposed:

1. stop using the affected credential;
2. revoke or rotate it at the provider;
3. invalidate related sessions when supported;
4. preserve the minimum evidence required for investigation without redistributing the secret;
5. inspect commits, pull requests, workflow logs, artifacts, issues, and generated archives for copies;
6. remove tracked copies through a separately reviewed incident-recovery plan;
7. add or strengthen regression checks that prevent recurrence.

Deleting a file from the latest commit is not sufficient when the value exists in Git history or external artifacts.

## Dependency and supply-chain changes

Dependency additions and upgrades must be intentional, minimal, and reviewed. Lockfiles or version constraints must be updated consistently with the ecosystem in use. Automated dependency changes do not authorize a release, deploy, or Shopify mutation.
