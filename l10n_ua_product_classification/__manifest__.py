# -*- coding: utf-8 -*-
{
    'name': 'Ukrainian Product Classification',
    'author': 'ERP Ukraine',
    'website': 'https://erp.co.ua',
    'support': 'support@erp.co.ua',
    'category': 'Sales',
    'depends': ['sale'],
    'version': '1.1',
    'license': 'Other proprietary',
    'price': 250.00,
    'currency': 'EUR',
    'description': """
    Ukrainian Classifier of Foreign Trade
    """,
    'auto_install': False,
    'demo': [],
    'data': [
        'security/ir.model.access.csv',
        'views/product_classification_views.xml',
        'data/product.classification.csv',
        # 'data/reference_book_trade_01_30.yml',
        # 'data/reference_book_trade_31_60.yml',
        # 'data/reference_book_trade_61_97.yml',
    ],
    'installable': True,
}
