# -*- coding: utf-8 -*-
{
  # App information
    'name': 'Export Product Stock in Excel',
    'version': '11.0',
    'category': 'Warehouse Management',
    'license': 'OPL-1',
    'summary' : 'Export stock info with different filters & total valuation',
   
  
    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',   
    'website': 'http://www.emiprotechnologies.com/',
  
  
  # Dependencies
    'depends': ['stock_account', 'web'],
    'update_xml': [
                   'security/security_group.xml',
                   'view/configuration_view.xml',
                   'wizard/wizard_get_report.xml',
                   ],
    
   # Odoo Store Specific   
    'images': ['static/description/main_screen.jpg'], 
  
  
    
     # Technical        
    'external_dependencies' : {'python' : ['xlwt'], },
    'installable': True,
    'auto_install': False,
    'application' : True,
    'price': 20.00,
    'currency': 'EUR',
    
    
    
    # Dependencies
    'depends': ['sale', 'purchase', 'stock_account'],
    'data':[
        'security/security_group.xml',
        'wizard/export_stockinfo_config_setting_views.xml',
        'wizard/export_stockinfo_report_views.xml',
        'data/ir_cron.xml',
        'data/mail_template_data.xml',
        'report/export_stockinfo_report.xml',
        'report/export_stockinfo_report_views.xml',
        'report/layouts.xml',
            ],
    
   
    }
