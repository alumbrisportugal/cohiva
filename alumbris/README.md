# Alumbris Living Premium — Engineering workspace

This directory contains the initial design and acceptance criteria for the Portuguese residential platform, derived from [Cohiva](https://github.com/tegonal/cohiva).

**Status:** design/audit only. No resident-facing features, Portuguese legal compliance, Docker production deployment, or NAS validation are claimed.

## Product boundaries
- One resident portal covering seven independently located apartments.
- Long-term tenancy administration (leases, rent, deposits, renewal dates, maintenance, communications).
- Short-term rental capability via existing Cohiva modules only if verified suitable; otherwise evaluate a module before developing one.
- Resident premium experience without Nextcloud: shared/apartment/private documents, notices, requests, calendar, communication, optional personal services.
- Reuse native Synology services only where necessary, while keeping a cohesive portal and permissions.
- Portuguese (Portugal) language, currency EUR, timezone Europe/Lisbon.
- No network-management changes to routers; no alteration of production MCP gateway or pre-existing containers.

## Non-negotiable controls
- Strict access control: residents may only access their own tenancy resources and allowed shared materials; tenancy historical records and personal data are not transferred to the next occupant.
- One account per adult; no shared administrative or tenant passwords.
- No exposure of Portuguese rent contracts, tenant identity documents, banking details, secrets, or real data in repository or demo fixtures.
- Legal and fiscal acts require human validation until independently verified; do not advertise automatic AT receipt issuance, compliant notices, or signature workflows.
- Production deployments require reviewed release, secrets injection, volume backups, rollback and acceptance tests.

## Existing project modules needing code-level inspection
- `django/finance`, `django/credit_accounting`
- `django/reservation`
- `django/portal`
- `django/geno` and `django/website_example`
- `pwa/src/i18n` and `django/locale`
- `django/cohiva` settings, auth and access-control interfaces

## Workflow
1. Audit dependencies, licences, runtime topology, module functionality and Swiss-specific assumptions.
2. Prepare pt-PT backend and PWA language catalogs with completeness checks.
3. Introduce test fixtures for seven apartments, residents, move-out transitions, data isolation and billing cycles.
4. Run security/unit/integration tests in isolated CI.
5. Build and test a separate Synology Container Manager staging stack, with resource monitoring.
6. Only then consider a staged production rollout with backups and manual approval.

See [acceptance criteria](ACCEPTANCE.md), [localization plan](LOCALIZATION.md) and [deployment guardrails](DEPLOYMENT.md).
