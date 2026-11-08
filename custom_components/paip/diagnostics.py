"""Diagnostics for PAIP (account numbers and personal details redacted)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import PaipConfigEntry

# The PahangGo lookup is unauthenticated, so an account number alone exposes
# the owner's name and address. Never let any of these leave the box.
TO_REDACT = {
    "account_number",
    "owner_name",
    "premise_number",
    "address",
    "nickname",
    "meter_number",
    "last_payment_receipt",
    "NO_AKAUN",
    "NO_PREMIS",
    "NO_INVOIS",
    "NAMA",
    "ALAMAT1",
    "ALAMAT2",
    "ALAMAT3",
    "NO_METER",
    "BAYAR_DAHULU_NO_RESIT",
    "DEPOSIT",
    "accountNo",
    "ownerName",
    "ref1",
    "invoice",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PaipConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "accounts": {
            f"account_{i + 1}": async_redact_data(asdict(data), TO_REDACT)
            for i, data in enumerate((coordinator.data or {}).values())
        },
    }
