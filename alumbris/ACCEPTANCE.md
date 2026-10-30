# Functional and security acceptance criteria

## Residential scope
- Seven independent apartments; no assumptions that they share a building, utilities or amenities.
- Units can be long-term rented or used for short-term lodging, with independent operational modes.
- Tenant accounts linked to a defined tenancy period, NOT permanent access to a unit's past records.
- Contract dates, renewals, optional rent review, deposit, installments and notices retain an immutable audit trail.
- Legal notice calculation must be reviewed for Portuguese law and contract terms; never auto-send a binding legal communication solely from an AI-generated date.
- Recurring rent records, arrears and receipts must be distinct from official Portuguese tax receipts.
- Maintenance requests: photograph attachments, status, assignee, timestamps and tenant-visible progress.
- Document library: public/common, unit-stable, tenancy-specific, per-person and administrator-only.
- Calendar, notices, rules, instructions and emergency contacts supported in resident-facing flows.
- Short-term accommodation: rate/availability, reservation, cancellation, guest info and channel-sync anti-double-booking tests (if enabled).

## Mandatory negative security tests
1. Tenant A cannot list/download/search Tenant B's contract, receipts, private files or messages.
2. Former tenant loses access upon move-out without destroying landlord's retention-controlled record.
3. New tenant cannot see previous tenant personal information.
4. Anonymous user cannot read any protected document using predictable URL/ID.
5. Attachment access must be authorised server-side, not just hidden in the PWA.
6. A tenant cannot change a unit/tenancy ownership ID in requests to escalate access.
7. Admin operations and legal/financial actions leave audit records.
8. No secrets or user data are committed to Git or included in build logs.

## Operational tests
- Clean install from a documented compose project on x86_64.
- Backup and restore of database AND file volumes.
- Reversible deployment with image pinning and migration compatibility checks; database rollback only from verified backups.
- Resource monitoring and sustained use on Intel J4025 / 18 GB RAM; concurrency tested with realistic resident usage.
- External HTTPS; secure cookies, CSRF, CORS, authentication expiry, brute-force limits and protected admin interfaces.
- No production changes, no use of existing MCP credentials for app users, no destructive NAS cleanup.
- Configuration/migrations should not require external SaaS or paid services for core operation.
- Verify legal requirements with Portuguese specialists before actual resident use.

## Definition of done
Every relevant item is supported by reproducible test evidence; a checklist alone does not qualify as implementation.
