# -*- coding: cp1251 -*-

import os
import io
import base64
import shutil
import zipfile
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.osutil import tempdir

_logger = logging.getLogger(__name__)


class ImportFromCashFront(models.TransientModel):
    _name = 'import.cashfront'

    fname = fields.Char(string="File Name",
                        readonly=False)
    fdata = fields.Binary(string="ZIP file",
                          readonly=False)
    state = fields.Selection([('draft', 'Draft'),
                              ('done', 'Done')],
                             string="State",
                             default='draft')

    @api.model
    def sort_by_date(self, file_name):
        if len(file_name) > 10:
            file_name = file_name[:-4].split('/')[len(file_name[:-4].split('/')) - 1]
        year = file_name[8:10]
        month = file_name[3:5]
        day = file_name[:2]
        return year + month + day

    def create_product(self, name, default_code, lst_price, barcode):
        self.env['product.product'].create({
            'name': name,
            'default_code': default_code,
            'lst_price': lst_price,
            'barcode': barcode,
        })

    @api.model
    def read_file(self, file_data, decode):
        """
        :param file_data: file with data
        :type file_data: binary or list(str)
        :param decode:  character encoding
        :type decode: str
        :return: dict
        """
        sort_data_orders = {}
        if type(file_data) is not list:
            fdata = io.StringIO(
                base64.b64decode(file_data).strip().decode(decode)).readlines()
        else:
            fdata = file_data
        for data in fdata:
            row_sold_item = data.strip().split('|')
            name = row_sold_item[0]
            if name in sort_data_orders:
                sort_data_orders[name].append(row_sold_item)
            else:
                sort_data_orders[name] = [row_sold_item]
        return sort_data_orders

    @api.model
    def get_pos_order_data(self, name, date, amount, journal_id, statement_id, account_id, ref):
        return {
            'name': name,
            'date': date,
            'amount': amount,
            'journal_id': journal_id,
            'statement_id': statement_id,
            'account_id': account_id,
            'ref': ref
        }

    @api.multi
    def get_date(self, name):
        name_sale_path = name.split('/')
        date = name_sale_path[len(name_sale_path) - 1:]
        return date[0].split('.txt')[0]

    @api.multi
    def cashfront_import_wizard(self):
        if not self.fdata:
            raise UserError(_("Select zip file to import"))

        journal_file_list = []
        sale_file_list = []
        with tempdir() as dump_dir:
            archive = zipfile.ZipFile(io.BytesIO(base64.b64decode(self.fdata)))
            files = archive.namelist()
            archive.extractall(dump_dir, files)
            for file in files:
                if '/Jornal/' in file:
                    if '.txt' in file:
                        journal_file_list.append(os.path.join(dump_dir, file))
                if '/Sales/' in file:
                    if '.txt' in file:
                        sale_file_list.append(os.path.join(dump_dir, file))

            fdata_sale = sorted(sale_file_list, key=lambda x: self.sort_by_date(x))
            name_sale_path = fdata_sale[0].split('/')
            path = '/'.join(name_sale_path[:len(name_sale_path) - 1])
            fdata_journal = sorted([x for x in journal_file_list if path + '/' + x.split('/')[len(name_sale_path) - 1] in fdata_sale],
                        key=lambda x: self.sort_by_date(x))

            for fdata_sale, fdata_journal in zip(fdata_sale, fdata_journal):
                _logger.info('{} | {}'.format(fdata_sale, fdata_journal))
                start_at = str(datetime.strptime(self.get_date(fdata_sale), '%d.%m.%Y'))
                active_id = self.env.context.get('active_id')
                posconfig = self.env['pos.config'].browse(active_id)
                session = self.env['pos.session'].create({
                    'config_id': posconfig.id,
                    'start_at': start_at,
                })

                fdata_sale = open(fdata_sale, encoding='cp1251').readlines()
                fdata_journal = open(fdata_journal, encoding='cp1251').readlines()

                self.cashfront_import(fdata_sale, fdata_journal, session)

    @api.multi
    def cashfront_import(self, fdata, fdata_journal, session):
        self.ensure_one()
        try:
            sort_data_orders = self.read_file(fdata, 'cp1251')
            sort_data_journal = self.read_file(fdata_journal, 'cp1251')

            for order in sort_data_orders.values():
                val = {}
                lines = []
                for product in order:
                    date_order = datetime.strptime(product[0].split('#')[0], '%d.%m.%Y-%H:%M:%S')
                    default_code = product[1]
                    name = product[2]
                    price = float(product[3].replace(',', '.')) or 1.0
                    qty = float(product[4].replace(',', '.')) or 1.0
                    discount_amount = float(product[6].replace(',', '.')) / qty
                    discount = round((discount_amount * 100) / price)
                    barcode = product[10]
                    product_id = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
                    if product_id:
                        lines.append((0, 0, {
                            'product_id': product_id.id,
                            'name': product_id.name,
                            'qty': qty,
                            'price_unit': price,
                            'discount': discount,
                        }))
                val['lines'] = lines
                val['date_order'] = date_order
                order = self.env['pos.order'].create(val)
                for line in order.lines:
                    line.tax_ids = line.product_id.taxes_id
                    line.tax_ids_after_fiscal_position = line.order_id.fiscal_position_id.map_tax(line.tax_ids, line.product_id, line.order_id.partner_id)

            # payment
            for line_journal in sort_data_journal:
                line = sort_data_journal[line_journal][0]
                name = "{} {}".format(line[1],  line_journal)
                date_time_order = datetime.strptime(line_journal.split('#')[0], '%d.%m.%Y-%H:%M:%S')
                date = datetime.strptime(line_journal.split('#')[0].split('-')[0], '%d.%m.%Y').date()

                if line[2] == 'Card':
                    if session.statement_ids.search([('journal_type', '=', 'bank')], limit=1):
                        statement = session.statement_ids.search([('journal_type', '=', 'bank')], limit=1)
                    else:
                        raise UserError(_('You have to set a Sale Journal (bank)'))
                else:
                    if session.statement_ids.search([('journal_type', '=', 'cash')], limit=1):
                        statement = session.statement_ids.search([('journal_type', '=', 'cash')], limit=1)
                    else:
                        raise UserError(_('You have to set a Sale Journal (cash)'))

                journal_id = statement.journal_id
                account_id = journal_id.default_debit_account_id
                ref = statement.name

                if line[1] == 'Inventory':
                    orders = self.env['pos.order'].search([('date_order', '=', str(date_time_order))])
                    for ord in orders:
                        ord.unlink()

                if line[1] == 'Invoice':
                    orders = self.env['pos.order'].search([('date_order', '=', str(date_time_order))])
                    for ord in orders:
                        ord.unlink()

                if line[1] == 'Sales':
                    payment = line[8].split('-,')
                    amount = float(payment[0].split(' оплата: ')[1].replace(',', '.')) or 0.0
                    amount_return = - float(payment[1].split(' сдача: ')[1].replace(',', '.')) or 0.0
                else:
                    amount = line[3].replace(',', '.')
                    amount_return = 0.0

                data = self.get_pos_order_data(name, date, amount, journal_id.id, statement.id, account_id.id, ref)
                if line_journal in sort_data_orders.keys():
                    pos_order = self.env['pos.order'].search([('date_order', '=', str(date_time_order))])
                    if pos_order:
                        pos_order.write({
                            'statement_ids': [(0, 0, data)]
                        })
                        if amount_return:
                            name += ': return'
                            data = self.get_pos_order_data(name, date, amount_return, journal_id.id, statement.id, account_id.id, ref)
                            pos_order.write({
                                'statement_ids': [(0, 0, data)]
                            })
                        pos_order.state = 'paid'
                else:
                    statement.line_ids.create(data)

        except Exception as e:
            raise _logger.warning(e)

    @api.multi
    def _cashfront_import_cron(self):
        try:
            import_cashfront = self.env['import.cashfront'].create({
                'create_uid': self.env.user.id
            })
            posconfig = self.env['pos.config'].search([])
            if posconfig:
                for conf in posconfig:
                    path = conf.path
                    if path:
                        sale_file_list = os.listdir(path + '/Sales')
                        journal_file_list = os.listdir(path + '/Jornal')
                        file_name_list = [sorted(sale_file_list,
                                                 key=lambda x: self.sort_by_date(x)),
                                          sorted([x for x in journal_file_list if x in sale_file_list],
                                                 key=lambda x: self.sort_by_date(x))]
                        for name in file_name_list[0]:
                            if '.txt' in name:
                                fdata = open(path + '/Sales/' + name, encoding='cp1251')
                                fdata_journal = open(path + '/Jornal/' + name, encoding='cp1251')
                                sales_line = fdata.readlines()
                                journal_line = fdata_journal.readlines()
                                start_at = str(datetime.strptime(sales_line[0].split('|')[0].split('#')[0],
                                                                 '%d.%m.%Y-%H:%M:%S'))

                                if self.env['pos.session'].search([('start_at', '=', start_at[:10])]):
                                    session = self.env['pos.session'].search([('start_at', '=', start_at)])
                                else:
                                    session = self.env['pos.session'].create({
                                        'config_id': conf.id,
                                        'start_at': start_at,
                                    })
                                _logger.info('Import: {}'.format(name))
                                import_cashfront.cashfront_import(sales_line, journal_line, session)

                                imported_sales_directory = path + '/Sales/Imported'
                                if not os.path.exists(imported_sales_directory):
                                    os.makedirs(imported_sales_directory)
                                    shutil.move(path + '/Sales/' + name, imported_sales_directory)
                                else:
                                    shutil.move(path + '/Sales/' + name, imported_sales_directory)

                                imported_jornal_directory = path + '/Jornal/Imported'
                                if not os.path.exists(imported_jornal_directory):
                                    os.makedirs(imported_jornal_directory)
                                    shutil.move(path + '/Jornal/' + name, imported_jornal_directory)
                                else:
                                    shutil.move(path + '/Jornal/' + name, imported_jornal_directory)

                                fdata_journal.close()
                                fdata.close()
                        else:
                            _logger.warning("List empty: {}".format(conf.name))
                            continue
                    else:
                        _logger.warning("Specify the path to the files: {}".format(conf.name))
        except Exception as e:
            _logger.warning(e)
