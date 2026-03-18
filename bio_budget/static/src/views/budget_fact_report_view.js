/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { pivotView } from "@web/views/pivot/pivot_view";
import { PivotController } from "@web/views/pivot/pivot_controller";
import { useService } from "@web/core/utils/hooks";
const { useState, onMounted } = owl;

const LOG_PREFIX = "[BudgetFilter]";

// Mixin з логікою дат-фільтра (щоб не дублювати між list і pivot)
const DateFilterMixin = (superclass) => class extends superclass {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.dateFilter = useState({ dateFrom: "", dateTo: "", budgetId: 0, budgetName: "" });
        this.budgetOptions = useState({ list: [] });
        this.budgetModal = useState({ show: false });

        console.log(LOG_PREFIX, "setup() called");
        console.log(LOG_PREFIX, "this.model =", this.model);
        console.log(LOG_PREFIX, "this.model constructor =", this.model?.constructor?.name);
        console.log(LOG_PREFIX, "this.model.searchParams =", this.model?.searchParams);
        console.log(LOG_PREFIX, "this.model.root =", this.model?.root);
        console.log(LOG_PREFIX, "this.env.searchModel =", this.env?.searchModel);

        // Dump all model keys for debugging
        if (this.model) {
            console.log(LOG_PREFIX, "this.model keys =", Object.keys(this.model));
            console.log(LOG_PREFIX, "this.model proto keys =", Object.getOwnPropertyNames(Object.getPrototypeOf(this.model)));
        }

        onMounted(() => {
            console.log(LOG_PREFIX, "onMounted() - model state after mount:");
            console.log(LOG_PREFIX, "  model.searchParams =", JSON.stringify(this.model?.searchParams));
            console.log(LOG_PREFIX, "  model.root =", this.model?.root);
            console.log(LOG_PREFIX, "  model.root?.data =", this.model?.root?.data);
            if (this.env.searchModel) {
                console.log(LOG_PREFIX, "  searchModel.domain =", JSON.stringify(this.env.searchModel.domain));
                console.log(LOG_PREFIX, "  searchModel.context =", JSON.stringify(this.env.searchModel.context));
                console.log(LOG_PREFIX, "  searchModel.groupBy =", JSON.stringify(this.env.searchModel.groupBy));
                console.log(LOG_PREFIX, "  searchModel keys =", Object.keys(this.env.searchModel));
                console.log(LOG_PREFIX, "  searchModel proto keys =", Object.getOwnPropertyNames(Object.getPrototypeOf(this.env.searchModel)));
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
        console.log(LOG_PREFIX, "onDateFromChanged:", this.dateFilter.dateFrom);
    }

    onDateToChanged(ev) {
        this.dateFilter.dateTo = ev.target.value || "";
        console.log(LOG_PREFIX, "onDateToChanged:", this.dateFilter.dateTo);
    }

    async _rebuildAndReload(dateFrom, dateTo) {
        console.log(LOG_PREFIX, "=== _rebuildAndReload START ===");
        console.log(LOG_PREFIX, "  dateFrom =", dateFrom, "dateTo =", dateTo);

        // 1. Dump current state BEFORE rebuild
        console.log(LOG_PREFIX, "  BEFORE rebuild:");
        console.log(LOG_PREFIX, "    model =", this.model);
        console.log(LOG_PREFIX, "    model.constructor =", this.model?.constructor?.name);
        console.log(LOG_PREFIX, "    model.searchParams =", JSON.stringify(this.model?.searchParams));
        console.log(LOG_PREFIX, "    model.root =", this.model?.root);
        console.log(LOG_PREFIX, "    model.root?.records?.length =", this.model?.root?.records?.length);
        if (this.env.searchModel) {
            console.log(LOG_PREFIX, "    searchModel.domain =", JSON.stringify(this.env.searchModel.domain));
            console.log(LOG_PREFIX, "    searchModel.context =", JSON.stringify(this.env.searchModel.context));
            console.log(LOG_PREFIX, "    searchModel.groupBy =", JSON.stringify(this.env.searchModel.groupBy));
            console.log(LOG_PREFIX, "    searchModel.orderBy =", JSON.stringify(this.env.searchModel.orderBy));
        }

        // 2. Rebuild SQL VIEW on server
        console.log(LOG_PREFIX, "  Calling apply_date_filter on server...");
        const rpcResult = await this.orm.call(
            "budget.fact.report",
            "apply_date_filter",
            [],
            { date_from: dateFrom || false, date_to: dateTo || false }
        );
        console.log(LOG_PREFIX, "  apply_date_filter returned:", rpcResult);

        // 3. Build searchParams from SearchModel (current filters)
        const searchModel = this.env.searchModel;
        const reloadParams = {
            domain: searchModel.domain,
            context: searchModel.context,
            groupBy: searchModel.groupBy,
            orderBy: searchModel.orderBy || [],
        };
        console.log(LOG_PREFIX, "  reloadParams from searchModel =", JSON.stringify(reloadParams));

        // 4. Try to reload model
        console.log(LOG_PREFIX, "  Attempting model.load()...");
        try {
            if (typeof this.model.load === "function") {
                console.log(LOG_PREFIX, "    Using this.model.load(reloadParams)");
                await this.model.load(reloadParams);
                console.log(LOG_PREFIX, "    model.load() succeeded");
            } else if (this.model.root && typeof this.model.root.load === "function") {
                console.log(LOG_PREFIX, "    Using this.model.root.load(reloadParams)");
                await this.model.root.load(reloadParams);
                console.log(LOG_PREFIX, "    model.root.load() succeeded");
            } else {
                console.error(LOG_PREFIX, "    NO load() method found on model or model.root!");
                console.log(LOG_PREFIX, "    model keys:", Object.keys(this.model));
                if (this.model.root) {
                    console.log(LOG_PREFIX, "    model.root keys:", Object.keys(this.model.root));
                }
            }
        } catch (loadErr) {
            console.error(LOG_PREFIX, "  model.load() FAILED:", loadErr);
            console.error(LOG_PREFIX, "  Error details:", loadErr.message, loadErr.stack);
            throw loadErr;
        }

        // 5. Notify
        console.log(LOG_PREFIX, "  Calling model.notify()...");
        this.model.notify();

        // 6. Dump state AFTER
        console.log(LOG_PREFIX, "  AFTER rebuild:");
        console.log(LOG_PREFIX, "    model.searchParams =", JSON.stringify(this.model?.searchParams));
        console.log(LOG_PREFIX, "    model.root?.records?.length =", this.model?.root?.records?.length);
        console.log(LOG_PREFIX, "=== _rebuildAndReload END ===");
    }

    async onDateFilterApply() {
        console.log(LOG_PREFIX, "onDateFilterApply clicked, dateFilter =", JSON.stringify(this.dateFilter));
        try {
            await this._rebuildAndReload(this.dateFilter.dateFrom, this.dateFilter.dateTo);
            this.notification.add("Filter applied", { type: "success" });
        } catch (e) {
            console.error(LOG_PREFIX, "onDateFilterApply ERROR:", e);
            this.notification.add(`Filter error: ${e.message || String(e)}`, { type: "danger", sticky: true });
        }
    }

    async onDateFilterClear() {
        console.log(LOG_PREFIX, "onDateFilterClear clicked");
        this.dateFilter.dateFrom = "";
        this.dateFilter.dateTo = "";
        this.dateFilter.budgetId = 0;
        this.dateFilter.budgetName = "";
        try {
            await this._rebuildAndReload(false, false);
        } catch (e) {
            console.error(LOG_PREFIX, "onDateFilterClear ERROR:", e);
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
