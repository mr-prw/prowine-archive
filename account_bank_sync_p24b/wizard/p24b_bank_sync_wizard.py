# -*- coding: utf-8 -*-

import base64
import json
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime as dt
from datetime import timedelta as td

import dateutil.parser
import requests

from odoo import _, api, fields, models
from odoo.addons.base.res.res_bank import sanitize_account_number

_logger = logging.getLogger(__name__)


class P24BBankSync(models.TransientModel):
    _name = 'account.p24b.sync'
    _description = 'Privat24Business Sync client'

######################################################
# Privat24Business part###############################
######################################################

    BASIC_AUTH_URL = 'https://link.privatbank.ua/api/auth/'
    CREATE_SESSION_URL = BASIC_AUTH_URL + 'createSession'
    VALIDATE_SESSION_URL = BASIC_AUTH_URL + 'validateSession'
    REMOVE_SESSION_URL = BASIC_AUTH_URL + 'removeSession'

    P24_AUTH_URL = 'https://link.privatbank.ua/api/p24BusinessAuth/'
    P24_CREATE_SESSION_URL = P24_AUTH_URL + 'createSession'
    P24_SEL_OTP_DEV_URL = P24_AUTH_URL + 'sendOtp'
    P24_CHECK_OTP_URL = P24_AUTH_URL + 'checkOtp'

    P24_URL = 'https://link.privatbank.ua/api/p24b/'
    P24_STATEMENTS_URL = P24_URL + 'statements'
    P24_RESTS_URL = P24_URL + 'rests'
    P24_NEWPAYMENT_URL = P24_URL + 'nbu_payment_new'

    r = None
    session_expires_in = None
    roles = None
    # Reusable session
    s = requests.Session()

    def _basic_auth(self):
        """First step of authorization.

        On success we get session token with user role.
        """
        data = {
            'clientId': self.client_id,
            'clientSecret': self.client_secret
        }
        if not self.client_id:
            _logger.warning('basic auth: no client_id')
        if not self.client_secret:
            _logger.warning('basic auth: no client_secret')
        if 'Authorization' in self.s.headers:
            del self.s.headers['Authorization']
        self.r = self.s.post(self.CREATE_SESSION_URL,
                             data=json.dumps(data),
                             timeout=self.timeout)
        _logger.debug('Response body [%s]', self.r.text)
        response = self.r.json()
        if 'error' in response:
            _logger.warning(response.get('error', ''))
            self.error_message = (
                _('[%s] basic auth: %s') %
                (self.r.status_code, response.get('error', ''))
            )
            return False
        if self.r.status_code == 200:
            # OK
            if self.client_id != response['clientId']:
                self.error_message = _('basic auth: wrong client_id received.')
                _logger.warning('basic auth: wrong client_id received.')
                return False
            self.session_id = response.get('id', '')
            if not self.session_id:
                self.error_message = _('basic auth: no session_id received.')
                _logger.warning('basic auth: no session_id received.')
                return False
            self.session_expires_in = dt.fromtimestamp(response['expiresIn'])
            self.roles = response.get('roles', '')
            # update header so each request will contain received token
            self.s.headers.update(
                {'Authorization': 'Token ' + self.session_id})
            return True
        else:
            _logger.warning('Error: %s', self.r.status_code)
            self.error_message = (
                    _('[%s] basic auth: Error!') % (self.r.status_code,)
            )
            return False

    def _p24_business_auth(self):
        """Gain business role on basic session."""
        data = {
            'sessionId': self.session_id,
            'login': self.login,
            'password': self.passwd
        }
        if not self.session_id:
            _logger.warning('business auth: no session_id')
        if not self.login:
            _logger.warning('business auth: no login')
        if not self.passwd:
            _logger.warning('business auth: no password')
        self.r = self.s.post(self.P24_CREATE_SESSION_URL,
                             data=json.dumps(data),
                             timeout=self.timeout)
        _logger.debug('Response body [%s]', self.r.text)
        response = self.r.json()
        if 'error' in response:
            _logger.warning(response.get('error', ''))
            self.error_message = (
                _('[%s] business auth: %s') %
                (self.r.status_code, response.get('error', ''))
            )
            return False
        if self.r.status_code == 200:
            # OK
            if self.client_id != response.get('clientId', ''):
                self.error_message = _('business auth: '
                                       'wrong client_id received.')
                _logger.warning('business auth: wrong client_id received.')
                return False
            if self.session_id != response.get('id', ''):
                self.error_message = _('business auth: '
                                       'wrong session_id received.')
                _logger.warning('business auth: wrong session_id received.')
                return False

            self.session_expires_in = dt.fromtimestamp(response['expiresIn'])
            self.roles = response.get('roles', '')
            # update header so each request will contain received token
            self.s.headers.update({
                'Authorization': 'Token ' + self.session_id})
            return True
        else:
            _logger.warning('Error: %s', self.r.status_code)
            self.error_message = (
                    _('[%s] business auth: Error!') % (self.r.status_code,)
            )
            return False

    def _select_otp_phone(self, tel_id):
        """Select phone to send OTP to.

        This step is needed if there is more than 1 phone.
        On success OTP is sent to desired phone.
        So we need to send OTP to the server on next step.
        """
        if not tel_id:
            return False
        data = {
            'sessionId': self.session_id,
            'otpDev': tel_id
        }

        self.r = self.s.post(self.P24_SEL_OTP_DEV_URL,
                             data=json.dumps(data),
                             timeout=self.timeout)
        if self.r.status_code == 200:
            # OK
            response = self.r.json()
            if self.client_id != response['clientId']:
                return False    # wrong client
            if self.session_id != response['id']:
                return False    # wrong session
            return True
        else:
            return False

    def _send_otp(self, otp):
        """Send OTP for auth.

        On success we receive response 200 and gain business role.
        """
        if not otp:
            return False
        data = {
            'sessionId': self.session_id,
            'otp': otp
        }

        self.r = self.s.post(self.P24_CHECK_OTP_URL,
                             data=json.dumps(data),
                             timeout=self.timeout)
        if self.r.status_code == 200:
            # OK
            response = self.r.json()
            if self.client_id != response['clientId']:
                return False    # wrong client
            if self.session_id != response['id']:
                return False    # wrong session

            self.roles = response['roles']
            return True
        else:
            return False

    def _validate_session(self):
        """Validate current session.

        returns True if response status is 200.
        returns False on non 200 status.
        Error details can be obtained in self.r

        This function updates internal data about session
        to be in sync with server.
        """
        if not self.session_id:
            self.roles = []
            if 'Authorization' in self.s.headers:
                del self.s.headers['Authorization']
            _logger.warning('No session_id stored in model')
            return False
        data = {
            'sessionId': self.session_id
        }
        self.r = self.s.post(self.VALIDATE_SESSION_URL,
                             data=json.dumps(data),
                             timeout=self.timeout)
        _logger.debug('Response body [%s]', self.r.text)
        if self.r.status_code == 200:
            # OK
            response = self.r.json()
            if self.client_id != response.get('clientId', ''):
                self.error_message = _('business auth: '
                                       'wrong client_id received.')
                _logger.warning('business auth: wrong client_id received.')
                return False
            if self.session_id != response.get('id', ''):
                self.error_message = _('business auth: '
                                       'wrong session_id received.')
                _logger.warning('business auth: wrong session_id received.')
                return False

            self.session_expires_in = dt.fromtimestamp(response['expiresIn'])
            self.roles = response['roles']
            # update header so each request will contain received token
            self.s.headers.update(
                {'Authorization': 'Token ' + self.session_id})
            return True
        else:
            self.session_id = ''
            self.roles = []
            if 'Authorization' in self.s.headers:
                del self.s.headers['Authorization']
            _logger.warning('Error: %s', self.r.status_code)
            self.error_message = (
                    _('[%s] validation: Error!') % (self.r.status_code,)
            )
            return False

    def _remove_session(self):
        """Remove current session.

        returns True if response status is 200.
        returns False on non 200 status.
        Error details can be obtained in self.r

        This function removes internal data about session on success.
        """
        if not self.session_id:
            self.roles = []
            del self.s.headers['Authorization']
            return True
        data = {
            'sessionId': self.session_id
        }
        self.r = self.s.post(self.REMOVE_SESSION_URL,
                             data=json.dumps(data),
                             timeout=self.timeout)
        if self.r.status_code == 200:
            # OK
            self.session_id = ''
            self.roles = []
            if 'Authorization' in self.s.headers:
                del self.s.headers['Authorization']
            return True
        else:
            # not 200
            return False

