from odoo import models, fields, api

class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    account_cluster_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Cluster',
        domain="[('plan_id.type', '=', 'cluster')]",
        help='Аналітичний рахунок з плану типу Cluster'
    )

    account_business_unit_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Business Unit',
        domain="[('plan_id.type', '=', 'business_unit')]",
        help='Аналітичний рахунок з плану типу Business Unit'
    )

    account_brand_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Brand',
        domain="[('plan_id.type', '=', 'brand')]",
        help='Аналітичний рахунок з плану типу Brand'
    )
    is_grouped_account = fields.Boolean(
        string="Груповий рахунок",
        compute="_compute_is_grouped_account",
        store=True,
    )

    @api.depends('account_cluster_id', 'account_business_unit_id', 'account_brand_id')
    def _compute_is_grouped_account(self):
        for rec in self:
            filled = sum(bool(x) for x in (
                rec.account_cluster_id,
                rec.account_business_unit_id,
                rec.account_brand_id,
            ))
            rec.is_grouped_account = filled >= 1


    @api.onchange('account_cluster_id', 'account_business_unit_id', 'account_brand_id')
    def _onchange_generate_name(self):
        for record in self:
            if not (record.account_cluster_id or record.account_business_unit_id or record.account_brand_id):
                return

            parts = [
                record.account_cluster_id.name if record.account_cluster_id else "Null",
                record.account_business_unit_id.name if record.account_business_unit_id else "Null",
                record.account_brand_id.name if record.account_brand_id else "Null",
            ]

            record.name = " / ".join(parts)

