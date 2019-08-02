# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import base64


class P24AccountJournal(models.Model):
    _inherit = "account.journal"

    bank_statements_source = fields.Selection(
        selection_add=[('p24b_import', _('Privat24Business Import'))])
    p24_login = fields.Char(
        string='Privat24 Login')
    p24_passwd = fields.Char(
        string='Privat24 Password')
    client_id = fields.Char(
        string='client_id',
        help='Taken from developer console',
        default='98defe24-1a91-4aa3-9b5a-be19c465dc9f')
    client_secret = fields.Char(
        string='client_secret',
        help='Taken from developer console',
        default='23b9b950a773404dba466412d9c5eb40')

    @api.multi
    def p24b_sync_statement(self):
        login = ''
        passwd = ''
        if not self.bank_acc_number:
            raise UserError(_(u'Provide account number on bank journal!'))
        if self.p24_login:
            login = base64.b64decode(self.p24_login)
        if self.p24_passwd:
            passwd = base64.b64decode(self.p24_passwd)
        initial_values = {
            'journal_id': self.id,
            'bank_acc': self.bank_acc_number,
            'state': 'success',
            'task': 'statement_import',
            'login': login,
            'passwd': passwd,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }

        p24b = self.env['account.p24b.sync'].create(initial_values)
        return p24b.do_sync()

    @api.multi
    def write(self, vals):
        if 'p24_login' in vals:
            # encode field
            vals['p24_login'] = base64.b64encode(vals['p24_login'].encode())
        if 'p24_passwd' in vals:
            # encode field
            vals['p24_passwd'] = base64.b64encode(vals['p24_passwd'].encode())
        return super(P24AccountJournal, self).write(vals)

    @api.model
    def create(self, vals):
        if 'p24_login' in vals:
            if vals['p24_login']:
                # encode field
                vals['p24_login'] = base64.b64encode(vals['p24_login'].encode())
        if 'p24_passwd' in vals:
            if vals['p24_passwd']:
                # encode field
                vals['p24_passwd'] = base64.b64encode(vals['p24_passwd'].encode())
        return super(P24AccountJournal, self).create(vals)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        data = super(P24AccountJournal, self).read(fields=fields, load=load)
        for vals in data:
            if 'p24_login' in vals:
                if vals['p24_login']:
                    vals['p24_login'] = base64.b64decode(vals['p24_login']).decode()
            if 'p24_passwd' in vals:
                if vals['p24_passwd']:
                    vals['p24_passwd'] = base64.b64decode(vals['p24_passwd']).decode()
        return data
