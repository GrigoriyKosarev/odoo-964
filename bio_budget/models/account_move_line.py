# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def action_update_grouped_aa(self):
        AnalyticAccount = self.env["account.analytic.account"]
        AnalyticLine = self.env["account.analytic.line"]
        AnalyticPlan = self.env["account.analytic.plan"]

        combined_plan = AnalyticPlan.search([("name", "=", "General")], limit=1)
        if not combined_plan:
            raise UserError("Аналітичний план 'General' не знайдено.")

        for line in self:
            move = line.move_id

            # ---------------------------
            # 0. Remove old General analytic lines and clean distribution
            # ---------------------------
            old_general_lines = AnalyticLine.search([
                ("move_line_id", "=", line.id),
                ("account_id.is_grouped_account", "=", True),
                ("plan_id", "=", combined_plan.id),
            ])
            if old_general_lines:
                existing_dist = line.analytic_distribution or {}
                new_dist = {
                    k: v for k, v in existing_dist.items()
                    if int(k) not in old_general_lines.mapped("account_id").ids
                }
                line.analytic_distribution = new_dist
                old_general_lines.unlink()

            # ---------------------------
            # 1. Group analytics by plan type
            # ---------------------------
            grouped = {
                "brand": [],
                "business_unit": [],
                "cluster": [],
            }
            source_line = None
            for analytic in line.analytic_line_ids:
                account = analytic.account_id

                if account.is_grouped_account:
                    continue

                plan_type_raw = analytic.plan_id.type
                if not plan_type_raw:
                    continue

                plan_type = plan_type_raw.lower().replace(' ', '_')
                if plan_type in grouped:
                    grouped[plan_type].append((account, analytic.amount))

                if plan_type in ("cluster", "business_unit", "brand") and source_line is None:
                    source_line = analytic

            clusters = grouped["cluster"]
            bus = grouped["business_unit"]
            brands = grouped["brand"]

            if not (clusters or bus or brands):
                continue

            if not source_line:
                continue

            # ---------------------------
            # 2. Subtotal
            # ---------------------------
            subtotal = line.price_subtotal

            # ---------------------------
            # 3. Generate combinations
            # ---------------------------
            results = []
            total_amount_calc = 0.0

            if clusters and bus and brands:
                # Three types: Cluster x Business Unit x Brand
                for c_acc, c_amt in clusters:
                    c_pct = c_amt / subtotal if subtotal else 0
                    for b_acc, b_amt in bus:
                        b_pct = b_amt / subtotal if subtotal else 0
                        for r_acc, r_amt in brands:
                            r_pct = r_amt / subtotal if subtotal else 0
                            combined_pct = c_pct * b_pct * r_pct
                            combined_amount = subtotal * combined_pct
                            total_amount_calc += combined_amount

                            combined_acc = move._find_or_create_combined_account(
                                combined_plan, move, c_acc, b_acc, r_acc)
                            results.append({
                                "account": combined_acc,
                                "amount": combined_amount,
                                "percent": combined_pct,
                            })

            elif clusters and bus:
                for c_acc, c_amt in clusters:
                    c_pct = c_amt / subtotal if subtotal else 0
                    for b_acc, b_amt in bus:
                        b_pct = b_amt / subtotal if subtotal else 0
                        combined_pct = c_pct * b_pct
                        combined_amount = subtotal * combined_pct
                        total_amount_calc += combined_amount

                        combined_acc = move._find_or_create_combined_account(
                            combined_plan, move, c_acc, b_acc, None)
                        results.append({
                            "account": combined_acc,
                            "amount": combined_amount,
                            "percent": combined_pct,
                        })

            elif clusters and brands:
                for c_acc, c_amt in clusters:
                    c_pct = c_amt / subtotal if subtotal else 0
                    for r_acc, r_amt in brands:
                        r_pct = r_amt / subtotal if subtotal else 0
                        combined_pct = c_pct * r_pct
                        combined_amount = subtotal * combined_pct
                        total_amount_calc += combined_amount

                        combined_acc = move._find_or_create_combined_account(
                            combined_plan, move, c_acc, None, r_acc)
                        results.append({
                            "account": combined_acc,
                            "amount": combined_amount,
                            "percent": combined_pct,
                        })

            elif bus and brands:
                for b_acc, b_amt in bus:
                    b_pct = b_amt / subtotal if subtotal else 0
                    for r_acc, r_amt in brands:
                        r_pct = r_amt / subtotal if subtotal else 0
                        combined_pct = b_pct * r_pct
                        combined_amount = subtotal * combined_pct
                        total_amount_calc += combined_amount

                        combined_acc = move._find_or_create_combined_account(
                            combined_plan, move, None, b_acc, r_acc)
                        results.append({
                            "account": combined_acc,
                            "amount": combined_amount,
                            "percent": combined_pct,
                        })

            elif clusters:
                for c_acc, c_amt in clusters:
                    c_pct = c_amt / subtotal if subtotal else 0
                    combined_amount = c_amt
                    total_amount_calc += combined_amount

                    combined_acc = move._find_or_create_combined_account(
                        combined_plan, move, c_acc, None, None)
                    results.append({
                        "account": combined_acc,
                        "amount": combined_amount,
                        "percent": c_pct,
                    })

            elif bus:
                for b_acc, b_amt in bus:
                    b_pct = b_amt / subtotal if subtotal else 0
                    combined_amount = b_amt
                    total_amount_calc += combined_amount

                    combined_acc = move._find_or_create_combined_account(
                        combined_plan, move, None, b_acc, None)
                    results.append({
                        "account": combined_acc,
                        "amount": combined_amount,
                        "percent": b_pct,
                    })

            elif brands:
                for r_acc, r_amt in brands:
                    r_pct = r_amt / subtotal if subtotal else 0
                    combined_amount = r_amt
                    total_amount_calc += combined_amount

                    combined_acc = move._find_or_create_combined_account(
                        combined_plan, move, None, None, r_acc)
                    results.append({
                        "account": combined_acc,
                        "amount": combined_amount,
                        "percent": r_pct,
                    })

            # ---------------------------
            # 4. Rounding correction
            # ---------------------------
            diff = subtotal - total_amount_calc
            if results:
                results[-1]["amount"] += diff

            # ---------------------------
            # 5. Create analytic lines
            # ---------------------------
            base_vals = source_line.copy_data()[0]
            for item in results:
                acc = item["account"]

                existing_line = AnalyticLine.search([
                    ("move_line_id", "=", line.id),
                    ("account_id", "=", acc.id),
                ], limit=1)

                if existing_line:
                    continue

                new_vals = base_vals.copy()
                new_vals.update({
                    "account_id": acc.id,
                    "plan_id": combined_plan.id,
                    "amount": item["amount"],
                })

                AnalyticLine.create(new_vals)

            # ---------------------------
            # 6. Update analytic_distribution
            # ---------------------------
            existing_dist = line.analytic_distribution or {}
            new_dist = existing_dist.copy()

            for item in results:
                acc = item["account"]
                pct = item["percent"] * 100
                new_dist[str(acc.id)] = pct

            line.analytic_distribution = new_dist
