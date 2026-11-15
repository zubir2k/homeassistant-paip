"""Constants for the PAIP (Pengurusan Air Pahang Berhad) integration."""

from datetime import timedelta
from enum import StrEnum

from homeassistant.const import ATTR_CONFIG_ENTRY_ID, Platform

DOMAIN = "paip"
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

CONF_ACCOUNTS = "accounts"
CONF_ACCOUNT_NUMBER = "account_number"
CONF_NICKNAME = "nickname"
CONF_REMOVE = "remove"

# Bills are monthly and the balance only moves when PAIP posts a payment
# (1-3 days after paying), so once a day is plenty.
DEFAULT_SCAN_INTERVAL = timedelta(hours=24)


class PaipService(StrEnum):
    """Services for the PAIP integration."""

    REFRESH = "refresh"
    GENERATE_BILL_PDF = "generate_bill_pdf"


class PaipServiceArgument(StrEnum):
    """Service arguments for the PAIP integration."""

    ACCOUNT_NUMBER = "account_number"
    BILL_NUMBER = "bill_number"
    EXPIRES = "expires"


SERVICE_REFRESH = PaipService.REFRESH
SERVICE_GENERATE_BILL_PDF = PaipService.GENERATE_BILL_PDF
ATTR_ACCOUNT_NUMBER = PaipServiceArgument.ACCOUNT_NUMBER
ATTR_BILL_NUMBER = PaipServiceArgument.BILL_NUMBER

MANUFACTURER = "Pengurusan Air Pahang Berhad"
MODEL = "Water account"
CURRENCY_RM = "MYR"
TIME_ZONE = "Asia/Kuala_Lumpur"

# Generated bills are kept OUT of /config/www (which /local serves to anyone).
# They live in <config>/paip_bills and are served only through an authenticated
# view; the action hands out short-lived signed links.
PDF_SUBDIR = ("paip_bills",)
LEGACY_PDF_SUBDIR = ("www", "paip")
PDF_URL_PREFIX = "/api/paip/bill"
PDF_FILENAME_RE = r"bil_\d{10}_\d{6}\.pdf"
ATTR_EXPIRES = PaipServiceArgument.EXPIRES
DEFAULT_LINK_HOURS = 24
MAX_LINK_HOURS = 168

__all__ = [
    "ATTR_ACCOUNT_NUMBER",
    "ATTR_BILL_NUMBER",
    "ATTR_CONFIG_ENTRY_ID",
    "ATTR_EXPIRES",
    "CONF_ACCOUNTS",
    "CONF_ACCOUNT_NUMBER",
    "CONF_NICKNAME",
    "CONF_REMOVE",
    "CURRENCY_RM",
    "DEFAULT_LINK_HOURS",
    "DEFAULT_SCAN_INTERVAL",
    "DOMAIN",
    "LEGACY_PDF_SUBDIR",
    "MANUFACTURER",
    "MAX_LINK_HOURS",
    "MODEL",
    "PDF_FILENAME_RE",
    "PDF_SUBDIR",
    "PDF_URL_PREFIX",
    "PLATFORMS",
    "PaipService",
    "PaipServiceArgument",
    "SERVICE_GENERATE_BILL_PDF",
    "SERVICE_REFRESH",
    "TIME_ZONE",
]
