"""Conservative period evaluation for Alumbris tenancy workflows.

This module is independent of Django and does not grant access to any resource.
Authorization MUST additionally verify the authenticated person's relationship
to the requested contract, unit and document on the server.

The upstream Contract.active field is deliberately untouched because billing and
other legacy consumers need a separate compatibility assessment.
"""
from __future__ import annotations

from datetime import date
from enum import Enum


class ContractPeriod(str, Enum):
    FUTURE = "future"
    CURRENT = "current"
    EXPIRED = "expired"
    INVALID = "invalid"
    UNSIGNED = "unsigned"


def contract_period(
    *,
    start: date,
    end: date | None,
    state: str,
    today: date | None = None,
) -> ContractPeriod:
    """Classify a contract for workflow display, not authorization.

    The state 'unterzeichnet' is the existing signed state in Cohiva.
    Terminated or cancellation-notice states are conservatively not current
    until a reviewed rule distinguishes notice from the termination date.
    """
    current_date = today if today is not None else date.today()
    if end is not None and end < start:
        return ContractPeriod.INVALID
    if state in {"ungueltig", "gekuendigt"}:
        return ContractPeriod.INVALID
    if state != "unterzeichnet":
        return ContractPeriod.UNSIGNED
    if start > current_date:
        return ContractPeriod.FUTURE
    if end is not None and end < current_date:
        return ContractPeriod.EXPIRED
    return ContractPeriod.CURRENT
