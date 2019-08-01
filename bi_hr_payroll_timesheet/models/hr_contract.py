# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields


class hr_contract(models.Model):
    _name = 'hr.contract'
    _inherit = 'hr.contract'

    # fields
    salary_per_h = fields.Float(string= "Salary per Hour")
#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
