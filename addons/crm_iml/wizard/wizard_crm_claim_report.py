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
from datetime import datetime
import pytz
from openerp import SUPERUSER_ID
import time
from openerp import tools

class wizard_crm_claim_report(osv.osv_memory):

	_name = 'wizard.crm.claim.report'
	_columns = {
		'date_begin': fields.datetime('Дата начала', required=True),
		'date_end': fields.datetime("Дата окончания", required=True),
		"section_id": fields.many2one('crm.case.section', "Подразделение"),
		"user_id": fields.many2one('res.users', "Ответственный"),
	}

	def define_delta(self, cr, uid, ids, check_tz=True):
		user_pool = self.pool.get('res.users')
		user = user_pool.browse(cr, SUPERUSER_ID, uid)
		tz = pytz.timezone(user.partner_id.tz) or pytz.utc
		d = datetime(2012, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
		d2 = d.astimezone(tz)
		tz_moscov  = pytz.timezone("Europe/Moscow")
		#Из перевода часов в России часовой пояс Москвы стал не +4, а +3, а здесь до сих пор +4
		if (tz == tz_moscov) and (check_tz):
			delta = -3
		else:
			delta = d.hour - d2.hour
		return delta

	def get_time(self, cr, uid, ids, isBegin):
		now = datetime.now()
		hour = 0
		minute = 0
		second = 0
		month = now.month - 1
		if not(isBegin):
			hour = 23
			minute = 59
			second = 59
			month = now.month
		res_date = datetime(year=now.year, 
			month= month,
			day=now.day,
			hour=hour,
			minute=minute,
			second=second)
		delta = self.define_delta(cr, uid, ids)
		t=time.mktime(res_date.timetuple())
		res_date = datetime.fromtimestamp(t+delta*3600)
		return res_date




	def _default_start_date(self, cr, uid, ids):
		start_time = self.get_time(cr, uid, ids, True)
		return start_time


	def _default_stop_date(self, cr, uid, ids):
		stop_time = self.get_time(cr, uid, ids, False)
		return stop_time

	_defaults = {
		'date_begin': _default_start_date,
		'date_end': _default_stop_date,
	}


	def form_domen(self,cr, uid, data, date_begin, date_end):
		domain = ['&',('date_closed', '<=', "'" + date_end + "'" ), ('date_closed', '>=', "'" + date_begin  + "'" )]
		if (data['section_id']):
			section = data['section_id']
			domain.extend([('section_id', '=', int(section[0]))])
		if (data['user_id']):
			user = data['user_id']
			domain.extend([('user_id', '=', int(user[0]))])
		res_obj = self.pool.get("crm.claim.stage")
		res_id = res_obj.search(cr, uid, [("name", "=", 'Settled')], context=None)
		if res_id:
			domain.extend([('stage_id',"=", res_id[0])])
		domain_str = str(domain)
		return domain_str

	def get_right_date(self, cr, uid, ids, date):
		delta = self.define_delta(cr, uid, ids)
		date_str = date
		date_begin = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
		t = time.mktime(date_begin.timetuple())
		date_begin = datetime.fromtimestamp(t-delta*3600)
		date_str = date_begin.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
		return date_str 


	def open_table(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		data = self.read(cr, uid, ids, context=context)[0]
		ctx = context.copy()
		ctx['group_by'] = ['section_id','user_id']
		date_begin = self.get_right_date(cr, uid, ids, data['date_begin'])
		date_end = self.get_right_date(cr, uid, ids, data['date_end'])
		domain_str = self.form_domen(cr, uid, data, date_begin, date_end)
		return {
			#'domain': "[('date', '<=', '" + data['date'] + "')]",
			'domain': domain_str,
			"name": "Отчет закрытые обращения за период с " + date_begin + " по " + date_end,
			"target": "current",
			'group_by': 'section_id,user_id',
			'view_type': 'form',
			'view_mode': 'graph',
			'res_model': 'crm.claim.report',
			'type': 'ir.actions.act_window',
			'context': ctx,
		}