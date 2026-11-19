"""Binary sensors for PAIP."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from paip import payment_url

from .const import TIME_ZONE_OBJ
from .coordinator import PaipConfigEntry, PaipCoordinator
from .entity import PaipEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaipConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(OverdueSensor(coordinator, n) for n in coordinator.data)


class OverdueSensor(PaipEntity, BinarySensorEntity):
    """On when there is a balance owed past the bill's due date (or arrears)."""

    _attr_translation_key = "overdue"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: PaipCoordinator, account_number: str) -> None:
        super().__init__(coordinator, account_number, "overdue")

    @property
    def is_on(self) -> bool | None:
        data = self.account_data
        if data is None:
            return None
        today = dt_util.now(TIME_ZONE_OBJ).date()
        return data.is_overdue(today)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.account_data
        if data is None or data.latest_bill is None:
            return None
        b = data.latest_bill
        return {
            "amount_due_rm": data.amount_due_rm,
            "due_date": b.due_date.isoformat() if b.due_date else None,
            "arrears_rm": max(b.arrears_rm, 0.0),
            "payment_url": payment_url(data.account_number),
        }
