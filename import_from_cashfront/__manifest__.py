# -*- coding: utf-8 -*-
{
    'name': 'Import sold product from CashFront',
    'author': 'ERP Ukraine',
    'website': 'https://erp.co.ua',
    'support': 'support@erp.co.ua',
    'category': 'Sales',
    'depends': [
        'sale',
        'point_of_sale'
    ],
    'version': '1.2',
    'license': 'Other proprietary',
    'price': 50.00,
    'currency': 'EUR',
    'description': """""",
    'auto_install': False,
    'demo': [],
    'data': [
        'views/pos_config_view.xml',
        'wizard/pos_order_import_wizard.xml',
        'data/import_from_cashfront.xml',
    ],
    'installable': True,
    'application': True,
}
