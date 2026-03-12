# -*- coding: utf-8 -*-

{
    'name': 'UnitSoft - Extras Analytical Accounts for Biosphera project',
    'author': 'UnitSoft',
    'category': 'Accounting/Localizations/Base',
    'version': '16.0.0.1',
    'description': """
UnitSoft. Extras Analytical Accounts for Biosphera project.
=======================================================
    """,
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'us_product_extra',
        ],
    'data': [
        'views/account_analytic_account_views.xml',
        'views/account_analytic_plan_views.xml',
        'views/res_partner_view.xml',
        'views/product_product_line_view.xml',
    ],
    'assets': {
    },
    'auto_install': False,
}
