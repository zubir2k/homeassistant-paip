"""The PAIP (Pengurusan Air Pahang Berhad) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import PaipClient
from .const import CONF_ACCOUNT_NUMBER, CONF_ACCOUNTS, DOMAIN, PLATFORMS
from .coordinator import PaipCoordinator
from .services import async_setup_services

type PaipConfigEntry = ConfigEntry[PaipCoordinator]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PaipConfigEntry) -> bool:
    accounts = entry.data.get(CONF_ACCOUNTS, [])
    coordinator = PaipCoordinator(
        hass, entry, PaipClient(async_get_clientsession(hass)), accounts
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Drop devices for accounts that were removed in Configure.
    wanted = {str(a[CONF_ACCOUNT_NUMBER]) for a in accounts}
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        numbers = {i[1] for i in device.identifiers if i[0] == DOMAIN}
        if numbers and not numbers & wanted:
            registry.async_remove_device(device.id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PaipConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: PaipConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow deleting a device only when its account is no longer configured."""
    wanted = {str(a[CONF_ACCOUNT_NUMBER]) for a in entry.data.get(CONF_ACCOUNTS, [])}
    return not any(i[0] == DOMAIN and i[1] in wanted for i in device.identifiers)


async def _async_update_listener(hass: HomeAssistant, entry: PaipConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
