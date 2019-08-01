# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
from odoo import models, fields, exceptions, api, _
from odoo.exceptions import UserError




class account_invoice(models.Model):
    _inherit = 'account.invoice'

    credit_limit_id = fields.Integer(string="Credit Limit")
    total_receivable = fields.Integer(string="Amount Receivable",compute='_compute_total_receivable')


    
    @api.multi
    def _compute_total_receivable(self):
        self.update({'total_receivable':self.partner_id.credit})





    @api.model
    def create(self, val):
        
        if val.get('partner_id'):
           partner_id = self.env['res.partner'].browse(val.get('partner_id')) 
           val.update({'credit_limit_id':partner_id.credit_limit})
        res = super(account_invoice, self).create(val)
        return res   





    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        account_id = False
        payment_term_id = False
        fiscal_position = False
        bank_id = False
        warning = {}
        domain = {}
        company_id = self.company_id.id
        p = self.partner_id if not company_id else self.partner_id.with_context(force_company=company_id)
        type = self.type
        if p:
            rec_account = p.property_account_receivable_id
            pay_account = p.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

            if type in ('out_invoice', 'out_refund'):
                account_id = rec_account.id
                payment_term_id = p.property_payment_term_id.id
            else:
                account_id = pay_account.id
                payment_term_id = p.property_supplier_payment_term_id.id

            delivery_partner_id = self.get_delivery_partner_id()
            fiscal_position = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id, delivery_id=delivery_partner_id)

            # If partner has no warning, check its company
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                    p = p.parent_id
                warning = {
                    'title': _("Warning for %s") % p.name,
                    'message': p.invoice_warn_msg
                    }
                if p.invoice_warn == 'block':
                    self.partner_id = False

        self.account_id = account_id
        self.payment_term_id = payment_term_id
        self.date_due = False
        self.fiscal_position_id = fiscal_position

        self.credit_limit_id = self.partner_id.credit_limit
        self.total_receivable = self.partner_id.credit


        if type in ('in_invoice', 'out_refund'):
            bank_ids = p.commercial_partner_id.bank_ids
            bank_id = bank_ids[0].id if bank_ids else False
            self.partner_bank_id = bank_id
            domain = {'partner_bank_id': [('id', 'in', bank_ids.ids)]}

        res = {}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res












    @api.multi
    def action_invoice_open(self):
        res = super(account_invoice, self).action_invoice_open()
        
        account_move_line = self.env['account.move.line']
        account_move_line = account_move_line.\
            search([('partner_id', '=', self.partner_id.id),
                    ('account_id.user_type_id.name', 'in',
                     ['Receivable', 'Payable'])
                    ])
                    
        debit, credit = 0.0, 0.0
        for line in account_move_line:
            credit += line.debit
            debit += line.credit
                
        for order in self:
            
            
            if (credit - debit + self.amount_total) > order.partner_id.credit_limit:
                if not order.partner_id.override_limit:
                    order.write({'credit_limit_id':order.partner_id.credit_limit})
                    raise UserError(_('You can not confirm invoice , Please check partner credit and amount receivable'))
                    return False
                else:
                    order.partner_id.write({
                        'credit_limit': credit - debit + self.amount_total})
                    order.write({'credit_limit_id':order.partner_id.credit_limit})
                    return True
            else:
                order.write({'credit_limit_id':order.partner_id.credit_limit})
                return True
        return res




