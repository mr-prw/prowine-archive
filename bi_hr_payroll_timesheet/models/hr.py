# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from datetime import time as datetime_time
from dateutil import relativedelta
from odoo import api, fields, models, tools, _


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def getDuration(self, payslip):
        duration = 0.0
        tsheet_obj = self.env['account.analytic.line']
        timesheets = tsheet_obj.search([('user_id', '=', self.user_id.id),('date', '>=', payslip.date_from),('date', '<=', payslip.date_to)])
        for tsheet in timesheets: #counting duration from timesheets
            duration += tsheet.unit_amount   
        return duration

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

















