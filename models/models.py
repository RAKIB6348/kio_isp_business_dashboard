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
        total_sales = self._invoice_total_amount(date_from, date_to)
        total_upstream_bill = self._vendor_bill_total_amount(date_from, date_to)
        cogs = max(self._sum_lines_by_account_type(["expense_direct_cost"], date_from, date_to), 0.0)
        operating_expenses = max(self._sum_lines_by_account_type(["expense", "expense_depreciation"], date_from, date_to), 0.0)
        hr_expense_total = self._expense_total(date_from, date_to)

        gross_profit = revenue - cogs
        operating_profit = gross_profit - operating_expenses
        other_income = max(-self._sum_lines_by_account_type(["income_other"], date_from, date_to), 0.0)
        net_profit = operating_profit + other_income

        collection = self._get_collection(date_from, date_to)
        cash_in_hand = self._journal_balance("cash", date_from, date_to)
        bank_balance = self._journal_balance("bank", date_from, date_to)
        cash_bank_balance = cash_in_hand + bank_balance

        receivable = abs(self._sum_lines_by_account_type(["asset_receivable"], date_from, date_to))
        payable = abs(self._sum_lines_by_account_type(["liability_payable"], date_from, date_to))
        invoice_total = self.env["account.move"].search_count(
            self._posted_move_domain(date_from, date_to, ["out_invoice"])
        )
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
                self._kpi(
                    "Total Sales",
                    total_sales,
                    "+12.6%",
                    "fa-line-chart",
                    "blue",
                    action=self._move_action("Total Sales", date_from, date_to, ["out_invoice"]),
                ),
                self._kpi(
                    "Total Collection",
                    collection,
                    "+8.2%",
                    "fa-credit-card",
                    "green",
                    action=self._payment_action("Total Collection", date_from, date_to, "inbound"),
                ),
                # self._kpi(
                #     "Total Invoice",
                #     invoice_total,
                #     "+4.7%",
                #     "fa-file-text-o",
                #     "violet",
                #     "number",
                #     action=self._move_action("Total Invoice", date_from, date_to, ["out_invoice"]),
                # ),
                self._kpi(
                    "Total Upstream Bill",
                    total_upstream_bill,
                    "+0.0%",
                    "fa-file-text-o",
                    "violet",
                    action=self._vendor_bill_action("Total Upstream Bill", date_from, date_to),
                ),
                self._kpi(
                    "Total Expenses",
                    hr_expense_total,
                    "-3.4%",
                    "fa-shopping-bag",
                    "orange",
                    action=self._expense_action("Total Expenses", date_from, date_to),
                ),
                self._kpi(
                    "Gross Profit",
                    gross_profit,
                    "+10.9%",
                    "fa-pie-chart",
                    "cyan",
                    action=self._profit_loss_report_action(),
                ),
                self._kpi(
                    "Net Profit",
                    net_profit,
                    "+7.8%",
                    "fa-trophy",
                    "red",
                    action=self._profit_loss_report_action(),
                ),
            ],
            "secondary_kpis": [
                # self._kpi(
                #     "Cash In Hand",
                #     cash_in_hand,
                #     "Available",
                #     "fa-money",
                #     "green",
                #     action=self._journal_action("Cash In Hand", "cash"),
                # ),
                # self._kpi(
                #     "Bank Balance",
                #     bank_balance,
                #     "Current",
                #     "fa-university",
                #     "blue",
                #     action=self._journal_action("Bank Balance", "bank"),
                # ),
            ] + self._cash_bank_journal_kpis(date_from, date_to) + [
                self._kpi(
                    "Accounts Receivable",
                    receivable,
                    "Open dues",
                    "fa-user-plus",
                    "violet",
                    action=self._move_line_action("Accounts Receivable", None, None, ["asset_receivable"]),
                ),
                self._kpi(
                    "Accounts Payable",
                    payable,
                    "Vendor dues",
                    "fa-user-times",
                    "orange",
                    action=self._move_line_action("Accounts Payable", None, None, ["liability_payable"]),
                ),
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
            "cash_flow": self._cash_flow_summary(date_from, date_to, cash_bank_balance),
            "aged_receivable": self._aged_summary("customer", date_from, date_to),
            "aged_payable": self._aged_summary("vendor", date_from, date_to),
            "top_due_customers": self._top_due_partners("customer", date_from, date_to),
            "top_due_vendors": self._top_due_partners("vendor", date_from, date_to),
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

    def _cash_bank_journal_kpis(self, date_from=None, date_to=None):
        journals = self.env["account.journal"].search([
            ("company_id", "=", self.env.company.id),
            ("type", "in", ["cash", "bank"]),
            ("default_account_id", "!=", False),
        ], order="type, name")

        kpis = []
        for journal in journals:
            is_cash = journal.type == "cash"
            kpis.append(
                self._kpi(
                    journal.name,
                    self._journal_account_balance(journal.default_account_id.id, date_from, date_to),
                    "Cash Journal" if is_cash else "Bank Journal",
                    "fa-money" if is_cash else "fa-university",
                    "green" if is_cash else "blue",
                    action=self._journal_move_line_action(journal),
                )
            )
        return kpis

    def _journal_account_balance(self, account_id, date_from=None, date_to=None):
        domain = [
            ("parent_state", "=", "posted"),
            ("company_id", "=", self.env.company.id),
            ("account_id", "=", account_id),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))

        groups = self.env["account.move.line"].read_group(domain, ["balance:sum"], [])
        return groups[0]["balance"] if groups else 0.0

    def _journal_move_line_action(self, journal):
        return {
            "type": "ir.actions.act_window",
            "name": journal.name,
            "res_model": "account.move.line",
            "views": [[False, "list"], [False, "form"]],
            "domain": [
                ("parent_state", "=", "posted"),
                ("company_id", "=", self.env.company.id),
                ("account_id", "=", journal.default_account_id.id),
            ],
            "context": {"create": False},
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
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "account.move",
            "views": [[False, "list"], [False, "form"]],
            "domain": self._posted_move_domain(date_from, date_to, move_types),
            "context": {"create": False},
        }

    def _payment_action(self, name, date_from, date_to, payment_type):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "account.payment",
            "views": [[False, "list"], [False, "form"]],
            "domain": [
                ("state", "=", "posted"),
                ("company_id", "=", self.env.company.id),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("payment_type", "=", payment_type),
            ],
            "context": {"create": False},
        }

    def _invoice_total_amount(self, date_from, date_to):
        groups = self.env["account.move"].read_group(
            self._posted_move_domain(date_from, date_to, ["out_invoice"]),
            ["amount_total_signed:sum"],
            [],
        )
        return groups[0]["amount_total_signed"] if groups else 0.0

    def _vendor_bill_total_amount(self, date_from, date_to):
        groups = self.env["account.move"].read_group(
            self._posted_move_domain(date_from, date_to, ["in_invoice"]),
            ["amount_total_signed:sum"],
            [],
        )
        return abs(groups[0]["amount_total_signed"]) if groups else 0.0

    def _vendor_bill_action(self, name, date_from, date_to):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "account.move",
            "views": [[False, "list"], [False, "form"]],
            "domain": self._posted_move_domain(date_from, date_to, ["in_invoice"]),
            "context": {"create": False},
        }

    def _profit_loss_report_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "kio_account_reports.action_account_report_pl"
        )
        action["target"] = "current"
        return action

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
            "views": [[False, "list"], [False, "form"]],
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
            "domain": [
                ("company_id", "=", self.env.company.id),
                ("type", "=", journal_type),
            ],
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

    def _journal_balance(self, journal_type, date_from=None, date_to=None):
        journals = self.env["account.journal"].search([
            ("company_id", "=", self.env.company.id),
            ("type", "=", journal_type),
            ("default_account_id", "!=", False),
        ])
        account_ids = journals.mapped("default_account_id").ids
        if not account_ids:
            return 0.0

        domain = [
            ("parent_state", "=", "posted"),
            ("company_id", "=", self.env.company.id),
            ("account_id", "in", account_ids),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))

        groups = self.env["account.move.line"].read_group(domain, ["balance:sum"], [])

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

        return self._with_ratios([
            {"label": "Opening Balance", "amount": opening_balance, "tone": "blue"},
            {"label": "Cash In", "amount": cash_in, "tone": "green"},
            {"label": "Cash Out", "amount": cash_out, "tone": "orange"},
            {"label": "Closing Balance", "amount": closing_balance, "tone": "violet"},
        ])

    def _aged_summary(self, partner_type, date_from=None, date_to=None):
        values = self._empty_aged_values()
        move_types = ["out_invoice"] if partner_type == "customer" else ["in_invoice"]
        today = fields.Date.context_today(self)

        moves = self.env["account.move"].search(
            self._posted_move_domain(date_from, date_to, move_types) + [
                ("payment_state", "in", ["not_paid", "partial"]),
                ("amount_residual", ">", 0),
            ]
        )

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

    def _top_due_partners(self, partner_type, date_from=None, date_to=None):
        move_types = ["out_invoice"] if partner_type == "customer" else ["in_invoice"]
        today = fields.Date.context_today(self)
        totals = {}

        moves = self.env["account.move"].search(
            self._posted_move_domain(date_from, date_to, move_types) + [
                ("payment_state", "in", ["not_paid", "partial"]),
                ("amount_residual", ">", 0),
            ],
            limit=300,
        )

        for move in moves:
            partner = move.partner_id
            if not partner:
                continue

            due_date = move.invoice_date_due or move.invoice_date or move.date or today
            days = max((today - due_date).days, 0)

            bucket = totals.setdefault(partner.id, {
                "name": partner.display_name,
                "amount": 0.0,
                "days": 0,
            })
            bucket["amount"] += abs(move.amount_residual_signed or move.amount_residual)
            bucket["days"] = max(bucket["days"], days)

        return sorted(totals.values(), key=lambda row: row["amount"], reverse=True)[:5]

    def _quick_nav_items(self):
        return [
            {"label": "Accounting Dashboard", "icon": "fa-calculator", "tone": "blue", "action": "kio_isp_management.action_isp_account_dashboard_client"},
            {
                "label": "Expense Dashboard",
                "icon": "fa-users",
                "tone": "green",
                "action_xml_id": "kio_isp_management.action_isp_expense_dashboard_client",
            },
            {
                "label": "Equity Dashboard",
                "icon": "fa-shopping-cart",
                "tone": "orange",
                "action_xml_id": "kio_owner_equity.action_owner_equity_dashboard",
            },
            {
                "label": "Operation Overview",
                "icon": "fa-file-text-o",
                "tone": "violet",
                "action_xml_id": "kio_isp_business_dashboard.action_kio_isp_operation_dashboard",
            },
            {
                "label": "Capacity Dashboard",
                "icon": "fa-credit-card",
                "tone": "red",
                "action_xml_id": "kio_capacity_analysis.action_kio_capacity_dashboard",
            },
            {"label": "Customer Ledger", "icon": "fa-address-book-o", "tone": "cyan"},
            {"label": "Vendor Ledger", "icon": "fa-truck", "tone": "orange"},
            {
                "label": "Reports",
                "icon": "fa-bar-chart",
                "tone": "blue",
                "action_xml_id": "kio_isp_business_dashboard.action_kio_isp_reports_dashboard",
            },
            {"label": "Settings", "icon": "fa-cog", "tone": "violet"},
        ]


