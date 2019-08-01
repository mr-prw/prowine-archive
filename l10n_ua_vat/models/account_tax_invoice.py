# -*- coding: utf-8 -*-

import calendar
import os
from io import BytesIO
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from lxml import etree
from odoo import _, api, fields, models
from odoo.exceptions import UserError

import odoo.addons.decimal_precision as dp
import re
#
TYPE2JOURNAL = {
    'out_tax_invoice': 'sale',
    'in_tax_invoice': 'purchase',
}


class TIContrType(models.Model):
    _name = 'account.taxinvoice.contrtype'
    _description = 'Tax Invoice Contract Type'

    name = fields.Char(string="Тип договору")


class TIPayMeth(models.Model):
    _name = 'account.taxinvoice.paymeth'
    _description = 'Tax Invoice Payment method'

    name = fields.Char(string="Спосіб оплати")


class TaxInvoice(models.Model):
    _name = 'account.taxinvoice'
    _inherit = ['mail.thread']
    _description = 'Tax Invoice'

    state = fields.Selection(
        [
            ('draft', "Чорновий"),
            ('ready', "Підготовлено"),
            ('sent', "На реєстрації"),
            ('registered', "Зареєстровано"),
            ('cancel', "Скасовано"),
        ],
        string="Статус",
        index=True,
        readonly=True,
        default='draft',
        track_visibility='onchange',
        copy=False,
    )

    h01 = fields.Boolean(string="Складається інвестором",
                         default=False,
                         readonly=True,
                         states={'draft': [('readonly', False)]})
    h03 = fields.Boolean(string="Зведена ПН",
                         default=False,
                         readonly=True,
                         states={'draft': [('readonly', False)]})
    horig1 = fields.Boolean(string="Не видається покупцю",
                            states={'draft': [('readonly', False)]},
                            readonly=True,
                            default=False)
    htypr = fields.Selection([
        ('00', "Немає"),
        ('01', "01 - "
         "Складена на суму перевищення звичайної ціни над фактичною"),
        ('02', "02 - "
         "Постачання неплатнику податку"),
        ('03', "03 - "
         "Постачання товарів/послуг у рахунок оплати праці фізичним особам, "
         "які перебувають у трудових відносинах із платником податку"),
        ('04', "04 - "
         "Постачання у межах балансу для невиробничого використання"),
        ('05', "05 - "
         "Ліквідація основних засобів за самостійним "
         "рішенням платника податку"),
        ('06', "06 - "
         "Переведення виробничих основних засобів до складу невиробничих"),
        ('07', "07 - "
         "Експортні постачання"),
        ('08', "08 - "
         "Постачання для операцій, які не є об'єктом оподаткування "
         "податком на додану вартість"),
        ('09', "09 - "
         "Постачання для операцій, які звільнені від оподаткування "
         "податком на додану вартість"),
        ('10', "10 - "
         "Визначення при анулюванні платника податку податкових зобов'язань "
         "по товарах/послугах, необоротних активах, суми податку по яких "
         "були включені до складу податкового кредиту, не були використані "
         "в оподатковуваних операціях у межах господарської діяльності"),
        ('11', "11 - "
         "Складена за щоденними підсумками операцій"),
        ('12', "12 - "
         "Складена на вартість безоплатно поставлених товарів/послуг, "
         "обчислену виходячи з рівня звичайних цін"),
        ('13', "13 - "
         "Використання виробничих або невиробничих засобів, інших "
         "товарів/послуг не у господарській діяльності"),
        ('14', "14 - "
         "Складена покупцем (отримувачем) послуг від нерезидента"),
        ('15', "15 - "
         "Складена на суму перевищення митної вартості над фактичною "
         "ціною постачання"),
        ('16', "16 - "
         "Складена на суму перевищення балансової (залишкової) вартості "
         "необоротних активів над фактичною ціною їх постачання"),
        ('17', "17 - "
         "Складена на суму перевищення собівартості самостійно виготовлених "
         "товарів/послуг над фактичною ціною їх постачання"),
    ], string="Тип причини", index=True,
        change_default=True, default='00',
        states={'draft': [('readonly', False)]},
        readonly=True,
        track_visibility='always')

    date_vyp = fields.Date(
        string="Дата складання",
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Дата першої події з ПДВ",
        default=lambda self: fields.Date.context_today(self),
        copy=True,
        required=True)

    registration_deadline = fields.Date(
        string="Крайній термін реєстрації",
        compute='_deadline_date',
        index=True,
        readonly=True,
        help="Кінцева дата реєстрації в ЄРПН")

    danger_date = fields.Date(
        compute='_day_to_deadline',
        readonly=True)

    date_reg = fields.Date(string="Дата реєстрації", index=True,
                           readonly=False,
                           states={'registered': [('readonly', True)]},
                           help="Дата реєстрації в ЄРПН",
                           copy=False)

    number = fields.Char(string="Номер", size=7,
                         readonly=True,
                         states={'draft': [('readonly', False)],
                                 'ready': [('readonly', False)]},
                         required=False)
    number1 = fields.Char(string="Ознака спеціальної ПН",
                          states={'draft': [('readonly', False)]},
                          readonly=True,
                          size=1)

    @api.model
    def _get_my_number2(self):
        company_id = self.env.user.company_id
        my_code = company_id.kod_filii or ''
        return my_code

    number2 = fields.Char(string="Код філії",
                          states={'draft': [('readonly', False)]},
                          readonly=True,
                          default=_get_my_number2,
                          size=4)
    kod_filii = fields.Char(string="Код філії партнера",
                            states={'draft': [('readonly', False)]},
                            readonly=True,
                            size=4)

    category = fields.Selection(
        [
            ('out_tax_invoice', "Видані ПН"),
            ('in_tax_invoice', "Отримані ПН"),
        ],
        string="Категорія", readonly=True,
        index=True, change_default=True,
        default=lambda self: self._context.get('category', 'out_tax_invoice'),
        track_visibility='always')

    doc_type = fields.Selection(
        [
            ('pn', "Податкова накладна"),
            ('rk', "Розрахунок коригування до ПН"),
            ('vmd', "Митна декларація"),
            ('tk', "Транспортний квиток"),
            ('bo', "Бухгалтерська довідка"),
        ],
        string="Тип документу", index=True,
        states={'draft': [('readonly', False)]},
        readonly=True,
        change_default=True, default='pn',
        track_visibility='always')
    name = fields.Char(
        compute='_compute_name',
        readonly=True)

    partner_id = fields.Many2one(
        'res.partner',
        string="Партнер", ondelete='set null',
        help="Компанія-партнер",
        index=True, required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[ \
                  ('supplier', \
                   { \
                     'out_tax_invoice': '<=', \
                     'in_tax_invoice': '=' \
                    }.get(category, []), \
                   'True'), \
                   ('customer', \
                    { \
                      'out_tax_invoice': '=', \
                      'in_tax_invoice': '<=' \
                     }.get(category, []), \
                    'True'), \
                ]"  # Show only customers or suppliers
    )

    ipn_partner = fields.Char(string="ІПН партнера",
                              states={'draft': [('readonly', False)]},
                              readonly=True,
                              required=True)
    adr_partner = fields.Char(string="Адреса партнера",
                              states={'draft': [('readonly', False)]},
                              readonly=True,
                              required=False)
    tel_partner = fields.Char(string="Телефон партнера",
                              readonly=True,
                              states={'draft': [('readonly', False)]})

    contract_type = fields.Many2one('account.taxinvoice.contrtype',
                                    string="Тип договору",
                                    ondelete='set null',
                                    states={'draft': [('readonly', False)]},
                                    readonly=True,
                                    help="Тип договору згідно ЦКУ",
                                    index=True)
    contract_date = fields.Date(string="Дата договору",
                                readonly=True,
                                states={'draft': [('readonly', False)]})
    contract_numb = fields.Char(string="Номер договору",
                                readonly=True,
                                states={'draft': [('readonly', False)]},)
    payment_meth = fields.Many2one('account.taxinvoice.paymeth',
                                   string="Спосіб оплати",
                                   states={'draft': [('readonly', False)]},
                                   readonly=True,
                                   ondelete='set null',
                                   help="Спосіб оплати за постачання",
                                   index=True)
    prych_zv = fields.Char(string="Причина звільнення від ПДВ",
                           states={'draft': [('readonly', False)]},
                           readonly=True,
                           required=False)
    signer_id = fields.Many2one('res.users',
                                string="Відповідальна особа",
                                states={'draft': [('readonly', False)]},
                                readonly=True,
                                required=False,
                                ondelete='set null',
                                help="Особа, яка склала і підписала ПН",
                                index=True,
                                domain="[('company_id', '=', company_id)]")

    responsible_employee_id = fields.Many2one('hr.employee',
                                              string="Відповідальна особа",
                                              related='company_id.responsible_employee_id')

    company_full_name = fields.Char(string='Company name',
                                    related='company_id.company_full_name')

    @api.multi
    def _day_to_deadline(self):
        for record in self:
            deadline = fields.Date.from_string(record.registration_deadline)
            danger = deadline - timedelta(days=3)
            record.danger_date = danger

    @api.multi
    @api.depends('date_vyp')
    def _deadline_date(self):
        for rec in self:
            start_date = fields.Date.from_string(rec.date_vyp)
            if start_date.day < 16:
                _, last_day = calendar.monthrange(start_date.year,
                                                  start_date.month)
                rec.registration_deadline = date(start_date.year,
                                                 start_date.month,
                                                 last_day)
            else:
                date_after_month = start_date + relativedelta(months=1)
                rec.registration_deadline = date(date_after_month.year,
                                                 date_after_month.month,
                                                 15)

    @api.multi
    def _compute_name(self):
        for record in self:
            record.name = record.name_get()[0][1]

    # Modified record name on form view
    @api.multi
    def name_get(self):
        TYPES = {
            'pn': "Податкова накладна",
            'rk': "Розрахунок коригування до ПН",
            'vmd': "Митна декларація",
            'tk': "Транспортний квиток",
            'bo': "Бухгалтерська довідка",
        }
        result = []
        for inv in self:
            date = fields.Date.from_string(inv.date_vyp)
            datef = date.strftime('%d.%m.%Y')
            result.append(
                (inv.id, "%s № %s від %s" %
                 (TYPES[inv.doc_type], inv.number or '', datef)))
        return result

    @api.onchange('partner_id')
    def update_partner_info(self):
        if not self.partner_id:
            return
        else:
            self.ipn_partner = self.partner_id.vat if \
                self.partner_id.vat else ''
            self.kod_filii = self.partner_id.kod_filii if \
                self.partner_id.kod_filii else ''
        return {}

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(
                self._context.get('default_journal_id'))
        tinv_type = self._context.get('category', 'out_tax_invoice')
        tinv_types = tinv_type if isinstance(tinv_type, list) else [tinv_type]
        company_id = self._context.get('company_id',
                                       self.env.user.company_id.id)
        domain = [
            ('type', 'in',
             [TYPE2JOURNAL[ty] for ty in tinv_types if ty in TYPE2JOURNAL]),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    @api.model
    def _default_account(self):
        company_id = self.env.user.company_id
        return company_id.vat_account_id

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id

    taxinvoice_line_ids = fields.One2many('account.taxinvoice.line',
                                          'taxinvoice_id',
                                          string="Рядки ПН",
                                          readonly=True,
                                          states={'draft': [('readonly',
                                                             False)]},
                                          copy=True)
    tax_line_ids = fields.One2many('account.taxinvoice.tax', 'taxinvoice_id',
                                   string="Рядки податків",
                                   readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   copy=True)
    move_id = fields.Many2one('account.move', string="Запис в журналі",
                              readonly=True,
                              index=True,
                              ondelete='restrict',
                              copy=False,
                              help="Посилання на запис в журналі проведень")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True,
                                  readonly=True,
                                  states={'draft': [('readonly', False)]},
                                  default=_default_currency,
                                  track_visibility='always')
    company_currency_id = fields.Many2one('res.currency',
                                          related='company_id.currency_id',
                                          readonly=True)
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="""[
            ('type', 'in',
                {
                    'out_tax_invoice': ['sale'],
                    'in_tax_invoice': ['purchase']
                }.get(category, [])
            ),
            ('company_id', '=', company_id)
        ]""")
    company_id = fields.Many2one(
        'res.company',
        string="Компанія",
        change_default=True,
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: (self.env['res.company']._company_default_get(
            'account.taxinvoice')))
    account_id = fields.Many2one('account.account',
                                 string="Рахунок",
                                 required=True,
                                 readonly=True,
                                 default=_default_account,
                                 states={'draft': [('readonly', False)]},
                                 domain=[('deprecated', '=', False)],
                                 help="Рахунок розрахунків по ПДВ")
    amount_untaxed = fields.Monetary(string="Разом",
                                     store=True,
                                     readonly=True,
                                     compute='_compute_amount',
                                     track_visibility='always')
    amount_tax = fields.Monetary(string="Податок",
                                 store=True,
                                 readonly=True,
                                 track_visibility='always',
                                 compute='_compute_amount')
    amount_total = fields.Monetary(string="Всього",
                                   store=True,
                                   readonly=True,
                                   track_visibility='always',
                                   compute='_compute_amount')
    amount_tara = fields.Monetary(string="Зворотна тара",
                                  readonly=True,
                                  states={'draft': [('readonly', False)]},
                                  default=0.00)
    commercial_partner_id = fields.Many2one('res.partner',
                                            related='partner_id.commercial_partner_id')

    invoice_id = fields.Many2one('account.invoice',
                                 readonly=False,
                                 string="Рахунок-фактура",
                                 copy=False,
                                 help="Пов’язаний рахунок",
                                 domain="[('type', 'in', \
                                          {'out_tax_invoice': \
                                           ['out_invoice'], \
                                           'in_tax_invoice': \
                                           ['in_invoice']}.get( \
                                           category, [])), \
                                           ('company_id', '=', \
                                           company_id), \
                                           ('commercial_partner_id', '=', \
                                           commercial_partner_id)]")

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            self.currency_id = self.journal_id.currency_id.id or \
                self.journal_id.company_id.currency_id.id

    @api.onchange('taxinvoice_line_ids')
    def _onchange_taxinvoice_line_ids(self):
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.browse([])
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
        self.tax_line_ids = tax_lines
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

    @api.multi
    def get_taxes_values(self):
        self.ensure_one()
        tax_grouped = {}
        vat_tags = self.get_vat_tags(self.company_id)

        for line in self.taxinvoice_line_ids:
            if not line.taxinvoice_line_tax_id:
                continue

            tl_id = line.taxinvoice_line_tax_id
            vat_tag = None

            for tag in tl_id.tag_ids:
                if tag in vat_tags:
                    vat_tag = tag
                    break
            if not vat_tag:
                continue

            price_unit = line.price_unit * \
                (1 - (line.discount or 0.0) / 100.0)

            prec = self.currency_id.decimal_places
            if self.company_id.tax_calculation_rounding_method == \
               'round_globally':
                prec += 5
            total_excluded = total_included = base = \
                round(price_unit * line.quantity, prec)

            if not tl_id.price_include:
                tax_amount = base * tl_id.amount / 100
            if tl_id.price_include:
                tax_amount = (base * tl_id.amount /
                              (100 + tl_id.amount))

            tax_amount = self.currency_id.round(tax_amount)

            if not tl_id.price_include:
                total_included += tax_amount
            if tl_id.price_include:
                total_excluded -= tax_amount
                base -= tax_amount

            val = {
                'taxinvoice_id': self.id,
                'name': tl_id.name,
                'tax_id': tl_id.id,
                'base': base,
                'amount': tax_amount,
                'manual': False,
                'sequence': tl_id.sequence,
                'account_analytic_id': tl_id.analytic or False,
                'account_id': (tl_id.account_id or line.account_id.id),
            }
            key = tl_id.id
            if key not in tax_grouped:
                tax_grouped[key] = val
            else:
                tax_grouped[key]['amount'] += val['amount']
                tax_grouped[key]['base'] += val['base']
        return tax_grouped

    @api.multi
    @api.depends('taxinvoice_line_ids.price_subtotal',
                 'tax_line_ids.amount',
                 'tax_line_ids.base',
                 'currency_id',
                 'company_id',
                 'amount_tara')
    def _compute_amount(self):
        for rec in self:
            amount_untaxed = 0
            amount_tax = 0
            for tax_line in rec.tax_line_ids:
                amount_untaxed += tax_line.base
                amount_tax += tax_line.amount
            rec.amount_untaxed = amount_untaxed
            rec.amount_tax = amount_tax
            rec.amount_total = amount_untaxed + amount_tax
            rec.amount_total += rec.amount_tara

    @api.multi
    def action_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def action_ready(self):
        for tinv in self:
            ctx = dict(self._context, lang=tinv.partner_id.lang)
            ctx['ir_sequence_date'] = tinv.date_vyp
            if tinv.category == 'out_tax_invoice':
                if not tinv.taxinvoice_line_ids:
                    raise UserError(_("Немає жодного рядка в документі!"))
                if not tinv.number:
                    tinv.number = self.env['ir.sequence'].with_context(
                        ctx).next_by_code('out.taxinvoice')
                    if not tinv.number:
                        self.env['ir.sequence'].create({
                            'name': 'Видані ПН',
                            'implementation': 'standard',
                            'code': 'out.taxinvoice',
                            'active': True,
                            'company_id': self.company_id.id,
                            'use_date_range': True,
                            'padding': 1,
                            'number_increment': 1,
                            'number_next': 1
                        })
                        tinv.number = self.env['ir.sequence'].with_context(
                            ctx).next_by_code('out.taxinvoice')
            if tinv.category == 'in_tax_invoice':
                if not tinv.number:
                    raise UserError(_("Вкажіть номер податкової накладної"))
        self.write({'state': 'ready'})

    @api.multi
    def action_sent(self):
        self.write({'state': 'sent'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def action_registered(self):
        for tinv in self:
            if not tinv.date_reg:
                raise UserError(_("Спочатку вкажіть дату реєстрації."))
        self.write({'state': 'registered'})

        self.action_move_create()

    @api.multi
    def action_move_create(self):
        """ Creates tax invoice related financial move lines """
        account_move = self.env['account.move']

        for tinv in self:
            # if tinv.amount_tax == 0:
            #     raise UserError(_("Сума ПДВ дорівнює нулю!"))
            if tinv.move_id:
                if tinv.move_id.id != 0:
                    raise UserError(_("Запис в журналі вже створенно!"))
            if tinv.invoice_id:
                if tinv.invoice_id.number:
                    reference = tinv.invoice_id.number
                else:
                    reference = '/'
            else:
                reference = '/'
            ctx = dict(self._context, lang=tinv.partner_id.lang)
            # date_taxinvoice = tinv.date_vyp
            # company_currency = tinv.company_id.currency_id
            journal = tinv.journal_id.with_context(ctx)
            date = tinv.date_vyp
            move_vals = {
                'name': "ПН/%s" % tinv.number,
                'journal_id': journal.id,
                'ref': reference,
                'date': date,
            }
            ctx['company_id'] = tinv.company_id.id
            ctx['dont_create_taxes'] = True
            ctx['check_move_validity'] = False
            move = account_move.with_context(ctx).create(move_vals)
            # one move per tax line and
            # last move in counterpart for total tax amount
            for t_line in tinv.tax_line_ids:
                if t_line.amount > 0:
                    deb = t_line.amount \
                        if (tinv.category == 'out_tax_invoice') else 0.00
                    cred = t_line.amount \
                        if (tinv.category == 'in_tax_invoice') else 0.00
                    self.env['account.move.line'].with_context(ctx).create({
                        'date_maturity': tinv.date_vyp,
                        'partner_id': tinv.partner_id.id,
                        'name': t_line.name,
                        'debit': deb,
                        'credit': cred,
                        'account_id': t_line.account_id.id,
                        'currency_id': tinv.currency_id.id,
                        'quantity': 1.00,
                        'tax_line_id': t_line.tax_id.id,
                        'analytic_line_ids': False,
                        'product_id': False,
                        'product_uom_id': False,
                        'analytic_account_id': False,
                        'invoice_id': False,
                        'tax_ids': False,
                        'move_id': move.id,
                    })
            deb = tinv.amount_tax \
                if (tinv.category == 'in_tax_invoice') else 0.00
            cred = tinv.amount_tax \
                if (tinv.category == 'out_tax_invoice') else 0.00
            self.env['account.move.line'].with_context(ctx).create({
                'date_maturity': tinv.date_vyp,
                'partner_id': tinv.partner_id.id,
                'name': "ПН/%s" % tinv.number,
                'debit': deb,
                'credit': cred,
                'account_id': tinv.account_id.id,
                'currency_id': tinv.currency_id.id,
                'quantity': 1.00,
                'analytic_line_ids': False,
                'product_id': False,
                'product_uom_id': False,
                'analytic_account_id': False,
                'invoice_id': False,
                'tax_ids': False,
                'tax_line_id': False,
                'move_id': move.id,
            })
            move.post()
            # make the taxinvoice point to that move
            vals = {
                'move_id': move.id,
            }
            tinv.with_context(ctx).write(vals)
        return True

    @api.multi
    def xml_validate(self, xmldata, tag):
        path = os.path.dirname(os.path.abspath(__file__))
        xmlfile = etree.parse(BytesIO(xmldata))
        xmlscheme = etree.XMLSchema(etree.parse(path +
                                                "/../data/{}01009.xsd"
                                                .format(tag)))
        validate = xmlscheme.validate(xmlfile)
        if validate:
            return True, "OK"

        result_error = []
        for error in xmlscheme.error_log:
            result_error.append("Помилка, рядок {}: {}"
                                .format(error.line, error.message))
        return False, '\n'.join(result_error)

    @api.multi
    def export_validate(self):
        err_log = []
        ukt_zed_valid = re.compile(r'(^\d{10}$)|(^\d{8}$)|(^\d{6}$)'
                                   r'|(^\d{3}$)|(^\d{4}$)|(^[0]$)')
        self.ensure_one()
        if not self.number:
            err_log.append(_(". Вкажіть номер податкової накладної."))
        if not self.company_id.comp_sti:
            err_log.append(_(". Вкажіть вашу ДПІ у налаштуваннях компанії."))
        if not self.company_id.company_registry:
            err_log.append(_(". Вкажіть ЄДРПОУ у налаштуваннях компанії."))
        if not self.company_id.vat:
            err_log.append(_(". Вкажіть ІПН у налаштуваннях компанії."))
        if not self.responsible_employee_id.identification_id:
            err_log.append(_(""". Вкажіть ідентифікаційний код
                                      відповідальної особи у налаштуваннях
                                      пов’язаного контрагента."""))

        for tl in self.taxinvoice_line_ids:
            if tl.product_id.type != 'service':
                if type(tl.ukt_zed_id.name) == bool:
                    err_log.append(_(". Поле УКТ ЗЕД для товару '{}' "
                                     "не заповнене."
                                     .format(tl.product_id.name)))
                elif tl.is_imported and len(tl.ukt_zed_id.name.strip()) != 10:
                    err_log.append(_(". Імпортований товар '{}' "
                                     "має невірний формат УКТ ЗЕД: {}. "
                                     "Очікується 10 символів."
                                     .format(tl.product_id.name,
                                             tl.product_id.ukt_zed_id.name)))
                elif not ukt_zed_valid.match(tl.ukt_zed_id.name):
                    err_log.append(_(". Товар '{}' має невірний формат "
                                     "УКТ ЗЕД: {}. Очікується більше 4-х "
                                     "символів (4, 6, 8 або 10)."
                                     .format(tl.product_id.name,
                                             tl.product_id.ukt_zed_id.name)))
        if len(err_log) > 0:
            err_log = [str(num+1) + text for num, text in enumerate(err_log)]
            return False, '\n'.join(err_log)
        return True, "OK"

    @api.multi
    def _export_xml_data(self):
        """Prepare xml data for export.
        This function returns name of xml file
        and data to be put inside."""
        self.ensure_one()
        valid, err_msg = self.export_validate()
        if not valid:
            raise UserError(err_msg)

        data = {}
        jf = 'J' if self.company_id.legal_status == 'company' else 'F'
        tag = jf + '12'
        ver = '9'
        date = fields.Date.from_string(self.date_vyp)
        tag20 = self.company_id.vat20_tax_tag_id
        tag7 = self.company_id.vat7_tax_tag_id
        tag0 = self.company_id.vat0_tax_tag_id
        tagfree = self.company_id.vatfree_tax_tag_id
        tagnot = self.company_id.vatnot_tax_tag_id
        # compose file name
        fname = ''
        fname = self.company_id.comp_sti.c_reg.zfill(2)
        fname += self.company_id.comp_sti.c_raj.zfill(2)
        fname += self.company_id.company_registry.zfill(10)
        fname += tag
        fname += '010'
        fname += ver.zfill(2)
        fname += '1'
        fname += '00'
        fname += self.number.zfill(7)
        fname += '1'
        fname += date.strftime('%m')
        fname += date.strftime('%Y')
        fname += self.company_id.comp_sti.c_sti.zfill(4)
        fname += '.xml'

        data['xsd_ver'] = tag + '0100' + ver + '.xsd'
        data['tin'] = self.company_id.company_registry
        data['c_doc'] = tag
        data['c_doc_sub'] = '010'
        data['c_doc_ver'] = ver
        data['c_doc_type'] = '00'
        data['c_doc_cnt'] = self.number
        data['c_reg'] = self.company_id.comp_sti.c_reg
        data['c_raj'] = self.company_id.comp_sti.c_raj
        data['per_month'] = date.strftime('%m')
        data['per_type'] = '1'
        data['per_year'] = date.strftime('%Y')
        data['c_sti_orig'] = self.company_id.comp_sti.c_sti.zfill(4)
        data['c_doc_stan'] = '1'
        data['linked'] = {'nil': 'true'}
        data['d_fill'] = date.strftime('%d%m%Y')
        data['software'] = 'Odoo'

        # declarbody part
        if self.h03:
            data['h03'] = {'cnt': '1'}
        else:
            data['h03'] = {'nil': 'true'}

        # begin
        found_20 = found_7 = found_0 = found_zv = False
        base_20 = amount_20 = base_7 = amount_7 = base_0 = base_zv = 0.0
        not_vat_base = 0
        for tx in self.tax_line_ids:
            if (len(tx.tax_id.tag_ids.filtered(lambda t: t == tag20)) > 0 and
                    not found_20):
                found_20 = True
                base_20 = "%.2f" % tx.base
                amount_20 = "%.2f" % tx.amount
                continue
            if (len(tx.tax_id.tag_ids.filtered(lambda t: t == tag7)) > 0 and
                    not found_7):
                found_7 = True
                base_7 = "%.2f" % tx.base
                amount_7 = "%.2f" % tx.amount
                continue
            if (len(tx.tax_id.tag_ids.filtered(lambda t: t == tag0)) > 0 and
                    not found_0):
                found_0 = True
                base_0 = "%.2f" % tx.base
                continue
            if (len(tx.tax_id.tag_ids.filtered(lambda t: t == tagfree)) > 0 and
                    not found_zv):
                found_zv = True
                base_zv = "%.2f" % tx.base
        # end
        if not found_zv:
            data['r03g10s'] = {'nil': 'true'}
        else:
            data['r03g10s'] = {'cnt': ''}
        if self.horig1:
            data['horig1'] = {'cnt': '1'}
            data['htypr'] = {'cnt': self.htypr}
        else:
            data['horig1'] = {'nil': 'true'}
            data['htypr'] = {'nil': 'true'}
        data['hfill'] = date.strftime('%d%m%Y')
        data['hnum'] = self.number
        if self.number1 is not False:
            data['hnum1'] = {'cnt': self.number1}
        else:
            data['hnum1'] = {'nil': 'true'}
        if self.category == 'out_tax_invoice':
            esc_hnamesel = self.company_full_name or self.company_id.name
            data['hnamesel'] = ''
            if self.htypr == '02':
                esc_hnamebuy = "Неплатник"
                data['hnamebuy'] = ''
            else:
                esc_hnamebuy = self.partner_id.parent_name or \
                               self.partner_id.name
                data['hnamebuy'] = ''
            data['hksel'] = self.company_id.vat
            if self.number2 is not False:
                data['hnum2'] = {'cnt': self.number2}
            else:
                data['hnum2'] = {'nil': 'true'}
            if self.htypr == '02':
                data['hkbuy'] = "100000000000"
            else:
                data['hkbuy'] = self.ipn_partner
            if self.kod_filii is not False:
                data['hfbuy'] = {'cnt': self.kod_filii}
            else:
                data['hfbuy'] = {'nil': 'true'}
        else:   # in tax invoice
            esc_hnamesel = self.partner_id.parent_name or self.partner_id.name
            esc_hnamebuy = self.company_full_name or self.company_id.name
            data['hnamesel'] = ''
            data['hnamebuy'] = ''
            data['hksel'] = {'cnt': self.ipn_partner}
            if self.kod_filii is not False:
                data['hnum2'] = {'cnt': self.kod_filii}
            else:
                data['hnum2'] = {'nil': 'true'}
            data['hkbuy'] = self.company_id.vat
            if self.number2 is not False:
                data['hfbuy'] = {'cnt': self.number2}
            else:
                data['hfbuy'] = {'nil': 'true'}

        # begin subtotal
        for tl in self.taxinvoice_line_ids:
            tax_id = tl.taxinvoice_line_tax_id
            if len(tax_id.tag_ids.filtered(lambda t: t == tagnot)) > 0:
                not_vat_base += tl.price_subtotal
                continue
        if self.amount_total:
            data['r04g11'] = {
                'cnt': '{0:.2f}'.format(
                    float(self.amount_total - not_vat_base))}
        else:
            data['r04g11'] = {'nil': 'true'}
        if self.amount_tax:
            data['r03g11'] = {'cnt': '{0:.2f}'.format(self.amount_tax)}
        else:
            data['r03g11'] = {'nil': 'true'}
        if not found_20:
            data['r01g7'] = {'nil': 'true'}
            data['r03g7'] = {'nil': 'true'}
        else:
            data['r03g7'] = {'cnt': amount_20}
            data['r01g7'] = {'cnt': base_20}
        if not found_7:
            data['r03g109'] = {'nil': 'true'}
            data['r01g109'] = {'nil': 'true'}
        else:
            data['r03g109'] = {'cnt': amount_7}
            data['r01g109'] = {'cnt': base_7}
        if not found_0:
            data['r01g9'] = {'nil': 'true'}
            data['r01g8'] = {'nil': 'true'}
        else:
            if self.htypr == '07':
                data['r01g9'] = {'cnt': base_0}
                data['r01g8'] = {'nil': 'true'}
            else:
                data['r01g9'] = {'nil': 'true'}
                data['r01g8'] = {'cnt': base_0}
        if not found_zv:
            data['r01g10'] = {'nil': 'true'}
        else:
            data['r01g10'] = {'cnt': base_zv}
        # total
        if self.amount_tara > 0:
            data['r02g11'] = {'cnt': '{0:.2f}'.format(self.amount_tara)}
        else:
            data['r02g11'] = {'nil': 'true'}
        # end

        # for tax lines loop
        data['rxxxxg3s'] = []
        data['rxxxxg4'] = []
        data['rxxxxg32'] = []
        data['rxxxxg33'] = []
        data['rxxxxg4s'] = []
        data['rxxxxg105_2s'] = []
        data['rxxxxg5'] = []
        data['rxxxxg6'] = []
        data['rxxxxg008'] = []
        data['rxxxxg009'] = []
        data['rxxxxg010'] = []
        data['rxxxxg011'] = []

        esc_g3s_list = []
        esc_g4s_list = []
        row_num = 0
        for tl in self.taxinvoice_line_ids:
            tax_id = tl.taxinvoice_line_tax_id
            if len(tax_id.tag_ids.filtered(lambda t: t == tagnot)) > 0:
                continue
                # do not export lines with this tax

            row_num += 1
            esc_g3s_list.append(tl.name)
            data['rxxxxg3s'].append('')

            if tl.ukt_zed_id.name and tl.product_id.type != 'service':
                data['rxxxxg4'].append({'cnt': tl.ukt_zed_id.name})
            else:
                data['rxxxxg4'].append({'nil': 'true'})

            if tl.is_imported:
                data['rxxxxg32'].append({'cnt': '1'})
            else:
                data['rxxxxg32'].append({'nil': 'true'})

            if tl.dkpp and tl.product_id.type == 'service':
                data['rxxxxg33'].append({'cnt': tl.dkpp})
            else:
                data['rxxxxg33'].append({'nil': 'true'})
            esc_g4s_list.append(tl.uom_id.name)
            data['rxxxxg4s'].append('')

            if tl.uom_id.uom_code:
                data['rxxxxg105_2s'].append({'cnt': tl.uom_id.uom_code})
            else:
                data['rxxxxg105_2s'].append({'nil': 'true'})

            data['rxxxxg5'].append(tl.quantity)

            data['rxxxxg6'].append('{0:.2f}'.format(tl.price_unit_wo_tax))

            if len(tax_id.tag_ids.filtered(lambda t: t == tag20)) > 0:
                tag_text = '20'
            if len(tax_id.tag_ids.filtered(lambda t: t == tag7)) > 0:
                tag_text = '7'
            if len(tax_id.tag_ids.filtered(lambda t: t == tag0)) > 0:
                if self.htypr == '07':  # if export
                    tag_text = '901'
                else:
                    tag_text = '902'
            if len(tax_id.tag_ids.filtered(lambda t: t == tagfree)) > 0:
                tag_text = '903'
            data['rxxxxg008'].append(tag_text)

            if tl.kod_pilg:
                data['rxxxxg009'].append({'cnt': tl.kod_pilg})
            else:
                data['rxxxxg009'].append({'nil': 'true'})

            if tl.price_subtotal != 0:
                data['rxxxxg010'].append({
                    'cnt': '{0:.2f}'.format(tl.price_subtotal)
                })
            else:
                data['rxxxxg010'].append({'nil': 'true'})

            if tl.vd_sgt:
                data['rxxxxg011'].append({'cnt': tl.vd_sgt})
            else:
                data['rxxxxg011'].append({'nil': 'true'})

        # footer
        esc_hbos = self.responsible_employee_id.name
        data['hbos'] = ''
        data['hkbos'] = self.responsible_employee_id.identification_id
        if self.prych_zv:
            data['r003g10s'] = {'cnt': self.prych_zv}
        else:
            data['r003g10s'] = {'nil': 'true'}

        result = self.env['ir.ui.view'].render_template(
            'l10n_ua_vat.export_template', data).strip()
        root = etree.parse(BytesIO(result)).getroot()

        declarbody = root.find('DECLARBODY')
        declarbody.find('HNAMESEL').text = esc_hnamesel
        declarbody.find('HNAMEBUY').text = esc_hnamebuy
        declarbody.find('HBOS').text = esc_hbos
        if 'nil' not in data['r03g10s']:
            declarbody.find('R03G10S').text = 'Звільнено'

        g3s_names = declarbody.iterfind('RXXXXG3S')
        g4s_uom = declarbody.iterfind('RXXXXG4S')
        for index, g3s_4s in enumerate(zip(g3s_names, g4s_uom)):
            g3s_4s[0].text = esc_g3s_list[index]
            g3s_4s[1].text = esc_g4s_list[index]

        xmldata = etree.tostring(root,
                                 encoding='windows-1251',
                                 method='xml')

        # xml validate
        validate, err_msg = self.xml_validate(xmldata, tag)
        if not validate:
            raise UserError(_(err_msg))

        return xmldata, fname


class TaxInvoiceLine(models.Model):
    _name = 'account.taxinvoice.line'
    _description = 'Tax Invoice Line'

    @api.multi
    @api.depends('price_unit', 'discount', 'taxinvoice_line_tax_id',
                 'quantity', 'product_id')
    def _compute_subtotal(self):
        for rec in self:
            if not rec.taxinvoice_line_tax_id:
                rec.price_subtotal = 0
                rec.tax_amount = 0
                continue

            if rec.taxinvoice_id:
                currency = rec.taxinvoice_id.currency_id
            if not currency:
                raise UserError(_("Виберіть валюту в документі!"))

            prec = currency.decimal_places
            if (rec.taxinvoice_id.company_id
                    .tax_calculation_rounding_method == 'round_globally'):
                prec += 5

            tl_id = rec.taxinvoice_line_tax_id
            tax_rate = tl_id.amount
            qty = rec.quantity
            price = rec.price_unit * (1 - (rec.discount or 0.0) / 100.0)
            price_subtotal = round(qty * price, prec)
            if not tl_id.price_include:
                tax_amount = price_subtotal * tax_rate / 100
            if tl_id.price_include:
                tax_amount = price_subtotal * tax_rate / (100 + tax_rate)
                price_subtotal -= tax_amount

            if qty != 0:
                rec.update({
                    'price_subtotal': currency.round(price_subtotal),
                    'tax_amount': currency.round(tax_amount),
                    'price_unit_wo_tax': price_subtotal / qty,
                })

    name = fields.Text(
        string="Назва",
        required=True)
    sequence = fields.Integer(
        string="Послідовність", default=10,
        help="Перетягніть для зміни порядкового номеру")
    taxinvoice_id = fields.Many2one(
        'account.taxinvoice',
        string="Посилання на ПН",
        ondelete='cascade', index=True)
    date_vynyk = fields.Date(
        string="Дата виникнення ПЗ",
        related='taxinvoice_id.date_vyp',
        help="Дата першої події з ПДВ",
        copy=True,
        store=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='taxinvoice_id.company_id',
        store=True, readonly=True)
    product_id = fields.Many2one(
        'product.product', string='Product',
        ondelete='restrict',
        index=True, required=True)
    uom_id = fields.Many2one(
        'product.uom', string="Одиниця виміру",
        ondelete='set null', index=True, required=True)
    uom_code = fields.Char(
        string="Код одиниць",
        help="Код одниниць виміру згідно КСПОВО",
        size=4)
    price_unit = fields.Float(
        string="Ціна за одиницю",
        digits=dp.get_precision('Product Price'),
        default=0, required=True)
    price_unit_wo_tax = fields.Float(
        string="Ціна без ПДВ",
        compute='_compute_subtotal',
        digits=(14, 4),
        store=True)
    discount = fields.Float(
        string="Знижка (%)",
        digits=dp.get_precision('Discount'),
        default=0.0)
    quantity = fields.Float(
        string="Кількість",
        digits=dp.get_precision('Product Unit of Measure'),
        required=True, default=1)
    ukt_zed_id = fields.Many2one(
        string="Код УКТ ЗЕД",
        help="Код товару згідно УКТ ЗЕД",
        related='product_id.ukt_zed_id',
        size=10)
    dkpp = fields.Char(
        string="Код ДКПП",
        related='product_id.dkpp',
        help="Код послуг згідно ДКПП")
    vd_sgt = fields.Char(
        string="Код ВД СГТ",
        help="Код виду діяльності сільськогосподарського товаровиробника")
    is_imported = fields.Boolean(
        string="Імпортований",
        related='product_id.is_imported',
        help="Ознака імпортованого товару")
    taxinvoice_line_tax_id = fields.Many2one(
        'account.tax',
        string="Ставка податку",
        required=True
    )
    kod_pilg = fields.Char(
        string="Код пільги")
    price_subtotal = fields.Float(
        string="Сума",
        digits=dp.get_precision('Product Price'),
        store=True,
        readonly=True,
        compute='_compute_subtotal')
    account_id = fields.Many2one(
        'account.account', string="Рахунок",
        domain=[('deprecated', '=', False)],
        help="Рахунок підтверженного ПДВ")
    tax_amount = fields.Float(
        string="Сума податку",
        digits=dp.get_precision('Product Price'),
        store=True,
        compute='_compute_subtotal')

    @api.multi
    def _get_self_description(self, product_id):
        self.ensure_one()
        if not product_id or not self.taxinvoice_id:
            return ''
        name = product_id.partner_ref
        if self.taxinvoice_id.category == 'in_tax_invoice':
            if product_id.description_purchase:
                name += '\n' + product_id.description_purchase
        else:
            if product_id.description_sale:
                name += '\n' + product_id.description_sale
        return name

    @api.multi
    def _get_vat_tax_id(self, product_id):
        self.ensure_one()

        if not product_id or not self.taxinvoice_id:
            return None, None

        vat_tags = self.taxinvoice_id.get_vat_tags(
            self.taxinvoice_id.company_id)

        if self.taxinvoice_id.category == 'out_tax_invoice':
            taxes = product_id.taxes_id
        else:
            taxes = product_id.supplier_taxes_id

        if taxes:
            t = taxes.filtered(
                lambda tx: any(
                    tx.tag_ids.filtered(
                        lambda tg: tg in vat_tags)))
            if t:
                return t[0], [tag.id for tag in vat_tags]
        return None, None

    @api.onchange('product_id')
    def onchange_product_id(self):
        """Update other fields when product is changed."""

        domain = {}
        company = self.taxinvoice_id.company_id
        currency = self.taxinvoice_id.currency_id
        category = self.taxinvoice_id.category

        if not company or not currency or not category:
            return domain

        if not self.taxinvoice_id or not self.taxinvoice_id.partner_id:
            warning = {
                'title': _("Попередження!"),
                'message': _("Спочатку оберіть партнера!"),
            }
            return {'warning': warning}

        if not self.product_id:
            self.update({
                'name': '',
                'price_unit': 0.0,
                'discount': 0.0,
                'quantity': 0,
                'ukt_zed_id': '',
                'dkpp': '',
                'vd_sgt': '',
                'kod_pilg': '',
                'is_imported': False,
                'uom_id': False,
                'uom_code': '',
                'account_id': False,
            })
            domain['uom_id'] = []
            return domain

        product = self.product_id
        name = self._get_self_description(product)
        tax_id, vat_tags_ids = self._get_vat_tax_id(product)
        account_id = tax_id.account_id if tax_id else None

        if category == 'in_tax_invoice':
            price_unit = self.price_unit or product.standard_price
        else:
            price_unit = product.lst_price

        if not self.uom_id or \
                product.uom_id.category_id.id != \
                self.uom_id.category_id.id:
            uom_id = product.uom_id.id
            uom_code = product.uom_id.uom_code

        if self.uom_id:
            uom_id = self.uom_id
            uom_code = self.uom_code
            if self.uom_code != self.uom_id.uom_code:
                uom_code = self.uom_id.uom_code

        if company.currency_id != currency:
            if category == 'in_tax_invoice':
                price_unit = product.standard_price
            price_unit = price_unit * \
                currency.with_context(
                    dict(self._context or {},
                         date=self.taxinvoice_id.date_vyp)).rate

        if self.uom_id and self.uom_id.id != product.uom_id.id:
            price_unit = \
                self.uom_id._compute_price(price_unit, product.uom_id)

        self.update({
            'name': name,
            'price_unit': price_unit,
            'discount': 0.0,
            'quantity': 1.0,
            'ukt_zed_id': int(product.ukt_zed_id.name),
            'dkpp': product.dkpp,
            'vd_sgt': product.vd_sgt,
            'kod_pilg': product.exemption,
            'is_imported': product.is_imported,
            'account_id': account_id,
            'taxinvoice_line_tax_id': tax_id and tax_id.id or None,
            'uom_id': uom_id,
            'uom_code': uom_code,
        })

        domain['uom_id'] = [
            ('category_id', '=', product.uom_id.category_id.id)]
        domain['taxinvoice_line_tax_id'] = [
            ('type_tax_use', 'in',
             {'out_tax_invoice': ['sale'],
              'in_tax_invoice': ['purchase']}.get(category, [])
             ),
            ('company_id', '=', company.id),
            ('tag_ids', 'in', vat_tags_ids)
        ]
        return {'domain': domain}

    @api.onchange('uom_id')
    def onchange_uom_id(self):
        """Update uom_code field when uom_id is changed."""
        warning = {}
        result = {}
        self.onchange_product_id()
        if not self.uom_id:
            self.price_unit = 0.0
        if self.product_id and self.uom_id:
            if self.product_id.uom_id.category_id.id != \
               self.uom_id.category_id.id:
                warning = {
                    'title': _("Попередження!"),
                    'message': _("Обрана одиниця виміру не "
                                 "сумісна з одиницею виміру "
                                 "товару."),
                }
                self.uom_id = self.product_id.uom_id.id
        if warning:
            result['warning'] = warning
        return result

    @api.onchange('taxinvoice_line_tax_id')
    def onchange_taxinvoice_line_tax_id(self):
        """Update account_id field when taxinvoice_line_tax_id is changed."""
        if self.taxinvoice_line_tax_id:
            if self.taxinvoice_line_tax_id.account_id:
                self.account_id = self.taxinvoice_line_tax_id.account_id
            else:
                self.account_id = None
        else:
            self.account_id = None


class TaxInvoiceTax(models.Model):
    _name = 'account.taxinvoice.tax'
    _description = 'Tax Invoice taxes'
    _order = 'sequence'

    sequence = fields.Integer(string="Послідовність",
                              help="Перетягніть для зміни порядкового номеру")
    taxinvoice_id = fields.Many2one('account.taxinvoice',
                                    string="Посилання на ПН",
                                    ondelete='cascade', index=True)
    name = fields.Char(string="Назва податку",
                       required=True)
    account_id = fields.Many2one('account.account', string="Рахунок податку",
                                 required=True)
    account_analytic_id = fields.Many2one('account.analytic.account',
                                          string="Аналітичний рахунок")
    base = fields.Monetary(string="База", readonly=True)
    amount = fields.Monetary(string="Сума")
    manual = fields.Boolean(string="Вручну", default=True)
    company_id = fields.Many2one('res.company',
                                 string="Компанія",
                                 related='account_id.company_id',
                                 store=True, readonly=True)
    tax_id = fields.Many2one('account.tax', string="Податок")
    currency_id = fields.Many2one('res.currency',
                                  related='taxinvoice_id.currency_id',
                                  store=True, readonly=True)
