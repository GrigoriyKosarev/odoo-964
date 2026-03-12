from odoo import models, api

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _apply_analytic_distribution_from_partner_and_product(self):
        AnalyticModel = self.env["account.analytic.distribution.model"]

        for line in self:
            # 1️⃣ ЗАВЖДИ починаємо з нуля
            result = {}

            partner = line.move_id.partner_id
            if partner and partner.analytic_distribution:
                result = dict(partner.analytic_distribution)

            # Побудова мапи планів партнера
            partner_plan_map = {}
            for acc_id, percent in result.items():
                acc = self.env["account.analytic.account"].browse(int(acc_id))
                if acc.plan_id:
                    partner_plan_map[acc.plan_id.id] = percent

            # 2️⃣ Обробка продукту
            if line.product_id:
                rule = AnalyticModel.search([
                    ("product_id", "=", line.product_id.id),
                    ("company_id", "=", False),
                    ("partner_id", "=", False),
                ], limit=1)

                if rule and rule.analytic_distribution:
                    for acc_id, percent in rule.analytic_distribution.items():
                        acc = self.env["account.analytic.account"].browse(int(acc_id))
                        if not acc.plan_id:
                            continue

                        #  НОВЕ: якщо рахунок вже є у партнера — ігноруємо продукт
                        if acc_id in result:
                            continue

                        plan_id = acc.plan_id.id

                        # Якщо плану немає у партнера → беремо продукт
                        if plan_id not in partner_plan_map:
                            result[acc_id] = percent
                            continue

                        # Якщо є у партнера
                        partner_percent = partner_plan_map[plan_id]

                        # 100% партнера → ігноруємо продукт
                        if partner_percent >= 100:
                            continue

                        # <100% → продукт отримує залишок
                        remainder = 100 - partner_percent
                        if remainder > 0:
                            result[acc_id] = remainder

            # 3️⃣ Запис результату
            line.analytic_distribution = result
    @api.onchange("product_id")
    def _onchange_product_apply_analytic_distribution(self):
        self._apply_analytic_distribution_from_partner_and_product()
