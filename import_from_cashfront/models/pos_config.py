# -*- coding: utf-8 -*-
from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    is_ftp = fields.Boolean(string='Use FTP')
    path = fields.Char(string='Path')
