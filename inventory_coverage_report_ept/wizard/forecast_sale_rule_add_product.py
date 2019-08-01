from odoo import models, fields, api

class forecast_sale_rule_wizard_ept(models.TransientModel):
    _name = "forecast.sale.rule.add.product"
 
    product_ids =fields.Many2many("product.product",string= 'Products')
    sale_ratio = fields.Float(string="Sale Ratio")
    
    @api.multi
    def add_products(self):
        if  self._context.get('active_id'):
            for product in self.product_ids:
                val = {'forecast_sale_rule_id':self._context.get('active_id') ,
                       'product_id': product.id,
                       'sale_ratio': self.sale_ratio ,
                       }
                self.env['forecast.sale.rule.line.ept'].create(val)
