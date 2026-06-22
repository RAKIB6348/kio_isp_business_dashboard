/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const DATE_RANGE_STORAGE_KEY = "kio_isp_business_dashboard_date_range";

export class BusinessOverviewDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const dateRange = this.getStoredDateRange() || this.getCurrentMonthRange();

        this.state = useState({
            loading: true,
            data: {},
            dateFrom: dateRange.dateFrom,
            dateTo: dateRange.dateTo,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    // ================= LOAD DATA =================
    async loadDashboardData() {
        this.state.loading = true;

        const args =
            this.state.dateFrom && this.state.dateTo
                ? [this.state.dateFrom, this.state.dateTo]
                : [];

        this.state.data = await this.orm.call(
            "kio.isp.business.dashboard",
            "get_dashboard_data",
            args
        );

        this.state.dateFrom = this.state.data.period.date_from;
        this.state.dateTo = this.state.data.period.date_to;
        this.persistDateRange();

        this.state.loading = false;
    }

    getCurrentMonthRange() {
        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, "0");
            const day = String(date.getDate()).padStart(2, "0");
            return `${year}-${month}-${day}`;
        };

        return {
            dateFrom: formatDate(new Date(today.getFullYear(), today.getMonth(), 1)),
            dateTo: formatDate(today),
        };
    }

    getStoredDateRange() {
        const savedRange = localStorage.getItem(DATE_RANGE_STORAGE_KEY);
        if (!savedRange) {
            return null;
        }

        try {
            const range = JSON.parse(savedRange);
            if (!range.dateFrom || !range.dateTo) {
                return null;
            }
            return range;
        } catch (error) {
            localStorage.removeItem(DATE_RANGE_STORAGE_KEY);
            return null;
        }
    }

    persistDateRange() {
        if (!this.state.dateFrom || !this.state.dateTo) {
            return;
        }

        localStorage.setItem(
            DATE_RANGE_STORAGE_KEY,
            JSON.stringify({
                dateFrom: this.state.dateFrom,
                dateTo: this.state.dateTo,
            })
        );
    }

    // ================= DATE FILTER =================
    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
    }

    async applyDateFilter() {
        if (!this.state.dateFrom || !this.state.dateTo) {
            return;
        }

        if (this.state.dateFrom > this.state.dateTo) {
            const temp = this.state.dateFrom;
            this.state.dateFrom = this.state.dateTo;
            this.state.dateTo = temp;
        }

        this.persistDateRange();
        await this.loadDashboardData();
    }

    async clearDateFilter() {
        const currentMonthRange = this.getCurrentMonthRange();
        this.state.dateFrom = currentMonthRange.dateFrom;
        this.state.dateTo = currentMonthRange.dateTo;
        this.persistDateRange();
        await this.loadDashboardData();
    }

    updateDateFrom(ev) {
        this.onDateFromChange(ev);
    }

    updateDateTo(ev) {
        this.onDateToChange(ev);
    }

    async applyDateRange() {
        await this.applyDateFilter();
    }

    // ================= FORMAT HELPERS =================
    formatCurrency(amount) {
        const currency = this.state.data.currency || {};

        const value = Math.abs(amount || 0).toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });

        const formatted =
            currency.position === "after"
                ? `${value} ${currency.symbol || ""}`
                : `${currency.symbol || ""} ${value}`;

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

    // ================= KPI CLICK =================
    async openKpiAction(kpi) {
        if (!kpi?.action?.type) return;
        await this.action.doAction(kpi.action);
    }

    // ================= PANEL CLICK (FIXED FOR AR/AP) =================
    async openPanelAction(action) {
        if (!action) return;

        await this.action.doAction(action);
    }

    openCashFlowReport() {
        this.action.doAction("kio_account_reports.action_account_report_cs");
    }

    openQuickNav(nav) {
        if (!nav?.action) {
            return;
        }

        this.action.doAction(nav.action, {
            additionalContext: {
                from_business_dashboard: true,
                business_dashboard_action: "kio_isp_business_dashboard.action_kio_isp_business_dashboard",
            },
        });
    }

    // ================= QUICK ACTIONS =================
    openInvoices() {
        this.action.doAction("account.action_move_out_invoice_type");
    }

    openBills() {
        this.action.doAction("account.action_move_in_invoice_type");
    }
}

BusinessOverviewDashboard.template =
    "kio_isp_business_dashboard.BusinessOverviewDashboard";

registry.category("actions").add(
    "kio_isp_business_dashboard.business_overview",
    BusinessOverviewDashboard
);