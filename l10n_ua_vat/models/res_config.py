# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    comp_sti = fields.Many2one(
        'account.sprsti',
        string="Податковий орган",
        related='company_id.comp_sti',
        help="Виберіть ДПІ в якій взято на облік "
        "ваше підприємство",
    )
    kod_filii = fields.Char(
        string="Код філії",
        related='company_id.kod_filii',
        size=4
    )
    vat_account_id = fields.Many2one(
        'account.account',
        related='company_id.vat_account_id',
        domain=lambda self: [('deprecated', '=', False)],
        string="Рахунок ПДВ",
    )
    legal_status = fields.Selection(
        [('company', "Юридична особа"), ('fop', "Фізична особа")],
        related='company_id.legal_status',
        string="Юридичний статус",
        default='company',
    )
    vat20_tax_tag_id = fields.Many2one(
        'account.account.tag',
        string="Тег ПДВ 20%",
        related='company_id.vat20_tax_tag_id',
        domain=lambda self: [
            ('applicability', '=', 'taxes'),
        ]
    )
    vat7_tax_tag_id = fields.Many2one(
        'account.account.tag',
        string="Тег ПДВ 7%",
        related='company_id.vat7_tax_tag_id',
        domain=lambda self: [
            ('applicability', '=', 'taxes'),
        ]
    )
    vat0_tax_tag_id = fields.Many2one(
        'account.account.tag',
        string="Тег ПДВ 0%",
        related='company_id.vat0_tax_tag_id',
        domain=lambda self: [
            ('applicability', '=', 'taxes'),
        ]
    )
    vatfree_tax_tag_id = fields.Many2one(
        'account.account.tag',
        string="Тег Звільнено від ПДВ",
        related='company_id.vatfree_tax_tag_id',
        domain=lambda self: [
            ('applicability', '=', 'taxes'),
        ]
    )
    vatnot_tax_tag_id = fields.Many2one(
        'account.account.tag',
        string="Тег Не є ПДВ",
        related='company_id.vatnot_tax_tag_id',
        domain=lambda self: [
            ('applicability', '=', 'taxes'),
        ]
    )

    responsible_employee_id = fields.Many2one(
        'hr.employee',
        string='Responsible person',
        related='company_id.responsible_employee_id'
    )

    company_full_name = fields.Char(
        string='Company name',
        related='company_id.company_full_name')
