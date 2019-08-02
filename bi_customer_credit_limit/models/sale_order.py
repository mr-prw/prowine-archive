# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
from odoo import models, fields, exceptions, api, _
from odoo.exceptions import UserError

class sale_order(models.Model):
    _inherit = 'sale.order'

    credit_limit_id = fields.Integer(string="Credit Limit")
    total_receivable = fields.Integer(string="Amount Receivable",compute='_compute_total_receivable')

    #res_partner_id = fields.Many2one('res.partner')
    #credit_limit_id = fields.Float(string='Credit Limit',related='res_partner_id.credit_limit',readonly=True)
    
    @api.multi
    def _compute_total_receivable(self):
        self.update({'total_receivable':self.partner_id.credit})




  


















            
    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment term
        - Invoice address
        - Delivery address
        - Credit Limit
        - Amount Receivable
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'note': self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note,
            'credit_limit_id': self.partner_id.credit_limit,
            'total_receivable': self.partner_id.credit,
        }
        
        if self.partner_id.user_id:
            values['user_id'] = self.partner_id.user_id.id
        if self.partner_id.team_id:
            values['team_id'] = self.partner_id.team_id.id
        self.update(values)

    @api.multi
    def action_confirm(self):
        res = super(sale_order, self).action_confirm()
        partner = self.partner_id
        
        account_move_line = self.env['account.move.line']
        account_move_line = account_move_line.\
            search([('partner_id', '=', partner.id),
                    ('account_id.user_type_id.name', 'in',
                     ['Receivable', 'Payable'])
                    ])
                    
        debit, credit = 0.0, 0.0
        for line in account_move_line:
            credit += line.debit
            debit += line.credit
                
        for order in self:
            
            
            if (credit - debit + self.amount_total) > partner.credit_limit:
                if not partner.override_limit:
                    order.write({'credit_limit_id':partner.credit_limit})
                    raise UserError(_('You can not confirm sale order, Please check partner credit and amount receivable'))
                    return False
                else:
                    partner.write({
                        'credit_limit': credit - debit + self.amount_total})
                    order.write({'credit_limit_id':partner.credit_limit})
                    return True
            else:
                order.write({'credit_limit_id':partner.credit_limit})
                return True
        return res
            
class res_partner(models.Model):
    _inherit = 'res.partner'

    #res_credit_limit = fields.Integer(string="Credit Limit")
    override_limit = fields.Boolean(string="Allow Override")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
    
