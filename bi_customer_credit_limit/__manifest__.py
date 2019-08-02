# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Customer Credit Warning on Sales',
    'version': '11.0.0.1',
    'sequence': 4,
    'summary': 'Customer credit limit warning agaist account receivable amount',
    'description': """ This openerp module show credit limit on partner, Account receivable amount agaist credit limit, Partner credit limit Warning, customer credit limit Warning, Total Account Receivable amount on sale. AR on sales,Partner AR agaist credit limit, ovedue warning, customer warning , customer credit warning,Customer Credit limit Warning on Sales, Sales Credit Warning Against AR.Payment credit warning, Account limit warning, Client overdemand warning, Client overlimit warning.
    """,
    'category' : 'Sales',
    'author': 'BrowseInfo',
    'website': '',
    'depends': ['base','sale_management','account'],
    'data': [
             "views/sale_order.xml"
             ],
	'qweb': [
		],
    'demo': [],
    'price': '20',
    'currency': "EUR",
    'test': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    "images":['static/description/banner.png'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
