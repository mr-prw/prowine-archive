
{
	# App information
    'name': 'Inventory Coverage Report',
    'version': '11.0',
    'category': 'stock',
    'summary' : 'Inventory coverage report app for Odoo helps you to analyse your warehouse wise products stock availability, for next how many days your products will be there in stock.',
    'license': 'OPL-1',

    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
    
    # Dependencies
    'depends': ['purchase','stock','sale'],
    
    # Views
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/view_res_config.xml',
        'data/data_sequence_requisition.xml',
        'data/report_paperformat.xml',
        'views/view_product_product.xml',
        'views/requisition_period_ept_view.xml',
        'views/view_product_template.xml',
        'views/requisition_fiscal_year_ept_view.xml',
        'views/forecast_sale_ept_view.xml',
        'wizard/view_import_export_forecast_sales.xml',
        'wizard/view_requisition_product_suggestion.xml',
        'views/requisition_log.xml',
        'views/requisition_log_line.xml',
        'views/forecast_sale_rule_ept_view.xml',
        'views/forecast_sale_rule_line_ept_view.xml',
        'wizard/view_forecast_sale_rule_add_product.xml',
        'wizard/view_import_export_forecast_sales_rule.xml',
        'wizard/view_mismatch_data.xml',
        'report/view_forecast_sale_ept_report.xml',
        'report/view_forecast_and_actual_sales.xml',
        'views/menuitem_inventory_report.xml',  
        'views/report_template_inventory_coverage.xml',
        'views/report_inventory_coverage.xml',
    ],
       
      # Odoo Store Specific    
    'price': '99' ,
    'currency': 'EUR',
    'images': ['static/description/Inventory-Coverage-Report-Store-Cover.jpg'],    
    'installable': True,
    'live_test_url':'http://www.emiprotechnologies.com/free-trial?app=inventory-coverage-report-ept&version=11',
    'application': True,
    'auto_install': False,

    
}
