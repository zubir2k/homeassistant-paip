"""Parser tests with a synthetic PahangGo record (no real customer data)."""

import importlib.util
import pathlib
import sys
from datetime import date

_API = pathlib.Path(__file__).parents[1] / "custom_components" / "paip" / "api.py"
spec = importlib.util.spec_from_file_location("paip_api", _API)
api = importlib.util.module_from_spec(spec)
sys.modules["paip_api"] = api
spec.loader.exec_module(api)

BILL = {
    "NO_AKAUN": "0300000001", "NO_BIL": "082026", "NO_BIL_KETERANGAN": "082026 (Ogos 2026)",
    "TARIKH_BIL": "13-08-2026", "BAYAR_SEBELUM": "07-09-2026", "TUNGGAKAN": "-0.65",
    "JUMLAH_BIL_SEMASA": "22.88", "PENGENAPAN": "0.02", "JUMLAH_BIL": "22.25",
    "BAYAR_DAHULU_TARIKH": "15-07-2026", "BAYAR_DAHULU_AMAUN": "26.00",
    "BAYAR_DAHULU_NO_RESIT": "00000001", "NO_METER": "1600000000",
    "TARIKH_SEMASA": "13-08-2026", "BACA_SEMASA": "2869", "TARIKH_DAHULU": "13-07-2026",
    "BACA_DAHULU": "2844", "JUMLAH_PENGGUNAAN": "25", "TEMPOH_BIL": "31 Hari",
    "KETERANGAN_TARIF": "A0 Domestik", "JENIS_BACAAN": "N (Sebenar)",
    "BLOK_1": "0 - 18", "M3_1": "21", "KADAR_1": "0.800", "AMAUN_1": "16.80",
    "BLOK_2": "> 18 - 45", "M3_2": "4", "KADAR_2": "1.520", "AMAUN_2": "6.08",
    "JUMLAH_CAJ_AIR_SEMASA": "22.88", "PELARASAN_BIL": "0.00",
}
RECORD = {
    "owner_name": "TEST", "account_number": "0300000001", "account_status": "A",
    "premise_address": "NO 1 JALAN UJIAN, 28000 TEMERLOH", "tariff": "A0",
    "bill_number": "082026", "payable_amount": 1200,
    "raw_data": {"BAKI_TERKINI": "12.00", "SENARAI_BIL_DETAIL": [BILL]},
}


def test_parse():
    d = api.AccountData.from_api(RECORD)
    assert d.balance_rm == 12.0 and d.amount_due_rm == 12.0 and d.credit_rm == 0
    b = d.latest_bill
    assert b.bill_date == date(2026, 8, 13) and b.due_date == date(2026, 9, 7)
    assert b.usage_m3 == 25 and b.reading == 2869 and b.period_days == 31
    assert [t.volume_m3 for t in b.blocks] == [21, 4]
    assert d.last_payment_date == date(2026, 7, 15)
    assert d.is_overdue(date(2026, 9, 8)) and not d.is_overdue(date(2026, 9, 1))


def test_credit_and_portal():
    rec = {**RECORD, "raw_data": {**RECORD["raw_data"], "BAKI_TERKINI": "-11.75"}}
    d = api.AccountData.from_api(rec)
    assert d.credit_rm == 11.75 and not d.is_overdue(date(2027, 1, 1))
    d.apply_portal({"lastPayDate": "19-10-2026", "account_status": "A (AKTIF)", "isPendingSync": False})
    assert d.last_payment_date == date(2026, 10, 19)


def test_normalise():
    assert api.normalise_account("0317-628 422") == "0317628422"
    assert api.payment_url("0317 628422").endswith("/payment/check/0317628422")
