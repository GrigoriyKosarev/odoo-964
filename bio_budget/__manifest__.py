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
             'reports/crossovered_budget_report.xml',
             ],
    'assets': {
    },
    'auto_install': False,
}
