"""Render a PAIP water bill PDF that matches the PahangGo app's layout.

Rebuilt from PahangGo v3.1.14 (BillPaipDetailScreen._buildBillPdfBody) and
a bill PDF the app produced. Page: A4, 8 pt margins, Helvetica.

Input: one entry from
  GET https://apiv2.pahanggo.com/api/service/43/search?query=<account>
  -> data[0].raw_data.SENARAI_BIL_DETAIL[n]

Usage:
  from paip_bill_pdf import render_bill
  pdf_bytes = render_bill(bill_dict)            # returns bytes
  render_bill(bill_dict, "bil_102026.pdf")      # or writes a file

Needs: reportlab
"""

from __future__ import annotations

import io
import os
from typing import Any

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_assets")

NAVY = HexColor("#033863")
BLUE = HexColor("#0059A2")
RED = HexColor("#FF5252")
GREY = HexColor("#E0E0E0")

PAGE_W, PAGE_H = A4  # 595.28 x 841.89
L, R = 8.0, PAGE_W - 8.0  # content edges
LINE = 11.55  # row pitch for 10 pt label/value rows


# ---------------------------------------------------------------- helpers
def _f(v: Any) -> float | None:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def money(v: Any) -> str:
    """App shows '-' for zero and for negative amounts (credit/rounding down).

    Inferred from the sample: PENGENAPAN -0.02 and TUNGGAKAN 0.00 both print '-'.
    """
    n = _f(v)
    if n is None or n <= 0:
        return "-"
    return f"RM {n:,.2f}"


def text(v: Any) -> str:
    return "-" if v in (None, "") else str(v)


class _Page:
    """Tiny wrapper so coordinates read top-down, like the original."""

    def __init__(self, c: Canvas) -> None:
        self.c = c

    def y(self, top: float) -> float:
        return PAGE_H - top

    def txt(self, x, top, s, size=10, bold=False, color=black, right=False):
        c = self.c
        c.setFillColor(color)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        base = self.y(top) - size * 0.93  # top of box -> baseline
        (c.drawRightString if right else c.drawString)(x, base, s)

    def rule(self, top, width=1.0):
        c = self.c
        c.setStrokeColor(black)
        c.setLineWidth(width)
        c.line(L, self.y(top), R, self.y(top))

    def box(self, x0, top, x1, bottom, fill):
        c = self.c
        c.setFillColor(fill)
        c.rect(x0, self.y(bottom), x1 - x0, bottom - top, stroke=0, fill=1)

    def img(self, name, x, top, w, h):
        path = os.path.join(ASSETS, name)
        if os.path.exists(path):
            self.c.drawImage(path, x, self.y(top + h), w, h, mask="auto")

    def kv(self, top, label, value, bold=False, size=10):
        self.txt(L, top, label, size, bold)
        self.txt(R, top, value, size, bold, right=True)

    def table(self, top, cols, header, rows):
        """cols = x positions of column starts; rows of strings."""
        hh, rh = 18.7, 18.4
        bottom = top + hh + rh * len(rows)
        self.box(L, top, R, top + hh, GREY)
        c = self.c
        c.setStrokeColor(black)
        c.setLineWidth(0.3)
        c.rect(L, self.y(bottom), R - L, bottom - top, stroke=1, fill=0)
        for x in cols[1:]:
            c.line(x, self.y(top), x, self.y(bottom))
        for i in range(len(rows)):
            yy = top + hh + rh * i
            c.line(L, self.y(yy), R, self.y(yy))
        for x, h in zip(cols, header):
            self.txt(x + 4, top + 4, h, 9, True)
        for i, row in enumerate(rows):
            for x, v in zip(cols, row):
                self.txt(x + 4, top + hh + 4, v, 9)
                pass
            top += rh
        return bottom


