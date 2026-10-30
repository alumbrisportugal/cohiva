# Verified upstream code audit — first pass (2026-10-30)

This document records direct source inspection, not a successful deployment.

## Existing components

- `django/portal/models.py`: Wagtail page types (`PortalPage`, `PortalHelpPage`, `PortalHelpPageSection`), with rich text, image and document links; tenant-admin and OAuth application permission models.
- `django/reservation/models.py`: reservable object, reservation type, usage type, prices and blocking-reservation queries. Default role choices refer to user/member/renter/community.
- `django/finance/`: accounting module directory exists. Rent-specific billing workflows have **not** yet been verified.
- `pwa/src/i18n/`: en-US, de-CH and fr-FR catalogs; pt-PT added in the Alumbris fork.
- `django/locale/de/LC_MESSAGES/`: backend German catalog exists; pt-PT catalog not yet implemented.
- `django/portal/README.md`: documents integration with Rocket.Chat OAuth and BookStack SAML, but includes old patch notes; not proof that either integration works in a new deployment.

## Risks seen in source

1. `ReservationType` calendar code directly formats date/time with German text and shows contact names, conditional on config. Privacy and Portuguese-language display must be checked.
2. German labels in backend reservation model fields are not all wrapped in Django translation functions; translation catalogs alone will be insufficient.
3. Reservation prices are for reservable community objects, not proven to represent residential monthly rent or tourist channel management.
4. Existing role choices operate at a community level; apartment-specific tenancy-level authorization has not been demonstrated.
5. Development Compose publishes MariaDB/Redis ports and ships known test credentials; must never be reused as production Compose.
6. Existing OAuth/SAML capabilities could support one login for services, but need end-to-end permission testing.
7. Portugal also supports QR-code payments. Do not discard the QR user experience: Swiss QR-bill and Portuguese rails are different schemes. Reuse QR presentation and payment lifecycle only where compatible, implementing provider-specific adapters and verifying receipts/settlement through official provider APIs. EUR labels alone do not convert Swiss payment instructions into Portuguese ones.

## Acceptance gates

- Source-aware permission audit for contract/document/payment endpoints.
- Verify lease and recurring billing models exist (or specify minimum additional ones).
- Audit reservations for public visitors vs residential logged-in users.
- Establish backend pt-PT message extraction and missing-string coverage.
- CI checks for PWA translation placeholders and matching keys.
- Run full frontend build and Django test suite on isolated CI before staging.
- Design Compose for DS220+ and complete functional and privacy tests with synthetic data before any resident onboarding.

## Explicitly out of scope of this audit

No source-level security certification, no full backend translation, no release approval, no live NAS execution.
