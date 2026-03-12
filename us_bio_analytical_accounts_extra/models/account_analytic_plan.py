from odoo import models, fields, api


class AccountAnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    type = fields.Selection([
        ('cluster', 'Cluster'),
        ('business_unit','Business Unit'),
        ('brand','Brand')], string='Type')
