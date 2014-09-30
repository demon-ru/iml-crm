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
from openerp.osv import fields, osv

class account_analytic_account(osv.osv):
	_inherit = 'account.analytic.account'
	_columns = {
		"crm_number": fields.char('Contract number', size = 255), 
		'storage_of_shipping' : fields.many2one('crm.shipping_storage', 'Storage of shipping') ,
		'region_of_delivery' : fields.selection([('moscow', 'Moscow'), ('regions', 'Regions except Moscow')], 'Delivery region'),
		'fio_authorized person_nominative_case' : fields.char('Full name of authorized person in nominative case', size = 255),
		'fio_authorized person_genitive_case' : fields.char('Full name of authorized person in genitive case', size = 255),
		'authorized_person_position_nominative_case' : fields.char('Position of authorized person in nominative case', size = 255), 
		'authorized_person_position_genetive_case' : fields.char('Position of authorized person in genetive case', size = 255),
		'number_of_powerOfattorney' : fields.char('Number of The Power of Attorney', size = 255),
		'date_of_powerOfattorney' : fields.date('The date of The Power of Attorney'),
	}
