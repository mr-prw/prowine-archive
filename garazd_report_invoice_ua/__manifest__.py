# -*- coding: utf-8 -*-
# Copyright 2018 Yurii Razumovskyi <https://garazd.biz>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    'name' : 'Garazd Report Invoice for UA',
    'version': '1.0.1',
    'author': 'Garazd Creation',
    'website' : 'https://garazd.biz',
    'category': 'Sales',
    'depends' : ['account'],
    'description': """
        Report of Delivered Products for Ukraine.
    """,
    'data': [
        'report/account_invoice_reports.xml',
        'report/account_invoice_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
