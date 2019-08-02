from odoo import models, fields


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    employee_id = fields.Many2one('hr.employee', string='Responsible person')
