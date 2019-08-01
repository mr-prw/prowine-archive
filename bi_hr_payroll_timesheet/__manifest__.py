# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.




{
    'name': 'Employee Payslip based on Timesheet Activity(Hourly)',
    'version': '11.0.0.1',
    'category': 'Human Resources',
    'sequence': 2,
    'summary': 'This apps generate employee payslip based on timesheet activities and calculate it based on hourly basis salary wage.',
    'description': """

        Hourly payslip on Payroll, HR hourly payroll, payslip based on hourly timesheet, payslip intergrated with timesheet. hourly salary calculation for employee, payslip calculation based on timesheet activity, HR timesheet payrol.Hourly payslip for employee,Generate Employee payslip based on timesheet. 


	""",
    'author': 'BrowseInfo',
    'price': '20',
    'currency': "EUR",
    'website': 'http://www.browseinfo.in',
   
    'depends': [
        'hr_payroll','hr_timesheet',    
    ],
    'data': [
       
        'views/hr_contract_view.xml',
          

    ],
    'demo': [
    ],
    'test': [

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [],
    "images":['static/description/Banner.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
