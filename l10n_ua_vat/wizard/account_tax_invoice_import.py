# -*- coding: utf-8 -*-

import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import xml.etree.ElementTree as ET
from xml.sax.saxutils import unescape
from lxml import etree
from io import BytesIO
import datetime
import os


class TaxInvoiceImport(models.TransientModel):
    _name = 'account.taxinvoice.import'
    _description = "Import single tax invoice"

    fname = fields.Char(string="File Name",
                        readonly=False)
    fdata = fields.Binary(string="File data",
                          readonly=False)
    state = fields.Selection([('draft', 'Draft'),
                              ('done', 'Done')],
                             string="State",
                             default='draft')

    @classmethod
    def filter_name(cls, name):
        return name.split(']')[1].strip() if ']' in name else name

    @api.multi
    def xml_validate(self, tag):
        path = os.path.dirname(os.path.abspath(__file__))
        xmlfile = etree.parse(BytesIO(base64.b64decode(self.fdata)))
        xmlscheme = etree.XMLSchema(etree.parse(path +
                                                "/../data/%s01009.xsd" % tag))
        validate = xmlscheme.validate(xmlfile)
        if validate:
            return True, "OK"

        result_error = []
        for error in xmlscheme.error_log:
            result_error.append("Помилка, рядок %s: %s" %
                                (error.line, error.message))

        return False, '\n'.join(result_error)

    @api.multi
    def get_products(self):
        root = ET.fromstring(base64.b64decode(self.fdata))
        declarbody = root.find('DECLARBODY')

        item_count = [x for x in declarbody.iterfind('RXXXXG3S')]
        products = list()

        g3s_names = declarbody.iterfind('RXXXXG3S')
        g4_uktzed = declarbody.iterfind('RXXXXG4')
        g32_is_imported = declarbody.iterfind('RXXXXG32')
        g33_dkpp = declarbody.iterfind('RXXXXG33')
        g4s_uom_name = declarbody.iterfind('RXXXXG4S')
        g105_2s_uom_code = declarbody.iterfind('RXXXXG105_2S')
        g5_quantity = declarbody.iterfind('RXXXXG5')
        g6_price_wo_wax = declarbody.iterfind('RXXXXG6')
        g008_pdv = declarbody.iterfind('RXXXXG008')
        g009_kod_pilg = declarbody.iterfind('RXXXXG009')
        g010_price_subtotal = declarbody.iterfind('RXXXXG010')
        g011_vd_sgt = declarbody.iterfind('RXXXXG011')

        for product in item_count:
            product_dict = {
                'name': unescape(self.filter_name(g3s_names.__next__().text)),
                'ukt_zed_id': self.env['product.classification'].search([('name', '=', g4_uktzed.__next__().text)]).id,
                'is_imported': g32_is_imported.__next__().text or False,
                'dkpp': g33_dkpp.__next__().text,
                'uom_id': g4s_uom_name.__next__().text,
                'uom_code': g105_2s_uom_code.__next__().text,
                'quantity': g5_quantity.__next__().text,
                'price_unit': g6_price_wo_wax.__next__().text,
                'taxinvoice_line_tax_id': g008_pdv.__next__().text,
                'kod_pilg': g009_kod_pilg.__next__().text,
                'price_subtotal': g010_price_subtotal.__next__().text,
                'vd_sgt': g011_vd_sgt.__next__().text
            }

            products.append(product_dict)

        return products

    @api.multi
    def create_partner(self, vat, name):
        return self.env['res.partner'].create({
            'vat': vat,
            'name': name,
            'supplier': True,
            'is_company': True
        })

    @api.multi
    def find_or_create_product(self, ctx, prod, partner_id):
        products = self.env['product.product']
        suppliers = self.env['product.supplierinfo']

        suppl_prod = suppliers.search([('product_name', '=', prod['name']),
                                       ('name', '=', partner_id.id)],
                                      limit=1)
        if suppl_prod:
            return suppl_prod.product_tmpl_id.product_variant_ids[0]
        else:
            product = products.with_context(ctx).create({
                'type': 'product' if not prod['dkpp'] else
                'service',
                'name': prod['name'],
                'ukt_zed_id': prod['ukt_zed_id'],
                'dkpp': prod['dkpp'],
                'vd_sgt': prod['vd_sgt'],
                'exemption': prod['kod_pilg'],
                'lst_price': prod['price_unit'],
            })

        suppliers.with_context(ctx).create({
            'name': partner_id.id,
            'product_name': prod['name'],
            'delay': 1,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_id': product.id,
        })

        return product

    @api.multi
    def create_taxinvoice_line(self, ctx, tax, tax_invoice,
                               partner_id, imp_prod, tax_tag):
        ati_line = self.env['account.taxinvoice.line']
        for prod in imp_prod:
            if str(tax_tag) == prod['taxinvoice_line_tax_id']:
                product = self.find_or_create_product(ctx, prod, partner_id)
                prod_uom = self.get_product_uom(prod['uom_code'])
                if not prod_uom:
                    raise UserError(_("Код одиниці виміру не знайдено!"))

                prod['taxinvoice_id'] = tax_invoice.id
                prod['product_id'] = product.id
                prod['sequence'] = product.id
                prod['account_id'] = tax_invoice.account_id.id
                prod['uom_id'] = prod_uom.id
                prod['uom_code'] = prod_uom.uom_code
                prod['taxinvoice_line_tax_id'] = tax.id
                atil = ati_line.with_context(ctx).create(prod)

                atil._compute_subtotal()

                tax_invoice.write({
                    'taxinvoice_line_ids': atil
                })

    @api.multi
    def get_product_uom(self, uom_code):
        prod_uom = self.env['product.uom'].search([('uom_code', '=', uom_code)])
        missing_uom = len(prod_uom) == 0 or not uom_code
        return False if missing_uom else prod_uom

    @api.multi
    def taxinvoice_import(self):
        self.ensure_one()
        company_id = self._context.get('company_id',
                                       self.env.user.company_id)
        if not self.fdata:
            raise UserError(_("Виберіть файл для імпорту"))

        if not company_id.vat:
            raise UserError(_("Вкажіть ІПН у налаштуваннях компанії"))

        try:
            root = ET.fromstring(base64.b64decode(self.fdata))
        except ET.ParseError:
            raise UserError(_("Невірний формат xml файлу!"))
        # check document format and version
        declarhead = root.find('DECLARHEAD')
        if declarhead is None:
            raise UserError(_("Невірний формат файлу"))
        c_doc = declarhead.find('C_DOC')
        if c_doc is None:
            raise UserError(_("Невірна версія формату xml"))
        if c_doc.text != 'J12' and c_doc.text != 'F12':
            raise UserError(_("Невірна версія формату xml"))
        # xml validate
        validate, error_msg = self.xml_validate(c_doc.text)
        if not validate:
            raise UserError(_("%s" % error_msg))

        c_doc_sub = declarhead.find('C_DOC_SUB')
        if c_doc_sub is None or c_doc_sub.text != '010':
            raise UserError(_("Невірна версія формату xml"))
        c_doc_ver = declarhead.find('C_DOC_VER')
        if c_doc_ver is None or c_doc_ver.text != '9':
            raise UserError(_("Невірна версія формату xml"))

        declarbody = root.find('DECLARBODY')
        if declarbody is None:
            raise UserError(_("Невірний формат файлу"))
        # check if we are buyers
        hkbuy = declarbody.find('HKBUY')
        if hkbuy is None:
            raise UserError(_("Невірний формат файлу"))
        if hkbuy.text.find(company_id.vat) < 0:
            raise UserError(_("ІПН %s покупця не співпадає "
                              "з ІПН вашої організації!" % hkbuy.text))

        hfbuy = declarbody.find('HFBUY')
        if hfbuy is None:
            raise UserError(_("Невірний формат файлу"))
        num2txt = hfbuy.text or ''
        my_code = company_id.kod_filii or ''
        if my_code != num2txt:
            raise UserError(
                _("Код філії '%s' не співпадає "
                  "з кодом філії вашої організації!" % my_code))
        # check if partner is already in database
        hnamesel = declarbody.find('HNAMESEL')
        hksel = declarbody.find('HKSEL')
        if hksel is None:
            raise UserError(_("Невірний формат файлу"))
        domain = [('vat', '=', hksel.text),
                  ('supplier', '=', True),
                  ('is_company', '=', True)]
        partner_id = self.env['res.partner'].search(domain, limit=1)
        if len(partner_id) == 0:
            partner_id = self.create_partner(hksel.text,
                                             unescape(hnamesel.text))
        if partner_id.id == company_id.partner_id.id:
            raise UserError(_("ІПН продавця співпадає з вашим ІПН"))
        # Ok let's write taxinvoice
        ctx = dict(self._context)
        ctx['company_id'] = company_id.id
        ctx['category'] = 'in_tax_invoice'
        ctx['state'] = 'draft'
        date = datetime.datetime.strptime(declarbody.find('HFILL').text,
                                          '%d%m%Y').date()
        acc_ti = self.env['account.taxinvoice']
        account = acc_ti.with_context(ctx)._default_account()
        journal = acc_ti.with_context(ctx)._default_journal()
        currency = acc_ti.with_context(ctx)._default_currency()
        tag20 = company_id.vat20_tax_tag_id
        tag7 = company_id.vat7_tax_tag_id
        tag0 = company_id.vat0_tax_tag_id
        tagfree = company_id.vatfree_tax_tag_id
        tax_invoice = acc_ti.with_context(ctx).create({
            'state': 'draft',
            'h03': True if declarbody.find('H03').text == '1' else False,
            'horig1': True if declarbody.find('HORIG1').text == '1' else False,
            'htypr': declarbody.find('HTYPR').text or '00',
            'date_vyp': fields.Date.to_string(date),
            'number': declarbody.find('HNUM').text or '0',
            'number1': declarbody.find('HNUM1').text or None,
            'number2': declarbody.find('HFBUY').text or None,
            'kod_filii': declarbody.find('HNUM2').text or None,
            'category': 'in_tax_invoice',
            'doc_type': 'pn',
            'partner_id': partner_id.id,
            'ipn_partner': hksel.text,
            'prych_zv': declarbody.find('R003G10S').text or None,
            'currency_id': currency and currency.id or False,
            'journal_id': journal and journal.id or False,
            'company_id': company_id and company_id.id or False,
            'account_id': account and account.id or False,
            'amount_tara': float(declarbody.find('R02G11').text or 0)})

        # parse xml products
        imp_prod = self.get_products()
        # now add tax lines to tax invoice
        ti_taxline = self.env['account.taxinvoice.tax']
        domain = [('type_tax_use', '=', 'purchase'),
                  ('price_include', '=', False),
                  ('company_id', '=', company_id.id)]
        for tax in self.env['account.tax'].search(domain):
            if len(tax.tag_ids.filtered(lambda t: t == tag20)) > 0:
                if float(declarbody.find('R01G7').text or 0) > 0.0:
                    # create taxinvoice line
                    self.create_taxinvoice_line(ctx, tax, tax_invoice,
                                                partner_id, imp_prod,
                                                tax_tag=20)
                    # end
                    base = float(declarbody.find('R01G7').text)
                    amount = float(declarbody.find('R03G7').text)
                    ti_taxline.with_context(ctx).create({
                        'taxinvoice_id': tax_invoice.id,
                        'name': tax.name,
                        'tax_id': tax.id,
                        'base': base,
                        'amount': amount,
                        'manual': False,
                        'sequence': tax.sequence,
                        'account_analytic_id': tax.analytic or False,
                        'account_id': tax.account_id.id or False})
            if len(tax.tag_ids.filtered(lambda t: t == tag7)) > 0:
                if float(declarbody.find('R01G109').text or 0) > 0.0:
                    # create taxinvoice line
                    self.create_taxinvoice_line(ctx, tax, tax_invoice,
                                                partner_id, imp_prod,
                                                tax_tag=7)
                    # end
                    base = float(declarbody.find('R01G109').text)
                    amount = float(declarbody.find('R03G109').text)
                    ti_taxline.with_context(ctx).create({
                        'taxinvoice_id': tax_invoice.id,
                        'name': tax.name,
                        'tax_id': tax.id,
                        'base': base,
                        'amount': amount,
                        'manual': False,
                        'sequence': tax.sequence,
                        'account_analytic_id': tax.analytic or False,
                        'account_id': tax.account_id.id or False})
            if len(tax.tag_ids.filtered(lambda t: t == tag0)) > 0:
                base = amount = 0.0
                if float(declarbody.find('R01G9').text or 0) > 0.0:
                    base += float(declarbody.find('R01G9').text)
                if float(declarbody.find('R01G8').text or 0) > 0.0:
                    base += float(declarbody.find('R01G8').text)
                if base > 0.0:
                    # create taxinvoice line
                    self.create_taxinvoice_line(ctx, tax, tax_invoice,
                                                partner_id, imp_prod,
                                                tax_tag=902)
                    # end
                    ti_taxline.with_context(ctx).create({
                        'taxinvoice_id': tax_invoice.id,
                        'name': tax.name,
                        'tax_id': tax.id,
                        'base': base,
                        'amount': amount,
                        'manual': False,
                        'sequence': tax.sequence,
                        'account_analytic_id': tax.analytic or False,
                        'account_id': tax.account_id.id or False})
            if len(tax.tag_ids.filtered(lambda t: t == tagfree)) > 0:
                if float(declarbody.find('R01G10').text or 0) > 0.0:
                    # create taxinvoice line
                    self.create_taxinvoice_line(ctx, tax, tax_invoice,
                                                partner_id, imp_prod,
                                                tax_tag=903)
                    # end
                    base = float(declarbody.find('R01G10').text)
                    amount = 0.0
                    ti_taxline.with_context(ctx).create({
                        'taxinvoice_id': tax_invoice.id,
                        'name': tax.name,
                        'tax_id': tax.id,
                        'base': base,
                        'amount': amount,
                        'manual': False,
                        'sequence': tax.sequence,
                        'account_analytic_id': tax.analytic or False,
                        'account_id': tax.account_id.id or False})
        # we can't write to computed fields, so recompute them
        tax_invoice._compute_amount()
        # workflow can only be started from draft, so we move it to sent
        tax_invoice.action_ready()
        tax_invoice.action_sent()
        # redirect to supplier tax invoice list
        menu_id = self.env.ref('l10n_ua_vat.menu_supplier_vat_invoices').id
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'menu_id': menu_id}
        }
