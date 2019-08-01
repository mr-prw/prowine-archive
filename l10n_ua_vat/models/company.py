# -*- coding: utf-8 -*-

from odoo import fields, models


class CompanySti(models.Model):
    _inherit = 'res.company'

    comp_sti = fields.Many2one(
        'account.sprsti',
        string="Податковий орган",
        ondelete='set null',
        help="Виберіть ДПІ в якій взято на облік "
        "ваше підприємство",
        index=True
    )
    kod_filii = fields.Char(
        string="Код філії",
        size=4
    )
    vat_account_id = fields.Many2one(
        'account.account',
        string="Рахунок ПДВ",
        domain="[('deprecated', '=', False), ('company_id', '=', id)]"
    )
    legal_status = fields.Selection(
        [('company', "Юридична ососба"), ('fop', "Фізична особа")],
        string="Юридичний статус",
        default='company',
    )
    vat20_tax_tag_id = fields.Many2one(
        'account.account.tag',
        string="Тег ПДВ 20%",
        domain="""[
            ('company_id', '=', id),
            ('applicability', '=', 'taxes'),
        ]"""
    )
    vat7_tax_tag_id = fields.Many2one(
        'account.account.tag',
        string="Тег ПДВ 7%",
        domain="""[
            ('company_id', '=', id),
            ('applicability', '=', 'taxes'),
        ]"""
    )
    vat0_tax_tag_id = fields.Many2one(
        'account.account.tag',
        string="Тег ПДВ 0%",
        domain="""[
            ('company_id', '=', id),
            ('applicability', '=', 'taxes'),
        ]"""
    )
    vatfree_tax_tag_id = fields.Many2one(
        'account.account.tag',
        string="Тег Звільнено від ПДВ",
        domain="""[
            ('company_id', '=', id),
            ('applicability', '=', 'taxes'),
        ]"""
    )
    vatnot_tax_tag_id = fields.Many2one(
        'account.account.tag',
        string="Тег Не є ПДВ",
        domain="""[
            ('company_id', '=', id),
            ('applicability', '=', 'taxes'),
        ]"""
    )

    responsible_employee_id = fields.Many2one(
        'hr.employee',
        string='Responsible person'
    )

    company_full_name = fields.Char(string='Company name')
