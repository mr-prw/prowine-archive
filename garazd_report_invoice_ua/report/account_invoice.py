# -*- coding: utf-8 -*-

import decimal
from . import num2t4ua
from odoo import api, models


class report_invoice_ua(models.AbstractModel):
    _name = 'report.garazd_report_invoice_ua.report_invoice_ua_template'

    @api.model
    def get_report_values(self, docids, data=None):
        docs = self.env['account.invoice'].browse(docids)
        ttn = {}
        leave_allowed = {}
        client_order_ref = {}
        total_char = {}
        tax_char = {}
        for doc in docs:
            total_char[doc.id] = 'Усього сума ' + num2t4ua.decimal2text(
                decimal.Decimal(doc.amount_total))
            tax_char[doc.id] = 'Сума ПДВ ' + num2t4ua.decimal2text(
                decimal.Decimal(doc.amount_tax))
            sale_order = self.env['sale.order'].search([('name','=',doc.origin)])
            if sale_order:
                client_order_ref[doc.id] = sale_order.client_order_ref
            leave_allowed[doc.id] = False
            ttn[doc.id] = False
            for picking in sale_order.picking_ids.filtered(lambda x: x.location_dest_id.usage == 'customer' and x.state == 'done'):
                ttn[doc.id] = picking.name
                if picking.leave_allowed:
                    leave_allowed[doc.id] = picking.leave_allowed.name
        return {
            'doc_ids': docs.ids,
            'doc_model': 'account.invoice',
            'docs': docs,
            'leave_allowed': leave_allowed,
            'ttn': ttn,
            'client_order_ref': client_order_ref,
            'total_char': total_char,
            'tax_char': tax_char,
        }
