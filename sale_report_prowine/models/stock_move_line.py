# -*- coding: utf-8 -*-

from odoo import models, _


class StockMoveLine(models.Model):
    _name = "stock.move.line"
    _inherit = "stock.move.line"
    _description = "Packing Operation"
    _rec_name = "product_id"
    _order = "location_id, result_package_id desc, id"
