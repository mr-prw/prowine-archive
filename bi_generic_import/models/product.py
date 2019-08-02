# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import tempfile
import binascii
import xlrd
from odoo.exceptions import Warning
from odoo import models, fields, api

import logging
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

class gen_product(models.TransientModel):
    _name = "gen.product"

    file = fields.Binary('File')

    @api.multi
    def create_product(self, values):
        product_obj = self.env['product.product']
        product_categ_obj = self.env['product.category']
        product_uom_obj = self.env['product.uom']
        if values.get('categ_id')=='':
            raise Warning('CATEGORY field can not be empty')
        else:
            categ_id = product_categ_obj.search([('name','=',values.get('categ_id'))])

        if values.get('type') == 'Consumable':
            type ='consu'
        elif values.get('type') == 'Service':
            type ='service'
        elif values.get('type') == 'Stockable Product':
            type ='product'

        if values.get('uom_id')=='':
            uom_id = 1
        else:
            uom_search_id  = product_uom_obj.search([('name','=',values.get('uom'))])
            uom_id = uom_search_id.id

        if values.get('uom_po_id')=='':
            uom_po_id = 1
        else:
            uom_po_search_id  = product_uom_obj.search([('name','=',values.get('po_uom'))])
            uom_po_id = uom_po_search_id.id
        vals = {
                                  'name':values.get('name'),
                                  'default_code':values.get('default_code'),
                                  'categ_id':categ_id.id,
                                  'type':type,
                                  'barcode':values.get('barcode'),
                                  'uom_id':uom_id,
                                  'uom_po_id':uom_po_id,
                                  'lst_price':values.get('sale_price'),
                                  'standard_price':values.get('cost_price'),
                                  'weight':values.get('weight'),
                                  'volume':values.get('volume'),
                                  }
        res = product_obj.create(vals)
        return res

    @api.multi
    def import_product(self):

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
                values.update( {'name':line[0],
                                'default_code': line[1],
                                'categ_id': line[2],
                                'type': line[3],
                                'barcode': line[4],
                                'uom': line[5],
                                'po_uom': line[6],
                                'sale_price': line[7],
                                'cost_price': line[8],
                                'weight': line[9],
                                'volume': line[10],

                                })
                res = self.create_product(values)


        return res

