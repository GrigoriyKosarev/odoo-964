/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { pivotView } from "@web/views/pivot/pivot_view";
import { PivotController } from "@web/views/pivot/pivot_controller";
import { useService } from "@web/core/utils/hooks";
const { useState } = owl;

// Mixin з логікою дат-фільтра (щоб не дублювати між list і pivot)
const DateFilterMixin = (superclass) => class extends superclass {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.actionService = useService("action");
        // Restore date filter state from action context (preserved across reloads)
        const ctx = this.props.action?.context || {};
        this.dateFilter = useState({
            dateFrom: ctx.budget_date_from || "",
            dateTo: ctx.budget_date_to || "",
            budgetId: ctx.budget_id || 0,
            budgetName: ctx.budget_name || "",
        });
        this.budgetOptions = useState({ list: [] });
        this.budgetModal = useState({ show: false });
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

    async _reloadAction() {
        // Reload the action via actionService to guarantee:
        // 1. SearchModel re-applies default filters (search_default_filter_plan_general)
        // 2. Model loads fresh data from the rebuilt SQL VIEW
        // Pass date filter state as context so it's restored after reload.
        const actionId = this.props.action?.id;
        await this.actionService.doAction(actionId, {
            clearBreadcrumbs: true,
            additionalContext: {
                budget_date_from: this.dateFilter.dateFrom || false,
                budget_date_to: this.dateFilter.dateTo || false,
                budget_id: this.dateFilter.budgetId || 0,
                budget_name: this.dateFilter.budgetName || "",
            },
        });
    }

    async onDateFilterApply() {
        await this.orm.call(
            "budget.fact.report",
            "apply_date_filter",
            [],
            { date_from: this.dateFilter.dateFrom || false, date_to: this.dateFilter.dateTo || false }
        );
        await this._reloadAction();
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
        await this._reloadAction();
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