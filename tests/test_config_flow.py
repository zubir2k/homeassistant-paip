"""Config flow tests for PAIP."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from paip import PaipAccountNotFound, PaipConnectionError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paip.const import (
    CONF_ACCOUNT_NUMBER,
    CONF_ACCOUNTS,
    CONF_NICKNAME,
    DOMAIN,
)
from tests.conftest import TEST_ACCOUNT


async def test_user_flow_success(hass, mock_client):
    """Test successful initial setup of PAIP integration."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ACCOUNT_NUMBER: TEST_ACCOUNT,
            CONF_NICKNAME: "Home",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "PAIP"
    assert result["data"][CONF_ACCOUNTS][0][CONF_ACCOUNT_NUMBER] == TEST_ACCOUNT
    assert result["data"][CONF_ACCOUNTS][0][CONF_NICKNAME] == "Home"
    assert result["result"].unique_id == DOMAIN


async def test_user_flow_invalid_account(hass, mock_client):
    """Test user flow with non-10-digit account."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCOUNT_NUMBER: "1234"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ACCOUNT_NUMBER: "invalid_account"}


async def test_user_flow_not_found(hass, mock_client):
    """Test user flow when account does not exist."""
    flow_client, _ = mock_client
    flow_client.get_account.side_effect = PaipAccountNotFound("Not found")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCOUNT_NUMBER: "0999999999"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ACCOUNT_NUMBER: "account_not_found"}


async def test_user_flow_cannot_connect(hass, mock_client):
    """Test user flow on network timeout."""
    flow_client, _ = mock_client
    flow_client.get_account.side_effect = PaipConnectionError("Timeout")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCOUNT_NUMBER: TEST_ACCOUNT},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_add_second_account(hass, mock_client):
    """Test adding a second account into existing entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={
            CONF_ACCOUNTS: [{CONF_ACCOUNT_NUMBER: TEST_ACCOUNT, CONF_NICKNAME: "Home"}]
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ACCOUNT_NUMBER: "0300000002",
            CONF_NICKNAME: "Office",
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "account_added"
    assert len(entry.data[CONF_ACCOUNTS]) == 2


async def test_user_flow_already_added(hass, mock_client):
    """Test adding an account number that is already registered."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        data={
            CONF_ACCOUNTS: [{CONF_ACCOUNT_NUMBER: TEST_ACCOUNT, CONF_NICKNAME: "Home"}]
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ACCOUNT_NUMBER: TEST_ACCOUNT,
            CONF_NICKNAME: "Duplicate",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ACCOUNT_NUMBER: "already_added"}
