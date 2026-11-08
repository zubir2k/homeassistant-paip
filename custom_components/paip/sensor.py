"""Sensors for PAIP."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import PaipConfigEntry
from .api import AccountData, Bill, payment_url
from .const import CURRENCY_RM
from .entity import PaipEntity


@dataclass(frozen=True, kw_only=True)
class PaipSensorDescription(SensorEntityDescription):
    value_fn: Callable[[AccountData], StateType | date]
    attrs_fn: Callable[[AccountData], dict[str, Any]] | None = None


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def _latest(fn: Callable[[Bill], Any]) -> Callable[[AccountData], Any]:
    return lambda d: fn(d.latest_bill) if d.latest_bill else None


def _bill_attrs(d: AccountData) -> dict[str, Any]:
    b = d.latest_bill
    if b is None:
        return {}
    return {
        "bill_number": b.bill_number,
        "bill_period": b.label,
        "bill_date": _iso(b.bill_date),
        "due_date": _iso(b.due_date),
        "arrears_rm": b.arrears_rm,
        "current_charges_rm": b.current_charges_rm,
        "rounding_rm": b.rounding_rm,
        "adjustment_rm": b.adjustment_rm,
        "tariff_blocks": [
            {
                "block": t.block,
                "volume_m3": t.volume_m3,
                "rate_rm": t.rate_rm,
                "amount_rm": t.amount_rm,
            }
            for t in b.blocks
        ],
    }


def _history(d: AccountData) -> dict[str, Any]:
    return {
        "bill_history": [
            {
                "bill_number": b.bill_number,
                "bill_date": _iso(b.bill_date),
                "usage_m3": b.usage_m3,
                "amount_rm": b.total_rm,
                "water_charge_rm": b.water_charge_rm,
            }
            for b in d.bills
        ]
    }


def _reading_attrs(d: AccountData) -> dict[str, Any]:
    b = d.latest_bill
    if b is None:
        return {}
    return {
        "meter_number": b.meter_number,
        "reading_date": _iso(b.reading_date),
        "previous_reading": b.previous_reading,
        "previous_reading_date": _iso(b.previous_reading_date),
        "reading_type": b.reading_type,
        "period_days": b.period_days,
    }


def _payment_attrs(d: AccountData) -> dict[str, Any]:
    # Amount comes from PahangGo's bill history (the payment made before the
    # latest bill). A newer payment may only show up as last_payment_date.
    b = d.last_payment
    if b is None:
        return {}
    return {"receipt": b.last_payment_receipt, "paid_on": _iso(b.last_payment_date)}


SENSORS: tuple[PaipSensorDescription, ...] = (
    PaipSensorDescription(
        key="balance",
        translation_key="balance",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_RM,
        suggested_display_precision=2,
        # Negative = account in credit (overpaid), like the PahangGo app shows.
        value_fn=lambda d: d.balance_rm,
        attrs_fn=lambda d: {
            "amount_due_rm": d.amount_due_rm,
            "credit_rm": d.credit_rm,
            "payment_url": payment_url(d.account_number),
        },
    ),
    PaipSensorDescription(
        key="amount_due",
        translation_key="amount_due",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_RM,
        suggested_display_precision=2,
        value_fn=lambda d: d.amount_due_rm,
        attrs_fn=lambda d: {
            "due_date": _iso(d.latest_bill.due_date) if d.latest_bill else None,
            "payment_url": payment_url(d.account_number),
        },
    ),
    PaipSensorDescription(
        key="latest_bill_amount",
        translation_key="latest_bill_amount",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_RM,
        suggested_display_precision=2,
        value_fn=_latest(lambda b: b.total_rm),
        attrs_fn=_bill_attrs,
    ),
    PaipSensorDescription(
        key="water_charge",
        translation_key="water_charge",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_RM,
        suggested_display_precision=2,
        value_fn=_latest(lambda b: b.water_charge_rm),
    ),
    PaipSensorDescription(
        key="arrears",
        translation_key="arrears",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_RM,
        suggested_display_precision=2,
        value_fn=_latest(lambda b: max(b.arrears_rm, 0.0)),
    ),
    PaipSensorDescription(
        key="latest_bill_usage",
        translation_key="latest_bill_usage",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        # Per-bill value, not a running total: long-term history comes from the
        # imported paip:<account>_water statistic.
        value_fn=_latest(lambda b: b.usage_m3),
        attrs_fn=_history,
    ),
    PaipSensorDescription(
        key="average_monthly_usage",
        translation_key="average_monthly_usage",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        suggested_display_precision=1,
        value_fn=lambda d: d.average_usage_m3,
        attrs_fn=lambda d: {"bills_counted": len(d.bills)},
    ),
    PaipSensorDescription(
        key="meter_reading",
        translation_key="meter_reading",
        device_class=SensorDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_latest(lambda b: b.reading),
        attrs_fn=_reading_attrs,
    ),
    PaipSensorDescription(
        key="bill_date",
        translation_key="bill_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=_latest(lambda b: b.bill_date),
    ),
    PaipSensorDescription(
        key="due_date",
        translation_key="due_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=_latest(lambda b: b.due_date),
    ),
    PaipSensorDescription(
        key="last_payment_amount",
        translation_key="last_payment_amount",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_RM,
        suggested_display_precision=2,
        value_fn=lambda d: d.last_payment.last_payment_amount_rm if d.last_payment else None,
        attrs_fn=_payment_attrs,
    ),
    PaipSensorDescription(
        key="last_payment_date",
        translation_key="last_payment_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda d: d.last_payment_date,
        attrs_fn=lambda d: {"pending_sync": d.portal_pending_sync},
    ),
    PaipSensorDescription(
        key="account_status",
        translation_key="account_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:water-check",
        value_fn=lambda d: d.portal_status or d.status,
        attrs_fn=lambda d: {
            "disconnection_charge_rm": d.disconnection_charge_rm,
            "reconnection_charge_rm": d.reconnection_charge_rm,
            "account_number": d.account_number,
            "premise_number": d.premise_number,
            "owner": d.owner_name,
            "address": d.address,
            "tariff": d.latest_bill.tariff if d.latest_bill else d.tariff_code,
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaipConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        PaipSensor(coordinator, number, desc)
        for number in coordinator.data
        for desc in SENSORS
    )


class PaipSensor(PaipEntity, SensorEntity):
    entity_description: PaipSensorDescription

    def __init__(self, coordinator, account_number, description) -> None:
        super().__init__(coordinator, account_number, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | date:
        data = self.account_data
        return self.entity_description.value_fn(data) if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.account_data
        if data is None or self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(data)
