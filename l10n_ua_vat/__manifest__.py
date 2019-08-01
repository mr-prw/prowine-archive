# -*- coding: utf-8 -*-
{
    'name': "Ukraine - Accounting VAT support",
    'summary': """Облік ПДВ для України""",
    'description': """
        Цей модуль дає можливість вести облік виданих
        та отриманих податкових накладних.

        Конфліктує з модулем: base_vat
    """,
    'author': "ERP Ukraine",
    'website': "https://erp.co.ua",
    'support': 'support@erp.co.ua',
    'category': 'Localization/Account Charts',
    'version': '2.7',
    'license': 'Other proprietary',
    'price': 500.00,
    'currency': 'EUR',
    'depends': [
        'account',
        'hr',
        'l10n_ua',
        'purchase_supplier_product_name',
        'l10n_ua_product_classification',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/taxinvoice_security.xml',
        'wizard/account_single_tax_invoice_export_wizard.xml',
        'views/account_tax_invoice_view.xml',
        'views/res_users_simplified.xml',
        'views/account_spr_sti_view.xml',
        'views/export_template.xml',
        'views/company_view.xml',
        'views/product_view.xml',
        'views/partner_view.xml',
        'views/account_invoice_view.xml',
        'views/res_config_view.xml',
        'wizard/account_tax_invoice_export_wizard.xml',
        'wizard/account_tax_invoice_import_wizard.xml',
        'data/account.sprsti.csv',
        'data/taxinvoice_paymeth_data.xml',
        'data/account.taxinvoice.contrtype.csv',
        'data/out_taxinvoice_sequence.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
