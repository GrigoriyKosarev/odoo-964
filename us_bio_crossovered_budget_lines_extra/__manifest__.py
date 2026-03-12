# -*- coding: utf-8 -*-
{
    'name': 'UnitSoft - Extras Budgets Analysis for Biosphera project',
    'author': 'UnitSoft',
    'category': 'Accounting/Localizations/Base',
    'version': '16.0.0.1',
    'description': """
UnitSoft - Extras Budgets Analysis for Biosphera project.
=======================================================
    """,
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'account_budget',
        'us_bio_analytical_accounts_extra',
        ],
    'data': [
        'views/account_budget_views.xml',
    ],
    'assets': {
    },
    'auto_install': False,
}
