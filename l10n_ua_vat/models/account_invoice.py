# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VatAccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def _get_taxinvoices_count(self):
        for invoice in self:
            if invoice.state not in ('open', 'paid'):
                invoice.tax_invoice_count = 0
            else:
                invoice.tax_invoice_count = len(invoice.tax_invoice_ids)
            return

    @staticmethod
    def get_vat_tags(company_id):
        if not company_id:
            return ()
        return (
            company_id.vat20_tax_tag_id or None,
            company_id.vat7_tax_tag_id or None,
            company_id.vat0_tax_tag_id or None,
            company_id.vatfree_tax_tag_id or None,
            company_id.vatnot_tax_tag_id or None
        )

    def _get_fully_tax_invoiced(self):
        for invoice in self:
            invoice._get_taxinvoices_count()

            if invoice.tax_invoice_count <= 0:
                invoice.fully_tax_invoiced = False
                return False

            inv_tax_amt = 0
            tax_inv_tax_amt = 0
            vat_tags = invoice.get_vat_tags(invoice.company_id)

            for tax in invoice.tax_line_ids:
                if (len(tax.tax_id.tag_ids.filtered(
                        lambda t: t in vat_tags)) > 0):
                    inv_tax_amt += tax.amount
            for tax_inv in invoice.tax_invoice_ids:
                tax_inv_tax_amt += tax_inv.amount_tax
            if inv_tax_amt <= tax_inv_tax_amt:
                invoice.fully_tax_invoiced = True
                return True
            else:
                invoice.fully_tax_invoiced = False
                return False

    tax_invoice_count = fields.Integer(
        string='# of Tax Invoices',
        compute='_get_taxinvoices_count',
        readonly=True)
    tax_invoice_ids = fields.One2many(
        'account.taxinvoice',
        'invoice_id',
        string='Tax Invoices',
        readonly=True,
        copy=False)
    fully_tax_invoiced = fields.Boolean(
        string='Fully Tax Invoiced',
        compute='_get_fully_tax_invoiced',
        readonly=True)

    @api.multi
    def action_view_taxinvoices(self):
        self.ensure_one()
        tax_invoice_ids = self.mapped('tax_invoice_ids')
        imd = self.env['ir.model.data']
        if self.type in ('out_invoice', 'out_refund'):
            action = imd.xmlid_to_object(
                'l10n_ua_vat.customer_tax_invoice_list_action')
        else:
            action = imd.xmlid_to_object(
                'l10n_ua_vat.supplier_tax_invoice_list_action')
        list_view_id = imd.xmlid_to_res_id(
            'l10n_ua_vat.tax_invoice_tree_view')
        form_view_id = imd.xmlid_to_res_id(
            'l10n_ua_vat.tax_invoice_form_view')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [
                [list_view_id, 'tree'],
                [form_view_id, 'form'],
                [False, 'graph'],
                [False, 'kanban'],
                [False, 'calendar'],
                [False, 'pivot']
            ],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(tax_invoice_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % tax_invoice_ids.ids
        elif len(tax_invoice_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = tax_invoice_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.multi
    def tax_invoice_create(self):
        for inv in self:
            ipn_partner = inv.partner_id.vat
            if ipn_partner:
                if ipn_partner == "100000000000":
                    horig1 = True
                    htypr = '02'
                else:
                    horig1 = False
                    htypr = '00'
            else:
                raise UserError(_("Вкажіть ІПН у налаштуваннях контрагента."))

            product_id = inv.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
            deposit_product_id = inv.env['product.product'].browse(int(product_id))

            taxes_id = inv.env['product.product'].browse(int(product_id)).taxes_id

            vat_tax_id = False
            vat_tags = inv.get_vat_tags(inv.company_id)

            for tax in self.env['account.tax'].browse(int(taxes_id)):
                if len(tax.tag_ids.filtered(lambda t: t in vat_tags)) > 0:
                    vat_tax_id = tax
                    break

            acc_ti = self.env['account.taxinvoice']
            ctx = dict(self._context)
            ctx['company_id'] = inv.company_id.id
            ctx['category'] = 'out_tax_invoice'
            ctx['state'] = 'draft'
            account = acc_ti.with_context(ctx)._default_account()
            tax_invoice = acc_ti.with_context(ctx).create({
                'state': 'draft',
                'h03': False,
                'horig1': horig1,
                'htypr': htypr,
                'date_vyp': inv.date,
                'number': None,
                'number1': None,
                'number2': inv.company_id.kod_filii or None,
                'kod_filii': inv.partner_id.kod_filii,
                'category': 'out_tax_invoice',
                'doc_type': 'pn',
                'partner_id': inv.partner_id.id,
                'ipn_partner': ipn_partner,
                'prych_zv': None,
                'signer_id': self.env.user.id,
                'currency_id': inv.currency_id.id,
                'journal_id': inv.journal_id.id,
                'company_id': inv.company_id.id,
                'account_id': account and account.id,
                'invoice_id': inv.id,
                'amount_tara': 0})

            # create tax invoice lines
            ti_line = self.env['account.taxinvoice.line']
            for line in inv.invoice_line_ids:
                taxes = line.invoice_line_tax_ids.compute_all(
                    line.price_unit, inv.currency_id, line.quantity,
                    line.product_id, self.partner_id)['taxes']
                for tax in taxes:
                    tax_id = self.env['account.tax'].browse(tax['id'])
                    if (line.quantity > 0 and
                            len(tax_id.tag_ids.filtered(
                                lambda t: t in vat_tags)) > 0):
                        ti_l = ti_line.with_context(ctx).create({
                            'taxinvoice_id': tax_invoice.id,
                            'taxinvoice_line_tax_id': tax_id.id,
                            'account_id': tax_id.account_id.id or False,
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'uom_id': line.uom_id.id,
                            'uom_code': line.uom_id.uom_code,
                            'price_unit': line.price_unit,
                            'discount': line.discount,
                            'quantity': line.quantity,
                            'ukt_zed_id': line.product_id.ukt_zed_id.id,
                            'dkpp': line.product_id.dkpp,
                            'vd_sgt': line.product_id.vd_sgt,
                            'kod_pilg': line.product_id.exemption,
                            'is_imported': line.product_id.is_imported,

                        })
                        ti_l._compute_subtotal()
                    else:
                        continue
                if (len(line.invoice_line_tax_ids) == 0 and
                        line.quantity > 0 and
                        line.product_id == deposit_product_id):
                    tax_rate = vat_tax_id.amount / 100 if vat_tax_id else 0.0
                    ti_l = ti_line.with_context(ctx).create({
                        'taxinvoice_id': tax_invoice.id,
                        'taxinvoice_line_tax_id': vat_tax_id and vat_tax_id.id,
                        'account_id': (vat_tax_id and vat_tax_id.account_id and
                                       vat_tax_id.account_id.id),
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'uom_id': line.uom_id.id,
                        'uom_code': line.uom_id.uom_code,
                        'price_unit': (line.price_unit -
                                       (line.price_unit * tax_rate) /
                                       (1 + tax_rate)
                                       ),
                        'discount': line.discount,
                        'quantity': line.quantity,
                        'ukt_zed_id': line.product_id.ukt_zed_id.id,
                        'dkpp': line.product_id.dkpp,
                        'vd_sgt': line.product_id.vd_sgt,
                        'kod_pilg': line.product_id.exemption,
                        'is_imported': line.product_id.is_imported,
                    })
                    ti_l._compute_subtotal()
            tax_invoice._onchange_taxinvoice_line_ids()
            tax_invoice._compute_amount()
        return {}
