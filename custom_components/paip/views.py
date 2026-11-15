"""Authenticated download view for generated bill PDFs."""

from __future__ import annotations

import os
import re
from http import HTTPStatus

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import PDF_FILENAME_RE, PDF_SUBDIR, PDF_URL_PREFIX

_NAME = re.compile(rf"^{PDF_FILENAME_RE}$")


class PaipBillView(HomeAssistantView):
    """Serve a bill PDF to a signed-in user or a valid signed link only."""

    url = PDF_URL_PREFIX + "/{filename}"
    name = "api:paip:bill"
    requires_auth = True

    def __init__(self, hass: HomeAssistant, bill_dir: str | None = None) -> None:
        self.hass = hass
        self._folder = bill_dir or hass.config.path(*PDF_SUBDIR)

    async def get(self, request: web.Request, filename: str) -> web.StreamResponse:
        if not _NAME.match(filename):
            return web.Response(status=HTTPStatus.NOT_FOUND)
        path = os.path.join(self._folder, filename)
        if not await self.hass.async_add_executor_job(os.path.isfile, path):
            return web.Response(status=HTTPStatus.NOT_FOUND)
        return web.FileResponse(
            path,
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "private, no-store",
                "X-Robots-Tag": "noindex",
            },
        )
