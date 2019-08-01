from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    sale_id = fields.Many2one(
        'sale.order',
        'Sale Order',
        compute='_compute_sale_id')

    @api.depends('invoice_line_ids.sale_line_ids')
    def _compute_sale_id(self):
        for inv in self:
            for inv_line in inv.invoice_line_ids:
                for sale_line in inv_line.sale_line_ids:
                    if sale_line.order_id:
                        inv.sale_id = sale_line.order_id
                        return


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    amount_tax = fields.Monetary(string='Amount Tax', compute='_compute_amount_tax')


    @api.multi
    def _compute_amount_tax(self):
        for line in self:
            line.amount_tax = line.price_total - line.price_subtotal