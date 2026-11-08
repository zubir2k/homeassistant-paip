"""Actions for PAIP: refresh, and generate_bill_pdf."""

from __future__ import annotations

import os
from datetime import timedelta

import voluptuous as vol
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.util import dt as dt_util

from .api import normalise_account
from .const import (
    ATTR_ACCOUNT_NUMBER,
    ATTR_BILL_NUMBER,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_EXPIRES,
    DEFAULT_LINK_HOURS,
    DOMAIN,
    MAX_LINK_HOURS,
    PDF_SUBDIR,
    PDF_URL_PREFIX,
    SERVICE_GENERATE_BILL_PDF,
    SERVICE_REFRESH,
)

REFRESH_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_CONFIG_ENTRY_ID): vol.All(cv.ensure_list, [cv.string])}
)
PDF_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ACCOUNT_NUMBER): cv.string,
        vol.Optional(ATTR_BILL_NUMBER): cv.string,
        vol.Optional(ATTR_EXPIRES, default=DEFAULT_LINK_HOURS): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_LINK_HOURS)
        ),
    }
)


def _loaded(hass: HomeAssistant):
    return [
        e for e in hass.config_entries.async_entries(DOMAIN)
        if e.state is ConfigEntryState.LOADED
    ]


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def _refresh(call: ServiceCall) -> None:
        wanted = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entries = [e for e in _loaded(hass) if not wanted or e.entry_id in wanted]
        if wanted and len(entries) != len(set(wanted)):
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="entry_not_loaded"
            )
        for entry in entries:
            await entry.runtime_data.async_refresh()

    async def _generate_pdf(call: ServiceCall) -> ServiceResponse:
        number = normalise_account(call.data[ATTR_ACCOUNT_NUMBER])
        bill_no = call.data.get(ATTR_BILL_NUMBER)
        account = None
        for entry in _loaded(hass):
            account = (entry.runtime_data.data or {}).get(number)
            if account:
                break
        if account is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="account_not_configured"
            )
        bill = account.bill(bill_no)
        if bill is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="bill_not_found",
                translation_placeholders={"bill_number": bill_no or ""},
            )

        folder = hass.config.path(*PDF_SUBDIR)
        filename = f"bil_{number}_{bill.bill_number}.pdf"
        path = os.path.join(folder, filename)

        def _write() -> None:
            from .bill_pdf import render_bill  # reportlab import is slow; keep lazy

            os.makedirs(folder, exist_ok=True)
            render_bill(bill.raw, path)

        await hass.async_add_executor_job(_write)
        hours = call.data[ATTR_EXPIRES]
        # Signed link: works in a notification tap without a login prompt, stops
        # working after `expires` hours (or on restart), and never touches /local.
        url = async_sign_path(
            hass, f"{PDF_URL_PREFIX}/{filename}", timedelta(hours=hours)
        )
        try:
            full_url = get_url(hass, allow_internal=False, prefer_cloud=False) + url
        except NoURLAvailableError:
            full_url = None
        return {
            "path": path,
            "url": url,
            "external_url": full_url,
            "expires_at": (dt_util.now() + timedelta(hours=hours)).isoformat(),
            "bill_number": bill.bill_number,
        }

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, _refresh, schema=REFRESH_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_BILL_PDF,
        _generate_pdf,
        schema=PDF_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
