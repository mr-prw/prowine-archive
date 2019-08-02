# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    np_city_id = fields.Many2one(
        comodel_name='nova.poshta.city',
        string='City',
    )
    np_city_ref = fields.Char(
        related='np_city_id.ref',
        help="Domain for warehouse by city referance",
    )
    np_warehouse_id = fields.Many2one(
        comodel_name='nova.poshta.warehouse',
        string='NP Warehouse',
    )
