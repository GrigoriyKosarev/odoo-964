import json
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # analytic_distribution = fields.Json(string='Analytic Account', company_dependent=True,)
    analytic_distribution_text = fields.Text(company_dependent=True)

    analytic_distribution = fields.Json(string='Analytic Account',
        compute="_compute_analytic_distribution",
        inverse="_inverse_analytic_distribution",
        store=False,
    )


    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )

    @api.model_create_multi
    def create(self, vals_list):
        # підтягуємо analytic_distribution з parent тільки якщо його НЕ передали в vals
        parent_ids = {vals.get("parent_id") for vals in vals_list if vals.get("parent_id")}
        parents = {p.id: p for p in self.browse(list(parent_ids)).exists()}

        for vals in vals_list:
            parent_id = vals.get("parent_id")
            if not parent_id:
                continue

            # користувач/інтеграція може передати analytic_distribution явно — тоді не втручаємось
            if "analytic_distribution" in vals:
                continue

            parent = parents.get(parent_id)
            if parent and parent.analytic_distribution:
                vals["analytic_distribution"] = parent.analytic_distribution

        return super().create(vals_list)

    def _compute_analytic_distribution(self):
        for rec in self:
            rec.analytic_distribution = json.loads(rec.analytic_distribution_text or "{}")

    def _inverse_analytic_distribution(self):
        for rec in self:
            rec.analytic_distribution_text = json.dumps(rec.analytic_distribution or {})