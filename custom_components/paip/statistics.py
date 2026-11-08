"""Long-term statistics for PAIP bills.

PAIP meters are read monthly; each bill knows its reading dates and the m³
used between them. Usage and the bill's water charge are spread evenly over
the days of the reading period and imported as external statistics:

* ``paip:<account>_water``  (m³, usable in the Energy dashboard Water card)
* ``paip:<account>_cost``   (MYR)

Day values are an even split, but per-bill totals match exactly. Imports are
incremental (only days after the last imported one), so sums never reset when
old bills drop out of the API's six-bill window.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .api import AccountData, Bill
from .const import CURRENCY_RM, DOMAIN, TIME_ZONE

_LOGGER = logging.getLogger(__name__)


def spread_bills(bills: list[Bill]) -> list[tuple[date, float, float]]:
    """Return ``(day, usage_m3, cost_rm)`` per day, oldest first."""
    days: list[tuple[date, float, float]] = []
    for bill in sorted(
        (b for b in bills if b.reading_date or b.bill_date),
        key=lambda b: b.reading_date or b.bill_date,
    ):
        end = bill.reading_date or bill.bill_date
        start = bill.previous_reading_date or (end - timedelta(days=bill.period_days or 30))
        length = (end - start).days
        if length <= 0:
            continue
        cost = bill.water_charge_rm or 0.0
        for offset in range(1, length + 1):
            days.append(
                (start + timedelta(days=offset), bill.usage_m3 / length, cost / length)
            )
    return days


async def async_import_bill_statistics(
    hass: HomeAssistant, data: AccountData, label: str
) -> None:
    if "recorder" not in hass.config.components:
        return
    days = spread_bills(data.bills)
    if not days:
        return
    number = data.account_number
    await _import(
        hass, f"{DOMAIN}:{number}_water", f"PAIP {label} water",
        UnitOfVolume.CUBIC_METERS, [(d, u) for d, u, _ in days],
    )
    await _import(
        hass, f"{DOMAIN}:{number}_cost", f"PAIP {label} cost",
        CURRENCY_RM, [(d, c) for d, _, c in days],
    )


async def _import(
    hass: HomeAssistant,
    statistic_id: str,
    name: str,
    unit: str,
    series: list[tuple[date, float]],
) -> None:
    tz = dt_util.get_time_zone(TIME_ZONE)
    last = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, statistic_id, True, {"sum"}
    )
    total = 0.0
    last_ts: float | None = None
    if rows := (last or {}).get(statistic_id):
        total = rows[0].get("sum") or 0.0
        last_ts = _as_ts(rows[0].get("start"))

    stats: list[StatisticData] = []
    for day, value in series:
        start = datetime(day.year, day.month, day.day, tzinfo=tz)
        if last_ts is not None and start.timestamp() <= last_ts:
            continue
        total += value
        stats.append(StatisticData(start=start, state=round(value, 4), sum=round(total, 4)))
    if not stats:
        return

    async_add_external_statistics(
        hass,
        StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=name,
            source=DOMAIN,
            statistic_id=statistic_id,
            unit_of_measurement=unit,
        ),
        stats,
    )
    _LOGGER.debug("Imported %d rows into %s", len(stats), statistic_id)


def _as_ts(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    return value.timestamp()
