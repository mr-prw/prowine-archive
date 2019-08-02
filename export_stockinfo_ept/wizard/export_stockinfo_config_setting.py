from odoo import models, fields,api


class ExportStockInfoConfigSetting(models.TransientModel):
    
    _inherit = 'res.config.settings'
    
    
    group_visible_export_stock = fields.Boolean( string='Export Stockinfo In Excel file?',
                        implied_group='export_stockinfo_ept.group_export_multi_warehouse_stock',                                     
                        help="By selecting this option, user can see 'Export Stock' menu in /Reporting/Warehouse." )
    company_id = fields.Many2one('res.company', string='Company', required=True,default=lambda self: self.env.user.company_id)


    @api.multi
    def set_all_companydefaults(self):
        self.company_id.write({'group_visible_export_stock':self.group_visible_export_stock})