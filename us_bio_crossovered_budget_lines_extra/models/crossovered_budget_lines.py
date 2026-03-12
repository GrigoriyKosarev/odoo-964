# -*- coding: utf-8 -*-

from odoo import fields, models


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    account_cluster_id = fields.Many2one(
        comodel_name="account.analytic.account",
        related="analytic_account_id.account_cluster_id",
        store=True,
        readonly=True,
    )

    account_business_unit_id = fields.Many2one(
        comodel_name="account.analytic.account",
        related="analytic_account_id.account_business_unit_id",
        store=True,
        readonly=True,
    )

    account_brand_id = fields.Many2one(
        comodel_name="account.analytic.account",
        related="analytic_account_id.account_brand_id",
        store=True,
        readonly=True,
    )

    is_grouped_account = fields.Boolean(
        related="analytic_account_id.is_grouped_account",
        store=True,
        readonly=True,
    )

    plan_type = fields.Selection(
        related="analytic_account_id.plan_id.type",
        store=True,
        readonly=True,
    )