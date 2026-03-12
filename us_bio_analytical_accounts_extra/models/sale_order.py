from odoo import models, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange("partner_id")
    def _onchange_partner_propagate_analytic_distribution(self):
        for order in self:
            if order.order_line:
                order.order_line._apply_analytic_distribution_from_partner_and_product()