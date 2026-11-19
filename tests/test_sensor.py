"""Sensor and entity tests for PAIP."""

from homeassistant.helpers import device_registry as dr
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


async def test_sensors(hass, mock_client):
    """Test all PAIP sensor states and attributes."""
    entry = await _setup(hass)
    prefix = "sensor.paip_home_"

    balance = hass.states.get(prefix + "balance")
    assert balance is not None
    assert balance.state == "12.0"
    assert balance.attributes["unit_of_measurement"] == "MYR"

    amount_due = hass.states.get(prefix + "amount_due")
    assert amount_due is not None
    assert amount_due.state == "12.0"

    bill_amount = hass.states.get(prefix + "latest_bill_amount")
    assert bill_amount is not None
    assert bill_amount.state == "22.25"

    usage = hass.states.get(prefix + "latest_bill_usage")
    assert usage is not None
    assert usage.state == "25.0"

    due_date = hass.states.get(prefix + "due_date")
    assert due_date is not None
    assert due_date.state == "2026-09-07"

    last_payment = hass.states.get(prefix + "last_payment_date")
    assert last_payment is not None
    assert last_payment.state == "2026-07-15"

    # Test device registry entry
    reg = dr.async_get(hass)
    device = reg.async_get_device_by_identifier((DOMAIN, TEST_ACCOUNT), entry.entry_id)
    assert device is not None
    assert device.manufacturer == "Pengurusan Air Pahang Berhad"
    assert device.model == "Water account"


async def test_binary_sensor_and_button(hass, mock_client):
    """Test payment overdue binary sensor and manual refresh button."""
    await _setup(hass)

    overdue = hass.states.get("binary_sensor.paip_home_overdue")
    assert overdue is not None

    _, init_client = mock_client
    init_client.get_account.reset_mock()

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.paip_home_refresh"},
        blocking=True,
    )
    init_client.get_account.assert_awaited()
