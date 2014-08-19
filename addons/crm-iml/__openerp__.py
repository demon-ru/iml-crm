# -*- coding: utf-8 -*-
{
    'name': 'CRM_IML',
    'version': '1.0',
    'category': 'Customer Relationship Management',
    'sequence': 2,
    'summary': 'Leads, Opportunities, Phone Calls, Client Category',
    'description': """
	The description will be later
""",
    'author': 'OrientExpress',
    'website': 'http://www.iml.oe-it.ru',
    # I think depends our module is like as crm module
    'depends': [
	'crm'
    ],
    'data': [

        'crm_clientcategory_data.xml',
        'crm_clientcategory_view.xml',
        'crm_clientcategory_menu.xml',

	'res_partner_view.xml',
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
}