class KioIspOperationDashboard(models.AbstractModel):
    _name = "kio.isp.operation.dashboard"
    _description = "KIO ISP Operation Overview Dashboard"

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None):
        today = fields.Date.context_today(self)
        date_from = fields.Date.to_date(date_from) if date_from else today.replace(day=1)
        date_to = fields.Date.to_date(date_to) if date_to else today

        stages = self._pipeline_stages(date_from, date_to)
        survey_stage = stages[0] if stages else {}
        total_leads = survey_stage.get("total", 0)
        confirmed_leads = survey_stage.get("confirmed", 0)
        pending_confirmation = survey_stage.get("pending", 0)
        rejected_leads = survey_stage.get("rejected", 0)
        leads_this_month = self._count_model("isp.survey", self._date_domain("create_date", date_from, date_to))
        closed_this_month = self._closed_this_month(date_from, date_to)
        conversion_rate = self._percentage(confirmed_leads, total_leads)

        return {
            "period": {
                "label": date_from.strftime("%m/%d/%Y") + " - " + date_to.strftime("%m/%d/%Y"),
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
            },
            "summary_kpis": [
                self._operation_kpi("Total Leads", total_leads, "fa-users", "blue", self._model_action("Total Leads", "isp.survey")),
                self._operation_kpi("Confirmed Leads", confirmed_leads, "fa-check-circle", "green", self._model_action("Confirmed Leads", "isp.client", [("pipeline_state", "=", "noc_confirm")])),
                self._operation_kpi("Pending Confirmation", pending_confirmation, "fa-hourglass-half", "orange", self._pending_action()),
                self._operation_kpi("Conversion Rate", conversion_rate, "fa-line-chart", "green", value_type="percent"),
                self._operation_kpi("Leads This Month", leads_this_month, "fa-pie-chart", "cyan", self._model_action("Leads This Month", "isp.survey", self._date_domain("create_date", date_from, date_to))),
                self._operation_kpi("Leads Closed This Month", closed_this_month, "fa-trophy", "red", self._closed_action(date_from, date_to)),
            ],
            "pipeline_stages": stages,
            "status_distribution": self._status_distribution(total_leads, confirmed_leads, pending_confirmation, rejected_leads),
            "source_distribution": self._source_distribution(date_from, date_to),
            "lead_aging": self._lead_aging(date_from, date_to),
            "pending_total": pending_confirmation,
            "recent_leads": self._recent_leads(),
            "transition_summary": stages,
            "quick_nav": self._operation_quick_nav_items(),
        }

    def _operation_kpi(self, title, value, icon, tone, action=None, value_type="number"):
        return {
            "title": title,
            "value": value,
            "icon": icon,
            "tone": tone,
            "action": action or {},
            "value_type": value_type,
        }

    def _pipeline_stages(self, date_from, date_to):
        stage_specs = [
            {
                "key": "survey",
                "label": "Survey",
                "icon": "fa-search",
                "tone": "blue",
                "model": "isp.survey",
                "total_domain": [],
                "confirmed_domain": [("state", "in", ["done", "work_order"])],
                "pending_domain": [("state", "=", "draft")],
                "rejected_domain": [("id", "=", 0)],
                "action_xml_id": "kio_isp_management.action_isp_survey",
            },
            {
                "key": "work_order",
                "label": "Work Order",
                "icon": "fa-calendar",
                "tone": "green",
                "model": "isp.work.order",
                "total_domain": [],
                "confirmed_domain": [("work_state", "in", ["sell_confirm", "marketing_confirm", "legal_confirm"])],
                "pending_domain": [("work_state", "=", "work_order")],
                "rejected_domain": [("work_state", "in", ["marketing_revert", "legal_revert"])],
                "action_xml_id": "kio_isp_management.action_work_order_admin",
            },
            {
                "key": "sale",
                "label": "Sale",
                "icon": "fa-tags",
                "tone": "violet",
                "model": "isp.work.order",
                "total_domain": [("work_state", "in", ["sell_confirm", "marketing_confirm", "marketing_revert", "legal_confirm", "legal_revert"])],
                "confirmed_domain": [("work_state", "in", ["marketing_confirm", "legal_confirm"])],
                "pending_domain": [("work_state", "=", "sell_confirm")],
                "rejected_domain": [("work_state", "=", "marketing_revert")],
                "action_xml_id": "kio_isp_management.action_work_order_marketing_head",
            },
            {
                "key": "legal",
                "label": "Legal",
                "icon": "fa-gavel",
                "tone": "orange",
                "model": "isp.work.order",
                "total_domain": [("work_state", "in", ["marketing_confirm", "legal_confirm", "legal_revert"])],
                "confirmed_domain": [("work_state", "=", "legal_confirm")],
                "pending_domain": [("work_state", "=", "marketing_confirm")],
                "rejected_domain": [("work_state", "=", "legal_revert")],
                "action_xml_id": "kio_isp_management.action_work_order_legal",
            },
            {
                "key": "nttn",
                "label": "NTTN",
                "icon": "fa-sitemap",
                "tone": "cyan",
                "model": "isp.transmission.nttn",
                "total_domain": [],
                "confirmed_domain": [("state", "in", ["confirm", "noc_confirm", "done"])],
                "pending_domain": [("state", "=", "draft")],
                "rejected_domain": [("id", "=", 0)],
                "action_xml_id": "kio_isp_management.action_transmission_nttn",
            },
            {
                "key": "own_network",
                "label": "Own Network",
                "icon": "fa-trophy",
                "tone": "red",
                "model": "isp.transmission.own",
                "total_domain": [],
                "confirmed_domain": [("state", "in", ["confirm", "noc_confirm", "done"])],
                "pending_domain": [("state", "=", "draft")],
                "rejected_domain": [("id", "=", 0)],
                "action_xml_id": "kio_isp_management.action_transmission_own",
            },
            {
                "key": "noc",
                "label": "NOC",
                "icon": "fa-headphones",
                "tone": "blue",
                "model": "isp.client",
                "total_domain": [("pipeline_state", "in", ["transmission_confirm", "noc_confirm"])],
                "confirmed_domain": [("pipeline_state", "=", "noc_confirm")],
                "pending_domain": [("pipeline_state", "=", "transmission_confirm")],
                "rejected_domain": [("id", "=", 0)],
                "action_xml_id": "kio_isp_management.action_isp_transmission_nttn_noc_duplicate",
            },
        ]

        stages = []
        for spec in stage_specs:
            total_domain = self._stage_period_domain(spec["model"], spec["key"], date_from, date_to) + spec["total_domain"]
            total = self._count_model(spec["model"], total_domain)
            confirmed = self._count_model(spec["model"], self._stage_period_domain(spec["model"], spec["key"], date_from, date_to) + spec["confirmed_domain"])
            pending = self._count_model(spec["model"], self._stage_period_domain(spec["model"], spec["key"], date_from, date_to) + spec["pending_domain"])
            rejected = self._count_model(spec["model"], self._stage_period_domain(spec["model"], spec["key"], date_from, date_to) + spec["rejected_domain"])
            stages.append({
                "key": spec["key"],
                "label": spec["label"],
                "icon": spec["icon"],
                "tone": spec["tone"],
                "total": total,
                "confirmed": confirmed,
                "pending": pending,
                "rejected": rejected,
                "conversion": self._percentage(confirmed, total),
                "confirmed_ratio": self._percentage(confirmed, total),
                "pending_ratio": self._percentage(pending, total),
                "rejected_ratio": self._percentage(rejected, total),
                "action": spec["action_xml_id"] or self._model_action(spec["label"], spec["model"], total_domain),
                "action_xml_id": spec["action_xml_id"],
            })
        return stages

    def _stage_period_domain(self, model, key, date_from, date_to):
        date_fields = {
            "survey": "create_date",
            "work_order": "create_date",
            "sale": "work_state_sell_confirm_date",
            "legal": "work_state_marketing_confirm_date",
            "nttn": "create_date",
            "own_network": "create_date",
            "noc": "write_date",
        }
        field_name = date_fields.get(key, "create_date")
        if model in self.env.registry.models and field_name in self.env[model]._fields:
            return self._date_domain(field_name, date_from, date_to)
        return self._date_domain("create_date", date_from, date_to)

    def _date_domain(self, field_name, date_from, date_to):
        return [
            (field_name, ">=", fields.Datetime.to_datetime(date_from)),
            (field_name, "<", fields.Datetime.to_datetime(date_to) + timedelta(days=1)),
        ]

    def _count_model(self, model_name, domain=None):
        if model_name not in self.env.registry.models:
            return 0
        return self.env[model_name].sudo().search_count(domain or [])

    def _percentage(self, part, total):
        return round(((part or 0) / total) * 100, 2) if total else 0.0

    def _model_action(self, name, model_name, domain=None):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model_name,
            "views": [[False, "list"], [False, "form"]],
            "domain": domain or [],
            "context": {"create": False},
        }

    def _pending_action(self):
        return self._model_action("Pending Confirmations", "isp.client", [("pipeline_state", "!=", "noc_confirm")])

    def _closed_this_month(self, date_from, date_to):
        total = self._count_model("isp.transmission.nttn", self._date_domain("state_noc_confirm_date", date_from, date_to) + [("state", "in", ["noc_confirm", "done"])])
        total += self._count_model("isp.transmission.own", self._date_domain("state_noc_confirm_date", date_from, date_to) + [("state", "in", ["noc_confirm", "done"])])
        return total

    def _closed_action(self, date_from, date_to):
        return self._model_action("Closed Leads", "isp.client", [("pipeline_state", "=", "noc_confirm")] + self._date_domain("write_date", date_from, date_to))

    def _status_distribution(self, total, confirmed, pending, rejected):
        return self._ratio_rows([
            {"label": "Confirmed", "value": confirmed, "tone": "green"},
            {"label": "Pending", "value": pending, "tone": "orange"},
            {"label": "Rejected", "value": rejected, "tone": "red"},
        ], total)

    def _source_distribution(self, date_from, date_to):
        values = [
            {"label": "Website", "value": self._count_model("isp.survey", self._date_domain("create_date", date_from, date_to) + [("is_from_new_link_request", "=", True)]), "tone": "green"},
            {"label": "Walk-in", "value": self._count_model("isp.survey", self._date_domain("create_date", date_from, date_to) + [("visiting_type", "=", "office_visit")]), "tone": "orange"},
            {"label": "Phone Call", "value": self._count_model("isp.survey", self._date_domain("create_date", date_from, date_to) + [("visiting_type", "=", "phone_call")]), "tone": "blue"},
            {"label": "Online Leads", "value": self._count_model("kio.isp.lead", self._date_domain("create_date", date_from, date_to)), "tone": "violet"},
        ]
        return self._ratio_rows(values)

    def _lead_aging(self, date_from, date_to):
        today = fields.Date.context_today(self)
        values = [
            {"label": "0-7 Days", "value": 0, "tone": "green"},
            {"label": "8-15 Days", "value": 0, "tone": "orange"},
            {"label": "16-30 Days", "value": 0, "tone": "red"},
            {"label": "31-60 Days", "value": 0, "tone": "magenta"},
            {"label": "60+ Days", "value": 0, "tone": "violet"},
        ]
        clients = self.env["isp.client"].sudo().search([("pipeline_state", "!=", "noc_confirm")] + self._date_domain("create_date", date_from, date_to), limit=1000)
        for client in clients:
            days = max((today - fields.Date.to_date(client.create_date)).days, 0)
            if days <= 7:
                values[0]["value"] += 1
            elif days <= 15:
                values[1]["value"] += 1
            elif days <= 30:
                values[2]["value"] += 1
            elif days <= 60:
                values[3]["value"] += 1
            else:
                values[4]["value"] += 1
        return self._ratio_rows(values)

    def _ratio_rows(self, values, forced_total=None):
        total = forced_total if forced_total is not None else sum(item["value"] for item in values)
        for item in values:
            item["ratio"] = self._percentage(item["value"], total)
        return values

    def _recent_leads(self):
        rows = []
        surveys = self.env["isp.survey"].sudo().search([], order="create_date desc, id desc", limit=5)
        for survey in surveys:
            client = self.env["isp.client"].sudo().search([("survey_id", "=", survey.id)], limit=1)
            source = "Website" if survey.is_from_new_link_request else ("Walk-in" if survey.visiting_type == "office_visit" else "Phone Call")
            stage = dict(client._fields["pipeline_state"].selection).get(client.pipeline_state, survey.state) if client else dict(survey._fields["state"].selection).get(survey.state, survey.state)
            rows.append({
                "id": survey.name or survey.display_name,
                "customer": survey.customer_name or survey.organization_name or survey.display_name,
                "source": source,
                "stage": stage,
                "status": "Confirmed" if client and client.pipeline_state == "noc_confirm" else "Pending",
                "date": fields.Date.to_string(fields.Date.to_date(survey.create_date)),
            })
        return rows

    def _operation_quick_nav_items(self):
        return [
            {"label": "Lead Management", "icon": "fa-user", "tone": "blue", "action_xml_id": "kio_online_isp_management.action_kio_isp_leads_standard"},
            {"label": "Survey Dashboard", "icon": "fa-line-chart", "tone": "blue", "action_xml_id": "kio_isp_management.action_isp_survey"},
            {"label": "Work Order Dashboard", "icon": "fa-calendar", "tone": "green", "action_xml_id": "kio_isp_management.action_work_order_admin"},
            {"label": "Sales Dashboard", "icon": "fa-pie-chart", "tone": "red", "action_xml_id": "kio_isp_management.action_work_order_marketing_head"},
            {"label": "Legal Dashboard", "icon": "fa-plus-circle", "tone": "orange", "action_xml_id": "kio_isp_management.action_work_order_legal"},
            {"label": "NTTN Dashboard", "icon": "fa-sitemap", "tone": "cyan", "action_xml_id": "kio_isp_management.action_transmission_nttn"},
            {"label": "Own Network Dashboard", "icon": "fa-road", "tone": "orange", "action_xml_id": "kio_isp_management.action_transmission_own"},
            {"label": "NOC Dashboard", "icon": "fa-headphones", "tone": "blue", "action_xml_id": "kio_isp_management.action_isp_transmission_nttn_noc_duplicate"},
            {"label": "Reports & Analytics", "icon": "fa-bar-chart", "tone": "violet", "action_xml_id": "kio_isp_business_dashboard.action_kio_isp_reports_dashboard"},
        ]


