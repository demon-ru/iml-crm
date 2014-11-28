# -*- coding: utf-8 -*-
##############################################################################
#
#    OpernERP module for Customer Relationship Management for Logistic company
#    Copyright (C) 2014 Orient Express  (<http://www.iml.oe-it.ru>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
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
    'depends': [
	'crm',
	'analytic',
	'account',
    'crm_claim',
    'sales_team',
    ],
    'data': [

        'crm_clientcategory_data.xml',
        'crm_clientcategory_view.xml',
        'crm_clientcategory_menu.xml',
        
        'crm_goodscategory_view.xml',
        'crm_goodscategory_menu.xml',
        
        'crm_shipping_storages_view.xml',
        'crm_shipping_storages_menu.xml',
        
        'crm_company_org_type_data.xml',
        'crm_company_org_type_view.xml',
        'crm_company_org_type_menu.xml',
        
        'crm_settlement_center_view.xml',
        'crm_settlement_center_menu.xml',

		'res_partner_view.xml',
	
		"crm_iml_sqlserver_view.xml",
		"crm_iml_sqlserver_menu.xml",

        "crm_iml_exchange_settings.xml",

		'crm_iml_opportunities_type_data.xml',
		'crm_iml_opportunities_type_view.xml',
		'crm_iml_opportunities_type_menu.xml',

		'crm_lead_view.xml',

		'security/ir.model.access.csv',
        'wizard/wizard_crm_claim_report_view.xml',

		"res_config_view.xml",	

		"account_analytic_account_view.xml",
		"res_users_view.xml",
        "crm_claim_view.xml",
        "crm_iml_exchange_settings_menu.xml",
        "sales_team_view.xml",
        "crm_phonecall_view.xml",

    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
}
