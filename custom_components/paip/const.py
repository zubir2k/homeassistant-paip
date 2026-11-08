"""Constants for the PAIP (Pengurusan Air Pahang Berhad) integration."""

from datetime import timedelta

DOMAIN = "paip"
PLATFORMS = ["sensor", "binary_sensor", "button"]

CONF_ACCOUNTS = "accounts"
CONF_ACCOUNT_NUMBER = "account_number"
CONF_NICKNAME = "nickname"
CONF_REMOVE = "remove"

# Bills are monthly and the balance only moves when PAIP posts a payment
# (1-3 days after paying), so once a day is plenty.
DEFAULT_SCAN_INTERVAL = timedelta(hours=24)

SERVICE_REFRESH = "refresh"
SERVICE_GENERATE_BILL_PDF = "generate_bill_pdf"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_ACCOUNT_NUMBER = "account_number"
ATTR_BILL_NUMBER = "bill_number"

MANUFACTURER = "Pengurusan Air Pahang Berhad"
MODEL = "Water account"
CURRENCY_RM = "MYR"
TIME_ZONE = "Asia/Kuala_Lumpur"

# Generated bills land in <config>/www/paip -> served at /local/paip/
PDF_SUBDIR = ("www", "paip")
PDF_URL_PREFIX = "/local/paip"
