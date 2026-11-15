"""Config flow for PAIP.

One "PAIP" entry holds every water account. Add accounts either by adding the
integration again (it folds into the existing entry) or from Configure.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ACCOUNT_RE,
    AccountData,
    PaipAccountNotFound,
    PaipClient,
    PaipConnectionError,
    PaipError,
    normalise_account,
)
from .const import CONF_ACCOUNT_NUMBER, CONF_ACCOUNTS, CONF_NICKNAME, CONF_REMOVE, DOMAIN

_LOGGER = logging.getLogger(__name__)

ACCOUNT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT_NUMBER): str,
        vol.Optional(CONF_NICKNAME): str,
    }
)


async def _validate(
    hass: HomeAssistant, user_input: dict[str, Any], existing: list[dict[str, Any]]
) -> tuple[dict[str, str] | None, dict[str, str], dict[str, str]]:
    """Return (account dict, errors, description placeholders)."""
    number = normalise_account(user_input[CONF_ACCOUNT_NUMBER])
    if not ACCOUNT_RE.match(number):
        return None, {CONF_ACCOUNT_NUMBER: "invalid_account"}, {}
    if any(a[CONF_ACCOUNT_NUMBER] == number for a in existing):
        return None, {CONF_ACCOUNT_NUMBER: "already_added"}, {}
    try:
        data: AccountData = await PaipClient(async_get_clientsession(hass)).get_account(number)
    except PaipAccountNotFound:
        return None, {CONF_ACCOUNT_NUMBER: "account_not_found"}, {}
    except PaipConnectionError:
        return None, {"base": "cannot_connect"}, {}
    except PaipError as err:
        _LOGGER.debug("PAIP lookup failed: %s", err)
        return None, {"base": "cannot_connect"}, {}
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error validating PAIP account")
        return None, {"base": "unknown"}, {}
    nickname = (user_input.get(CONF_NICKNAME) or "").strip()
    if not nickname:
        # Default to the street line of the premise address, e.g. "NO 591 JALAN ...".
        nickname = (data.address or number).split(",")[0].title()
    return {CONF_ACCOUNT_NUMBER: number, CONF_NICKNAME: nickname}, {}, {}


def _hub(hass: HomeAssistant) -> ConfigEntry | None:
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


class PaipConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a PAIP water account."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        hub = _hub(self.hass)
        existing = list(hub.data.get(CONF_ACCOUNTS, [])) if hub else []
        if user_input is not None:
            account, errors, _ = await _validate(self.hass, user_input, existing)
            if account:
                if hub:
                    self.hass.config_entries.async_update_entry(
                        hub, data={**hub.data, CONF_ACCOUNTS: [*existing, account]}
                    )
                    return self.async_abort(
                        reason="account_added",
                        description_placeholders={"nickname": account[CONF_NICKNAME]},
                    )
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="PAIP", data={CONF_ACCOUNTS: [account]})

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(ACCOUNT_SCHEMA, user_input or {}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure an existing PAIP config entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        existing = list(entry.data.get(CONF_ACCOUNTS, []))
        if user_input is not None:
            number = normalise_account(user_input.get(CONF_ACCOUNT_NUMBER, ""))
            others = [a for a in existing if a[CONF_ACCOUNT_NUMBER] != number]
            account, errors, _ = await _validate(self.hass, user_input, others)
            if account:
                if any(
                    a[CONF_ACCOUNT_NUMBER] == account[CONF_ACCOUNT_NUMBER]
                    for a in existing
                ):
                    updated = [
                        account
                        if a[CONF_ACCOUNT_NUMBER] == account[CONF_ACCOUNT_NUMBER]
                        else a
                        for a in existing
                    ]
                else:
                    updated = [*existing, account]
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_ACCOUNTS: updated},
                )

        suggested = user_input or (existing[0] if existing else {})
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(ACCOUNT_SCHEMA, suggested),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PaipOptionsFlow()


class PaipOptionsFlow(OptionsFlow):
    """Add or remove accounts on the existing PAIP entry."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=["add_account", "remove_accounts"])

    def _accounts(self) -> list[dict[str, Any]]:
        return list(self.config_entry.data.get(CONF_ACCOUNTS, []))

    def _save(self, accounts: list[dict[str, Any]]) -> ConfigFlowResult:
        self.hass.config_entries.async_update_entry(
            self.config_entry, data={**self.config_entry.data, CONF_ACCOUNTS: accounts}
        )
        return self.async_create_entry(data={})

    async def async_step_add_account(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            account, errors, _ = await _validate(self.hass, user_input, self._accounts())
            if account:
                return self._save([*self._accounts(), account])
        return self.async_show_form(
            step_id="add_account",
            data_schema=self.add_suggested_values_to_schema(ACCOUNT_SCHEMA, user_input or {}),
            errors=errors,
        )

    async def async_step_remove_accounts(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        accounts = self._accounts()
        errors: dict[str, str] = {}
        if user_input is not None:
            remove = set(user_input.get(CONF_REMOVE) or [])
            keep = [a for a in accounts if a[CONF_ACCOUNT_NUMBER] not in remove]
            if not keep:
                errors["base"] = "keep_one"
            else:
                return self._save(keep)
        options = [
            selector.SelectOptionDict(
                value=a[CONF_ACCOUNT_NUMBER],
                label=f"{a.get(CONF_NICKNAME) or a[CONF_ACCOUNT_NUMBER]} ({a[CONF_ACCOUNT_NUMBER]})",
            )
            for a in accounts
        ]
        return self.async_show_form(
            step_id="remove_accounts",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_REMOVE, default=[]): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=options, multiple=True)
                    )
                }
            ),
            errors=errors,
        )
