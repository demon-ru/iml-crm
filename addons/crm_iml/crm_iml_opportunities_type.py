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

from openerp.osv import fields,osv,orm

class crm_iml_opportunities_type(osv.osv):

	_name = "crm.iml.opportunities.type"
	_description = "Type of opportunities"

	_columns = {
		'description': fields.char('Description', size=256, required=True),
		'name': fields.char('Name', size=64, required=True),
		'user_id': fields.many2one('res.users', 'Ответственный по умолчанию'),
		'section_id': fields.many2one('crm.case.section', 'Отдел по умолчанию'),
	}

	def name_get(self,cr, user, ids, context=None):
		res = []
		for typeOport in self.browse(cr, user, ids, context=context):
			res.append((typeOport.id,typeOport.description))
		return res
crm_iml_opportunities_type()
