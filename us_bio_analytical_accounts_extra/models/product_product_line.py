
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models

class ProductProductLine(models.Model):
    _inherit = "product.product.line"


    analytic_distribution = fields.Many2one('account.analytic.account', string='Analytic')
    generate_distribution_model = fields.Boolean(string='Generate distribution model')
