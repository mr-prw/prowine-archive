# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResPartnerKod(models.Model):
    _inherit = 'res.partner'

    kod_filii = fields.Char(string="Код філії", size=4)
    default_ipn = fields.Boolean(string="Неплатник ПДВ", default=False)

    @api.onchange('default_ipn')
    def _fill_ipt(self):
        self.ensure_one()
        if self.default_ipn:
            self.update({'vat': '100000000000'})
        else:
            self.update({'vat': False})


ResPartnerKod()
