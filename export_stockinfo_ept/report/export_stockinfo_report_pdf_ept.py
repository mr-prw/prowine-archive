from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from datetime import timedelta
from itertools import chain
class ExportStockReportPDF(models.AbstractModel):
    _name = 'report.export_stockinfo_ept.export_stockinfo_report_pdf_ept'
    
    
    @api.model
    def get_report_values(self, docids, data=None):
        # docids - get the active ids list...
        data = data if data is not None else {}
        export_stockinfo_obj = self.env['export.stockinfo.report.ept'].browse(docids)
        return{
            'doc_model': 'export.stockinfo.report.ept',
            'docs':export_stockinfo_obj,
            'data':dict(get_date=self.get_report_date(export_stockinfo_obj),
                        get_warehouse_or_loc=self.get_report_warehouse_or_loc(export_stockinfo_obj),
                        all_product_ids=self.get_product(export_stockinfo_obj),
                        single_data_dict=self.get_single_data(export_stockinfo_obj)),
               
               
        }
       
    
    def get_product(self, export_stockinfo_obj):
        
        domain = [('type', '!=', 'service')]
        product_obj = self.env['product.product']
        
        if export_stockinfo_obj.supplier_ids:
            supplier_ids = [x.id for x in export_stockinfo_obj.supplier_ids]
            domain.append(('seller_ids.name', 'in', supplier_ids))
            
        if export_stockinfo_obj.category_ids:
            category_ids = [x.id for x in export_stockinfo_obj.category_ids]
            domain.append(('categ_id', 'child_of', category_ids))
        
        if export_stockinfo_obj.is_active_product:
            all_product_ids = product_obj.search(domain)
        
        else:
            domain.extend(['|', ('active', '=', True), ('active', '=', False)])
            all_product_ids = product_obj.search(domain)
        return all_product_ids
    
    
    def get_single_data(self, export_stockinfo_obj):
        
        today = datetime.now().strftime("%Y-%m-%d")
       
        domain = [('type', '!=', 'service')]
        product_obj = self.env['product.product']
        
        if export_stockinfo_obj.supplier_ids:
            supplier_ids = [x.id for x in export_stockinfo_obj.supplier_ids]
            domain.append(('seller_ids.name', 'in', supplier_ids))
            
        if export_stockinfo_obj.category_ids:
            category_ids = [x.id for x in export_stockinfo_obj.category_ids]
            domain.append(('categ_id', 'child_of', category_ids))
        
        if export_stockinfo_obj.is_active_product:
            all_product_ids = product_obj.search(domain)
        
        else:
            domain.extend(['|', ('active', '=', True), ('active', '=', False)])
            all_product_ids = product_obj.search(domain)
            
        
        warehouse_or_location = False
        if export_stockinfo_obj.report_wise == 'Warehouse':
            warehouse_or_location = export_stockinfo_obj.warehouse_ids.ids
        else:
            warehouse_or_location = export_stockinfo_obj.location_ids.ids
        
        single_data_dict = export_stockinfo_obj.prepare_data(today, all_product_ids, warehouse_or_location)
        return single_data_dict
    
    def get_report_date(self, export_stockinfo_obj):
        if export_stockinfo_obj.to_date:
            date = export_stockinfo_obj.to_date
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            date = today
        return date
    
    def get_report_warehouse_or_loc(self,export_stockinfo_obj):
        warehouse_obj = self.env['stock.warehouse']
        location_obj = self.env['stock.location']
        location_lst = []
        warehouse_ids = False
        
        warehouse_or_location = False
        if export_stockinfo_obj.report_wise == 'Warehouse':
            warehouse_or_location = export_stockinfo_obj.warehouse_ids.ids
        else:
            warehouse_or_location = export_stockinfo_obj.location_ids.ids
        if export_stockinfo_obj.report_wise == 'Warehouse':
            warehouse_ids = warehouse_obj.search([('id', 'in', warehouse_or_location)])
        else:
            if not warehouse_ids:
                location_ids = location_obj.search([('id', 'in', warehouse_or_location)])
                if location_ids:
                    for location in location_ids:
                        child_list = export_stockinfo_obj.get_child_locations(location)
                        location_lst.append(child_list)
                    
                    locations = location_obj.browse(list(set(list(chain(*location_lst)))))
                else:
                    return True
    
    
        return  warehouse_ids or locations
