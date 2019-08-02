# -*- coding: utf-8 -*-
{
    'name': "POS connector to Fiscal Printer BlackBox",
    'summary': """
        POS connector to Fiscal Printer BlackBox""",
    'description': """
Ukraine Fiscal POS Printer connector to ArtSoft Hardware Driver connector
=========================================================================

This module work with Ukrainian Fiscal Printers.
For his work need POS BlackBox with module hw_blackbox_ua!
This module redefine POS printing Order from Report to JSON 
for printing order in fiscal, low-level commands. 
        
    """,
    'author': "Oleksandr Komarov",
    'website': "https://modool.pro",
    'category': 'Point of Sale',
    'version': '11.0.0.1',
    'depends': ['point_of_sale',],
    'data': [
        'views/point_of_sale.xml',
        'views/pos_box.xml',
        'views/pos_session_view.xml',
    ]
}