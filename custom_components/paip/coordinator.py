"""DataUpdateCoordinator for PAIP."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AccountData, PaipAccountNotFound, PaipClient, PaipError
from .const import CONF_ACCOUNT_NUMBER, CONF_NICKNAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .statistics import async_import_bill_statistics

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class PaipCoordinator(DataUpdateCoordinator[dict[str, AccountData]]):
    """Fetch every configured PAIP account in one cycle."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: PaipClient,
        accounts: list[dict[str, Any]],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.accounts = {
            str(a[CONF_ACCOUNT_NUMBER]): a.get(CONF_NICKNAME) or None for a in accounts
        }

    def nickname(self, account_number: str) -> str:
        return self.accounts.get(account_number) or account_number

    async def _async_update_data(self) -> dict[str, AccountData]:
        numbers = list(self.accounts)
        results = await asyncio.gather(
            *(self.client.get_account(n) for n in numbers), return_exceptions=True
        )
        data: dict[str, AccountData] = {}
        errors: list[str] = []
        for number, result in zip(numbers, results, strict=True):
            if isinstance(result, AccountData):
                data[number] = result
            elif isinstance(result, PaipAccountNotFound):
                _LOGGER.warning("PAIP account ...%s returned no record", number[-4:])
            elif isinstance(result, PaipError):
                errors.append(f"...{number[-4:]}: {result}")
            else:
                raise result  # unexpected bug, surface it

        if not data and errors:
            raise UpdateFailed("; ".join(errors))
        if errors:
            _LOGGER.warning("Some PAIP accounts failed to update: %s", "; ".join(errors))
            # Keep the last good values for accounts that failed this round.
            for number in numbers:
                if number not in data and self.data and number in self.data:
                    data[number] = self.data[number]

        for number, account in data.items():
            try:
                await async_import_bill_statistics(
                    self.hass, account, self.nickname(number)
                )
            except Exception:  # noqa: BLE001 - statistics must never break polling
                _LOGGER.exception("Failed to import statistics for ...%s", number[-4:])
        return data
