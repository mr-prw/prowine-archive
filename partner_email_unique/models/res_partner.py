# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains('email')
    def _check_unique_email(self):
        for partner in self:
            if partner.email:
                duplicates = self.env['res.partner'].search([
                        ('email', '=ilike', partner.email),
                        ('id', '!=', partner.id)
                    ], order="id")
                if len(duplicates) > 0:
                    raise ValidationError(_('Partner e-mail must be unique! This email use the partner "%s"') % duplicates[0].name)
