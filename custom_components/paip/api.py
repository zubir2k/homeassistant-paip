"""Async client for PAIP water bills via the PahangGo API.

PAIP closed its own OnlinePay portal; bills are now only presented through the
PahangGo app. Its Laravel backend exposes the PAIP bill lookup (service 43)
without authentication:

    GET https://apiv2.pahanggo.com/api/service/43/search?query=<10-digit account>

The response carries the account, the running balance and the latest six bills
(``raw_data.SENARAI_BIL_DETAIL``, newest first) with meter readings, usage and
tariff blocks. Amounts are strings in RM; dates are ``dd-mm-yyyy``.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://apiv2.pahanggo.com"
PAIP_SERVICE_ID = 43
USER_AGENT = "HomeAssistant-PAIP (+https://github.com/zubir2k/homeassistant-paip)"
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=45)

ACCOUNT_RE = re.compile(r"^\d{10}$")

# PAIP's own new portal (not yet public). Its bill-check page embeds a
# ``const billData = {...};`` JSON blob. Used as best-effort enrichment for
# what PahangGo lacks: the latest payment date, sync state and charges.
PORTAL_URL = "https://myairpahang.paip.com.my"
_BILLDATA_RE = re.compile(r"const\s+billData\s*=\s*(\{.*?\});\s*\n", re.S)


def payment_url(account_number: str) -> str:
    return f"{PORTAL_URL}/payment/check/{normalise_account(account_number)}"


class PaipError(Exception):
    """Base error."""


class PaipConnectionError(PaipError):
    """Network-level failure or a 5xx from PahangGo."""


class PaipAccountNotFound(PaipError):
    """The account number returned no record."""


def normalise_account(value: str) -> str:
    """Strip spaces/dashes; PAIP account numbers are 10 digits."""
    return re.sub(r"\D", "", value or "")


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("RM", "").strip())
    except (TypeError, ValueError):
        return None


def _i(value: Any) -> int | None:
    n = _f(value)
    return int(n) if n is not None else None


def _d(value: Any) -> date | None:
    """Parse ``13-10-2026``. Non-dates such as ``SEGERA`` return None."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%d-%m-%Y").date()
    except ValueError:
        return None


@dataclass(slots=True)
class TariffBlock:
    block: str
    volume_m3: float | None
    rate_rm: float | None
    amount_rm: float | None


@dataclass(slots=True)
class Bill:
    """One monthly bill (one SENARAI_BIL_DETAIL entry)."""

    bill_number: str
    label: str | None
    bill_date: date | None
    due_date: date | None
    arrears_rm: float
    current_charges_rm: float | None
    rounding_rm: float
    total_rm: float | None
    meter_number: str | None
    reading_date: date | None
    reading: int | None
    previous_reading_date: date | None
    previous_reading: int | None
    usage_m3: float
    period_days: int | None
    tariff: str | None
    reading_type: str | None
    water_charge_rm: float | None
    adjustment_rm: float
    last_payment_date: date | None
    last_payment_amount_rm: float | None
    last_payment_receipt: str | None
    blocks: list[TariffBlock] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> Bill:
        blocks: list[TariffBlock] = []
        n = 1
        while item.get(f"BLOK_{n}") is not None:
            blocks.append(
                TariffBlock(
                    block=str(item[f"BLOK_{n}"]),
                    volume_m3=_f(item.get(f"M3_{n}")),
                    rate_rm=_f(item.get(f"KADAR_{n}")),
                    amount_rm=_f(item.get(f"AMAUN_{n}")),
                )
            )
            n += 1
        period = str(item.get("TEMPOH_BIL") or "").split()
        return cls(
            bill_number=str(item.get("NO_BIL") or ""),
            label=item.get("NO_BIL_KETERANGAN"),
            bill_date=_d(item.get("TARIKH_BIL")),
            due_date=_d(item.get("BAYAR_SEBELUM")),
            arrears_rm=_f(item.get("TUNGGAKAN")) or 0.0,
            current_charges_rm=_f(item.get("JUMLAH_BIL_SEMASA")),
            rounding_rm=_f(item.get("PENGENAPAN")) or 0.0,
            total_rm=_f(item.get("JUMLAH_BIL")),
            meter_number=item.get("NO_METER"),
            reading_date=_d(item.get("TARIKH_SEMASA")),
            reading=_i(item.get("BACA_SEMASA")),
            previous_reading_date=_d(item.get("TARIKH_DAHULU")),
            previous_reading=_i(item.get("BACA_DAHULU")),
            usage_m3=_f(item.get("JUMLAH_PENGGUNAAN")) or 0.0,
            period_days=_i(period[0]) if period else None,
            tariff=item.get("KETERANGAN_TARIF"),
            reading_type=item.get("JENIS_BACAAN"),
            water_charge_rm=_f(item.get("JUMLAH_CAJ_AIR_SEMASA")),
            adjustment_rm=_f(item.get("PELARASAN_BIL")) or 0.0,
            last_payment_date=_d(item.get("BAYAR_DAHULU_TARIKH")),
            last_payment_amount_rm=_f(item.get("BAYAR_DAHULU_AMAUN")),
            last_payment_receipt=item.get("BAYAR_DAHULU_NO_RESIT"),
            blocks=blocks,
            raw=item,
        )


