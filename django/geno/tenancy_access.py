"""Fail-closed tenant-access decision helper for Alumbris Living.

Pure policy function, deliberately not wired to HTTP endpoints yet.
The caller MUST look up the authenticated Django user's Address via trusted
server-side relations, not accept party IDs from client request parameters.
"""
from __future__ import annotations

from datetime import date

from .tenancy_period import ContractPeriod, contract_period


def can_access_contract(
    *,
    person_id: int | None,
    contractor_ids: set[int],
    unit_ids: set[int],
    requested_unit_id: int,
    start: date,
    end: date | None,
    state: str,
    today: date | None = None,
) -> bool:
    """Deny by default, including historical and future contracts.

    This checks a single *contract's* tenancy rights. A document or payment
    endpoint must additionally verify that its target object belongs to that
    contract and that the operation is permitted for the requested document.
    """
    if person_id is None or isinstance(person_id, bool) or person_id <= 0:
        return False
    if requested_unit_id <= 0 or isinstance(requested_unit_id, bool):
        return False
    if person_id not in contractor_ids or requested_unit_id not in unit_ids:
        return False
    return contract_period(start=start, end=end, state=state, today=today) is ContractPeriod.CURRENT
