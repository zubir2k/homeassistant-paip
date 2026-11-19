"""Lifecycle and service tests for PAIP."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paip.const import (
    CONF_ACCOUNT_NUMBER,
    CONF_ACCOUNTS,
    CONF_NICKNAME,
    DOMAIN,
)
from tests.conftest import TEST_ACCOUNT


async def _setup(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={
            CONF_ACCOUNTS: [{CONF_ACCOUNT_NUMBER: TEST_ACCOUNT, CONF_NICKNAME: "Home"}]
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_and_unload(hass, mock_client):
    """Test setting up and unloading the PAIP integration entry."""
    entry = await _setup(hass)
    assert entry.runtime_data is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_service_refresh(hass, mock_client):
    """Test paip.refresh service."""
    await _setup(hass)
    _, coord_client = mock_client
    coord_client.get_account.reset_mock()

    await hass.services.async_call(DOMAIN, "refresh", blocking=True)
    coord_client.get_account.assert_awaited()
