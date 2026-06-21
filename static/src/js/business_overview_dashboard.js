/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class BusinessOverviewDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: {},
            dateFrom: null,
            dateTo: null,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        const args = this.state.dateFrom && this.state.dateTo ? [this.state.dateFrom, this.state.dateTo] : [];
        this.state.data = await this.orm.call("kio.isp.business.dashboard", "get_dashboard_data", args);
        this.state.dateFrom = this.state.data.period.date_from;
        this.state.dateTo = this.state.data.period.date_to;
        this.state.loading = false;
    }

    updateDateFrom(ev) {
        this.state.dateFrom = ev.target.value;
    }

    updateDateTo(ev) {
        this.state.dateTo = ev.target.value;
    }

    async applyDateRange() {
        if (!this.state.dateFrom || !this.state.dateTo) {
            return;
        }
        if (this.state.dateFrom > this.state.dateTo) {
            const dateFrom = this.state.dateFrom;
            this.state.dateFrom = this.state.dateTo;
            this.state.dateTo = dateFrom;
        }
        await this.loadDashboardData();
    }

    formatCurrency(amount) {
        const currency = this.state.data.currency || {};
        const value = Math.abs(amount || 0).toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
        const formatted = currency.position === "after" ? `${value} ${currency.symbol || ""}` : `${currency.symbol || ""} ${value}`;
        return amount < 0 ? `-${formatted}` : formatted.trim();
    }

    formatMetric(item) {
        if (item.value_type === "number") {
            return (item.value || 0).toLocaleString();
        }
        return this.formatCurrency(item.value);
    }

    formatPercent(value) {
        return `${Math.round(value || 0)}%`;
    }

    donutStyle(items) {
        const colors = {
            blue: "#2563eb",
            green: "#16a34a",
            orange: "#f59e0b",
            red: "#ef4444",
            violet: "#7c3aed",
            cyan: "#0891b2",
        };
        let cursor = 0;
        const stops = (items || []).map((item) => {
            const start = cursor;
            cursor += item.ratio || 0;
            return `${colors[item.tone] || colors.blue} ${start}% ${cursor}%`;
        });
        return `background: conic-gradient(${stops.join(", ") || "#e5e7eb 0% 100%"});`;
    }

    async openKpiAction(kpi) {
        if (!kpi || !kpi.action || !kpi.action.type) {
            return;
        }
        await this.action.doAction(kpi.action);
    }

    openInvoices() {
        this.action.doAction("account.action_move_out_invoice_type");
    }

    openBills() {
        this.action.doAction("account.action_move_in_invoice_type");
    }
}

BusinessOverviewDashboard.template = "kio_isp_business_dashboard.BusinessOverviewDashboard";
registry.category("actions").add("kio_isp_business_dashboard.business_overview", BusinessOverviewDashboard);