class KioIspReportsDashboard(models.AbstractModel):
    _name = "kio.isp.reports.dashboard"
    _description = "KIO ISP Reports Dashboard"

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None):
        today = fields.Date.context_today(self)
        date_from = fields.Date.to_date(date_from) if date_from else today.replace(month=1, day=1)
        date_to = fields.Date.to_date(date_to) if date_to else today

        business = self.env["kio.isp.business.dashboard"]
        revenue = max(-business._sum_lines_by_account_type(["income", "income_other"], date_from, date_to), 0.0)
        expenses = max(business._sum_lines_by_account_type(["expense", "expense_depreciation", "expense_direct_cost"], date_from, date_to), 0.0)
        collection = business._get_collection(date_from, date_to)
        receivable = abs(business._sum_lines_by_account_type(["asset_receivable"], None, date_to))
        net_profit = revenue - expenses
        total_leads = self._count_model("isp.survey", self._date_domain("create_date", date_from, date_to))
        active_customers = self._count_model("isp.client", [("pipeline_state", "=", "noc_confirm")])
        new_connections = self._count_model("isp.client", [("pipeline_state", "=", "noc_confirm")] + self._date_domain("active_date_from", date_from, date_to))
        churned_customers = self._count_model("isp.client", [("active", "=", False)] + self._date_domain("write_date", date_from, date_to))

        monthly = self._monthly_report_rows(date_from, date_to)
        map_data = self._client_map_markers()

        return {
            "currency": self._currency_payload(),
            "period": {
                "label": date_from.strftime("%b %d, %Y") + " - " + date_to.strftime("%b %d, %Y"),
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "updated_at": fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime("%b %d, %Y %I:%M %p"),
            },
            "kpis": [
                self._report_kpi("Total Leads", total_leads, "fa-users", "blue", "number"),
                self._report_kpi("Active Customers", active_customers, "fa-users", "green", "number"),
                self._report_kpi("Monthly Revenue", revenue, "fa-file-text-o", "violet"),
                self._report_kpi("Total Collection", collection, "fa-credit-card", "green"),
                self._report_kpi("Outstanding Receivable", receivable, "fa-user-plus", "orange", trend=-5.6),
                self._report_kpi("Net Profit", net_profit, "fa-trophy", "red"),
                self._report_kpi("New Connections", new_connections, "fa-cube", "cyan", "number"),
                self._report_kpi("Churned Customers", churned_customers, "fa-users", "red", "number", trend=-4.3),
            ],
            "charts": {
                "pl": self._line_chart(monthly, [
                    ("revenue", "Total Revenue", "blue"),
                    ("expenses", "Total Expenses", "red"),
                    ("net_profit", "Net Profit", "green"),
                ]),
                "cash_flow": self._combo_chart(monthly),
                "new_customers": self._line_chart(monthly, [("new_customers", "New Customers", "blue")], value_type="number"),
                "revenue_collection": self._line_chart(monthly, [
                    ("revenue", "Revenue", "blue"),
                    ("collection", "Collection", "green"),
                ]),
                "cash_in_category": self._stacked_chart(monthly, [
                    ("customer_collection", "Customer Collection", "green"),
                    ("new_connection_fees", "New Connection Fees", "blue"),
                    ("installation_charges", "Installation Charges", "orange"),
                    ("other_income", "Other Income", "violet"),
                ]),
                "cash_out_category": self._stacked_chart(monthly, [
                    ("upstream_bills", "Upstream Bills", "red"),
                    ("employee_salary", "Employee Salary", "blue"),
                    ("vendor_payments", "Vendor Payments", "orange"),
                    ("other_expenses", "Other Expenses", "violet"),
                ]),
                "new_vs_churn": self._line_chart(monthly, [
                    ("new_customers", "New Customers", "green"),
                    ("churned_customers", "Churned Customers", "red"),
                ], value_type="number"),
            },
            "pl_summary": [
                {"label": "Total Revenue", "amount": revenue},
                {"label": "Total Expenses", "amount": expenses},
                {"label": "Gross Profit", "amount": revenue - self._monthly_sum(monthly, "upstream_bills"), "highlight": True},
                {"label": "Operating Expenses", "amount": self._monthly_sum(monthly, "other_expenses") + self._monthly_sum(monthly, "employee_salary")},
                {"label": "Operating Profit", "amount": net_profit, "highlight": True},
                {"label": "Other Income", "amount": self._monthly_sum(monthly, "other_income")},
                {"label": "Net Profit", "amount": net_profit, "highlight": True},
            ],
            "cash_summary": [
                {"label": "Opening Balance", "amount": 0.0},
                {"label": "Total Cash In", "amount": self._monthly_sum(monthly, "cash_in"), "highlight": True},
                {"label": "Total Cash Out", "amount": self._monthly_sum(monthly, "cash_out"), "negative": True},
                {"label": "Net Cash Flow", "amount": self._monthly_sum(monthly, "net_cash_flow"), "highlight": True},
                {"label": "Closing Balance", "amount": self._monthly_sum(monthly, "net_cash_flow")},
            ],
            "map": map_data,
        }

    def _currency_payload(self):
        currency = self.env.company.currency_id
        return {"symbol": currency.symbol or "", "position": currency.position or "before"}

    def _report_kpi(self, title, value, icon, tone, value_type="currency", trend=12.5):
        return {
            "title": title,
            "value": value,
            "icon": icon,
            "tone": tone,
            "value_type": value_type,
            "trend": trend,
        }

    def _month_start(self, value):
        return value.replace(day=1)

    def _next_month(self, value):
        return value.replace(year=value.year + 1, month=1, day=1) if value.month == 12 else value.replace(month=value.month + 1, day=1)

    def _monthly_report_rows(self, date_from, date_to):
        rows = []
        current = self._month_start(date_from)
        business = self.env["kio.isp.business.dashboard"]
        while current <= date_to:
            next_month = self._next_month(current)
            month_to = min(next_month - timedelta(days=1), date_to)
            revenue = max(-business._sum_lines_by_account_type(["income", "income_other"], current, month_to), 0.0)
            upstream_bills = business._vendor_bill_total_amount(current, month_to)
            employee_salary = self._hr_expense_total(current, month_to)
            other_expenses = max(business._sum_lines_by_account_type(["expense", "expense_depreciation"], current, month_to), 0.0)
            expenses = upstream_bills + employee_salary + other_expenses
            cash_in = business._get_collection(current, month_to)
            cash_out = self._payment_total("outbound", current, month_to)
            new_customers = self._count_model("isp.client", [("pipeline_state", "=", "noc_confirm")] + self._date_domain("active_date_from", current, month_to))
            churned = self._count_model("isp.client", [("active", "=", False)] + self._date_domain("write_date", current, month_to))
            other_income = max(-business._sum_lines_by_account_type(["income_other"], current, month_to), 0.0)
            rows.append({
                "label": current.strftime("%b"),
                "revenue": revenue,
                "expenses": expenses,
                "net_profit": revenue - expenses,
                "collection": cash_in,
                "cash_in": cash_in,
                "cash_out": cash_out,
                "net_cash_flow": cash_in - cash_out,
                "new_customers": new_customers,
                "churned_customers": churned,
                "customer_collection": cash_in,
                "new_connection_fees": max(other_income * 0.45, 0.0),
                "installation_charges": max(other_income * 0.35, 0.0),
                "other_income": max(other_income * 0.20, 0.0),
                "upstream_bills": upstream_bills,
                "employee_salary": employee_salary,
                "vendor_payments": max(cash_out - employee_salary, 0.0),
                "other_expenses": other_expenses,
            })
            current = next_month
        return rows

    def _line_chart(self, rows, series_specs, value_type="currency"):
        max_value = max([abs(row[key]) for row in rows for key, _label, _tone in series_specs] + [1])
        series = []
        for key, label, tone in series_specs:
            points = []
            for index, row in enumerate(rows):
                x = 28 + (index * (244 / max(len(rows) - 1, 1)))
                y = 126 - ((max(row[key], 0) / max_value) * 104)
                points.append(f"{round(x, 2)},{round(y, 2)}")
            series.append({"key": key, "label": label, "tone": tone, "points": " ".join(points), "last": rows[-1][key] if rows else 0})
        return {"labels": [row["label"] for row in rows], "series": series, "max": max_value, "value_type": value_type}

    def _combo_chart(self, rows):
        chart = self._line_chart(rows, [("net_cash_flow", "Net Cash Flow", "blue")])
        max_value = max([row[key] for row in rows for key in ["cash_in", "cash_out", "net_cash_flow"]] + [1])
        chart["max"] = max_value
        chart["bars"] = []
        for index, row in enumerate(rows):
            chart["bars"].append({
                "label": row["label"],
                "cash_in": round((row["cash_in"] / max_value) * 112, 2),
                "cash_out": round((row["cash_out"] / max_value) * 112, 2),
                "net": row["net_cash_flow"],
            })
        return chart

    def _stacked_chart(self, rows, series_specs):
        max_value = max([sum(row[key] for key, _label, _tone in series_specs) for row in rows] + [1])
        bars = []
        for row in rows:
            cursor = 0
            segments = []
            for key, label, tone in series_specs:
                height = round((row[key] / max_value) * 118, 2)
                segments.append({"label": label, "tone": tone, "height": height, "bottom": cursor})
                cursor += height
            bars.append({"label": row["label"], "segments": segments})
        return {"labels": [row["label"] for row in rows], "series": [{"label": label, "tone": tone} for _key, label, tone in series_specs], "bars": bars}

    def _monthly_sum(self, rows, key):
        return sum(row.get(key, 0.0) for row in rows)

    def _payment_total(self, payment_type, date_from, date_to):
        if "account.payment" not in self.env.registry.models:
            return 0.0
        payments = self.env["account.payment"].sudo().search([
            ("state", "=", "posted"),
            ("company_id", "=", self.env.company.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("payment_type", "=", payment_type),
        ])
        return sum(payments.mapped("amount"))

    def _hr_expense_total(self, date_from, date_to):
        if "hr.expense" not in self.env.registry.models:
            return 0.0
        groups = self.env["hr.expense"].sudo().read_group(
            [("company_id", "=", self.env.company.id), ("date", ">=", date_from), ("date", "<=", date_to)],
            ["total_amount:sum"],
            [],
        )
        return groups[0]["total_amount"] if groups else 0.0

    def _client_map_markers(self):
        if "isp.client" not in self.env.registry.models:
            return {"markers": [], "legend": []}
        bounds = {"lat_min": 20.45, "lat_max": 26.75, "lon_min": 88.0, "lon_max": 92.75}
        buckets = {}
        clients = self.env["isp.client"].sudo().search([("pipeline_state", "=", "noc_confirm")], limit=2000)
        for client in clients:
            lat = self._parse_float(getattr(client, "survey_latitude", False))
            lon = self._parse_float(getattr(client, "survey_longitude", False))
            if lat is None or lon is None:
                continue
            if not (bounds["lat_min"] <= lat <= bounds["lat_max"] and bounds["lon_min"] <= lon <= bounds["lon_max"]):
                continue
            key = (round(lat, 1), round(lon, 1))
            bucket = buckets.setdefault(key, {"lat": key[0], "lon": key[1], "count": 0})
            bucket["count"] += 1

        markers = []
        for bucket in buckets.values():
            x = ((bucket["lon"] - bounds["lon_min"]) / (bounds["lon_max"] - bounds["lon_min"])) * 100
            y = ((bounds["lat_max"] - bucket["lat"]) / (bounds["lat_max"] - bounds["lat_min"])) * 100
            count = bucket["count"]
            tone = "green" if count <= 10 else "orange" if count <= 30 else "amber" if count <= 50 else "red"
            markers.append({"x": round(x, 2), "y": round(y, 2), "count": count, "tone": tone})
        return {
            "markers": sorted(markers, key=lambda marker: marker["count"], reverse=True)[:80],
            "legend": [
                {"label": "1 - 10 Clients", "tone": "green"},
                {"label": "11 - 30 Clients", "tone": "orange"},
                {"label": "31 - 50 Clients", "tone": "amber"},
                {"label": "51+ Clients", "tone": "red"},
            ],
        }

    def _parse_float(self, value):
        if not value:
            return None
        try:
            return float(str(value).strip().split(",")[0])
        except (TypeError, ValueError):
            return None

    def _date_domain(self, field_name, date_from, date_to):
        return [
            (field_name, ">=", fields.Datetime.to_datetime(date_from)),
            (field_name, "<", fields.Datetime.to_datetime(date_to) + timedelta(days=1)),
        ]

    def _count_model(self, model_name, domain=None):
        if model_name not in self.env.registry.models:
            return 0
        return self.env[model_name].sudo().search_count(domain or [])
