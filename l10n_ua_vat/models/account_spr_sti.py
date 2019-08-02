# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SprSti(models.Model):
    _name = 'account.sprsti'
    _description = "Довідник ДПІ"

    c_reg = fields.Char(string="Код області", required=True)
    c_raj = fields.Char(string="Код адміністративного району", required=True)
    c_sti = fields.Char(string="Код територіального органу отримувача", required=True)
    name = fields.Char(string="Назва", required=True)
    name_raj = fields.Char(string="Район", required=True)
