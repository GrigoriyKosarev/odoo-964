/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { pivotView } from "@web/views/pivot/pivot_view";
import { PivotController } from "@web/views/pivot/pivot_controller";
import { useService } from "@web/core/utils/hooks";
const { useState } = owl;

const STORAGE_KEY = "budget_fact_report_date_filter";

// Mixin з логікою дат-фільтра (щоб не дублювати між list і pivot)
const DateFilterMixin = (superclass) => class extends superclass {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        // Restore date filter state from sessionStorage (preserved across page reloads)
        const saved = sessionStorage.getItem(STORAGE_KEY);
        if (saved) {
            const s = JSON.parse(saved);
            this.dateFilter = useState({
                dateFrom: s.dateFrom || "",
                dateTo: s.dateTo || "",
                budgetId: s.budgetId || 0,
                budgetName: s.budgetName || "",
            });
        } else {
            this.dateFilter = useState({ dateFrom: "", dateTo: "", budgetId: 0, budgetName: "" });
        }
        this.budgetOptions = useState({ list: [] });
        this.budgetModal = useState({ show: false });
    }

    _saveDateFilter() {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
            dateFrom: this.dateFilter.dateFrom,
            dateTo: this.dateFilter.dateTo,
            budgetId: this.dateFilter.budgetId,
            budgetName: this.dateFilter.budgetName,
        }));
    }

    async onOpenBudgetModal() {
        this.budgetOptions.list = await this.orm.searchRead(
            "crossovered.budget", [], ["name", "date_from", "date_to"], { order: "name" }
        );
        this.budgetModal.show = true;
    }

    onSelectBudget(id, name, date_from, date_to) {
        this.dateFilter.budgetId = id;
        this.dateFilter.budgetName = name;
        this.dateFilter.dateFrom = date_from;
        this.dateFilter.dateTo = date_to;
        this.budgetModal.show = false;
    }

    onClearBudget() {
        this.dateFilter.budgetId = 0;
        this.dateFilter.budgetName = "";
    }

    onCloseBudgetModal() {
        this.budgetModal.show = false;
    }

    onDateFromChanged(ev) {
        this.dateFilter.dateFrom = ev.target.value || "";
    }

    onDateToChanged(ev) {
        this.dateFilter.dateTo = ev.target.value || "";
    }

    async onDateFilterApply() {
        await this.orm.call(
            "budget.fact.report",
            "apply_date_filter",
            [],
            { date_from: this.dateFilter.dateFrom || false, date_to: this.dateFilter.dateTo || false }
        );
        this._saveDateFilter();
        window.location.reload();
    }

    async onDateFilterClear() {
        this.dateFilter.dateFrom = "";
        this.dateFilter.dateTo = "";
        this.dateFilter.budgetId = 0;
        this.dateFilter.budgetName = "";
        await this.orm.call(
            "budget.fact.report",
            "apply_date_filter",
            [],
            { date_from: false, date_to: false }
        );
        sessionStorage.removeItem(STORAGE_KEY);
        window.location.reload();
    }
};

// List контролер
export class budgetFactReportViewController extends DateFilterMixin(ListController) {}

// Pivot контролер
export class budgetFactReportPivotController extends DateFilterMixin(PivotController) {}

// List view
export const budgetFactReportView = {
    ...listView,
    Controller: budgetFactReportViewController,
    buttonTemplate: "bio_budget.budgetFactReportView.Buttons",
};

// Pivot view
export const budgetFactReportPivotView = {
    ...pivotView,
    Controller: budgetFactReportPivotController,
    buttonTemplate: "bio_budget.budgetFactReportPivotView.Buttons",
};

registry.category("views").add("budget_fact_report_view", budgetFactReportView);
registry.category("views").add("budget_fact_report_pivot_view", budgetFactReportPivotView);
