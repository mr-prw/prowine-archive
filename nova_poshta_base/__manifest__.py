# -*- coding: utf-8 -*-
# Copyright (C) 2019 Yurii Razumovskyi <GarazdCreation@gmail.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
{
    'name': 'Nova Poshta Base',
    'version': '11.0.1.0.1',
    'category': 'Inventory',
    'author': 'Garazd Creation',
    'website': 'https://garazd.biz',
    'license': 'LGPL-3',
    'summary': """
        Integration with the Nova Poshta delivery service.
    """,
    'description': """
Nova Poshta Delivery: Synchronization of base catalogs.
Синхронізація основних каталогів зі службою доставки "Нова Пошта".
Синхронизация основных справочников со службой доставки "Новая Почта".

Технічна підтримка та розробка для Odoo
=======================================

Контакти для зв'язку з нами:

* support@garazd.biz
* `https://garazd.biz/page/contactus`_
.. _https://garazd.biz/page/contactus: https://garazd.biz/page/contactus

Пакети технічної підтримки: https://garazd.biz/page/odoo-support
    """,
    'images': ['static/description/banner.png'],
    'depends': [
        'product',
        'delivery',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/np_menu_views.xml',
        'views/np_config_views.xml',
        'views/np_area_views.xml',
        'views/np_warehouse_views.xml',
        'views/np_settlement_views.xml',
        'views/np_city_views.xml',
        'views/res_partner_views.xml',
    ],
    'external_dependencies': {
        'python': [
            'http',
            'json',
        ],
    },
    'application': False,
    'installable': True,
    'auto_install': False,
}
