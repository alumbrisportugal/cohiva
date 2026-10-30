# Alumbris Living implementation backlog — living working plan

## Shipped on this feature branch (not production)
- pt-PT PWA catalog and locale registration.
- Lightweight translation structural checks and regression tests.
- Pure contract period classifier with boundary tests.
- Pure, fail-closed tenancy permission policy with isolation tests.
- Technical model, deployment and payments audits.

## Gate 1: finish the safe foundation
- Run Python regression suite in CI and repair failures.
- Check TypeScript/Yarn build; validate the pt-PT catalog with an actual browser.
- Integrate tenancy policy into Django-authenticated endpoints after inspecting every resource query and ensuring object ownership from the server-side authenticated user.
- Prove historical documents and receipts are properly available to their owner where legally permitted without exposing the successor's data. Current pure policy denies historic access by design; it is not the complete product policy.
- Add backend Django pt-PT locale with extracted strings and coverage.
- Remove Swiss-specific assumptions without mutating historical accounting records.

## Gate 2: Rentila-inspired residential management
- Validate existing recurring invoices, outstanding balances, partial payments and billing jobs.
- Annual rent adjustment with configurable index and human approval.
- Lease renewal/end dates, protected notifications and lawful review of Portuguese notice rules.
- Entry/exit inspection with inventory and time-stamped photos.
- Deposit custody/return lifecycle; status/audit ledger.
- Multi-unit financial dashboard and downloadable statements.
- Portuguese payments: validated SEPA/MB WAY/MULTIBANCO integration; do not treat QR scan as settled funds.
- AT tax receipts: official workflow and legal review; not equivalent to Cohiva Invoice.

## Gate 3: tenant premium experience
- Responsive, single-portal tenant dashboard with contractual privacy and common/unit-specific information.
- Tenant maintenance, files, forms, bookings and communications.
- No mandatory Nextcloud or mobile app.
- Independent accommodation booking channel if and only if audited reservation module is insufficient.

## Gate 4: commercial validation
- Separate project in DSM Container Manager on Intel AMD64.
- Disposable credentials and test data, no use of production MCP services.
- Unit, HTTP authorization, integration, acceptance, restore and rollback tests.
- Measured CPU, RAM and IO performance on DS220+; written release report.
- No commercial-release label without test evidence.

## Document metadata security (current branch)
- `resident-contract-document` and `resident-contract-document-history` are metadata-only routes.
- Resident-visible document types are explicitly allowlisted in Django setting
  `ALUMBRIS_RESIDENT_DOCUMENT_TYPES`. Default empty means no titles or metadata
  are exposed to residents before a deliberate administrator configuration.
- Example *test-only* value: `("alumbris_test_contract_doc",)`.
- File downloads remain deliberately unavailable to residents; the existing
  admin-generation endpoint is not a safe tenant download endpoint.
- An allowlisted type still needs a privacy review: a contract can contain
  documents intended only for staff. Production requires document-level
  visibility classification, not merely a type allowlist.

- Per-document `Document.resident_visible` (migration 0033) is now required in addition to a type allowlist and current/historical contract ownership. Defaults to false for existing and new documents. Production still needs approval workflow and secure file delivery.

## Resident portal read-only overview (development branch)
- `GET /api/v1/geno/resident-overview/`: seven counters derived directly
  from the same server-side filtered querysets used by resident list/detail APIs.
  No contract notes, other tenants, bank details, payment references, or amounts.
- `GET /api/v1/geno/resident-contract-history/`: former contract headers
  (original parties only, ended signed/terminated state, no void contracts).
- These views are not a Portuguese tax-compliant payment/receipt module.
  The portal remains read-only; full user experience and privacy review pending.
