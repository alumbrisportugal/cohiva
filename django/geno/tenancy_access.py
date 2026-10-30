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
    if type(person_id) is not int or person_id <= 0:
        return False
    if type(requested_unit_id) is not int or requested_unit_id <= 0:
        return False
    if not isinstance(contractor_ids, (set, frozenset)) or not isinstance(unit_ids, (set, frozenset)):
        return False
    if not all(type(member) is int and member > 0 for member in contractor_ids):
        return False
    if not all(type(unit) is int and unit > 0 for unit in unit_ids):
        return False
    if person_id not in contractor_ids or requested_unit_id not in unit_ids:
        return False
    return contract_period(start=start, end=end, state=state, today=today) is ContractPeriod.CURRENT