# ---------------------------------------------------------------- render
def render_bill(b: dict[str, Any], out: str | None = None) -> bytes:
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=A4)
    c.setTitle(f"Bil Air {b.get('NO_BIL', '')}")
    p = _Page(c)

    # Header -----------------------------------------------------------
    p.img("logo_paip.png", 8, 8, 75, 50)
    p.img("logo_pulapel.png", 8, 64, 30, 20)
    p.txt(46, 66.9, "|09 - 573 9999", 12, True, BLUE)
    p.txt(123.4, 8, "Pengurusan Air Pahang Berhad", 14, True, NAVY)
    p.txt(123.4, 28.7, "Bil Air", 12, True)

    # social card (rounded navy box)
    c.setFillColor(NAVY)
    c.roundRect(460.7, p.y(74.4), R - 460.7, 66.4, 8, stroke=0, fill=1)
    p.img("logo_fb.png", 468.7, 16, 14, 14)
    p.txt(488.7, 17.8, "PAIPBerhad", 9, color=white)
    p.img("logo_web.png", 468.7, 36.5, 14, 9.4)
    p.txt(488.7, 36, "www.paip.com.my", 9, color=white)
    p.img("logo_tiktok.png", 468.7, 52.4, 14, 14)
    p.txt(488.7, 54.2, "PengurusanAirPahang", 9, color=white)

    p.rule(92.5)

    # Account block ----------------------------------------------------
    t = 108.0
    for label, val in (
        ("No Akaun", text(b.get("NO_AKAUN"))),
        ("No Premis", text(b.get("NO_PREMIS"))),
        ("No Bil", text(b.get("NO_BIL"))),
        ("Deposit", text(b.get("DEPOSIT"))),
        ("Tarikh Bil", text(b.get("TARIKH_BIL"))),
        ("No Kontrak", text(b.get("NO_KONTRAK"))),
    ):
        p.kv(t, label, val)
        t += LINE

    p.txt(L, 187.4, text(b.get("NAMA")), 11, True)
    addr = ", ".join(
        s for s in (b.get("ALAMAT1"), b.get("ALAMAT2"), b.get("ALAMAT3")) if s
    )
    p.txt(L, 203.5, addr, 10, True)

    # Makluman + amount due -------------------------------------------
    p.box(L, 227.4, R, 252.4, NAVY)
    p.txt(14, 233.4, "MAKLUMAN", 11, True, white)
    p.box(L, 260.4, R, 285.5, RED)
    p.txt(14, 266.4, "JUMLAH BIL PERLU DIBAYAR", 11, True, white)
    p.txt(R - 6, 266.4, money(b.get("JUMLAH_BIL")), 11, True, white, right=True)

    t = 293.5
    for label, val in (
        ("Tunggakan", money(b.get("TUNGGAKAN"))),
        ("Ansuran", money(b.get("ANSURAN"))),
        ("Jumlah Bil Semasa", money(b.get("JUMLAH_BIL_SEMASA"))),
        ("Penggenapan", money(b.get("PENGENAPAN"))),
    ):
        p.kv(t, label, val)
        t += LINE
    p.kv(t, "Jumlah Bil", money(b.get("JUMLAH_BIL")), bold=True)

    # Previous bill ----------------------------------------------------
    p.rule(372.2)
    p.txt(L, 379.7, "Bil Terdahulu", 11, True)
    p.kv(396.8, "Tarikh", text(b.get("BIL_DAHULU_TARIKH")))
    p.kv(408.3, "Amaun", money(b.get("BIL_DAHULU_AMAUN")))

    # Meter readings ---------------------------------------------------
    p.rule(440.4)
    p.txt(L, 447.9, "Bacaan Meter", 11, True)
    bottom = p.table(
        465.0,
        [L, 151.9, 285.9, 385.2],
        ["No Meter", "Tarikh", "Bacaan", "Penggunaan (m³)"],
        [
            [text(b.get("NO_METER")), text(b.get("TARIKH_SEMASA")),
             text(b.get("BACA_SEMASA")), text(b.get("PENGGUNAAN"))],
            ["", text(b.get("TARIKH_DAHULU")),
             text(b.get("BACA_DAHULU")), text(b.get("PENGGUNAAN_LAMA"))],
        ],
    )
    p.kv(bottom + 4, "Jumlah Penggunaan", text(b.get("JUMLAH_PENGGUNAAN")))

    # Period / tariff --------------------------------------------------
    p.rule(556.5)
    t = 564.0
    for label, val in (
        ("Tempoh Bil", text(b.get("TEMPOH_BIL"))),
        ("Prorata", text(b.get("PRORATA"))),
        ("Tarif", text(b.get("KETERANGAN_TARIF"))),
        ("Jenis Bacaan", text(b.get("JENIS_BACAAN"))),
    ):
        p.kv(t, label, val)
        t += LINE

    # Charges by block -------------------------------------------------
    p.rule(630.8)
    p.txt(L, 638.3, "Butiran Caj Mengikut Blok", 11, True)
    blocks = []
    n = 1
    while b.get(f"BLOK_{n}") is not None:
        blocks.append([
            text(b.get(f"BLOK_{n}")),
            text(b.get(f"M3_{n}")),
            text(b.get(f"KADAR_{n}")),
            money(b.get(f"AMAUN_{n}")),
        ])
        n += 1
    bottom = p.table(
        655.4, [L, 239.7, 355.6, 471.4],
        ["Blok Tarif (m³)", "Isipadu (m³)", "Kadar (RM)", "Amaun"],
        blocks or [["-", "-", "-", "-"]],
    )

    t = bottom + 10
    p.txt(L, t, "Penggunaan Air", 10, True)
    t += 15.9
    p.txt(L, t, "Isipadu (m³)", 9)
    p.txt(394.2, t, text(b.get("PENGGUNAAN_AIR_M3")), 9, right=True)
    p.txt(R, t, money(b.get("PENGGUNAAN_AIR_AMAUN")), 9, right=True)
    t += 18.4
    if _f(b.get("PELARASAN_BIL")):  # only when there is an adjustment
        p.kv(t, "Pelarasan Bil", money(b.get("PELARASAN_BIL")), size=9)
        t += 14
    p.kv(t, "Jumlah Caj Air Semasa", money(b.get("JUMLAH_CAJ_AIR_SEMASA")), bold=True)

    # Summary ----------------------------------------------------------
    t += 32.4
    p.rule(t)
    t += 7.5
    p.txt(L, t, "Keterangan", 10, True)
    t += 13.9
    p.kv(t, "Caj Air Semasa", money(b.get("JUMLAH_BIL")), bold=True)
    p.kv(t + 11.9, "Jumlah Bil Air Semasa", money(b.get("JUMLAH_BIL")), bold=True)

    c.showPage()
    c.save()
    data = buf.getvalue()
    if out:
        with open(out, "wb") as fh:
            fh.write(data)
    return data


