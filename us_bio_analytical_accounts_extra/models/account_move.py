# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()

        AnalyticAccount = self.env["account.analytic.account"]
        AnalyticLine = self.env["account.analytic.line"]
        AnalyticPlan = self.env["account.analytic.plan"]

        combined_plan = AnalyticPlan.search([("name", "=", "General")], limit=1)
        if not combined_plan:
            raise UserError("Аналітичний план 'General' не знайдено.")

        for records in self:
            for line in records.invoice_line_ids:
                # ---------------------------
                # 1. Групування
                # ---------------------------
                grouped = {
                    "brand": [],
                    "business_unit": [],
                    "cluster": [],
                }
                cluster_source_line = None  # для копіювання
                for analytic in line.analytic_line_ids:

                    account = analytic.account_id

                    # 2. Ігноруємо груповані рахунки
                    if account.is_grouped_account:
                        continue

                    plan_type_raw = analytic.plan_id.type  # наприклад 'Cluster'
                    if not plan_type_raw:
                        continue
                    #     raise UserError("В рахунку " + account.name + " вибрано аналітичний план з пустим полем 'тип плану' ")

                    plan_type = plan_type_raw.lower().replace(' ', '_')  # 'cluster'
                    if plan_type in grouped:
                        grouped[plan_type].append((account, analytic.amount))

                    # зберігаємо перший cluster рядок для копіювання
                    if plan_type == "cluster" and cluster_source_line is None:
                        cluster_source_line = analytic

                # Обов'язково має бути джерело для копії
                if not cluster_source_line:
                    continue

                # Списки для мультиплікації
                clusters = grouped["cluster"]
                bus = grouped["business_unit"]
                brands = grouped["brand"]


                # Якщо хоча б одна група порожня — пропускаємо
                if not (clusters and bus and brands):
                    continue

                # ---------------------------
                # 2. subtotal сума рядка
                # ---------------------------
                subtotal = line.price_subtotal
                # ---------------------------
                # 3. Попереднє накопичення
                # ---------------------------

                results = []
                total_amount_calc = 0.0

                # ---------------------------
                # 4. Генерація всіх комбінацій
                # ---------------------------
                for c_acc, c_amt in clusters:
                    c_pct = c_amt / subtotal if subtotal else 0

                    for b_acc, b_amt in bus:
                        b_pct = b_amt / subtotal if subtotal else 0

                        for r_acc, r_amt in brands:
                            r_pct = r_amt / subtotal if subtotal else 0

                            # Комбінований % (доля)
                            combined_pct = c_pct * b_pct * r_pct

                            # Сума
                            combined_amount = subtotal * combined_pct
                            total_amount_calc += combined_amount

                            # ---------------------------
                            # 5. Знайти або створити комбінований рахунок
                            # ---------------------------
                            base_domain = [
                                ("account_brand_id", "=", r_acc.id),
                                ("account_business_unit_id", "=", b_acc.id),
                                ("account_cluster_id", "=", c_acc.id),
                                ("is_grouped_account", "=", True),
                                ("plan_id", "=", combined_plan.id),
                            ]
                            combined_acc = False

                            # 1) АР + Компанія + Клієнт
                            if records.company_id and records.partner_id:
                                acc = AnalyticAccount.search(base_domain + [
                                    ("company_id", "=", records.company_id.id),
                                    ("partner_id", "=", records.partner_id.id),
                                ], limit=1)
                                if acc:
                                   combined_acc = acc

                            if not combined_acc:
                                # 2) АР + Компанія
                                if records.company_id:
                                    acc = AnalyticAccount.search(base_domain + [
                                        ("company_id", "=", records.company_id.id),
                                        ("partner_id", "=", False),
                                    ], limit=1)
                                    if acc:
                                        combined_acc = acc
                            if not combined_acc:
                                # 3) АР (глобальний)
                                acc = AnalyticAccount.search(base_domain + [
                                    ("company_id", "=", False),
                                    ("partner_id", "=", False),
                                ], limit=1)
                                if acc:
                                    combined_acc = acc

                            if not combined_acc:

                                name = f"{c_acc.name} / {b_acc.name} / {r_acc.name}"
                                combined_acc = AnalyticAccount.create({
                                    "name": name,
                                    "account_brand_id": r_acc.id,
                                    "account_business_unit_id": b_acc.id,
                                    "account_cluster_id": c_acc.id,
                                    "is_grouped_account": True,
                                    "company_id" : False,
                                    "plan_id": combined_plan.id,
                                    "partner_id" : False,
                                })

                            results.append({
                                "account": combined_acc,
                                "amount": combined_amount,
                                "percent": combined_pct,
                            })
                # ---------------------------
                # 6. Корекція округлення
                # ---------------------------
                diff = subtotal - total_amount_calc
                if results:
                    results[-1]["amount"] += diff  # корекція останнього рядка

                # ---------------------------
                # 7. Створення нових аналітичних рядків
                # ---------------------------

                base_vals = cluster_source_line.copy_data()[0]
                for item in results:

                    acc = item["account"]

                    # Перевірка чи рядок вже існує
                    existing_line = AnalyticLine.search([
                        ("move_line_id", "=", line.id),
                        ("account_id", "=", acc.id),
                    ], limit=1)

                    if existing_line:
                        continue  # вже існує — пропускаємо

                    new_vals = base_vals.copy()
                    new_vals.update({
                        "account_id": acc.id,
                        "plan_id": combined_plan.id,
                        "amount": item["amount"],
                        })

                    AnalyticLine.create(new_vals)


                # 1. Отримуємо поточний розподіл
                existing_dist = line.analytic_distribution or {}

                # 2. Копію в окремий dict (щоб не зіпсувати reference)
                new_dist = existing_dist.copy()

                # 3. Додаємо нові комбінації
                for item in results:
                    acc = item["account"]
                    pct = item["percent"] * 100  # у %
                    new_dist[str(acc.id)] = pct

                # 4. Записуємо назад
                line.analytic_distribution = new_dist


        return res


    @api.onchange("partner_id")
    def _onchange_partner_propagate_analytic_distribution(self):
        for move in self:
            # для інвойсів: invoice_line_ids
            if move.invoice_line_ids:
                move.invoice_line_ids._apply_analytic_distribution_from_partner_and_product()

            # якщо потрібно також для journal items (general entries):
            # if move.line_ids:
            #     move.line_ids._apply_analytic_distribution_from_partner_and_product()