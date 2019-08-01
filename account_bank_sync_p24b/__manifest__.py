# -*- coding: utf-8 -*-
{
    'name': 'PrivatBank online synchronization',
    'author': 'ERP Ukraine',
    'website': 'https://erp.co.ua',
    'support': 'support@erp.co.ua',
    'summary': u"Sync statements with PrivatBank online",
    'category': 'Accounting & Finance',
    'version': '1.7',
    'license': 'Other proprietary',
    'price': 250.00,
    'currency': 'EUR',
    'auto_install': False,
    'demo': [],
    'depends': ['account'],
    'data': [
        'wizard/p24b_bank_sync_wizard_view.xml',
        'views/account_journal_view.xml',
        'views/account_payment_view.xml'
    ],
    'installable': True,
    'application': True,
}
