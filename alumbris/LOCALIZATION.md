# pt-PT localization and Portuguese adaptation plan

## Confirmed baseline
- Backend: Django gettext catalog under `django/locale`; upstream translation helper currently targets `de`.
- PWA: Quasar/Vue with `pwa/src/i18n`; upstream README documents German-only UI.
- Django setup guide requires `de_CH.UTF-8`, so locale-dependent date/number assumptions must be audited.

## Work packages
1. Inventory Django translation IDs and PWA keys, including email templates, admin UI, validation errors, PDF output and notices.
2. Add pt-PT locale catalogs in native project formats; do not overwrite original German.
3. Replace hard-coded strings behind translation keys where necessary.
4. Configure EUR, `pt-PT` date/number formatting and Europe/Lisbon timezone per tenant/installation.
5. Replace Swiss-only labels, IBAN/payment and building-cooperative concepts with Portuguese labels only where semantic equivalence is proven.
6. Produce CI reports: missing keys, interpolation placeholders, HTML escaping, date/currency output, plural forms and screen overflow.
7. Human review of contract language and legal notices; AI translations are drafts, not legal certification.

## Canonical glossary
| German | Portuguese (Portugal) |
|---|---|
| Mietvertrag | Contrato de arrendamento |
| Mieter | Arrendatário |
| Vermieter | Senhorio |
| Miete | Renda |
| Nebenkosten | Encargos adicionais |
| Kaution | Caução |
| Kündigungsfrist | Prazo de pré-aviso |
| Schadensmeldung | Comunicação de avaria |
| Gemeinschaftsräume | Espaços comuns |

Translation work should be developed in a separate pull request with complete catalog and tests, not merely copied strings.
