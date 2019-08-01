# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import binascii
import io
import logging
import tempfile

from odoo import models, fields, exceptions, api, _
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)

try:
    import xmlrpc
except ImportError:
    _logger.debug('Cannot `import xmlrpclib`.')

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')
# for xls
try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')

class gen_inv(models.TransientModel):
    _name = "gen.inv"

    file = fields.Binary('File')
    inv_name = fields.Char('Inventory Name')
    location_id = fields.Many2one('stock.location', "Location")
    import_option = fields.Selection([('csv', 'CSV File'),('xls', 'XLS File')],string='Select',default='csv')
    import_prod_option = fields.Selection([('barcode', 'Barcode'),('code', 'Code')],string='Import Product By ',default='code')
#    filename = fields.Char('Filename')

    @api.multi
    def import_csv(self):

        """Load Inventory data from the CSV file."""
        if self.import_option == 'csv':
            if not self.location_id:
                raise Warning(_('Please Select Location'))
            """Load Inventory data from the CSV file."""
            ctx = self._context
            keys=['code', 'quantity']
            stloc_obj = self.env['stock.location']
            inventory_obj = self.env['stock.inventory']
            product_obj = self.env['product.product']
            data = base64.b64decode(self.file)
#             file_input = cStringIO.StringIO(data)
            file_input = io.StringIO(data.decode("utf-8"))
            file_input.seek(0)
            reader_info = []
            reader = csv.reader(file_input, delimiter=',')

            try:
                reader_info.extend(reader)
            except Exception:
                raise exceptions.Warning(_("Not a valid file!"))
            values = {}
            inventory_id = inventory_obj.create({'name':self.inv_name})
            for i in range(len(reader_info)):
                if i!= 0:
                    val = {}
                    try:
                         field= map(str, reader_info[i])
                    except ValueError:
                         raise exceptions.Warning(_("Dont Use Charecter only use numbers"))

        #             field = reader_info[i]
                    values = dict(zip(keys, field))
                    if self.import_prod_option == 'barcode':
                        prod_lst = product_obj.search([('barcode',  '=',values['code'])])
                    else:
                        prod_lst = product_obj.search([('default_code', '=',
                                                    values['code'])])
                    if prod_lst:
                        val['product'] = prod_lst[0].id
                        val['quantity'] = values['quantity']
                    if bool(val):
                        product_uom_id=product_obj.browse(val['product']).uom_id
                        res = inventory_id.write({
                    'line_ids': [(0, 0, {'product_id':val['product'] , 'location_id' : self.location_id.id, 'product_uom_id' : product_uom_id.id  ,'product_qty': val['quantity']})]})
                    else:
                        raise Warning(_('Product Not Found  "%s"') % values.get('code'))
                res = inventory_obj.with_context(ids=inventory_id).prepare_inventory()
            return res
        else:
            if not self.location_id:
                raise Warning(_('Please Select Location'))
            fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)
            values = {}
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
            inventory_id = self.env['stock.inventory'].create({'name':self.inv_name})
            product_obj = self.env['product.product']
            for row_no in range(sheet.nrows):
                val = {}
                if row_no <= 0:
                    fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
                else:
                    line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
                    if line:
                        values.update({'code':line[0],'quantity':line[1]})
                        if self.import_prod_option == 'barcode':
                            prod_lst = product_obj.search([('barcode',  '=',values['code'])])
                        else:
                            prod_lst = product_obj.search([('default_code', '=',
                                                      values['code'])])
                        if prod_lst:
                            val['product'] = prod_lst[0].id
                            val['quantity'] = values['quantity']
                        if bool(val):
                            product_uom_id=product_obj.browse(val['product']).uom_id
                            res = inventory_id.write({
                        'line_ids': [(0, 0, {'product_id':val['product'] , 'location_id' : self.location_id.id, 'product_uom_id' : product_uom_id.id  ,'product_qty': val['quantity']})]})
                        else:
                            raise Warning(_('Product Not Found  "%s"') % values.get('code'))
            res = self.env['stock.inventory'].with_context(ids=inventory_id).prepare_inventory()
            return res




#
class stock_inventory(models.Model):
    _inherit = "stock.inventory"


    @api.multi
    def action_start(self):
        if self._context.get('ids'):
            self = self._context.get('ids')
            for inventory in self:
                vals = {'state': 'confirm', 'date': fields.Datetime.now()}
                if (inventory.filter != 'partial') and not inventory.line_ids:
                    vals.update({'line_ids': [(0, 0, line_values) for line_values in inventory.line_ids]})
                inventory.write(vals)
        else:
            super(stock_inventory, self).action_start()
        return True

    prepare_inventory = action_start

