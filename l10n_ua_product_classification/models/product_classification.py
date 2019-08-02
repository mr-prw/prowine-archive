# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductClassification(models.Model):
    _name = 'product.classification'

    name = fields.Char('Code', index=True, default='-')
    main_name = fields.Char('Main Name')
    code = fields.Char('Name', index=True)
    description = fields.Char('Description')
    parent_id = fields.Many2one('product.classification', 'Parent', index=True, ondelete='cascade')
    childs = fields.One2many('product.classification', 'parent_id', 'Childs')
    excise_code = fields.Char(string="Excise code")
    item_count = fields.Integer(compute='_compute_item_count', store=True)

    @api.depends('childs')
    def _compute_item_count(self):
        for item in self:
            item.item_count = len(item.childs)

    @api.multi
    @api.depends('name')
    def name_get(self):
        result = []
        for el in self:
            if el.name:
                result.append((el.id, el.name))
            else:
                name = el.parent_id and el.parent_id.name or '-' + '/'
                result.append((el.id, name))
        return result
