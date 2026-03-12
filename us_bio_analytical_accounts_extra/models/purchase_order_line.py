from odoo import models, api

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _apply_analytic_distribution_from_partner_and_product(self):
        AnalyticModel = self.env["account.analytic.distribution.model"]
        AnalyticAccount = self.env["account.analytic.account"]

        for line in self:
            # 1) З нуля
            result = {}

            # partner береться з order
            partner = line.order_id.partner_id
            if partner and partner.analytic_distribution:
                result = dict(partner.analytic_distribution)

            # Мапа plan_id -> partner_percent
            partner_plan_map = {}
            for acc_id, percent in (result or {}).items():
                acc = AnalyticAccount.browse(int(acc_id))
                if acc.plan_id:
                    partner_plan_map[acc.plan_id.id] = percent

            # 2) Product rule
            if line.product_id:
                rule = AnalyticModel.search([
                    ("product_id", "=", line.product_id.id),
                    ("company_id", "=", False),
                    ("partner_id", "=", False),
                ], limit=1)

                if rule and rule.analytic_distribution:
                    for acc_id, percent in rule.analytic_distribution.items():
                        acc = AnalyticAccount.browse(int(acc_id))
                        if not acc.plan_id:
                            continue

                        # Якщо рахунок вже є у партнера — продукт ігноруємо
                        if acc_id in result:
                            continue

                        plan_id = acc.plan_id.id

                        # Якщо плану немає у партнера → беремо продукт як є
                        if plan_id not in partner_plan_map:
                            result[acc_id] = percent
                            continue

                        partner_percent = partner_plan_map[plan_id]

                        # 100% партнера → продукт ігноруємо
                        if partner_percent >= 100:
                            continue

                        # <100% → продукт отримує залишок
                        remainder = 100 - partner_percent
                        if remainder > 0:
                            result[acc_id] = remainder

            line.analytic_distribution = result

    @api.onchange("product_id")
    def _onchange_product_apply_analytic_distribution(self):
        self._apply_analytic_distribution_from_partner_and_product()