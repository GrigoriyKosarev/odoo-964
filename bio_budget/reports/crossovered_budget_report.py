from odoo import models, fields, tools


class BudgetFactReport(models.Model):
    _name = "budget.fact.report"
    _description = "Budget vs Fact Report"
    _auto = False

    # budget_id = fields.Many2one('account.budget.post', 'Budgetary Position')
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account"
    )
    plan_id = fields.Many2one('account.analytic.plan', 'Plan')
    cluster_id = fields.Many2one('account.analytic.account', 'Cluster')
    business_unit_id = fields.Many2one('account.analytic.account', 'Business Unit')
    brand_id = fields.Many2one('account.analytic.account', 'Brand')

    account_id = fields.Many2one(
        "account.account",
        string="Account"
    )

    plan = fields.Float(string="Budget Plan")
    fact = fields.Float(string="Budget Fact")
    diff = fields.Float(string="Diff")


    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS
            SELECT
                row_number() OVER() AS id,
                analytic_account_id,
                aaa.plan_id as plan_id,
                aaa.account_cluster_id  as cluster_id,
                aaa.account_business_unit_id as business_unit_id,
                aaa.account_brand_id as brand_id,
                account_id,
                SUM(plan) AS plan,
                SUM(fact) AS fact,
                SUM(plan) - SUM(fact) AS diff
            FROM (
            
                -- PLAN
                SELECT
                    cbl.analytic_account_id,
                    abr.account_id,
                    cbl.planned_amount AS plan,
                    0::numeric AS fact
                FROM crossovered_budget_lines cbl
                LEFT JOIN account_budget_rel abr
                    ON cbl.general_budget_id = abr.budget_id
                WHERE cbl.planned_amount > 0
            
                UNION
            
                -- FACT
                SELECT
                    aal.account_id AS analytic_account_id,
                    aal.general_account_id AS account_id,
                    0::numeric AS plan,
                    aal.amount AS fact
                FROM account_analytic_line aal
            
            ) t
            left join account_analytic_account aaa on aaa.id = t.analytic_account_id  
            GROUP BY analytic_account_id, account_id, aaa.plan_id, aaa.account_cluster_id, aaa.account_business_unit_id, aaa.account_brand_id
        """ % self._table)

    def action_open_move_lines(self):
        self.ensure_one()

        domain = [
            ('account_id', '=', self.account_id.id),
        ]

        if self.analytic_account_id:
            domain.append(
                ('id', 'in', self.analytic_account_id.line_ids.move_line_id.ids)
            )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Items',
            'res_model': 'account.move.line',
            'view_mode': 'tree',
            'domain': domain,
        }

    # def action_open_move_list(self):
    #     self.ensure_one()
    #
    #     domain = [
    #         ('account_id', '=', self.account_id.id),
    #     ]
    #
    #     if self.analytic_account_id:
    #         domain.append(('analytic_account_id', '=', self.analytic_account_id.id))
    #
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Journal Entries',
    #         'res_model': 'account.move',
    #         'view_mode': 'tree',
    #         'domain': domain,
    #     }