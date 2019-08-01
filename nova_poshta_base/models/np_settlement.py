# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class NovaPoshtaSettlement(models.Model):
    _name = "nova.poshta.settlement"

    ref = fields.Char('Ref')
    name = fields.Char('Name')
    name_ru = fields.Char('Name (RU)')
    type = fields.Char('Settlement Type')
    type_description = fields.Char('Type Description')
    type_description_ru = fields.Char('Type Description (RU)')
    latitude = fields.Char('Latitude')
    longitude = fields.Char('Longitude')
    area = fields.Char('Area')
    area_id = fields.Many2one('nova.poshta.area', 'Area')
    region = fields.Char('Region')
    region_description = fields.Char('Region Description')
    region_description_ru = fields.Char('Region Description (RU)')
    index_1 = fields.Char('Index 1')
    index_2 = fields.Char('Index 2')
    index_coatsu_1 = fields.Char('Index COATSU 1')
    delivery_1 = fields.Boolean('Delivery on Monday')
    delivery_2 = fields.Boolean('Delivery on Tuesday')
    delivery_3 = fields.Boolean('Delivery on Wednesday')
    delivery_4 = fields.Boolean('Delivery on Thursday')
    delivery_5 = fields.Boolean('Delivery on Friday')
    delivery_6 = fields.Boolean('Delivery on Saturday')
    delivery_7 = fields.Boolean('Delivery on Sunday')
    warehouse = fields.Integer('Warehouse')

    _sql_constraints = [
        ('nova_poshta_settlement_ref_uniq',
         'UNIQUE (ref)',
         'Settlement Ref must be unique!')
    ]
