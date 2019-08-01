# -*- coding: utf-8 -*-
{
    'name': 'Bill of lading',
    'author': "ERP Ukraine",
    'website': "https://erp.co.ua",
    'support': 'support@erp.co.ua',
    'license': 'Other proprietary',
    'price': 50.00,
    'currency': 'EUR',
    'category': 'Sales',
    'depends': ['sale',
                'stock',
                'delivery',
                'fleet',
                'l10n_ua',
                ],
    'version': '2.1',
    'description': """
    * Bill of lading
    """,

    'auto_install': False,
    'data': [
        'security/ir.model.access.csv',
        'report/report_paperformat.xml',
        'templates/report_bill.xml',
        'views/picking_view.xml',
        'views/fleet_vehicle_views.xml',
             ],
    'installable': True,
}
