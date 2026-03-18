import re
import logging

from odoo import api, models, fields, tools

_logger = logging.getLogger(__name__)


class BudgetFactReport(models.Model):
    _name = "budget.fact.report"
    _description = "Budget vs Fact Report"
    _auto = False

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account"
    )
    plan_id = fields.Many2one('account.analytic.plan', 'Plan')
    plan_name = fields.Char(string="Plan Name")
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
        _logger.info("_rebuild_view called: date_from=%s, date_to=%s", date_from, date_to)
        where_plan = ""
        where_fact = ""
        params_plan = []
        params_fact = []
        if date_from:
            where_plan += " AND cbl.date_from >= %s"
            where_fact += " AND aal.date >= %s"
            params_plan.append(date_from)
            params_fact.append(date_from)
        if date_to:
            where_plan += " AND cbl.date_to <= %s"
            where_fact += " AND aal.date <= %s"
            params_plan.append(date_to)
            params_fact.append(date_to)
        params = params_plan + params_fact

        _logger.info("_rebuild_view: where_plan='%s', where_fact='%s', params=%s",
                      where_plan, where_fact, params)

        tools.drop_view_if_exists(self.env.cr, self._table)

        query = """
            CREATE OR REPLACE VIEW %s AS
            SELECT
                row_number() OVER() AS id,
                analytic_account_id,
                aaa.plan_id as plan_id,
                aap.name as plan_name,
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
                WHERE cbl.planned_amount > 0 %s

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
            LEFT JOIN account_analytic_account aaa ON aaa.id = t.analytic_account_id
            LEFT JOIN account_analytic_plan aap ON aap.id = aaa.plan_id
            GROUP BY analytic_account_id, account_id, aaa.plan_id, aap.name, aaa.account_cluster_id, aaa.account_business_unit_id, aaa.account_brand_id
        """ % (self._table, where_plan, where_fact)

        _logger.info("_rebuild_view: executing SQL (length=%d)", len(query))
        self.env.cr.execute(query, params)

        # Verify: count rows in rebuilt view
        self.env.cr.execute("SELECT count(*) FROM %s" % self._table)
        row_count = self.env.cr.fetchone()[0]
        _logger.info("_rebuild_view: view rebuilt OK, row_count=%d", row_count)

    @api.model
    def apply_date_filter(self, date_from=False, date_to=False):
        """Called from JS to rebuild the SQL VIEW with date filters."""
        _logger.info("apply_date_filter: date_from=%s, date_to=%s", date_from, date_to)
        date_re = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        if date_from and not date_re.match(date_from):
            date_from = False
        if date_to and not date_re.match(date_to):
            date_to = False
        self._rebuild_view(
            date_from=date_from or None,
            date_to=date_to or None,
        )
        return True

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