######################################################
# Odoo part ##########################################
######################################################
    state = fields.Selection(
        [('loginpasswd', 'Provide Login and Password'),
         ('phone_sel', 'Select device'),
         ('otp', 'Enter OTP'),
         ('failure', 'Failure'),
         ('success', 'Success')],
        string="State to control wizard form",
        default='loginpasswd')
    task = fields.Selection(
        [('nothing', 'Nothing to do'),
         ('statement_import', 'Import Statement'),
         ('send_payment', 'Send Payment')],
        default='nothing',
        string="Task to sync with bank eg statement or Payment")
    client_id = fields.Char(
        string='client_id',
        help='Taken from developer console',
        required=True,
        default='98defe24-1a91-4aa3-9b5a-be19c465dc9f')
    client_secret = fields.Char(
        string='client_secret',
        help='Taken from developer console',
        required=True,
        default='23b9b950a773404dba466412d9c5eb40')
    session_id = fields.Char(
        string='session_id',
        help='Session token')
    timeout = fields.Integer(
        string='Network delay in sec before exception',
        default=30)
    login = fields.Char(
        string='Login',
        help='Privat24 Login',
        states={'loginpasswd': [('required', True)]})
    passwd = fields.Char(
        string='Password',
        help='Privat24 Password',
        states={'loginpasswd': [('required', True)]})
    otp = fields.Char(
        string='OTP',
        states={'otp': [('required', True)]})
    phone_sel = fields.Many2one(
        'account.p24b.sync.phone_sel',
        string="Select Phone",
        ondelete='cascade',
        states={'phone_sel': [('required', True)]})
    numb_of_tries = 2
    error_message = fields.Char(string='Error message', readonly=True)
    # Payment export
    partner_id = fields.Many2one('res.partner', string='Partner')
    memo = fields.Char(string='Memo')
    currency_id = fields.Many2one('res.currency', string='Currency')
    amount = fields.Monetary(string='Payment Amount')
    payment_date = fields.Date(string='Payment Date')
    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        help="""Payment that triggered this wizard.
        On successful sync payment state will be changed to Sent""")

    # task == 'statement_import' specific fields
    bank_acc = fields.Char(
        string='Bank Account Number',
        readonly=True)
    journal_id = fields.Many2one(
        'account.journal',
        help='Bank Journal for statement import')

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        ResPB = self.env['res.partner.bank']
        for st_vals in stmts_vals:
            st_vals['journal_id'] = journal.id

            for line_vals in st_vals['transactions']:
                unique_import_id = line_vals.get('unique_import_id')
                if unique_import_id:
                    sanitized_account_number = sanitize_account_number(
                        account_number)
                    line_vals['unique_import_id'] = \
                        (sanitized_account_number and
                            sanitized_account_number + '-' or '') + \
                        str(journal.id) + '-' + unique_import_id

                if not line_vals.get('bank_account_id'):
                    # Find the partner and his bank account or create
                    # the bank account. The partner selected during the
                    # reconciliation process will be linked to the bank
                    # when the statement is closed.
                    partner_id = False
                    bank_account_id = False
                    identifying_string = line_vals.get('account_number')
                    if identifying_string:
                        partner_bank = ResPB.search(
                            [('acc_number', '=', identifying_string)], limit=1)
                        if partner_bank:
                            bank_account_id = partner_bank.id
                            partner_id = partner_bank.partner_id.id
                        else:
                            bank_account_id = ResPB.create(
                                {'acc_number': line_vals['account_number']}).id
                    line_vals['partner_id'] = partner_id
                    line_vals['bank_account_id'] = bank_account_id

        return stmts_vals

    def _create_bank_statements(self, stmts_vals):
        """Create new bank statements from imported values.

        Filtering out already imported transactions, and returns
        data used by the reconciliation widget.
        """
        BankStatement = self.env['account.bank.statement']
        BankStatementLine = self.env['account.bank.statement.line']

        # Filter out already imported transactions and create statements
        statement_ids = []
        ignored_statement_lines_import_ids = []
        for st_vals in stmts_vals:
            filtered_st_lines = []
            for line_vals in st_vals['transactions']:
                if 'unique_import_id' not in line_vals \
                   or not line_vals['unique_import_id'] \
                   or not bool(BankStatementLine.sudo().search(
                       [(
                           'unique_import_id',
                           '=',
                           line_vals['unique_import_id'])], limit=1)):
                    filtered_st_lines.append(line_vals)
                else:
                    ignored_statement_lines_import_ids.append(
                        line_vals['unique_import_id'])
            if len(filtered_st_lines) > 0:
                # Remove values that won't be used to create records
                st_vals.pop('transactions', None)
                for line_vals in filtered_st_lines:
                    line_vals.pop('account_number', None)
                # Create the statement
                st_vals['line_ids'] = [[0, False, line] for line in
                                       filtered_st_lines]
                statement_ids.append(BankStatement.create(st_vals).id)
        if len(statement_ids) == 0:
            pass

        # Prepare import feedback
        notifications = []
        num_ignored = len(ignored_statement_lines_import_ids)
        if num_ignored > 0:
            notifications += [{
                'type': 'warning',
                'message': _(
                    "%d transactions had already been" +
                    "imported and were ignored.") % num_ignored if
                num_ignored > 1 else
                _("1 transaction had already been imported and was ignored."),
                'details': {
                    'name': _('Already imported items'),
                    'model': 'account.bank.statement.line',
                    'ids': BankStatementLine.search(
                        [(
                            'unique_import_id',
                            'in',
                            ignored_statement_lines_import_ids)]).ids
                }
            }]
        return statement_ids, notifications

    def _get_balance_end(self, day_date):
        par = {
            'stdate': day_date,
            'endate': day_date,
            'in_time': 'd',
            'acc': self.bank_acc,
        }
        enough = False
        count = 1
        _logger.info('trying to get balance rests')
        while not enough:
            try:
                _logger.info('try No %s', count)
                self.r = self.s.get(self.P24_RESTS_URL,
                                    params=par,
                                    headers={'Accept': 'application/xml'},
                                    timeout=self.timeout)
                self.r.raise_for_status()
                enough = True
            except (requests.exceptions.Timeout,
                    requests.exceptions.TooManyRedirects,
                    requests.exceptions.HTTPError) as err:
                _logger.warning(err)
                if count <= 5:
                    time.sleep(count)
                    count += 1
                else:
                    enough = True
                    _logger.warning('Unable to query xml rests')
                    return None, None

        xml_data = self.r.text.encode('utf8')
        # parse rests
        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError:
            _logger.warning('Unable to parse xml rests')
            return None, None

        if root.tag.lower() != 'rests':
            _logger.warning('wrong xml rests format')
            return None, None
        try:
            bal_st = root.find('turn').find('inrest').text
            bal_end = root.find('turn').find('outrest').text
            if bal_st and bal_end:
                return float(bal_st), float(bal_end)
            else:
                return None, None
        except:
            return None, None

    def _import_statement_data(self, xmldata):
        # st_currency = 'UAH'
        st_account = self.bank_acc
        st_data = []

        self.state = 'failure'
        try:
            root = ET.fromstring(xmldata)
        except ET.ParseError:
            _logger.warning('Unable to parse xml statement')
            return [], []

        if root.tag.lower() != 'statements':
            _logger.warning('wrong xml statement format')
            return [], []

        for row in root:
            info = row.find('info')
            if not info.get('flinfo') == 'r':
                continue
            if not info.get('state') == 'r':
                continue
            dt_date = dateutil.parser.parse(info.get('postdate'))
            date_str = dt_date.strftime('%Y-%m-%d')
            amount = row.find('amount')
            # st_currency = amount.get('ccy')

            partner = row.find('credit')
            partner_acc = partner.find('account')

            if not any(d.get('date', None) == date_str for d in st_data):
                # does not exists, create one
                bal_st, bal_end = self._get_balance_end(
                    dt_date.strftime('%d.%m.%Y'))
                name = self.journal_id.sequence_id.with_context(
                    ir_sequence_date=date_str).next_by_id()
                st_data.append({
                    'name': name,
                    'date': date_str,
                    'balance_start': bal_st,
                    'balance_end_real': bal_end,
                    'transactions': [],
                })
            for d in st_data:
                if d['date'] == date_str:
                    d['transactions'].append({
                        'name': row.find('purpose').text,
                        'date': date_str,
                        'amount': amount.get('amt'),
                        'unique_import_id': info.get('ref'),
                        'account_number': partner_acc.get('number'),
                        'partner_name': partner_acc.get('name'),
                        'ref': info.get('number'),
                    })
        if len(st_data) == 0:
            _logger.info('received bank statement is empty. do nothing')
            return [], []

        stmts_vals = self._complete_stmts_vals(
            st_data,
            self.journal_id,
            st_account)
        # Create the bank statements
        return self._create_bank_statements(stmts_vals)

    def _get_statement_stdate(self):
        # today in datetime
        today = fields.Date.from_string(fields.Date.today())
        # default is beginning of the year
        stdate = today.strftime('01.01.%Y')
        domain = [
            '&',
            ('journal_id', '=', self.journal_id.id),
            ('date', '<=', fields.Date.today())]
        stmts = self.env['account.bank.statement'].search(domain)
        if len(stmts) > 0:
            # find latest statement and check if it not in future
            # return last statement date or today
            stmts = stmts.sorted(key=lambda r: r.date, reverse=True)
            last_stmt = stmts[0]
            last_stmt_date = fields.Date.from_string(last_stmt.date)
            return last_stmt_date.strftime('%d.%m.%Y')
        else:
            # if nothing found
            return stdate

    def _do_send_payment(self):
        wiz_form_act = {
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'res_model': 'account.p24b.sync',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }
        bank = self.partner_id.bank_ids[0]
        pay_date = fields.Date.from_string(
            self.payment_date).strftime('%d.%m.%Y')
        data = {
            'A_ACC': self.bank_acc,
            'amt': self.amount,
            'B_ACC': bank.acc_number,
            'B_BIC': bank.bank_bic,
            'B_CRF': self.partner_id.company_registry,
            'B_NAME': self.partner_id.name,
            'DAT_INP': pay_date,
            'DAT_VAL': pay_date,
            'DETAILS': self.memo,
            'MUR': '',
            'type': 'cr',
        }

        # P24_NEWPAYMENT_URL
        self.r = self.s.post(self.P24_NEWPAYMENT_URL,
                             data=json.dumps(data),
                             timeout=self.timeout)
        if self.r.status_code == 200:
            # OK
            self.task = 'nothing'
            self.state = 'success'
            if self.payment_id.state in ('draft', 'posted'):
                self.payment_id.state = 'sent'
            return wiz_form_act
        else:
            _logger.info('can not send payment. trying to recreate session')
            self._remove_session()
            return self.do_sync()

    def _do_statement_import(self):
        def split_date_range(start, end, span_days):
            """ Split date range into chunks. """
            st_dt = dt.strptime(start, '%d.%m.%Y')
            end_dt = dt.strptime(end, '%d.%m.%Y')
            span = td(days=span_days)
            step = td(days=1)
            while st_dt + span < end_dt:
                current = st_dt + span
                yield st_dt.strftime('%d.%m.%Y'), current.strftime('%d.%m.%Y')
                st_dt = current + step
            else:
                yield st_dt.strftime('%d.%m.%Y'), end_dt.strftime('%d.%m.%Y')

        stdate = self._get_statement_stdate()
        endate = fields.Date.from_string(
            fields.Date.today()).strftime('%d.%m.%Y')

        start = dt.strptime(stdate, '%d.%m.%Y').date()
        end = dt.strptime(endate, '%d.%m.%Y').date()
        if start > end:
            start = end

        stdate = start.strftime('%d.%m.%Y')
        endate = end.strftime('%d.%m.%Y')
        statement_ids = []
        notifications = []
        for b_dt, e_dt in split_date_range(stdate, endate, 28):
            par = {
                'stdate': b_dt,
                'endate': e_dt,
                'acc': self.bank_acc,
                # 'showInf': ''
            }
            _logger.debug('statement period: %s to %s', b_dt, e_dt)
            self.r = self.s.get(self.P24_STATEMENTS_URL,
                                params=par,
                                headers={'Accept': 'application/xml'},
                                timeout=self.timeout)
            if self.r.status_code == 200:
                # OK
                xml_data = self.r.text.encode('utf8')
                self.task = 'nothing'
                # parse statement
                st, nt = self._import_statement_data(xml_data)
                statement_ids.extend(st)
                notifications.extend(nt)
            else:
                _logger.info(
                    'can not do statement. trying to recreate session')
                self._remove_session()
                return self.do_sync()

        if len(statement_ids) == 0:
            return True
        # Now that the import worked out,
        # set it as the bank_statements_source of the journal
        self.journal_id.bank_statements_source = 'p24b_import'
        # Finally dispatch to reconciliation interface
        action = self.env.ref('account.action_bank_reconcile_bank_statements')
        return {
            'name': action.name,
            'tag': action.tag,
            'context': {
                'statement_ids': statement_ids,
                'notifications': notifications
            },
            'type': 'ir.actions.client',
        }

    def _do_task(self):
        """Do business task after session was built.

        Try to do task and if it fails
        close session and call do_sync to recreate
        session from scratch and call _do_task on success.
        """
        wiz_form_act = {
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'res_model': 'account.p24b.sync',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }
        if self.task == 'nothing':
            self.state = 'success'
            return wiz_form_act

        self.numb_of_tries -= 1

        if self.task == 'statement_import':
            return self._do_statement_import()

        if self.task == 'send_payment':
            return self._do_send_payment()

    @api.multi
    def do_sync(self):
        """Public function to sync data with Privat24Business.

        This function checks current session and builds new one if needed.
        Then business role is acquired. On success we have active session
        with business role, so we can do business tasks API calls.
        At the end of this function business task is performed
        which is set in task variable.
        There is one caveat: even if business role is set on session
        it doesn't mean that business session is still active.
        Business session is active 30 mins by default. When it expires
        role is not updated.
        So we don't actually know does we really have business role ATM.
        Only thing we could do is to recreate session each time but user have
        to enter login, password and OTP each time. That's not what we want.
        So we are tying to reuse session, we do business task and if it
        fails maybe business session was expired so we close session,
        build it once again and try to do business task second time.
        """
        self.ensure_one()
        wiz_form_act = {
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'res_model': 'account.p24b.sync',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }

        if self.numb_of_tries == 0:
            self.state = 'failure'
            return wiz_form_act

        self.s.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Connection': 'close'
        })
        if self.session_id:
            self.s.headers.update(
                {'Authorization': 'Token ' + self.session_id})
        else:
            if 'Authorization' in self.s.headers:
                del self.s.headers['Authorization']

        try:
            auth_count = 1
            while not self.session_id:
                if auth_count <= 5:
                    _logger.info('no session. trying to get one')
                    _logger.info('try No %s', auth_count)
                    if not self._basic_auth():
                        _logger.warning('err code: %s', self.r.status_code)
                        _logger.warning('waiting for %s s', auth_count)
                        time.sleep(auth_count)
                        auth_count += 1
                else:
                    _logger.warning('basic_auth: exceeded number of tries.')
                    self.error_message = 'basic_auth: exceeded number of tries'
                    self.state = 'failure'
                    return wiz_form_act
            _logger.info('got session. validating')
            if not self._validate_session():
                # session is not valid
                # try to make new one
                auth_count = 1
                while not self.session_id:
                    if auth_count <= 5:
                        _logger.info('no session. trying to get one')
                        _logger.info('try No %s', auth_count)
                        if not self._basic_auth():
                            _logger.warning('err code: %s', self.r.status_code)
                            _logger.warning('waiting for %s s', auth_count)
                            time.sleep(auth_count)
                            auth_count += 1
                    else:
                        _logger.warning(
                            'basic_auth: exceeded number of tries.')
                        self.error_message = _(
                            'basic_auth: exceeded number of tries.')
                        self.state = 'failure'
                        return wiz_form_act
            _logger.info('session is valid. checking roles')
            if 'ROLE_P24_BUSINESS' in self.roles:
                # we have valid business session
                _logger.info('we have biz role')
                # Success! we have biz role
                return self._do_task()
            else:
                if self.otp and self.state == 'otp':
                    # user received OTP
                    # we should send it back to server
                    if not self._send_otp(self.otp):
                        _logger.warning('err code: %s', self.r.status_code)
                        self.otp = ''
                        self.state = 'failure'
                        return wiz_form_act
                    self.otp = ''
                    _logger.info('OTP was correct')
                    # Success! we have biz role
                    return self._do_task()
                if self.phone_sel and self.state == 'phone_sel':
                    # user have selected phone to send OTP to
                    # we should send it to the server
                    if not self._select_otp_phone(self.phone_sel.phone_id):
                        _logger.warning('err code: %s', self.r.status_code)
                        # self.phone_sel = []
                        self.state = 'failure'
                        return wiz_form_act
                    _logger.info('otp was sent')
                    self.state = 'otp'
                    return wiz_form_act

                _logger.info('got no biz role. trying to get one')
                # we have basic valid session
                # try to gain business role
                if not self.login or not self.passwd:
                    self.state = 'loginpasswd'
                    return wiz_form_act
                if not self._p24_business_auth():
                    _logger.warning('err code: %s', self.r.status_code)
                    self.state = 'failure'
                    return wiz_form_act
                if 'ROLE_P24_BUSINESS' in self.roles:
                    # we have valid business session
                    _logger.info('got biz role')
                    return self._do_task()
                else:
                    _logger.info('auth ok, but we need otp')
                    # biz auth OK but we should provide OTP to gain role
                    msg = self.r.json()['message']
                    if msg == u'Confirm authorization with OTP':
                        _logger.info('otp was sent')
                        # OTP was sent to clients phone
                        # ask user to input OTP
                        self.state = 'otp'
                        return wiz_form_act
                    elif isinstance(msg, list):
                        _logger.info('select phone first')
                        # we have list of phone to send OTP
                        # ask user to to choose one
                        phone_sel_cl = self.env['account.p24b.sync.phone_sel']
                        for rec in phone_sel_cl.search([]):
                            rec.unlink()
                        for item in msg:
                            self.phone_sel.create({
                                'phone_id': item['id'],
                                'name': item['number']
                            })
                        self.state = 'phone_sel'
                        return wiz_form_act
        except:
            self.state = 'failure'
            return wiz_form_act
        self.state = 'success'
        return wiz_form_act

    @api.multi
    def import_file(self):
        """ Process the file chosen in the wizard.

        create bank statement(s) and go to reconciliation.
        """
        self.ensure_one()
        # Let the appropriate implementation module parse
        # the file and return the required data
        # The active_id is passed in context in case
        # an implementation module requires information
        # about the wizard state (see QIF)
        currency_code, account_number, stmts_vals = self.with_context(
            active_id=self.ids[0])._parse_file(
                base64.b64decode(self.data_file))
        # Check raw data
        self._check_parsed_data(stmts_vals)
        # Try to find the currency and journal in odoo
        currency, journal = self._find_additional_data(
            currency_code, account_number)
        # If no journal found, ask the user about creating one
        if not journal:
            # The active_id is passed in context so the wizard
            # can call import_file again once the journal is created
            return self.with_context(
                active_id=self.ids[0])._journal_creation_wizard(
                    currency, account_number)
        # Prepare statement data to be used for bank statements creation
        stmts_vals = self._complete_stmts_vals(
            stmts_vals, journal, account_number)
        # Create the bank statements
        statement_ids, notifications = self._create_bank_statements(stmts_vals)
        # Now that the import worked out, set it as the
        # bank_statements_source of the journal
        journal.bank_statements_source = 'file_import'
        # Finally dispatch to reconciliation interface
        action = self.env.ref('account.action_bank_reconcile_bank_statements')
        return {
            'name': action.name,
            'tag': action.tag,
            'context': {
                'statement_ids': statement_ids,
                'notifications': notifications
            },
            'type': 'ir.actions.client',
        }


class P24BBankSyncPhoneSel(models.TransientModel):
    _name = 'account.p24b.sync.phone_sel'
    _description = 'Privat24Business phone list'

    phone_id = fields.Char('ID', required=True)
    name = fields.Char('Phone number', required=True)
