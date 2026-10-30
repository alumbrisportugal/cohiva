# Residential data model audit — 2026-10-30

Source: `django/geno/models.py` inspected on the fork's development baseline. This is a static audit; no Django/database runtime test has been executed.

## Confirmed existing functionality

| Model | Confirmed fields / relationships | Implication |
| --- | --- | --- |
| `Building` | Referenced by `RentalUnit.building` and `Tenant.building` | Support separate apartment locations via buildings |
| `RentalUnit` | Area, floor, type, billing period, net rent, extra charges, deposit, active/status | Core data already available for traditional leases |
| `Contract` | Tenant party M2M `contractors`, `main_contact`, M2M `rental_units`, date/date_end, billing date start/end, statuses and QR-bill preference | Contract model and billing dates exist; no need to recreate from scratch |
| `Invoice` | Contract or person, period month/year, amount, transaction/reference, accounting pointers | Billing entity exists, but **not** a Portuguese AT rent receipt |
| `Document` | Generic foreign key, template reference, document type, regeneration permission | Document generation infrastructure exists |
| `Tenant` | External contact and building, active boolean | Community/building association does not by itself prove tenancy-scoped access |

## High-priority defects and gaps to assess before any resident data

1. `Contract.is_active()` checks whether `date_end` is before today but does **not** check `date`, `state`, or billability. A future contract can therefore be treated as active; a cancelled/invalid contract with a future end date may also be treated as active. We must not rely on this flag for authorisation.
2. The M2M `Contract.rental_units` permits multiple units per contract and historical or overlapping contracts per unit. Business rules must distinguish dates, statuses and shared occupancy to avoid leaking data between successive residents.
3. `Tenant` is attached to a `Building`, not an individual active `Contract`. An apartment-specific permission model must resolve current contract relationships, including secondary residents.
4. `Contract.contractors` identifies legal contracting parties; children and additional occupants are separate concepts. Avoid equating every PWA user to a legal contractor.
5. `Contract.send_qrbill`, Swiss currency labels and `Invoice.__str__` include Swiss-specific semantics (CHF). Preserve data and existing payment processing until a Portugal-specific provider adapter and euro-aware formatting have been tested.
6. `Invoice` and `Contract` have cascades and M2M associations that merit retention/deletion impact review before enabling account removal.
7. `Document`'s generic relation provides flexibility but **not** visibility isolation. Every download/regeneration route must check the requesting user's rights to the referenced object.
8. `RentalUnit.billing_period` defaults to one month, but the existence of a field is not evidence of correct periodic rent issuance, arrears, deposit accounting or contract renewal notifications.
9. `Contract.date_end` may be empty. Portuguese notice periods and renewals depend on the contract and law; never infer legal deadline solely from nullable end date.
10. Personal data and financial information must remain absent from public Git history, CI fixtures and logs.

## Concrete next implementation

- Define a tenancy-period access resolver (unit + contract + party + dates + explicit role) and use it for every protected endpoint, not just PWA rendering.
- Build synthetic seven-apartment fixtures including new occupant taking over an apartment, future contract, expired contract, cancelled contract, co-occupants, multiple units and cross-building access.
- Add tests where a resident attempts to access another resident's files, messages, rent documents and historic contracts via guessed identifiers.
- Separate property-stable documents from tenancy-private and person-private documents.
- Audit `django/geno/api_views.py`, `django/geno/views.py`, `django/portal/auth.py` and download routes before modifying access control.
- Only after these tests, add pt-PT backend labels and contractual workflows.

## Release gate

No release to real tenants until security tests pass against HTTP endpoints in a disposable staging environment. This audit does not imply that those safeguards already exist.
