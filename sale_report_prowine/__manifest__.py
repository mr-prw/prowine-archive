# -*- coding: utf-8 -*-
{
    'name': 'Sales Invoice Reports Prowine',
    'author': 'ERP Ukraine',
    'website': 'https://erp.co.ua',
    'support': 'support@erp.co.ua',
    'category': 'Sales',
    'description': """
    * v1.4: Fixed move line list on picking form.
    """,
    'depends': ['sale',
                'sale_stock',
                'stock',
                'account'],
    'version': '1.7',
    'license': 'Other proprietary',
    'price': 50.00,
    'currency': 'EUR',
    'description': """""",
    'auto_install': False,
    'demo': [],
    'data': [
        'views/sales_invoice_report.xml',
        'views/sale_order_template.xml',
        'views/stock_picking_views.xml',
        'views/stockpicking_operations_report.xml',
        'views/stock_warehouse_views.xml',
        'views/deliveryslip_template.xml',
    ],
    'installable': True,
    'application': True,
}
