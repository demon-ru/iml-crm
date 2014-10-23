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

class crm_claim(osv.osv):
	_inherit = 'crm.claim'

	_columns = {
		'name': fields.char('Суть обращения', required=True),
		'date': fields.datetime('Дата обращения', select=True),
		'section_id': fields.many2one('crm.case.section', 'Подразделение', \
				select=True, help="Responsible sales team."\
				" Define Responsible user and Email account for"\
				" mail gateway."),
		'date_deadline': fields.date('Крайний срок'),
	}
