"""Buttons for PAIP."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PaipConfigEntry, PaipCoordinator
from .entity import PaipEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaipConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RefreshButton(coordinator, n) for n in coordinator.data)


class RefreshButton(PaipEntity, ButtonEntity):
    """Fetch the latest data from PAIP now."""

    _attr_translation_key = "refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: PaipCoordinator, account_number: str) -> None:
        super().__init__(coordinator, account_number, "refresh")

    @property
    def available(self) -> bool:
        return super().available and self.account_data is not None

    async def async_press(self) -> None:
        await self.coordinator.async_refresh()
