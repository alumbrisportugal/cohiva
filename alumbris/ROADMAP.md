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
