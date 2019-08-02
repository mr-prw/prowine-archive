# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.osv import expression


class NovaPoshtaCity(models.Model):
    _name = "nova.poshta.city"
    _order = "code"

    ref = fields.Char('Ref')
    name = fields.Char('Name')
    name_ru = fields.Char('Name (RU)')
    code = fields.Integer('City ID')
    area = fields.Char('Area')
    area_id = fields.Many2one('nova.poshta.area', 'Area')
    settlement_type = fields.Char('Settlement Type')
    settlement_type_description = fields.Char(
        'Settlement Type Description'
    )
    settlement_type_description_ru = fields.Char(
        'Settlement Type Description (RU)'
    )
    delivery_1 = fields.Boolean('Delivery on Monday')
    delivery_2 = fields.Boolean('Delivery on Tuesday')
    delivery_3 = fields.Boolean('Delivery on Wednesday')
    delivery_4 = fields.Boolean('Delivery on Thursday')
    delivery_5 = fields.Boolean('Delivery on Friday')
    delivery_6 = fields.Boolean('Delivery on Saturday')
    delivery_7 = fields.Boolean('Delivery on Sunday')

    _sql_constraints = [
        ('nova_poshta_city_ref_uniq',
         'UNIQUE (ref)',
         'City Reference must be unique!')
    ]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator in ('ilike', 'like', '=', '=like', '=ilike'):
            domain = expression.AND([
                args or [],
                ['|', ('name_ru', operator, name), ('name', operator, name)]
            ])
            recs = self.search(domain, limit=limit)
            return recs.name_get()
        return super(NovaPoshtaCity, self).name_search(name, args, operator, limit)
