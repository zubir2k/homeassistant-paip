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

    def __init__(self, hass: HomeAssistant) -> None:
        self._folder = hass.config.path(*PDF_SUBDIR)

    async def get(self, request: web.Request, filename: str) -> web.StreamResponse:
        if not _NAME.match(filename):
            return web.Response(status=HTTPStatus.NOT_FOUND)
        path = os.path.join(self._folder, filename)
        if not os.path.isfile(path):
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
