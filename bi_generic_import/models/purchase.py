# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import binascii
import io
import logging
import tempfile
from datetime import datetime

import xlrd
from odoo import models, fields, exceptions, api, _
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)

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

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    custom_seq = fields.Boolean('Custom Sequence')
    system_seq = fields.Boolean('System Sequence')

class gen_purchase(models.TransientModel):
    _name = "gen.purchase"

    file = fields.Binary('File')
    sequence_opt = fields.Selection([('custom', 'Use Excel/CSV Sequence Number'), ('system', 'Use System Default Sequence Number')], string='Sequence Option',default='custom')
    import_option = fields.Selection([('csv', 'CSV File'), ('xls', 'XLS File')], string='Select', default='csv')

    @api.multi
    def make_purchase(self, values):
    	purchase_obj = self.env['purchase.order']
    	pur_search = purchase_obj.search([
                                                 ('name', '=', values.get('purchase_no')),
                                                 ])
    	if pur_search:
        	if pur_search.partner_id.name == values.get('vendor'):
        	    if  pur_search.currency_id.name == values.get('currency'):
        	        lines = self.make_purchase_line(values, pur_search)
        	        return lines
        	    else:
        	        raise Warning(_('Currency is different for "%s" .\n Please define same.') % values.get('currency'))
        	else:
        	    raise Warning(_('Customer name is different for "%s" .\n Please define same.') % values.get('vendor'))
    	else:
            if values.get('seq_opt') == 'system':
                name = self.env['ir.sequence'].next_by_code('purchase.order')
            elif values.get('seq_opt') == 'custom':
                name = values.get('purchase_no')
            partner_id = self.find_partner(values.get('vendor'))
            currency_id = self.find_currency(values.get('currency'))
            pur_date = self.make_purchase_date(values.get('date'))

            if partner_id.property_account_receivable_id:
                account_id = partner_id.property_account_payable_id
            else:
                account_search = self.env['ir.property'].search([('name', '=', 'property_account_expense_categ_id')])
                account_id = account_search.value_reference
                account_id = account_id.split(",")[1]
                account_id = self.env['account.account'].browse(account_id)
            pur_id = purchase_obj.create({
                                     'account_id' : account_id.id,
                                    'partner_id' : partner_id.id,
                                    'currency_id' : currency_id.id,
                                    'name':name,
                                    'date_order':pur_date,
                                    'custom_seq': True if values.get('seq_opt') == 'custom' else False,
                                    'system_seq': True if values.get('seq_opt') == 'system' else False,
                                    })
    	lines = self.make_purchase_line(values, pur_id)
    	return lines



    @api.multi
    def make_purchase_date(self, date):
        DATETIME_FORMAT = "%Y-%m-%d"
        i_date = datetime.strptime(date, DATETIME_FORMAT)
        return i_date


    @api.multi
    def make_purchase_line(self, values, pur_id):
        product_obj = self.env['product.product']
        account = False
        invoice_line_obj = self.env['purchase.order.line']
        product_search = product_obj.search([('default_code', '=', values.get('product'))])
        product_uom = self.env['product.uom'].search([('name', '=', values.get('uom'))])
        tax_ids = []
        if values.get('tax'):
            if ';' in  values.get('tax'):
                tax_names = values.get('tax').split(';')
                for name in tax_names:
                    tax= self.env['account.tax'].search([('name', '=', name),('type_tax_use','=','sale')])
                    if not tax:
                        raise Warning(_('"%s" Tax not in your system') % name)
                    tax_ids.append(tax.id)

            elif ',' in  values.get('tax'):
                tax_names = values.get('tax').split(',')
                for name in tax_names:
                    tax= self.env['account.tax'].search([('name', '=', name),('type_tax_use','=','sale')])
                    if not tax:
                        raise Warning(_('"%s" Tax not in your system') % name)
                    tax_ids.append(tax.id)
            else:
                tax_names = values.get('tax')
                tax= self.env['account.tax'].search([('name', '=', tax_names),('type_tax_use','=','sale')])
                if not tax:
                    raise Warning(_('"%s" Tax not in your system') % tax_names)
                tax_ids.append(tax.id)
        if product_search:
            product_id = product_search
        else:
            product_id = product_obj.search([('name', '=', values.get('product'))])
            if not product_id:
                product_id = product_obj.create({'name': values.get('product'),
                                                 'uom_id':product_uom.id,
                                              'uom_po_id':product_uom.id
                                                 })
        if product_uom.id == False:
            raise Warning(_(' "%s" Product UOM category is not available.') % values.get('uom'))

        if product_id.property_account_expense_id:
            account = product_id.property_account_expense_id
        elif product_id.categ_id.property_account_expense_categ_id:
            account = product_id.categ_id.property_account_expense_categ_id
        else:
                account_search = self.env['ir.property'].search([('name', '=', 'property_account_expense_categ_id')])
                account = account_search.value_reference
                account = account.split(",")[1]
                account = self.env['account.account'].browse(account)
        dict = {
                'product_id' : product_id.id,
                'quantity' : values.get('quantity'),
                'price_unit' : values.get('price'),
                'name' : values.get('description'),
                'account_id' : account.id,
                'product_uom' : product_uom.id,
                'purchase_id' : pur_id.id
                }
        res = invoice_line_obj.create({
                'product_id' : product_id.id,
                'product_qty' : values.get('quantity'),
                'price_unit' : values.get('price'),
                'name' : values.get('description'),
                'product_uom' : product_uom.id,
                'order_id' : pur_id.id,
                'date_planned': datetime.now()
                })
        if tax_ids:
            res.write({'taxes_id':([(6, 0, tax_ids)])})
        return True

    @api.multi
    def find_currency(self, name):
        currency_obj = self.env['res.currency']
        currency_search = currency_obj.search([('name', '=', name)])
        if currency_search:
            return currency_search
        else:
            raise Warning(_(' "%s" Currency are not available.') % name)

    @api.multi
    def find_partner(self, name):
        partner_obj = self.env['res.partner']
        partner_search = partner_obj.search([('name', '=', name)])
        if partner_search:
            return partner_search
        else:
            partner_id = partner_obj.create({
                                             'name' : name})
            return partner_id

    @api.multi
    def import_csv(self):
         """Load Inventory data from the CSV file."""
         if self.import_option == 'csv':
             keys = ['purchase_no', 'vendor', 'currency', 'product', 'quantity', 'uom', 'description', 'price','tax','date']
             data = base64.b64decode(self.file)
