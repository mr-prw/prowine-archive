# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class NovaPoshtaWarehouse(models.Model):
    _name = "nova.poshta.warehouse"

    ref = fields.Char('Ref')
    name = fields.Char('Name')
    name_ru = fields.Char('Name (RU)')
    type = fields.Char('Type of warehouse')
    site_key = fields.Integer('Warehouse Code')
    number = fields.Integer('Warehouse Number')
    city_ref = fields.Char('City Ref')
    city_description = fields.Char('City Description')
    city_description_ru = fields.Char('City Description (RU)')

    _sql_constraints = [
        ('nova_poshta_warehouse_ref_uniq',
         'UNIQUE (ref)',
         'Warehouse Ref must be unique!')
    ]
