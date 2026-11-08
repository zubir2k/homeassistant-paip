<img src="https://raw.githubusercontent.com/zubir2k/homeassistant-paip/main/images/banner.png" width="450">

[![GitHub Repo stars](https://img.shields.io/github/stars/zubir2k/homeassistant-paip?style=social)](https://github.com/zubir2k/homeassistant-paip/stargazers)
[![hacs_badge](https://img.shields.io/badge/HACS-Integration-41BDF5.svg)](https://github.com/hacs/integration)
![GitHub all releases](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=Download%20Count&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.paip.total)
[![Buy](https://img.shields.io/badge/Belanja-Coffee-yellow.svg)](https://zubirco.de/buymecoffee)
[![GitHub Release](https://img.shields.io/github/release/zubir2k/homeassistant-paip.svg)](https://github.com/zubir2k/homeassistant-paip/releases/)

Unofficial Home Assistant integration for **Pengurusan Air Pahang Berhad (PAIP)** water accounts. It covers balance, bills, usage, meter readings and due dates for any number of accounts, and can generate a PDF of any bill.

PAIP closed its OnlinePay portal and now presents bills through the **PahangGo** app. This integration reads the same bill lookup the app uses, then fills in details from PAIP's new portal (`myairpahang.paip.com.my`). No login is needed: you only need the 10-digit account number (No Akaun) printed on the bill.

## Features

- **No login**: just the 10-digit account number. Add as many accounts as you like.
- **Bills and balance**: amount due, balance or credit, arrears, due date, last payment, and an overdue alert.
- **Usage**: m³ per bill, monthly average, meter reading, and the last 6 bills as attributes.
- **Energy dashboard ready**: bill history is imported as long-term statistics (`paip:<account>_water` and `paip:<account>_cost`).
- **Bill PDF**: `paip.generate_bill_pdf` recreates the PahangGo bill as a PDF ([details](#bill-pdf)).
- **Pay link**: a `payment_url` attribute for alerts with a *Bayar sekarang* button ([examples](#automation-examples)).

## Install

Works with Home Assistant 2024.12 or newer, and is ready for the built-in **Marketplace** in 2026.11.

[![Open your Home Assistant instance and open this repository in the Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zubir2k&repository=homeassistant-paip&category=integration)

**Marketplace (HA 2026.11+):** go to Settings → Marketplace → **Add from link**, enter `zubir2k/homeassistant-paip`, then **Install**. No restart is needed on first install.

**HACS (HA 2026.10 or older):** go to HACS → ⋮ → Custom repositories, add this repo as *Integration*, install **PAIP (Air Pahang)**, then restart.

**Manual:** copy `custom_components/paip` into `/config/custom_components/`, then restart.

Then add the integration. Enter the 10-digit account number; a nickname is optional.

[![Open your Home Assistant instance and start setting up PAIP.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=paip)

### Multiple accounts
All accounts live under one PAIP entry, with one device per account.
- To add one, run **Add integration → PAIP** again. It joins the existing entry. You can also use **PAIP → Configure → Add an account**.
- To remove accounts, use **PAIP → Configure → Remove accounts**.

## Entities (per account)

| Entity | Notes |
|---|---|
| Balance | Running balance in RM. Negative = in credit (as the app shows). Attributes include `payment_url` |
| Amount due | Balance floored at 0. Attributes: `due_date`, `payment_url` |
| Latest bill | Total of the latest bill. Attributes: bill no, dates, arrears, rounding, tariff blocks |
| Water charge | Water charge for the current bill period |
| Arrears | Tunggakan on the latest bill |
| Latest bill usage | m³ for the latest bill. Attributes: last 6 bills |
| Average monthly usage | Average over the bills returned (up to 6) |
| Meter reading | Latest meter reading (m³, total_increasing). Attributes: meter no, dates, reading type |
| Bill date / Due date | Dates |
| Last payment / Last payment date | Date is the newest seen by PAIP's portal. Amount comes from the bill history |
| Overdue (binary) | On when money is owed past the due date, or when there are arrears. Attributes: `amount_due_rm`, `due_date`, `arrears_rm`, `payment_url` |
| Account status (diagnostic) | Status, tariff, owner, address, disconnection and reconnection charges |
| Refresh (button) | Fetch now |

**Energy dashboard:** the integration imports long-term statistics `paip:<account>_water` (m³) and `paip:<account>_cost` (MYR). Each bill is spread evenly over its reading period, so per-bill totals match the bills exactly. Add `paip:<account>_water` under **Water consumption**.

Polling runs once a day. PAIP posts payments 1–3 days after you pay.

## Actions

- `paip.refresh`: refresh now (all entries, or the one you pick).
- `paip.generate_bill_pdf`: renders a bill as a PDF in the same layout as the PahangGo app and saves it to `/config/www/paip/bil_<account>_<bill>.pdf`, served at `/local/paip/...`. Give it `account_number`, plus `bill_number` (MMYYYY) for an older bill. It returns `path` and `url`.

### Bill PDF

`paip.generate_bill_pdf` draws a bill the way the PahangGo app does: the PAIP header, account holder name and premise address, meter readings, the tariff-block breakdown, arrears and the amount due. Everything comes from the bill data, so no login is needed.

| Field | Required | |
|---|---|---|
| `account_number` | yes | A 10-digit account that is already added to the integration |
| `bill_number` | no | `MMYYYY`, e.g. `102026`. Leave it out for the latest bill. |

The response:

```yaml
path: /config/www/paip/bil_0312345678_102026.pdf
url: /local/paip/bil_0312345678_102026.pdf
bill_number: "102026"
```

Run it from **Developer tools → Actions** (tick *Return response*), or in an automation. See [example 1](#1-new-bill-pdf-to-your-phone).

Notes:
- Only the **last six bills** are available, because that is all PAIP's data returns.
- Running it again for the same bill overwrites the file.
- The first run after a restart takes a second or two, because the PDF library loads on demand.
- ⚠️ Files in `/config/www` are served at `/local/` **without signing in**. Anyone who can reach your Home Assistant and guesses the filename can open the bill, including your name and address. Keep these links inside your home network, or delete the PDFs after use.
- Errors: *account not configured* (add the account first) or *bill not found* (the bill number isn't among the last six).

## Payment link

Every account has a pay page on PAIP's portal: `https://myairpahang.paip.com.my/payment/check/<account>`. It needs no login and takes FPX or card. It shows up in two places:

- The **Visit** link on the account's device page.
- The `payment_url` attribute on **Amount due**, **Balance** and **Overdue**, for automations and dashboards. See examples [1](#1-new-bill-pdf-to-your-phone)–[3](#3-overdue-alert).

Payments show up in PAIP's data 1–3 days after you pay, so **Amount due** may stay above 0 for a day or two afterwards.

## Automation examples

The examples use an account nicknamed **rumah**, so its entities are `sensor.paip_rumah_*`. Open your account's device page to find your own entity IDs, and swap `notify.mobile_app_your_phone` for your phone's notify action. `url` opens the link when you tap the notification on iOS, and `clickAction` does the same on Android.

### 1. New bill: PDF to your phone

When a new bill arrives, render it as a PDF and send it with an open-PDF button and a pay button.

```yaml
alias: PAIP new bill
triggers:
  - trigger: state
    entity_id: sensor.paip_rumah_bill_date
    not_from: [unknown, unavailable]   # don't fire on restart
actions:
  - action: paip.generate_bill_pdf
    data:
      account_number: "0312345678"
    response_variable: bill
  - action: notify.mobile_app_your_phone
    data:
      title: "Bil air PAIP {{ bill.bill_number }}"
      message: >-
        RM {{ states('sensor.paip_rumah_latest_bill') }},
        {{ states('sensor.paip_rumah_latest_bill_usage') }} m³.
        Jumlah perlu dibayar RM {{ states('sensor.paip_rumah_amount_due') }}
        sebelum {{ states('sensor.paip_rumah_due_date') }}.
      data:
        url: "{{ bill.url }}"
        clickAction: "{{ bill.url }}"
        actions:
          - action: URI
            title: Lihat bil
            uri: "{{ bill.url }}"
          - action: URI
            title: Bayar sekarang
            uri: "{{ state_attr('sensor.paip_rumah_amount_due', 'payment_url') }}"
```

### 2. Payment reminder with pay link

At 9 am, three days before the due date, if money is owed.

```yaml
alias: PAIP payment reminder
triggers:
  - trigger: time
    at: "09:00:00"
conditions:
  - condition: numeric_state
    entity_id: sensor.paip_rumah_amount_due
    above: 0
  - condition: template
    value_template: >-
      {% set due = states('sensor.paip_rumah_due_date') %}
      {{ due not in ['unknown', 'unavailable']
         and (strptime(due, '%Y-%m-%d').date() - now().date()).days == 3 }}
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "Bil air PAIP: RM {{ states('sensor.paip_rumah_amount_due') }}"
      message: "Bayar sebelum {{ states('sensor.paip_rumah_due_date') }}."
      data:
        url: "{{ state_attr('sensor.paip_rumah_amount_due', 'payment_url') }}"
        clickAction: "{{ state_attr('sensor.paip_rumah_amount_due', 'payment_url') }}"
        actions:
          - action: URI
            title: Bayar sekarang
            uri: "{{ state_attr('sensor.paip_rumah_amount_due', 'payment_url') }}"
```

### 3. Overdue alert

```yaml
alias: PAIP overdue
triggers:
  - trigger: state
    entity_id: binary_sensor.paip_rumah_overdue
    from: "off"
    to: "on"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "⚠️ Bil air PAIP tertunggak"
      message: >-
        RM {{ state_attr('binary_sensor.paip_rumah_overdue', 'amount_due_rm') }}
        lewat sejak {{ state_attr('binary_sensor.paip_rumah_overdue', 'due_date') }}.
        Elak caj pemotongan bekalan.
      data:
        url: "{{ state_attr('binary_sensor.paip_rumah_overdue', 'payment_url') }}"
        clickAction: "{{ state_attr('binary_sensor.paip_rumah_overdue', 'payment_url') }}"
        actions:
          - action: URI
            title: Bayar sekarang
            uri: "{{ state_attr('binary_sensor.paip_rumah_overdue', 'payment_url') }}"
```

### 4. Payment received

```yaml
alias: PAIP payment received
triggers:
  - trigger: state
    entity_id: sensor.paip_rumah_last_payment_date
    not_from: [unknown, unavailable]
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "Bayaran PAIP diterima"
      message: >-
        Bayaran pada {{ states('sensor.paip_rumah_last_payment_date') }}.
        Baki sekarang RM {{ states('sensor.paip_rumah_balance') }}.
```

### 5. Unusual usage (possible leak)

Alert when a bill's usage is more than 1.5× your average and above 5 m³.

```yaml
alias: PAIP high usage
triggers:
  - trigger: state
    entity_id: sensor.paip_rumah_latest_bill_usage
    not_from: [unknown, unavailable]
conditions:
  - condition: template
    value_template: >-
      {% set used = states('sensor.paip_rumah_latest_bill_usage') | float(0) %}
      {% set avg = states('sensor.paip_rumah_average_monthly_usage') | float(0) %}
      {{ used > 5 and avg > 0 and used > avg * 1.5 }}
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "💧 Penggunaan air luar biasa"
      message: >-
        {{ states('sensor.paip_rumah_latest_bill_usage') }} m³ bulan ini, berbanding purata
        {{ states('sensor.paip_rumah_average_monthly_usage') }} m³. Periksa kebocoran.
```

### 6. Dashboard card

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Air Pahang
    entities:
      - sensor.paip_rumah_amount_due
      - sensor.paip_rumah_due_date
      - sensor.paip_rumah_balance
      - sensor.paip_rumah_latest_bill
      - sensor.paip_rumah_latest_bill_usage
      - binary_sensor.paip_rumah_overdue
  - type: button
    name: Bayar bil air
    icon: mdi:cash-fast
    tap_action:
      action: url
      url_path: https://myairpahang.paip.com.my/payment/check/0312345678
```

Button cards can't template a URL, so paste your account's link. You can copy it from the `payment_url` attribute in **Developer tools → States**. For usage history, add a **Statistics graph** card with `paip:<account>_water`, or use the Energy dashboard.

## Removing

Go to Settings → Devices & services → PAIP → ⋮ → **Delete**. Then uninstall it from the Marketplace (or HACS). PDFs you generated stay in `/config/www/paip/` until you delete them.

## Privacy

The bill lookup is unauthenticated, so anyone with an account number can see the owner's name and address. Never post account numbers in public issues. Diagnostics downloads redact account numbers, names, addresses, meter and receipt numbers.

## Disclaimer

This is unofficial and not affiliated with PAIP or PahangGo. It uses undocumented endpoints that may change without notice.

## Join us

* Join the local community discussion at [Home Assistant Malaysia](https://www.facebook.com/groups/homeassistantmalaysia).
