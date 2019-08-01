# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import ast


class ProductTemplUktZed(models.Model):
    _inherit = 'product.template'

    excise_code = fields.Char(
        related='product_variant_ids.excise_code',
        string='Excise code')

    ukt_zed = fields.Char(
        related='product_variant_ids.ukt_zed',
        string="Код УКТ ЗЕД",
        help="Код товару згідно УКТ ЗЕД",
        store=True)

    ukt_zed_id = fields.Many2one('product.classification',
                                 related='product_variant_ids.ukt_zed_id',
                                 string='УКТ ЗЕД'
                                 )
    dkpp = fields.Char(
        related='product_variant_ids.dkpp',
        string="Код ДКПП",
        help="Код послуг згідно ДКПП")
    vd_sgt = fields.Char(
        related='product_variant_ids.vd_sgt',
        string="Код ВД СГТ",
        help="Код виду діяльності сільськогосподарського товаровиробника")
    exemption = fields.Char(
        related='product_variant_ids.exemption',
        string="Код пільги",
        help="Код пільги або номер пункту ПКУ")
    is_imported = fields.Boolean(
        related='product_variant_ids.is_imported',
        string="Імпортований",
        help="Ознака імпортованого товару")
    prev_values = fields.Char(
        string="Зберігає попередні значення: УКТ ЗЕД, ДКПП, Імпортований")

    @api.onchange('type')
    def clear_uktzed_dkpp(self):
        self.ensure_one()
        if not self.prev_values:
            self.update({
                'prev_values': dict(ukt_zed_id=self.ukt_zed_id.id, dkpp=self.dkpp,
                                    is_imp=self.is_imported, type=self.type)
            })
        prev_dict = ast.literal_eval(self.prev_values)
        if self.type != 'service':
            if prev_dict['type'] == 'service':
                prev_dict['dkpp'] = self.dkpp
            else:
                prev_dict['ukt_zed_id'] = self.ukt_zed_id.id
                prev_dict['is_imp'] = self.is_imported

            prev_dict['type'] = self.type
            self.update({
                'ukt_zed_id': prev_dict['ukt_zed_id'],
                'dkpp': None,
                'is_imported': prev_dict['is_imp']
            })
        else:
            prev_dict['ukt_zed_id'] = self.ukt_zed_id.id
            prev_dict['is_imp'] = self.is_imported
            prev_dict['type'] = self.type

            self.update({
                'ukt_zed_id': None,
                'dkpp': prev_dict['dkpp'],
                'is_imported': None
            })
        self.prev_values = prev_dict


class ProductUktZed(models.Model):
    _inherit = 'product.product'

    excise_code = fields.Char(string="Excise code")
    ukt_zed_id = fields.Many2one('product.classification',
                                 string='УКТ ЗЕД')
    ukt_zed = fields.Char(
        string="Код УКТ ЗЕД",
        help="Код товару згідно УКТ ЗЕД",
        size=10)

    dkpp = fields.Char(
        string="Код ДКПП",
        help="Код послуг згідно ДКПП")
    vd_sgt = fields.Char(
        string="Код ВД СГТ",
        help="Код виду діяльності сільськогосподарського товаровиробника")
    exemption = fields.Char(
        string="Код пільги",
        help="Код пільги або номер пункту ПКУ")
    is_imported = fields.Boolean(
        string="Імпортований",
        help="Ознака імпортованого товару")
    prev_values = fields.Char(
        string="Зберігає попередні значення: УКТ ЗЕД, ДКПП, Імпортований")

    @api.onchange('type')
    def clear_uktzed_dkpp(self):
        self.ensure_one()
        if not self.prev_values:
            self.update({
                'prev_values': dict(ukt_zed_id=self.ukt_zed_id.id, dkpp=self.dkpp,
                                    is_imp=self.is_imported, type=self.type)
            })
        prev_dict = ast.literal_eval(self.prev_values)
        if self.type != 'service':
            if prev_dict['type'] == 'service':
                prev_dict['dkpp'] = self.dkpp
            else:
                prev_dict['ukt_zed_id'] = self.ukt_zed_id.id
                prev_dict['is_imp'] = self.is_imported

            prev_dict['type'] = self.type
            self.update({
                'ukt_zed_id': prev_dict['ukt_zed_id'],
                'dkpp': None,
                'is_imported': prev_dict['is_imp']
            })
        else:
            prev_dict['ukt_zed_id'] = self.ukt_zed_id.id
            prev_dict['is_imp'] = self.is_imported
            prev_dict['type'] = self.type

            self.update({
                'ukt_zed_id': None,
                'dkpp': prev_dict['dkpp'],
                'is_imported': None
            })
        self.prev_values = prev_dict


class ProductUomCode(models.Model):
    _inherit = 'product.uom'

    uom_code = fields.Char(
        string="Код одиниць виміру",
        help="Код згідно КСПОВО",
        size=4)
