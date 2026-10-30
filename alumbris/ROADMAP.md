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

## Resident portfolio snapshot (development branch)
- `GET /api/v1/geno/resident-portfolio/`: seven independent object collections
  with `{total, items, truncated}` per section.
- Every collection reuses its existing read-only, authenticated resident
  queryset and restricted serializer; no independent authorization path.
- Each section is capped at 50 rows, ordered by database primary key;
  `truncated=true` indicates the client must use its paginated detail route.
- Sensitive administrative notes, raw document contexts, template paths,
  bank details and unrelated tenant records remain excluded.
- This is not an accounting statement, tax receipt, file downloader, payment
  portal, or completed frontend dashboard.

## Paginated portal sections (development branch)
- `GET /api/v1/geno/resident-portfolio/sections/<section>/?page=1`
  provides a 25-row page for each of the seven explicit collection names.
- Section names: `current-contracts`, `historical-contracts`,
  `current-units`, `current-invoices`, `historical-invoices`,
  `current-documents`, `historical-documents`.
- Responses contain `section`, `page`, `page_size`, `total`,
  `has_next`, `items`; invalid page parameters receive HTTP 400.
- Each section delegates access filtering and response projection to the
  existing tenant-scoped viewset and resident serializer.
- Not a file download endpoint, payment provider, or legal tax receipt.

## Resident activity timeline (development branch)
- `GET /api/v1/geno/resident-timeline/`: at most 30 dated events from
  currently or historically authorized invoices and published contract
  document metadata. Entries contain only `kind`, `id`, `title`, `date`.
- Uses the same tenant-ownership, document-visibility and type allowlist
  enforcement as the existing seven portfolio sections. Revoking visibility
  removes documents from the timeline immediately.
- Not an accounting ledger, evidence of payment, official receipt, or
  downloadable document archive. All changes remain in PR draft.

## Timeline category selection and input hardening
- `GET /api/v1/geno/resident-timeline/?kind=document` restricts the feed
  to published, tenant-authorized current contract documents.
- Repeat `kind` for multiple groups, e.g.
  `?kind=invoice&kind=historical_invoice`. Permitted groups:
  `invoice`, `historical_invoice`, `document`, `historical_document`.
- Unrecognized groups are rejected with HTTP 400, never silently converted
  into unrestricted access. Without `kind`, all four permitted groups apply.
- The API remains capped at 30 events with no raw document or financial data.

- The timeline accepts inclusive ISO dates `from_date=YYYY-MM-DD` and
  `to_date=YYYY-MM-DD` for event filtering, applied to the authorized
  queryset before the 30-row cap. Malformed or reversed date ranges return 400.

## Authenticated portal capability negotiation
- `GET /api/v1/geno/resident-capabilities/` describes enabled read-only
  routes, the seven portfolio sections and pagination limits, timeline event
  categories and date filters; no tenant data or admin configuration.
- Explicitly advertises `document_download=false`,
  `online_payments=false`, and `official_pt_tax_receipts=false` until
  those services are implemented, tested and homologated.
- Timeline rejects repeated scalar date parameters and excessive category
  selections with HTTP 400 to avoid ambiguous filters.

## Resident portal first usable HTML screen (experimental)
- `/geno/resident/portal/` requires Django session authentication.
- The pt-PT dashboard retrieves seven counters via `resident-overview/`.
- Seven navigable record categories use `resident-portfolio/sections/`
  and previous/next page controls; display uses DOM textContent rather
  than injecting untrusted resident fields as HTML.
- This is read-only: no payment, Portuguese fiscal receipt, document download
  or resident writes. Browser accessibility and Synology staging deployment
  still require homologation before commercial release.

## Resident portal CI regression and usability
- The page authentication regression test explicitly logs out the base test
  fixture, which automatically logs in the Django superuser.
- Additional HTML checks verify safe `textContent` output, no `innerHTML`
  insertion, same-origin API credentials, and keyboard-focusable pagination.
- Field labels in the HTML resident record summaries are localized to pt-PT;
  the JSON API retains its stable field names.
- Commercial go-live remains blocked by browser acceptance testing, a secure
  installation path, payment and Portuguese fiscal workflows.

## Resident maintenance requests (experimental)
- `GET /api/v1/geno/resident-maintenance/`: each authenticated resident
  lists only tickets they created; staff have read access for triage.
- `POST /api/v1/geno/resident-maintenance/`: requires `rental_unit`,
  `title` (up to 140 characters) and `description` (10–3000 characters).
  Unit ownership is checked against the active rental-unit authorization.
- `GET /api/v1/geno/resident-maintenance/<id>/`: ownership restricted;
  resident name, status, and creation date returned without other tenants.
- Status begins at `open` and cannot be controlled by resident input.
  Existing records cannot be patched/deleted from this API.
- No staff triage interface, attachments, email alerts, SLA, or completion
  workflow exists yet. Migration 0034 creates the tickets table.

- Django admin staff triage now lists/searches requests, permits status
  updates, and locks resident-submitted identity, unit and description.
  Admin cannot add or delete requests. Staff read access via API is tested.

## Maintenance portal integration (experimental)
- The pt-PT resident HTML portal now provides a repair submission form and
  an individual list of submitted tickets. Rental units come from the same
  authenticated tenant-scoped API used elsewhere in the portal.
- Django sets a CSRF cookie when serving the authenticated page; the form
  submits authenticated JSON POST requests with the token. No token or
  database data is embedded into the static JavaScript.
- The UI does not yet provide photo attachments, staff messaging, live updates,
  scheduling, or push/email notifications. Browser and Synology staging
  acceptance tests are still required.

## Maintenance dashboard integration
- Resident overview now returns `maintenance_requests`, counted through the same authenticated, tenant-scoped repair ticket queryset as its read-only list/detail API.
- The resident HTML dashboard displays the ticket count; the separate repair form and ticket list remain available.
- Other residents' repairs never contribute to the total. The new counter is not part of the seven original portfolio sections.

## Maintenance administrative permission hardening
- Staff change access in the Django maintenance admin requires the explicit
  `geno.change_residentmaintenancerequest` permission (superusers excepted).
- The original resident, unit, subject and problem description remain locked
  on admin edit; administrators cannot add or delete tickets there.
- Staff may list/view tickets via the repair API but cannot create tickets
  through the resident submission endpoint. New permission and negative
  tests cover these boundaries.

## Maintenance conversations (experimental)
- Migration 0035 adds messages associated with a maintenance request,
  author and creation date. Resident authorship is server-controlled.
- `GET/POST /api/v1/geno/resident-maintenance-comments/` uses ticket
  ownership for residents; staff need explicit view/change ticket permissions.
- Reply creation is rejected after a ticket is marked `closed`. The resident
  portal can open conversations and send replies via authenticated CSRF
  protected requests.
- Staff notifications, server-side pagination, event audit trail, attachment
  scanning and cross-browser acceptance tests remain pending. No release.
