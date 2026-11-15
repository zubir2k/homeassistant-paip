"""DataUpdateCoordinator for PAIP."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AccountData, PaipAccountNotFound, PaipClient, PaipError
from .const import CONF_ACCOUNT_NUMBER, CONF_NICKNAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .statistics import async_import_bill_statistics

_LOGGER = logging.getLogger(__name__)

type PaipConfigEntry = ConfigEntry[PaipCoordinator]


class PaipCoordinator(DataUpdateCoordinator[dict[str, AccountData]]):
    """Fetch every configured PAIP account in one cycle."""

    config_entry: PaipConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PaipConfigEntry,
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
        self._failed_accounts: set[str] = set()

    def nickname(self, account_number: str) -> str:
        return self.accounts.get(account_number) or account_number

    async def _async_update_data(self) -> dict[str, AccountData]:
        numbers = list(self.accounts)
        if not numbers:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="no_accounts_configured",
            )
        results = await asyncio.gather(
            *(self.client.get_account(n) for n in numbers), return_exceptions=True
        )
        data: dict[str, AccountData] = {}
        errors: list[str] = []
        for number, result in zip(numbers, results, strict=True):
            if isinstance(result, AccountData):
                data[number] = result
                if number in self._failed_accounts:
                    self._failed_accounts.remove(number)
                    _LOGGER.info("PAIP account ...%s is back online", number[-4:])
            elif isinstance(result, PaipAccountNotFound):
                errors.append(f"...{number[-4:]}: account not found")
                if number not in self._failed_accounts:
                    self._failed_accounts.add(number)
                    _LOGGER.warning("PAIP account ...%s returned no record", number[-4:])
            elif isinstance(result, PaipError):
                errors.append(f"...{number[-4:]}: {result}")
                if number not in self._failed_accounts:
                    self._failed_accounts.add(number)
                    _LOGGER.warning(
                        "Failed to update PAIP account ...%s: %s", number[-4:], result
                    )
            else:
                raise result  # unexpected bug, surface it

        if not data:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={
                    "errors": "; ".join(errors) or "no valid accounts"
                },
            )
        if errors:
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
