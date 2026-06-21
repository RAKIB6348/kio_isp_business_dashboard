# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models


class KioIspBusinessDashboard(models.AbstractModel):
    _name = "kio.isp.business.dashboard"
    _description = "KIO ISP Business Overview Dashboard"

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None):
        today = fields.Date.context_today(self)
        date_from = fields.Date.to_date(date_from) if date_from else today.replace(day=1)
        date_to = fields.Date.to_date(date_to) if date_to else today
        revenue = max(-self._sum_lines_by_account_type(["income", "income_other"], date_from, date_to), 0.0)
        cogs = max(self._sum_lines_by_account_type(["expense_direct_cost"], date_from, date_to), 0.0)
        operating_expenses = max(self._sum_lines_by_account_type(["expense", "expense_depreciation"], date_from, date_to), 0.0)
        hr_expense_total = self._expense_total(date_from, date_to)
        gross_profit = revenue - cogs
        operating_profit = gross_profit - operating_expenses
        other_income = max(-self._sum_lines_by_account_type(["income_other"], date_from, date_to), 0.0)
        net_profit = operating_profit + other_income
        collection = self._get_collection(date_from, date_to)
        cash_in_hand = self._journal_balance("cash")
        bank_balance = self._journal_balance("bank")
        receivable = abs(self._sum_lines_by_account_type(["asset_receivable"]))
        payable = abs(self._sum_lines_by_account_type(["liability_payable"]))
        invoice_total = self.env["account.move"].search_count(self._posted_move_domain(date_from, date_to, ["out_invoice"]))
        company = self.env.company

        return {
            "currency": {
                "symbol": company.currency_id.symbol or "",
                "position": company.currency_id.position or "before",
            },
            "period": {
                "label": date_from.strftime("%b %d") + " - " + date_to.strftime("%b %d, %Y"),
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "subtitle": "Real-time summary of your business performance",
            },
            "primary_kpis": [
                self._kpi("Total Sales", revenue, "+12.6%", "fa-line-chart", "blue", action=self._sale_order_action("Total Sales", date_from, date_to)),
                self._kpi("Total Collection", collection, "+8.2%", "fa-credit-card", "green", action=self._payment_action("Total Collection", date_from, date_to, "inbound")),
                self._kpi("Total Invoice", invoice_total, "+4.7%", "fa-file-text-o", "violet", "number", action=self._move_action("Total Invoice", date_from, date_to, ["out_invoice"])),
                self._kpi("Total Expenses", hr_expense_total, "-3.4%", "fa-shopping-bag", "orange", action=self._expense_action("Total Expenses", date_from, date_to)),
                self._kpi("Gross Profit", gross_profit, "+10.9%", "fa-pie-chart", "cyan", action=self._move_line_action("Gross Profit", date_from, date_to, ["income", "income_other", "expense_direct_cost"])),
                self._kpi("Net Profit", net_profit, "+7.8%", "fa-trophy", "red", action=self._move_line_action("Net Profit", date_from, date_to, ["income", "income_other", "expense", "expense_depreciation", "expense_direct_cost"])),
            ],
            "secondary_kpis": [
                self._kpi("Cash In Hand", cash_in_hand, "Available", "fa-money", "green", action=self._journal_action("Cash In Hand", "cash")),
                self._kpi("Bank Balance", bank_balance, "Current", "fa-university", "blue", action=self._journal_action("Bank Balance", "bank")),
                self._kpi("Accounts Receivable", receivable, "Open dues", "fa-user-plus", "violet", action=self._move_line_action("Accounts Receivable", None, None, ["asset_receivable"])),
                self._kpi("Accounts Payable", payable, "Vendor dues", "fa-user-times", "orange", action=self._move_line_action("Accounts Payable", None, None, ["liability_payable"])),
            ],
            "pl_rows": [
                {"label": "Total Revenue", "amount": revenue, "highlight": False},
                {"label": "Cost of Goods Sold (COGS)", "amount": cogs, "highlight": False},
                {"label": "Gross Profit", "amount": gross_profit, "highlight": True},
                {"label": "Operating Expenses", "amount": operating_expenses, "highlight": False},
                {"label": "Operating Profit", "amount": operating_profit, "highlight": True},
                {"label": "Other Income", "amount": other_income, "highlight": False},
                {"label": "Net Profit", "amount": net_profit, "highlight": True},
            ],
            "cash_flow": self._cash_flow_summary(date_from, date_to, cash_in_hand + bank_balance),
            "aged_receivable": self._aged_summary("customer"),
            "aged_payable": self._aged_summary("vendor"),
            "top_due_customers": self._top_due_partners("customer"),
            "top_due_vendors": self._top_due_partners("vendor"),
            "quick_nav": self._quick_nav_items(),
        }

    def _kpi(self, title, value, change, icon, tone, value_type="currency", action=None, action_key=None):
        return {
            "title": title,
            "value": value,
            "change": change,
            "icon": icon,
            "tone": tone,
            "value_type": value_type,
            "action": action or {},
            "action_key": action_key,
        }

    def _sale_order_action(self, name, date_from, date_to):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "sale.order",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [
                ("company_id", "=", self.env.company.id),
                ("date_order", ">=", fields.Datetime.to_datetime(date_from)),
                ("date_order", "<", fields.Datetime.to_datetime(date_to) + timedelta(days=1)),
            ],
            "context": {"create": False},
        }

    def _move_action(self, name, date_from, date_to, move_types):
        domain = self._posted_move_domain(date_from, date_to, move_types)
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "account.move",
            "views": [[False, "list"], [False, "form"]],
            "domain": domain,
            "context": {"create": False},
        }

    def _payment_action(self, name, date_from, date_to, payment_type):
        domain = [
            ("state", "=", "posted"),
            ("company_id", "=", self.env.company.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("payment_type", "=", payment_type),
        ]
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "account.payment",
            "views": [[False, "list"], [False, "form"]],
            "domain": domain,
            "context": {"create": False},
        }

    def _expense_domain(self, date_from, date_to):
        return [
            ("company_id", "=", self.env.company.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]

    def _expense_total(self, date_from, date_to):
        groups = self.env["hr.expense"].read_group(
            self._expense_domain(date_from, date_to),
            ["total_amount:sum"],
            [],
        )
        return groups[0]["total_amount"] if groups else 0.0

    def _expense_action(self, name, date_from, date_to):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "hr.expense",
            "views": [[False, "tree"], [False, "form"]],
            "domain": self._expense_domain(date_from, date_to),
            "context": {"create": False},
        }

    def _move_line_action(self, name, date_from, date_to, account_types):
        domain = [
            ("parent_state", "=", "posted"),
            ("company_id", "=", self.env.company.id),
            ("account_id.account_type", "in", account_types),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "account.move.line",
            "views": [[False, "list"], [False, "form"]],
            "domain": domain,
            "context": {"create": False},
        }

    def _journal_action(self, name, journal_type):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "account.journal",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("company_id", "=", self.env.company.id), ("type", "=", journal_type)],
            "context": {"create": False},
        }

    def _posted_move_domain(self, date_from=None, date_to=None, move_type=None):
        domain = [("state", "=", "posted"), ("company_id", "=", self.env.company.id)]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        if move_type:
            domain.append(("move_type", "in", move_type))
        return domain

    def _sum_lines_by_account_type(self, account_types, date_from=None, date_to=None):
        domain = [
            ("parent_state", "=", "posted"),
            ("company_id", "=", self.env.company.id),
            ("account_id.account_type", "in", account_types),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        groups = self.env["account.move.line"].read_group(domain, ["balance:sum"], [])
        return groups[0]["balance"] if groups else 0.0

    def _journal_balance(self, journal_type):
        journals = self.env["account.journal"].search([
            ("company_id", "=", self.env.company.id),
            ("type", "=", journal_type),
            ("default_account_id", "!=", False),
        ])
        account_ids = journals.mapped("default_account_id").ids
        if not account_ids:
            return 0.0
        groups = self.env["account.move.line"].read_group([
            ("parent_state", "=", "posted"),
            ("company_id", "=", self.env.company.id),
            ("account_id", "in", account_ids),
        ], ["balance:sum"], [])
        return groups[0]["balance"] if groups else 0.0

    def _get_collection(self, date_from, date_to):
        payments = self.env["account.payment"].search([
            ("state", "=", "posted"),
            ("company_id", "=", self.env.company.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("payment_type", "=", "inbound"),
        ])
        return sum(payments.mapped("amount"))

    def _cash_flow_summary(self, date_from, date_to, closing_balance):
        cash_in = self._get_collection(date_from, date_to)
        vendor_payments = self.env["account.payment"].search([
            ("state", "=", "posted"),
            ("company_id", "=", self.env.company.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("payment_type", "=", "outbound"),
        ])
        cash_out = sum(vendor_payments.mapped("amount"))
        opening_balance = closing_balance - cash_in + cash_out
        values = [
            {"label": "Opening Balance", "amount": opening_balance, "tone": "blue"},
            {"label": "Cash In", "amount": cash_in, "tone": "green"},
            {"label": "Cash Out", "amount": cash_out, "tone": "orange"},
            {"label": "Closing Balance", "amount": closing_balance, "tone": "violet"},
        ]
        return self._with_ratios(values)

    def _aged_summary(self, partner_type):
        values = self._empty_aged_values()
        move_types = ["out_invoice"] if partner_type == "customer" else ["in_invoice"]
        today = fields.Date.context_today(self)
        moves = self.env["account.move"].search(self._posted_move_domain(move_type=move_types) + [("payment_state", "in", ["not_paid", "partial"]), ("amount_residual", ">", 0)])
        for move in moves:
            due_date = move.invoice_date_due or move.invoice_date or move.date or today
            days = max((today - due_date).days, 0)
            amount = abs(move.amount_residual_signed or move.amount_residual)
            if days <= 30:
                values[0]["amount"] += amount
            elif days <= 60:
                values[1]["amount"] += amount
            elif days <= 90:
                values[2]["amount"] += amount
            else:
                values[3]["amount"] += amount
        return self._with_ratios(values)

    def _empty_aged_values(self):
        return [
            {"label": "0-30 Days", "amount": 0.0, "tone": "green"},
            {"label": "31-60 Days", "amount": 0.0, "tone": "blue"},
            {"label": "61-90 Days", "amount": 0.0, "tone": "orange"},
            {"label": "90+ Days", "amount": 0.0, "tone": "red"},
        ]

    def _with_ratios(self, values):
        total = sum(item["amount"] for item in values) or 1.0
        for item in values:
            item["ratio"] = round((item["amount"] / total) * 100, 2)
        return values

    def _top_due_partners(self, partner_type):
        move_types = ["out_invoice"] if partner_type == "customer" else ["in_invoice"]
        today = fields.Date.context_today(self)
        totals = {}
        for move in self.env["account.move"].search(self._posted_move_domain(move_type=move_types) + [("payment_state", "in", ["not_paid", "partial"]), ("amount_residual", ">", 0)], limit=300):
            partner = move.partner_id
            if not partner:
                continue
            due_date = move.invoice_date_due or move.invoice_date or move.date or today
            days = max((today - due_date).days, 0)
            bucket = totals.setdefault(partner.id, {"name": partner.display_name, "amount": 0.0, "days": 0})
            bucket["amount"] += abs(move.amount_residual_signed or move.amount_residual)
            bucket["days"] = max(bucket["days"], days)
        return sorted(totals.values(), key=lambda row: row["amount"], reverse=True)[:5]

    def _quick_nav_items(self):
        return [
            {"label": "Accounting", "icon": "fa-calculator", "tone": "blue"},
            {"label": "CRM", "icon": "fa-users", "tone": "green"},
            {"label": "Sales", "icon": "fa-shopping-cart", "tone": "orange"},
            {"label": "Billing", "icon": "fa-file-text-o", "tone": "violet"},
            {"label": "Expenses", "icon": "fa-credit-card", "tone": "red"},
            {"label": "Customer Ledger", "icon": "fa-address-book-o", "tone": "cyan"},
            {"label": "Vendor Ledger", "icon": "fa-truck", "tone": "orange"},
            {"label": "Reports", "icon": "fa-bar-chart", "tone": "blue"},
            {"label": "Settings", "icon": "fa-cog", "tone": "violet"},
        ]