#              file_input = cStringIO.StringIO(data)
             file_input = io.StringIO(data.decode("utf-8"))
             file_input.seek(0)
             reader_info = []
             reader = csv.reader(file_input, delimiter=',')
             try:
                 reader_info.extend(reader)
             except Exception:
                 raise exceptions.Warning(_("Not a valid file!"))
             values = {}
             for i in range(len(reader_info)):
                 field = map(str, reader_info[i])
                 values = dict(zip(keys, field))
                 if values:
                     if i == 0:
                         continue
                     else:
                         values.update({'seq_opt':self.sequence_opt})
                         res = self.make_purchase(values)
         else:
             fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
             fp.write(binascii.a2b_base64(self.file))
             fp.seek(0)
             values = {}
             workbook = xlrd.open_workbook(fp.name)
             sheet = workbook.sheet_by_index(0)
             product_obj = self.env['product.product']
             for row_no in range(sheet.nrows):
                 val = {}
                 tax_line = ''
                 if row_no <= 0:
                     fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
                 else:
                     line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
                     a1 = int(float(line[9]))
                     a1_as_datetime = datetime(*xlrd.xldate_as_tuple(a1, workbook.datemode))
                     date_string = a1_as_datetime.date().strftime('%Y-%m-%d')
                     values.update({'purchase_no':line[0],
									'vendor': line[1],
									'currency': line[2],
									'product': line[3],
									'quantity': line[4],
									'uom': line[5],
									'description': line[6],
									'price': line[7],
                                    'tax': line[8],
                                    'date': date_string,
                                    'seq_opt':self.sequence_opt

})
                     res = self.make_purchase(values)
         return res

