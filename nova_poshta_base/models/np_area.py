# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class NovaPoshtaArea(models.Model):
    _name = "nova.poshta.area"

    ref = fields.Char('Ref')
    name = fields.Char('Area Name')
    center = fields.Char('Areas Center')

    _sql_constraints = [
        ('nova_poshta_area_ref_uniq',
         'UNIQUE (ref)',
         'Area Ref must be unique!')
    ]
