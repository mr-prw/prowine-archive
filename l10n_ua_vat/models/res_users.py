# -*- coding: utf-8 -*-

from odoo import models, fields


class UserRDPY(models.Model):
    _inherit = 'res.users'

    user_ipn = fields.Char(string='ІПН', related='partner_id.company_registry')
