import re

from odoo import api, models, fields, tools


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
        self._rebuild_view()

    def _rebuild_view(self, date_from=None, date_to=None):
        where_fact = ""
        params = []
        if date_from:
            where_fact += " AND aal.date >= %s"
            params.append(date_from)
        if date_to:
            where_fact += " AND aal.date <= %s"
            params.append(date_to)

        tools.drop_view_if_exists(self.env.cr, self._table)

        query = """
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
                WHERE 1=1 %s

            ) t
            left join account_analytic_account aaa on aaa.id = t.analytic_account_id
            GROUP BY analytic_account_id, account_id, aaa.plan_id, aaa.account_cluster_id, aaa.account_business_unit_id, aaa.account_brand_id
        """ % (self._table, where_fact)

        self.env.cr.execute(query, params)

    def _apply_date_context(self):
        """Rebuild VIEW if date_from/date_to present in context."""
        date_from = self.env.context.get('date_from')
        date_to = self.env.context.get('date_to')
        if date_from or date_to:
            # Validate date format to prevent injection
            date_re = re.compile(r'^\d{4}-\d{2}-\d{2}$')
            if date_from and not date_re.match(date_from):
                date_from = None
            if date_to and not date_re.match(date_to):
                date_to = None
            self._rebuild_view(date_from=date_from, date_to=date_to)
        else:
            self._rebuild_view()

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        self._apply_date_context()
        return super().search_read(domain, fields, offset, limit, order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        self._apply_date_context()
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

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