@dataclass(slots=True)
class AccountData:
    """Everything the integration shows for one account."""

    account_number: str
    owner_name: str | None
    premise_number: str | None
    address: str | None
    status: str | None
    tariff_code: str | None
    bill_number: str | None
    # Running balance (BAKI_TERKINI). Negative = account in credit.
    balance_rm: float | None
    bills: list[Bill] = field(default_factory=list)  # newest first
    # From the PAIP portal (None when it couldn't be read).
    portal_last_payment_date: date | None = None
    portal_paid_amount_rm: float | None = None
    portal_pending_sync: bool | None = None
    portal_status: str | None = None
    disconnection_charge_rm: float | None = None
    reconnection_charge_rm: float | None = None

    @property
    def last_payment_date(self) -> date | None:
        """Newest payment date known from either source."""
        dates = [d for d in (
            self.portal_last_payment_date,
            self.last_payment.last_payment_date if self.last_payment else None,
        ) if d]
        return max(dates) if dates else None

    def apply_portal(self, bd: dict[str, Any]) -> None:
        self.portal_last_payment_date = _d(bd.get("lastPayDate"))
        self.portal_paid_amount_rm = _f(bd.get("paidAmount"))
        pending = bd.get("isPendingSync")
        self.portal_pending_sync = bool(pending) if pending is not None else None
        self.portal_status = bd.get("account_status")
        self.disconnection_charge_rm = _f(bd.get("disconnectionCharge"))
        self.reconnection_charge_rm = _f(bd.get("reconnectionCharge"))

    @property
    def latest_bill(self) -> Bill | None:
        return self.bills[0] if self.bills else None

    @property
    def amount_due_rm(self) -> float:
        return round(max(self.balance_rm or 0.0, 0.0), 2)

    @property
    def credit_rm(self) -> float:
        return round(max(-(self.balance_rm or 0.0), 0.0), 2)

    @property
    def last_payment(self) -> Bill | None:
        """Newest bill that records a payment before it."""
        for bill in self.bills:
            if bill.last_payment_date:
                return bill
        return None

    @property
    def average_usage_m3(self) -> float | None:
        if not self.bills:
            return None
        return round(sum(b.usage_m3 for b in self.bills) / len(self.bills), 2)

    def is_overdue(self, today: date) -> bool:
        bill = self.latest_bill
        if self.amount_due_rm <= 0 or bill is None:
            return False
        if bill.arrears_rm > 0:
            return True
        return bool(bill.due_date and today > bill.due_date)

    def bill(self, bill_number: str | None) -> Bill | None:
        if not bill_number:
            return self.latest_bill
        return next((b for b in self.bills if b.bill_number == bill_number), None)

    @classmethod
    def from_api(cls, record: dict[str, Any]) -> AccountData:
        raw = record.get("raw_data") or {}
        balance = _f(raw.get("BAKI_TERKINI"))
        if balance is None and record.get("payable_amount") is not None:
            balance = round(float(record["payable_amount"]) / 100, 2)
        address = record.get("premise_address") or ", ".join(
            s for s in (raw.get("ALAMAT1"), raw.get("ALAMAT2"), raw.get("ALAMAT3")) if s
        )
        return cls(
            account_number=str(record.get("account_number") or raw.get("NO_AKAUN")),
            owner_name=record.get("owner_name") or raw.get("NAMA"),
            premise_number=record.get("premise_number") or raw.get("NO_PREMIS"),
            address=address or None,
            status=record.get("account_status") or raw.get("STATUS"),
            tariff_code=record.get("tariff") or raw.get("TARIF"),
            bill_number=record.get("bill_number") or raw.get("NO_BIL"),
            balance_rm=balance,
            bills=[Bill.from_api(b) for b in raw.get("SENARAI_BIL_DETAIL") or []],
        )


class PaipClient:
    """Minimal async client for the PahangGo PAIP lookup."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def get_account(self, account_number: str) -> AccountData:
        account = normalise_account(account_number)
        url = f"{BASE_URL}/api/service/{PAIP_SERVICE_ID}/search"
        try:
            async with self._session.get(
                url,
                params={"query": account},
                headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                timeout=DEFAULT_TIMEOUT,
            ) as resp:
                if resp.status >= 500:
                    raise PaipConnectionError(f"PahangGo HTTP {resp.status}")
                try:
                    payload = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError) as err:
                    raise PaipError(f"Non-JSON response (HTTP {resp.status})") from err
        except (TimeoutError, aiohttp.ClientError) as err:
            raise PaipConnectionError(str(err)) from err

        if not isinstance(payload, dict):
            raise PaipError("Unexpected response")
        records = payload.get("data")
        if not records or not isinstance(records, list):
            raise PaipAccountNotFound(payload.get("message") or "No record")
        record = next(
            (r for r in records if str(r.get("account_number")) == account),
            records[0],
        )
        data = AccountData.from_api(record)
        try:
            if bd := await self.get_portal_bill(account):
                data.apply_portal(bd)
        except PaipError as err:  # enrichment only; never fail the poll on it
            _LOGGER.debug("PAIP portal unavailable for ...%s: %s", account[-4:], err)
        return data

    async def get_portal_bill(self, account_number: str) -> dict[str, Any] | None:
        """Read the billData blob from PAIP's bill-check page."""
        try:
            async with self._session.get(
                payment_url(account_number),
                headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                timeout=DEFAULT_TIMEOUT,
            ) as resp:
                if resp.status != 200:
                    raise PaipError(f"portal HTTP {resp.status}")
                html = await resp.text()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise PaipConnectionError(str(err)) from err
        match = _BILLDATA_RE.search(html)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except ValueError as err:
            raise PaipError("portal billData unparsable") from err
