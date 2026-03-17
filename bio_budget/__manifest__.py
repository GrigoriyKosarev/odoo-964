# -*- coding: utf-8 -*-

{
    "name": 'Biosphera - Budget',
    "author": 'Biosphera',
    'category': 'Accounting/Localizations/Base',
    'version': '16.0.1.0.0',
    'description': 'Biosphera. Budget',
    'license': 'LGPL-3',
    'depends': ['account',
                'us_bio_analytical_accounts_extra',
                ],
    'data': ['security/ir.model.access.csv',
             'data/account_move_line_action.xml',
             'reports/crossovered_budget_report.xml',
             ],
    'assets': {
        'web.assets_backend': [
            'bio_budget/static/src/views/budget_fact_report_view.js',
            'bio_budget/static/src/views/budget_fact_report_view.xml',
        ],
    },
    'auto_install': False,
}
