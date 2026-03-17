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
        this.dateFilter = useState({ dateFrom: "", dateTo: "", taskId: 0, taskName: "" });
        this.taskOptions = useState({ list: [] });
        this.taskModal = useState({ show: false });
    }

    async onOpenTaskModal() {
        this.taskOptions.list = await this.orm.searchRead(
            "account.analytic.plan", [], ["name"], { order: "name" }
        );
        this.taskModal.show = true;
    }

    onSelectTask(id, name) {
        this.dateFilter.taskId = id;
        this.dateFilter.taskName = name;
        this.taskModal.show = false;
    }

    onClearTask() {
        this.dateFilter.taskId = 0;
        this.dateFilter.taskName = "";
    }

    onCloseTaskModal() {
        this.taskModal.show = false;
    }

    onDateFromChanged(ev) {
        this.dateFilter.dateFrom = ev.target.value || "";
    }

    onDateToChanged(ev) {
        this.dateFilter.dateTo = ev.target.value || "";
    }

    async _reloadModel() {
        // PivotModel uses model.load() directly; ListModel uses model.root.load()
        if (this.model.root && typeof this.model.root.load === "function") {
            await this.model.root.load();
        } else {
            await this.model.load(this.model.searchParams || {});
        }
        this.model.notify();
    }

    async onDateFilterApply() {
        console.log("=== [JS] onDateFilterApply:", this.dateFilter.dateFrom, this.dateFilter.dateTo);
        await this.orm.call(
            "budget.fact.report",
            "apply_date_filter",
            [],
            { date_from: this.dateFilter.dateFrom || false, date_to: this.dateFilter.dateTo || false }
        );
        await this._reloadModel();
    }

    async onDateFilterClear() {
        this.dateFilter.dateFrom = "";
        this.dateFilter.dateTo = "";
        this.dateFilter.taskId = 0;
        console.log("=== [JS] onDateFilterClear");
        await this.orm.call(
            "budget.fact.report",
            "apply_date_filter",
            [],
            { date_from: false, date_to: false }
        );
        await this._reloadModel();
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