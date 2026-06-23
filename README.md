# KIO ISP Business Dashboard

KIO ISP Business Dashboard is a custom Odoo 17 dashboard module for ISP business monitoring. It provides a centralized Business Overview screen with financial KPIs, receivable/payable summaries, cash flow analysis, profit and loss summary, and quick navigation to related dashboards.

## Features

* Business Overview client action dashboard
* Date range filter with browser local storage
* Total Sales KPI
* Total Collection KPI
* Total Upstream Bill KPI
* Total Expenses KPI
* Gross Profit and Net Profit KPI
* Dynamic Cash and Bank journal KPI cards
* Accounts Receivable and Accounts Payable summary
* Aged Receivable donut chart
* Aged Payable donut chart
* Top Due Customers table
* Top Due Vendors table
* Profit & Loss summary
* Cash Flow summary
* Quick Navigation cards
* Responsive dashboard UI
* Hidden Odoo control panel for clean dashboard view

## Dashboard Menu

The module adds a main menu:

* **Business Overview**

This menu opens the OWL client action:

```xml
kio_isp_business_dashboard.business_overview
```

## Technical Details

### Backend Model

Main backend abstract model:

```python
kio.isp.business.dashboard
```

Main method:

```python
get_dashboard_data(date_from=None, date_to=None)
```

This method prepares all dashboard data including:

* Currency information
* Reporting period
* Primary KPIs
* Secondary KPIs
* Profit & Loss rows
* Cash Flow summary
* Aged Receivable
* Aged Payable
* Top Due Customers
* Top Due Vendors
* Quick Navigation items

## Frontend Components

Main OWL component:

```javascript
BusinessOverviewDashboard
```

Registered action tag:

```javascript
kio_isp_business_dashboard.business_overview
```

Template:

```xml
kio_isp_business_dashboard.BusinessOverviewDashboard
```

## UI Sections

The dashboard contains:

1. Header with date filter
2. Primary KPI cards
3. Secondary KPI cards with horizontal scroll
4. Aged Receivable panel
5. Top Due Customers table
6. Aged Payable panel
7. Top Due Vendors table
8. Profit & Loss summary
9. Cash Flow summary
10. Quick Navigation panel

## Module Structure

```text
kio_isp_business_dashboard/
├── controllers/
├── demo/
├── models/
├── security/
├── static/
│   └── src/
├── views/
├── __init__.py
├── __manifest__.py
└── README.md
```

## Dependencies

This module commonly depends on:

* base
* web
* account
* mail
* hr_expense
* kio_account_reports
* kio_isp_management
* kio_capacity_analysis
* kio_owner_equity

Check `__manifest__.py` for the final dependency list.

## Installation

1. Place the module inside your Odoo custom addons path.

```bash
custom_addons/new_layer3/kio_isp_business_dashboard
```

2. Restart Odoo.

```bash
sudo systemctl restart odoo17
```

Or run manually:

```bash
./odoo-bin -c odoo.conf
```

3. Update Apps List.

4. Install **KIO ISP Business Dashboard**.

## Upgrade Command

```bash
./odoo-bin -c odoo.conf -d your_database_name -u kio_isp_business_dashboard
```

## Usage

Go to:

```text
Business Overview
```

Then select a date range and click **Apply** to reload dashboard data. Click KPI cards or dashboard panels to open related records or reports.

## Author

**Kendroo Limited**

## License

LGPL-3
