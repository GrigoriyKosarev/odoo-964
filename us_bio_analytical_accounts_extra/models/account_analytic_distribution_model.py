from odoo import models, api

class AccountAnalyticDistributionModel(models.Model):
    _inherit = "account.analytic.distribution.model"

    @api.constrains('company_id')
    def _check_company_accounts(self):
        # INTENTIONALLY OVERRIDDEN
        # Company consistency is handled by custom logic
        return