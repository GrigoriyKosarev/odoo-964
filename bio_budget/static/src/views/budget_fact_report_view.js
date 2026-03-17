/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
const { useState } = owl;

// Створюємо НОВИЙ контролер на основі стандартного
export class budgetFactReportViewController extends ListController {
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

    async onDateFilterApply() {
        console.log("=== [JS] onDateFilterApply:", this.dateFilter.dateFrom, this.dateFilter.dateTo);
        await this.orm.call(
            "budget.fact.report",
            "apply_date_filter",
            [],
            { date_from: this.dateFilter.dateFrom || false, date_to: this.dateFilter.dateTo || false }
        );
        await this.model.root.load();
        this.model.notify();
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
        await this.model.root.load();
        this.model.notify();
    }

}

// Створюємо новий об'єкт view на основі стандартного listView
export const budgetFactReportView = {
    ...listView,                          // Копіюємо все зі стандартного
    Controller: budgetFactReportViewController,       // Замінюємо контролер на наш
    buttonTemplate: "bio_budget.budgetFactReportView.Buttons",  // Шаблон кнопок
    //              ↑ цей підхід через buttonTemplate — рекомендований в Odoo 16
};

// Реєструємо нашу view під назвою "todo_list_view"
registry.category("views").add("budget_fact_report_view", budgetFactReportView);