# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _find_or_create_combined_account(self, combined_plan, records,
                                         cluster_acc, bus_acc, brand_acc):
        """Find or create a combined analytic account for the General plan.

        Uses hierarchical search:
        1) company + partner
        2) company only
        3) global (no company, no partner)
        If not found, creates a new global account.
        """
        AnalyticAccount = self.env["account.analytic.account"]

        base_domain = [
            ("account_cluster_id", "=", cluster_acc.id if cluster_acc else False),
            ("account_business_unit_id", "=", bus_acc.id if bus_acc else False),
            ("account_brand_id", "=", brand_acc.id if brand_acc else False),
            ("is_grouped_account", "=", True),
            ("plan_id", "=", combined_plan.id),
        ]

        combined_acc = False

        # 1) Company + Partner
        if records.company_id and records.partner_id:
            acc = AnalyticAccount.search(base_domain + [
                ("company_id", "=", records.company_id.id),
                ("partner_id", "=", records.partner_id.id),
            ], limit=1)
            if acc:
                combined_acc = acc

        if not combined_acc:
            # 2) Company only
            if records.company_id:
                acc = AnalyticAccount.search(base_domain + [
                    ("company_id", "=", records.company_id.id),
                    ("partner_id", "=", False),
                ], limit=1)
                if acc:
                    combined_acc = acc

        if not combined_acc:
            # 3) Global
            acc = AnalyticAccount.search(base_domain + [
                ("company_id", "=", False),
                ("partner_id", "=", False),
            ], limit=1)
            if acc:
                combined_acc = acc

        if not combined_acc:
            c_name = cluster_acc.name if cluster_acc else "Null"
            b_name = bus_acc.name if bus_acc else "Null"
            r_name = brand_acc.name if brand_acc else "Null"
            name = f"{c_name} / {b_name} / {r_name}"

            combined_acc = AnalyticAccount.create({
                "name": name,
                "account_cluster_id": cluster_acc.id if cluster_acc else False,
                "account_business_unit_id": bus_acc.id if bus_acc else False,
                "account_brand_id": brand_acc.id if brand_acc else False,
                "is_grouped_account": True,
                "company_id": False,
                "plan_id": combined_plan.id,
                "partner_id": False,
            })

        return combined_acc

    def action_post(self):
        AnalyticAccount = self.env["account.analytic.account"]
        AnalyticLine = self.env["account.analytic.line"]
        AnalyticPlan = self.env["account.analytic.plan"]

        combined_plan = AnalyticPlan.search([("name", "=", "General")], limit=1)
        if not combined_plan:
            raise UserError("Аналітичний план 'General' не знайдено.")

        # ---------------------------
        # 0. Clean General accounts from analytic_distribution BEFORE super
        #    (prevents standard Odoo from re-creating stale General analytic lines on re-post)
        # ---------------------------
        for records in self:
            for line in records.invoice_line_ids:
                existing_dist = line.analytic_distribution or {}
                if not existing_dist:
                    continue
                account_ids = []
                for k in existing_dist:
                    try:
                        account_ids.append(int(k))
                    except (ValueError, TypeError):
                        continue
                if not account_ids:
                    continue
                grouped_accounts = AnalyticAccount.search([
                    ("id", "in", account_ids),
                    ("is_grouped_account", "=", True),
                ])
                if grouped_accounts:
                    new_dist = {
                        k: v for k, v in existing_dist.items()
                        if int(k) not in grouped_accounts.ids
                    }
                    line.analytic_distribution = new_dist

        res = super().action_post()

        for records in self:
            for line in records.invoice_line_ids:
                # ---------------------------
                # 1. Групування аналітики за типом плану
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

                    if (plan_type == "cluster" or
                        plan_type == "business_unit" or
                        plan_type == "brand") and source_line is None :
                        source_line = analytic

                clusters = grouped["cluster"]
                bus = grouped["business_unit"]
                brands = grouped["brand"]

                # All 3 types filled — handled by us_bio_analytical_accounts_extra
                if clusters and bus and brands:
                    continue

                # None filled — nothing to do
                if not (clusters or bus or brands):
                    continue

                # No source line for copy_data — skip
                if not source_line:
                    continue

                # ---------------------------
                # 2. subtotal
                # ---------------------------
                # subtotal = line.price_subtotal
                subtotal = abs(line.balance)

                # ---------------------------
                # 3. Generate combinations
                # ---------------------------
                results = []
                total_amount_calc = 0.0

                if clusters and bus:
                    # Two types: Cluster x Business Unit, Brand = Null
                    for c_acc, c_amt in clusters:
                        c_pct = c_amt / subtotal if subtotal else 0
                        for b_acc, b_amt in bus:
                            b_pct = b_amt / subtotal if subtotal else 0
                            combined_pct = c_pct * b_pct
                            combined_amount = subtotal * combined_pct
                            total_amount_calc += combined_amount

                            combined_acc = self._find_or_create_combined_account(
                                combined_plan, records, c_acc, b_acc, None)
                            results.append({
                                "account": combined_acc,
                                "amount": combined_amount,
                                "percent": combined_pct,
                            })

                elif clusters and brands:
                    # Two types: Cluster x Brand, Business Unit = Null
                    for c_acc, c_amt in clusters:
                        c_pct = c_amt / subtotal if subtotal else 0
                        for r_acc, r_amt in brands:
                            r_pct = r_amt / subtotal if subtotal else 0
                            combined_pct = c_pct * r_pct
                            combined_amount = subtotal * combined_pct
                            total_amount_calc += combined_amount

                            combined_acc = self._find_or_create_combined_account(
                                combined_plan, records, c_acc, None, r_acc)
                            results.append({
                                "account": combined_acc,
                                "amount": combined_amount,
                                "percent": combined_pct,
                            })

                elif bus and brands:
                    # Two types: Business Unit x Brand, Cluster = Null
                    for b_acc, b_amt in bus:
                        b_pct = b_amt / subtotal if subtotal else 0
                        for r_acc, r_amt in brands:
                            r_pct = r_amt / subtotal if subtotal else 0
                            combined_pct = b_pct * r_pct
                            combined_amount = subtotal * combined_pct
                            total_amount_calc += combined_amount

                            combined_acc = self._find_or_create_combined_account(
                                combined_plan, records, None, b_acc, r_acc)
                            results.append({
                                "account": combined_acc,
                                "amount": combined_amount,
                                "percent": combined_pct,
                            })

                elif clusters:
                    # Single type: Cluster only
                    for c_acc, c_amt in clusters:
                        c_pct = c_amt / subtotal if subtotal else 0
                        combined_amount = c_amt
                        total_amount_calc += combined_amount

                        combined_acc = self._find_or_create_combined_account(
                            combined_plan, records, c_acc, None, None)
                        results.append({
                            "account": combined_acc,
                            "amount": combined_amount,
                            "percent": c_pct,
                        })

                elif bus:
                    # Single type: Business Unit only
                    for b_acc, b_amt in bus:
                        b_pct = b_amt / subtotal if subtotal else 0
                        combined_amount = b_amt
                        total_amount_calc += combined_amount

                        combined_acc = self._find_or_create_combined_account(
                            combined_plan, records, None, b_acc, None)
                        results.append({
                            "account": combined_acc,
                            "amount": combined_amount,
                            "percent": b_pct,
                        })

                elif brands:
                    # Single type: Brand only
                    for r_acc, r_amt in brands:
                        r_pct = r_amt / subtotal if subtotal else 0
                        combined_amount = r_amt
                        total_amount_calc += combined_amount

                        combined_acc = self._find_or_create_combined_account(
                            combined_plan, records, None, None, r_acc)
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

        return res
