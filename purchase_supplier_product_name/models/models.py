# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import AccessError


class PurchaseSupplierProductName(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def _add_supplier_to_product(self):
        for line in self.order_line:
            # Do not add a contact as a supplier
            partner = self.partner_id if not self.partner_id.parent_id else self.partner_id.parent_id
            if partner not in line.product_id.seller_ids.mapped('name') and len(line.product_id.seller_ids) <= 100:
                currency = partner.property_purchase_currency_id or self.env.user.company_id.currency_id
                supplierinfo = {
                    'name': partner.id,
                    'product_name': line.name,
                    'sequence': max(line.product_id.seller_ids.mapped('sequence')) + 1 if line.product_id.seller_ids else 1,
                    'product_uom': line.product_uom.id,
                    'min_qty': 0.0,
                    'price': self.currency_id.compute(line.price_unit, currency),
                    'currency_id': currency.id,
                    'delay': 0,
                }
                vals = {
                    'seller_ids': [(0, 0, supplierinfo)],
                }
                try:
                    line.product_id.write(vals)
                except AccessError:
                    break
