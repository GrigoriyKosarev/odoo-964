/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { pivotView } from "@web/views/pivot/pivot_view";
import { PivotController } from "@web/views/pivot/pivot_controller";
import { useService } from "@web/core/utils/hooks";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { serializeDate, deserializeDate } from "@web/core/l10n/dates";
const { useState, onMounted } = owl;

const STORAGE_KEY = "budget_fact_report_filter";

function saveFilterState(state) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
        dateFrom: state.dateFrom || "",
        dateTo: state.dateTo || "",
        budgetId: state.budgetId || 0,
        budgetName: state.budgetName || "",
    }));
}

function loadFilterState() {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        if (raw) {
            return JSON.parse(raw);
        }
    } catch (e) { /* ignore */ }
    return { dateFrom: "", dateTo: "", budgetId: 0, budgetName: "" };
}

// Mixin з логікою дат-фільтра (щоб не дублювати між list і pivot)
const DateFilterMixin = (superclass) => class extends superclass {
    static template = superclass.template;
    static components = { ...superclass.components, DateTimeInput };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");

        const saved = loadFilterState();
        this.dateFilter = useState({
            dateFrom: saved.dateFrom,
            dateTo: saved.dateTo,
            budgetId: saved.budgetId,
            budgetName: saved.budgetName,
        });
        this.budgetOptions = useState({ list: [] });
        this.budgetModal = useState({ show: false });

        onMounted(async () => {
            // If we have saved filter state, rebuild the VIEW to match
            if (this.dateFilter.dateFrom || this.dateFilter.dateTo || this.dateFilter.budgetId) {
                await this._rebuildAndReload(this.dateFilter.dateFrom, this.dateFilter.dateTo);
            }
        });
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
        saveFilterState(this.dateFilter);
    }

    onClearBudget() {
        this.dateFilter.budgetId = 0;
        this.dateFilter.budgetName = "";
        saveFilterState(this.dateFilter);
    }

    onCloseBudgetModal() {
        this.budgetModal.show = false;
    }

    get dateFromDT() {
        return this.dateFilter.dateFrom ? deserializeDate(this.dateFilter.dateFrom) : false;
    }

    get dateToDT() {
        return this.dateFilter.dateTo ? deserializeDate(this.dateFilter.dateTo) : false;
    }

    onDateFromChanged(dt) {
        this.dateFilter.dateFrom = dt ? serializeDate(dt) : "";
    }

    onDateToChanged(dt) {
        this.dateFilter.dateTo = dt ? serializeDate(dt) : "";
    }

    async _rebuildAndReload(dateFrom, dateTo) {
        await this.orm.call(
            "budget.fact.report",
            "apply_date_filter",
            [],
            { date_from: dateFrom || false, date_to: dateTo || false, budget_id: this.dateFilter.budgetId || false }
        );

        const searchModel = this.env.searchModel;
        const reloadParams = {
            domain: searchModel.domain,
            context: searchModel.context,
            groupBy: searchModel.groupBy,
            orderBy: searchModel.orderBy || [],
        };

        if (typeof this.model.load === "function") {
            await this.model.load(reloadParams);
        } else if (this.model.root && typeof this.model.root.load === "function") {
            await this.model.root.load(reloadParams);
        }

        this.model.notify();
    }

    async onDateFilterApply() {
        try {
            await this._rebuildAndReload(this.dateFilter.dateFrom, this.dateFilter.dateTo);
            saveFilterState(this.dateFilter);
            this.notification.add("Filter applied", { type: "success" });
        } catch (e) {
            this.notification.add(`Filter error: ${e.message || String(e)}`, { type: "danger", sticky: true });
        }
    }

    async onDateFilterClear() {
        this.dateFilter.dateFrom = "";
        this.dateFilter.dateTo = "";
        this.dateFilter.budgetId = 0;
        this.dateFilter.budgetName = "";
        saveFilterState(this.dateFilter);
        try {
            await this._rebuildAndReload(false, false);
        } catch (e) {
            this.notification.add(`Clear error: ${e.message || String(e)}`, { type: "danger", sticky: true });
        }
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
