"""Fixtures for PAIP tests."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from paip import AccountData, Bill, TariffBlock

pytest_plugins = ["pytest_homeassistant_custom_component"]

TEST_ACCOUNT = "0300000001"


def make_bill() -> Bill:
    block = TariffBlock("0-18", 18.0, 0.80, 14.40)
    return Bill(
        bill_number="082026",
        label="082026 (Ogos 2026)",
        bill_date=date(2026, 8, 13),
        due_date=date(2026, 9, 7),
        arrears_rm=-0.65,
        current_charges_rm=22.88,
        rounding_rm=0.02,
        total_rm=22.25,
        meter_number="1600000000",
        reading_date=date(2026, 8, 13),
        reading=2869,
        previous_reading_date=date(2026, 7, 13),
        previous_reading=2844,
        usage_m3=25.0,
        period_days=31,
        tariff="A0 Domestik",
        reading_type="N (Sebenar)",
        water_charge_rm=22.88,
        adjustment_rm=0.0,
        last_payment_date=date(2026, 7, 15),
        last_payment_amount_rm=26.0,
        last_payment_receipt="00000001",
        blocks=[block],
    )


def make_account_data(
    account_number: str = TEST_ACCOUNT,
    balance_rm: float = 12.00,
) -> AccountData:
    bill = make_bill()
    return AccountData(
        account_number=account_number,
        owner_name="TEST USER",
        premise_number="P100",
        address="NO 1 JALAN UJIAN, 28000 TEMERLOH",
        status="Aktif",
        tariff_code="A0",
        bill_number="082026",
        balance_rm=balance_rm,
        bills=[bill],
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    yield


@pytest.fixture(autouse=True)
async def cleanup_entries(hass):
    """Clean up config entries after each test."""
    yield
    from homeassistant.config_entries import ConfigEntryState

    from custom_components.paip.const import DOMAIN

    for entry in list(hass.config_entries.async_entries(DOMAIN)):
        if entry.state is ConfigEntryState.LOADED:
            await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()


@pytest.fixture
def mock_client():
    """Patch the PaipClient everywhere."""
    with (
        patch("custom_components.paip.async_get_clientsession"),
        patch("custom_components.paip.config_flow.async_get_clientsession"),
        patch("custom_components.paip.PaipClient", autospec=True) as init_cls,
        patch(
            "custom_components.paip.coordinator.PaipClient", autospec=True
        ) as coord_cls,
        patch(
            "custom_components.paip.config_flow.PaipClient", autospec=True
        ) as flow_cls,
    ):
        for cls in (init_cls, coord_cls, flow_cls):
            client = cls.return_value
            client.get_account = AsyncMock(
                side_effect=lambda acc: make_account_data(account_number=acc)
            )
            client.get_portal_bill = AsyncMock(return_value=None)
        yield flow_cls.return_value, init_cls.return_value
