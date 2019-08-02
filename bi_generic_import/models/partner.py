# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import binascii
import logging
import tempfile

import xlrd
from odoo import models, fields, api
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

class gen_partner(models.TransientModel):
    _name = "gen.partner"

    file = fields.Binary('File')


    @api.multi
    def find_country(self,val):
        country_search = self.env['res.country'].search([('name','=',val.get('country'))])
        if country_search:
            return country_search.id
        else:
            country = self.env['res.country'].create({'name':val.get('country')})
            return country.id

    @api.multi
    def find_state(self,val):
        state_search = self.env['res.country.state'].search([('name','=',val.get('state'))])
        if state_search:
            return state_search.id
        else:
            if not val.get('country'):
                raise Warning('State is not available in system And without country you can not create state')
            else:
                country_search = self.env['res.country'].search([('name','=',val.get('country'))])
                if not country_search:
                    country_crt = self.env['res.country'].create({'name':val.get('country')})
                    country = country_crt.id

                else:
                    country = country_search.id
                state = self.env['res.country.state'].create({
                                                  'name':val.get('state'),
                                                  'code':val.get('state')[:3],
                                                 'country_id':country
                                                  })
                return state.id


    @api.multi
    def create_partner(self, values):
        search_partner = self.env['res.partner'].search([('name','=',values.get('name'))])
        parent = False
        state = False
        country = False
        saleperson = False
        vendor_pmt_term = False
        cust_pmt_term = False
        if values.get('type') == 'company':
            if values.get('parent'):
                raise Warning('You can not give parent if you have select type is company')
            type =  'company'
        else:
            type =  'person'
            parent_search = self.env['res.partner'].search([('name','=',values.get('parent'))])
            if parent_search:
                parent =  parent_search.id
            else:
                raise Warning("Parent contact  not available")

        if values.get('state'):
            state = self.find_state(values)
        if values.get('country'):
            country = self.find_country(values)
        if values.get('saleperson'):
            saleperson_search = self.env['res.users'].search([('name','=',values.get('saleperson'))])
            if not saleperson_search:
                raise Warning("Salesperson not available in system")
            else:
                saleperson = saleperson_search.id
        if values.get('cust_pmt_term'):
            cust_payment_term_search = self.env['account.payment.term'].search([('name','=',values.get('cust_pmt_term'))])
            if not cust_payment_term_search:
                raise Warning("Payment term not available in system")
            else:
                cust_pmt_term = cust_payment_term_search.id
        if values.get('vendor_pmt_term'):
            vendor_payment_term_search = self.env['account.payment.term'].search([('name','=',values.get('vendor_pmt_term'))])
            if not vendor_payment_term_search:
                raise Warning("Payment term not available in system")
            else:
                vendor_pmt_term = vendor_payment_term_search.id

        if search_partner:
            search_partner.company_type = type
            search_partner.parent_id = parent or False
            search_partner.street = values.get('street')
            search_partner.street2 = values.get('street2')
            search_partner.city = values.get('city')
            search_partner.state_id = state
            search_partner.zip = values.get('zip')
            search_partner.country_id = country
            search_partner.website = values.get('website')

            search_partner.phone = values.get('phone')
            search_partner.mobile = values.get('mobile')
            search_partner.email = values.get('email')
            search_partner.customer = values.get('customer') or False
            search_partner.supplier = values.get('vendor') or False
            search_partner.user_id = saleperson
            search_partner.ref = values.get('street'),
            search_partner.property_payment_term_id = cust_pmt_term or False
            search_partner.property_supplier_payment_term_id = vendor_pmt_term or False
            return True
        else:
            vals = {
                                  'name':values.get('name'),
                                  'company_type':type,
                                  'parent_id':parent or False,
                                  'street':values.get('street'),
                                  'street2':values.get('street2'),
                                  'city':values.get('city'),
                                  'state_id':state,
                                  'zip':values.get('zip'),
                                  'country_id':country,
                                  'website':values.get('website'),
                                  'phone':values.get('phone'),
                                  'mobile':values.get('mobile'),
                                  'email':values.get('email'),
                                  'customer':values.get('customer') or False,
                                  'supplier':values.get('vendor') or False,
                                  'user_id':saleperson,
                                  'ref':values.get('ref'),
                                  'property_payment_term_id':cust_pmt_term or False,
                                  'property_supplier_payment_term_id':vendor_pmt_term or False,
                                  }
            res = self.env['res.partner'].create(vals)
            return res

    @api.multi
    def import_partner(self):

        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.file))
        fp.seek(0)
        values = {}
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        for row_no in range(sheet.nrows):
            if row_no <= 0:
                fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
            else:
                line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
                values.update( {'name':line[0],
                                'type': line[1],
                                'parent': line[2],
                                'street': line[3],
                                'street2': line[4],
                                'city': line[5],
                                'state': line[6],
                                'zip': line[7],
                                'country': line[8],
                                'website': line[9],
                                'phone': line[10],
                                'mobile': line[11],
                                'email': line[12],
                                'customer': line[13],
                                'vendor': line[14],
                                'saleperson': line[15],
                                'ref': line[16],
                                'cust_pmt_term': line[17],
                                'vendor_pmt_term': line[18],

                                })
                res = self.create_partner(values)


        return res

