# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import binascii
import logging
import tempfile
from datetime import datetime

import xlrd
from odoo import models, fields, exceptions, api, _
from odoo.exceptions import Warning, UserError

_logger = logging.getLogger(__name__)
import io
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

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.multi
    def post(self):
        invoice = self._context.get('invoice', False)
        self._post_validate()

        for move in self:
            move.line_ids.create_analytic_lines()
            if move.name == '/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.move_name and invoice.move_name != '/':
                    new_name = invoice.move_name
                elif invoice and invoice.custom_seq :
                    new_name = invoice.name
                elif invoice and invoice.system_seq :
                    new_name = invoice.name
                else:
                    if journal.sequence_id:
                        # If invoice is actually refund and journal has a refund_sequence then use that one or use the regular one
                        sequence = journal.sequence_id
                        if invoice and invoice.type in ['out_refund', 'in_refund'] and journal.refund_sequence:
                            sequence = journal.refund_sequence_id
                        new_name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                    else:
                        raise UserError(_('Please define a sequence on the journal.'))

                if new_name:
                    move.name = new_name
        return self.write({'state': 'posted'})


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    custom_seq = fields.Boolean('Custom Sequence')
    system_seq = fields.Boolean('System Sequence')


class gen_inv(models.TransientModel):
    _name = "gen.invoice"

    file = fields.Binary('File')
    account_opt = fields.Selection([('default', 'Use Account From Configuration product/Property'), ('custom', 'Use Account From Excel/CSV')], string='Account Option', required=True, default='default')
    type = fields.Selection([('in', 'Customer'), ('out', 'Supplier')], string='Type', required=True, default='in')
    sequence_opt = fields.Selection([('custom', 'Use Excel/CSV Sequence Number'), ('system', 'Use System Default Sequence Number')], string='Sequence Option',default='custom')
    import_option = fields.Selection([('csv', 'CSV File'),('xls', 'XLS File')],string='Select',default='csv')


    @api.multi
    def make_invoice(self, values):
        invoice_obj = self.env['account.invoice']
        if self.type == "in":
            invoice_search = invoice_obj.search([
                                                 ('name', '=', values.get('invoice')),
                                                 ('type', '=', 'out_invoice')
                                                 ])
        else:
            invoice_search = invoice_obj.search([
                                                 ('name', '=', values.get('invoice')),
                                                  ('type', '=', 'in_invoice')
                                                  ])
        if invoice_search:
            if invoice_search.partner_id.name == values.get('customer'):
                if  invoice_search.currency_id.name == values.get('currency'):
                    if  invoice_search.user_id.name == values.get('salesperson'):
                        lines = self.make_invoice_line(values, invoice_search)
                        return lines
                    else:
                        raise Warning(_('User(Salesperson) is different for "%s" .\n Please define same.') % values.get('invoice'))
                else:
                    raise Warning(_('Currency is different for "%s" .\n Please define same.') % values.get('invoice'))
            else:
                raise Warning(_('Customer name is different for "%s" .\n Please define same.') % values.get('invoice'))
        else:
            partner_id = self.find_partner(values.get('customer'))
            currency_id = self.find_currency(values.get('currency'))
            salesperson_id = self.find_sales_person(values.get('salesperson'))
            inv_date = self.find_invoice_date(values.get('date'))

            if self.type == "in":
                type_inv = "out_invoice"
                if partner_id.property_account_receivable_id:
                    account_id = partner_id.property_account_receivable_id
                else:
                    account_search = self.env['ir.property'].search([('name', '=', 'property_account_income_categ_id')])
                    account_id = account_search.value_reference
                    account_id = account_id.split(",")[1]
                    account_id = self.env['account.account'].browse(account_id)
            else:
                if partner_id.property_account_receivable_id:
                    account_id = partner_id.property_account_payable_id
                else:
                    account_search = self.env['ir.property'].search([('name', '=', 'property_account_expense_categ_id')])
                    account_id = account_search.value_reference
                    account_id = account_id.split(",")[1]
                    account_id = self.env['account.account'].browse(account_id)
                type_inv = "in_invoice"
            if values.get('seq_opt') == 'system':
                journal = self.env['account.invoice']._default_journal()
                if journal.sequence_id:
                        # If invoice is actually refund and journal has a refund_sequence then use that one or use the regular one
                        sequence = journal.sequence_id
                        name = sequence.with_context(ir_sequence_date=datetime.today().date().strftime("%Y-%m-%d")).next_by_id()
                else:
                    raise UserError(_('Please define a sequence on the journal.'))
            else:
                name = values.get('invoice')
            inv_id = invoice_obj.create({
                                         'account_id' : account_id.id,
                                        'partner_id' : partner_id.id,
                                        'currency_id' : currency_id.id,
                                        'user_id':salesperson_id.id,
                                        'name':name,
                                        'custom_seq': True if values.get('seq_opt') == 'custom' else False,
                                        'system_seq': True if values.get('seq_opt') == 'system' else False,
                                        'type' : type_inv,
                                        'date_invoice':inv_date
                                        })
            lines = self.make_invoice_line(values, inv_id)
            return lines



    @api.multi
    def make_invoice_line(self, values, inv_id):
        product_obj = self.env['product.product']
        invoice_line_obj = self.env['account.invoice.line']
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
                tax_names = values.get('tax').split(',')
                tax= self.env['account.tax'].search([('name', '=', tax_names),('type_tax_use','=','sale')])
                if not tax:
                    raise Warning(_('"%s" Tax not in your system') % tax_names)
                tax_ids.append(tax.id)
        if product_search:
            product_id = product_search
        else:
            product_id = product_obj.search([('name', '=', values.get('product'))])
            if not product_id:
                product_id = product_obj.create({'name': values.get('product')})
        if not product_uom:
            raise Warning(_(' "%s" Product UOM category is not available.') % values.get('uom'))
        if self.account_opt == 'default':
            if inv_id.type == 'out_invoice':
                if product_id.property_account_income_id:
                    account = product_id.property_account_income_id
                elif product_id.categ_id.property_account_income_categ_id:
                    account = product_id.categ_id.property_account_income_categ_id
                else:
                    account_search = self.env['ir.property'].search([('name', '=', 'property_account_income_categ_id')])
                    account = account_search.value_reference
                    account = account.split(",")[1]
                    account = self.env['account.account'].browse(account)
            if inv_id.type == 'in_invoice':
                if product_id.property_account_expense_id:
                    account = product_id.property_account_expense_id
                elif product_id.categ_id.property_account_expense_categ_id:
                    account = product_id.categ_id.property_account_expense_categ_id
                else:
                    account_search = self.env['ir.property'].search([('name', '=', 'property_account_expense_categ_id')])
                    account = account_search.value_reference
                    account = account.split(",")[1]
                    account = self.env['account.account'].browse(account)

        else:
            if values.get('account') == '':
                raise Warning(_(' You can not left blank account field if you select Excel/CSV Account Option'))
            else:
                if self.import_option == 'csv':
                    account_id = self.env['account.account'].search([('code','=',values.get('account'))])
                else:
                    acc = values.get('account').split('.')
                    account_id = self.env['account.account'].search([('code','=',acc[0])])
                if account_id:
                    account = account_id
                else:
                    raise Warning(_(' "%s" Account is not available.') % values.get('account'))
        res = invoice_line_obj.create({
                'product_id' : product_id.id,
                'quantity' : values.get('quantity'),
                'price_unit' : values.get('price'),
                'name' : values.get('description'),
                'account_id' : account.id,
                'uom_id' : product_uom.id,
                'invoice_id' : inv_id.id
                })
        if tax_ids:
            res.write({'invoice_line_tax_ids':([(6,0,tax_ids)])})
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
    def find_sales_person(self, name):
        sals_person_obj = self.env['res.users']
        partner_search = sals_person_obj.search([('name', '=', name)])
        if partner_search:
            return partner_search
        else:
            raise Warning(_('Not Valid Salesperson Name "%s"') % name)


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
    def find_invoice_date(self, date):
        DATETIME_FORMAT = "%Y-%m-%d"
        i_date = datetime.strptime(date, DATETIME_FORMAT)
        return i_date

    @api.multi
    def import_csv(self):
        """Load Inventory data from the CSV file."""
        if self.import_option == 'csv':
            if self.account_opt == 'default':
                keys = ['invoice', 'customer', 'currency', 'product', 'quantity', 'uom', 'description', 'price','salesperson','tax','date']
            else:
                keys = ['invoice', 'customer', 'currency', 'product','account', 'quantity', 'uom', 'description', 'price','salesperson','tax','date']
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
            for i in range(len(reader_info)):
	            field = map(str, reader_info[i])
	            values = dict(zip(keys, field))
	            if values:
	                if i == 0:
	                    continue
	                else:
	                    values.update({'type':self.type,'option':self.import_option,'seq_opt':self.sequence_opt})
	                    res = self.make_invoice(values)
        else:
            fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)
            values = {}
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
            for row_no in range(sheet.nrows):
                val = {}
                if row_no <= 0:
                    fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
                else:
                    line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
                    if self.account_opt == 'default':
                        if len(line) == 11:
                            a1 = int(float(line[10]))
                            a1_as_datetime = datetime(*xlrd.xldate_as_tuple(a1, workbook.datemode))
                            date_string = a1_as_datetime.date().strftime('%Y-%m-%d')
                            values.update( {'invoice':line[0],
                                            'customer': line[1],
                                            'currency': line[2],
                                            'product': line[3],
                                            'quantity': line[4],
                                            'uom': line[5],
                                            'description': line[6],
                                            'price': line[7],
                                            'salesperson': line[8],
                                            'tax': line[9],
                                            'date': date_string,
                                            'seq_opt':self.sequence_opt
                                            })
                        elif len(line) > 11:
                            raise Warning(_('Your File has extra column please refer sample file'))
                        else:
                            raise Warning(_('Your File has less column please refer sample file'))
                    else:
                        if len(line) == 12:
                            a1 = int(float(line[11]))
                            a1_as_datetime = datetime(*xlrd.xldate_as_tuple(a1, workbook.datemode))
                            date_string = a1_as_datetime.date().strftime('%Y-%m-%d')
                            values.update( {'invoice':line[0],
                                            'customer': line[1],
                                            'currency': line[2],
                                            'product': line[3],
                                            'account': line[4],
                                            'quantity': line[5],
                                            'uom': line[6],
                                            'description': line[7],
                                            'price': line[8],
                                            'salesperson': line[9],
                                            'tax': line[10],
                                            'date': date_string,
                                            'seq_opt':self.sequence_opt
                                            })
                        elif len(line) > 12:
                            raise Warning(_('Your File has extra column please refer sample file'))
                        else:
                            raise Warning(_('Your File has less column please refer sample file'))
                    res = self.make_invoice(values)



        return res

