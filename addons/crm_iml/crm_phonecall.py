# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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
from datetime import datetime
import pytz
from openerp import SUPERUSER_ID
import time
from openerp import tools

class crm_phonecall(osv.osv):
	_inherit = 'crm.phonecall'

	_columns = {
		'user_id': fields.many2one('res.users', 'Responsible', track_visibility='onchange'),
		'state': fields.selection(
			[('open', 'Запланировано'),
			 ('cancel', 'Отменено'),
			 ('done', 'Произведен')
			 ], string='Status', track_visibility='onchange',
			help='The status is set to Confirmed, when a case is created.\n'
				 'When the call is over, the status is set to Held.\n'
				 'If the callis not applicable anymore, the status can be set to Cancelled.'),
	}

	def _get_default_section_id(self, cr, uid, context=None):
		section_ids = self.pool.get('crm.case.section').search(cr, uid, ['|', ('user_id', '=', uid), ('member_ids', '=', uid)], context=context)
		if section_ids:
			section_id = section_ids[0]
		print "**************************"
		print section_id
		print "**************************"
		return section_id

	_defaults = {
		"duration" : 15.0/60.0,
		"section_id": _get_default_section_id,
	}

	def redirectToObject(self,cr,uid,ids,context=None): 
		call = self.browse(cr, uid, ids[0], context=context)
		model_data = self.pool.get("ir.model.data")
		# Get res_partner views
		dummy, form_view = model_data.get_object_reference(cr, uid, 'crm', 'crm_case_phone_form_view')

		return {
			'return':True,
			'view_mode': 'form',
			'view_id': "crm.crm_case_phone_form_view",
			'views': [(form_view or False,'form')],
			'view_type': 'form',
			'res_id' : call.id,
			'res_model': 'crm.phonecall',
			'target': 'current',
			'type': 'ir.actions.act_window',
		}

	def on_change_user(self, cr, uid, ids, user_id, context=None):
		""" When changing the user, also set a section_id or restrict section id
			to the ones user_id is member of. """
		section_id = None
		if user_id:
			section_ids = self.pool.get('crm.case.section').search(cr, uid, ['|', ('user_id', '=', user_id), ('member_ids', '=', user_id)], context=context)
			if section_ids:
				section_id = section_ids[0]
		return {'value': {'section_id': section_id}}

class crm_phonecall2phonecall(osv.osv_memory):
	_inherit = 'crm.phonecall2phonecall'

	_columns = {
		'user_id' : fields.many2one('res.users',"Assign To", track_visibility='onchange'),
		'action': fields.selection([('schedule','Schedule a call'), ('log','Log a call')], 'Action', readonly=True, required=True),
	}

	def default_get(self, cr, uid, fields, context=None):
		res = super(crm_phonecall2phonecall, self).default_get(cr, uid, fields, context=context)
		record_id = context and context.get('active_id', False) or False
		res.update({'action': 'schedule'})
		if record_id:
			phonecall = self.pool.get('crm.phonecall').browse(cr, uid, record_id, context=context)

			categ_id = False
			data_obj = self.pool.get('ir.model.data')
			try:
				res_id = data_obj._get_id(cr, uid, 'crm', 'categ_phone2')
				categ_id = data_obj.browse(cr, uid, res_id, context=context).res_id
			except ValueError:
				pass
			date = self.get_time(cr, uid, 0)
			call_date = time.mktime(date.timetuple())
			if (date):
				res.update({'date': date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
			if 'name' in fields:
				res.update({'name': phonecall.name})
			if 'user_id' in fields:
				res.update({'user_id': phonecall.user_id and phonecall.user_id.id or False})
			if 'section_id' in fields:
				res.update({'section_id': phonecall.section_id and phonecall.section_id.id or False})
			if 'categ_id' in fields:
				res.update({'categ_id': categ_id})
			if 'partner_id' in fields:
				res.update({'partner_id': phonecall.partner_id and phonecall.partner_id.id or False})
		return res

	def get_time(self, cr, uid, ids):
		now = datetime.now()
		res_date = datetime(year=now.year, 
			month= now.month,
			day=now.day,
			hour= now.hour,
			minute = now.minute,
			second = 0)
		t=time.mktime(res_date.timetuple())
		res_date = datetime.fromtimestamp(t+ 24*3600)
		return res_date

	_defaults = {
		'action': 'schedule',
		'date': get_time,
	}

	def on_change_user(self, cr, uid, ids, user_id, context=None):
		""" When changing the user, also set a section_id or restrict section id
			to the ones user_id is member of. """
		section_id = None
		if user_id:
			section_ids = self.pool.get('crm.case.section').search(cr, uid, ['|', ('user_id', '=', user_id), ('member_ids', '=', user_id)], context=context)
			if section_ids:
				section_id = section_ids[0]
		return {'value': {'section_id': section_id}}
