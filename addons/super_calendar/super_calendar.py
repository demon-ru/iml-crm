# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2012 Agile Business Group sagl (<http://www.agilebg.com>)
#    Copyright (C) 2012 Domsense srl (<http://www.domsense.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, orm
from openerp.tools.translate import _
import logging
from mako.template import Template
from datetime import datetime, timedelta
from openerp import tools
from openerp import models
from openerp.tools.safe_eval import safe_eval


# для переназначаемых моделей
import inspect
from openerp.models import BaseModel, Model

from openerp.osv import fields,osv
import string
# для crm.lead
from openerp.addons.base.res.res_partner import format_address

def calendar_id2real_id(calendar_id=None, with_date=False):
	"""
	Convert a "virtual/recurring event id" (type string) into a real event id (type int).
	E.g. virtual/recurring event id is 4-20091201100000, so it will return 4.
	@param calendar_id: id of calendar
	@param with_date: if a value is passed to this param it will return dates based on value of withdate + calendar_id
	@return: real event id
	"""
	if calendar_id and isinstance(calendar_id, (str, unicode)):
		res = calendar_id.split('-')
		if len(res) >= 2:
			real_id = res[0]
			if with_date:
				real_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.strptime(res[1], "%Y%m%d%H%M%S"))
				start = datetime.strptime(real_date, DEFAULT_SERVER_DATETIME_FORMAT)
				end = start + timedelta(hours=with_date)
				return (int(real_id), real_date, end.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
			return int(real_id)
	return calendar_id and int(calendar_id) or calendar_id

def _models_get(self, cr, uid, context=None):
	obj = self.pool.get('ir.model')
	ids = obj.search(cr, uid, [])
	res = obj.read(cr, uid, ids, ['model', 'name'], context)
	return [(r['model'], r['name']) for r in res]


class super_calendar_configurator(orm.Model):
	_logger = logging.getLogger('super.calendar')
	_name = 'super.calendar.configurator'
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'line_ids': fields.one2many('super.calendar.configurator.line',
									'configurator_id', 'Lines'),
	}

	def generate_calendar_records(self, cr, uid, ids, context=None):
		configurator_ids = self.search(cr, uid, [])
		super_calendar_pool = self.pool.get('super.calendar')
		super_calendar_ids = super_calendar_pool.search(cr, uid, [],
														context=context)
		super_calendar_pool.unlink(cr, uid,
								   super_calendar_ids,
								   context=context)
		for configurator in self.browse(cr, uid, configurator_ids, context):
			for line in configurator.line_ids:
				self._generate_record_from_line_with_id(cr, uid,
														 configurator,
														 line,
														 super_calendar_pool,
														 False,
														 context)
		self._logger.info('Calendar generated')
		return True


	def _generate_record_from_line_with_id(self, cr, uid, configurator, line, super_calendar_pool, _ids, context):
		current_pool = self.pool.get(line.name.model)
		if _ids:
			current_record_ids = _ids
		else:
			current_record_ids = current_pool.search(
				cr,
				uid,
				line.domain and safe_eval(line.domain) or [],
				context=context)

		for current_record_id in current_record_ids:
			record = current_pool.browse(cr, uid,
										 current_record_id,
										 context=context)
			if (line.user_field_id and \
			   record[line.user_field_id.name] and \
			   record[line.user_field_id.name]._name != 'res.users'):
				raise orm.except_orm(
					_('Error'),
					_("The 'User' field of record %s (%s) "
					  "does not refer to res.users")
					% (record[line.description_field_id.name],
					   line.name.model))

			if (((line.description_field_id and
				  record[line.description_field_id.name]) or
					line.description_code) and
					record[line.date_start_field_id.name]):
				duration = False
				if (not line.duration_field_id and
						line.date_stop_field_id and
						record[line.date_start_field_id.name] and
						record[line.date_stop_field_id.name]):
					date_start = datetime.strptime(
						record[line.date_start_field_id.name],
						tools.DEFAULT_SERVER_DATETIME_FORMAT
					)
					date_stop = datetime.strptime(
						record[line.date_stop_field_id.name],
						tools.DEFAULT_SERVER_DATETIME_FORMAT
					)
					duration = (date_stop - date_start).total_seconds() / 3600
				elif line.duration_field_id:
					duration = record[line.duration_field_id.name]
				if line.description_type != 'code':
					name = record[line.description_field_id.name]
				else:
					parse_dict = {'o': record}
					mytemplate = Template(line.description_code)
					name = mytemplate.render(**parse_dict)
				super_calendar_values = {
					'name': name,
					'model_description': line.description,
					'date_start': record[line.date_start_field_id.name],
					'duration': duration,
					'user_id': (
						line.user_field_id and
						record[line.user_field_id.name] and
						record[line.user_field_id.name].id or
						False
					),
					'configurator_id': configurator.id,
					'res_id': line.name.model+','+str(record['id']),
					'model_id': line.name.id,
					}
				super_calendar_pool.create(cr, uid, super_calendar_values, context=context)


class super_calendar_configurator_line(orm.Model):
	_name = 'super.calendar.configurator.line'

	def _get_model_name(self, cr, uid, ids, field_name, arg, context=None):
		res = dict(map(lambda x: (x,{"model_name": ''}), ids))
		# the user may not have access rights for opportunities or meetings
		try:
			for config in self.browse(cr, uid, ids, context):
				res[config.id] = {
					"model_name": config.name.model
				}
		except:
			pass
		return res


	_columns = {
		'name': fields.many2one('ir.model', 'Model', required=True),
		'description': fields.char('Description', size=128, required=True),
		'domain': fields.char('Domain', size=512),
		'configurator_id': fields.many2one('super.calendar.configurator',
										   'Configurator'),
		'view_id': fields.many2one('ir.ui.view', "View", 
			domain="[('type', '=', 'form'), ('model', '=', model_name)]"),
		'description_type': fields.selection([
			('field', 'Field'),
			('code', 'Code'),
			], string="Description Type"),
		'description_field_id': fields.many2one(
			'ir.model.fields', 'Description field',
			domain="[('model_id', '=', name),('ttype', '=', 'char')]"),
		'description_code': fields.text(
			'Description field',
			help="Use '${o}' to refer to the involved object. "
				 "E.g.: '${o.project_id.name}'"
			),
		'date_start_field_id': fields.many2one(
			'ir.model.fields', 'Start date field',
			domain="['&','|',('ttype', '=', 'datetime'),"
				   "('ttype', '=', 'date'),"
				   "('model_id', '=', name)]",
			required=True),
		'date_stop_field_id': fields.many2one(
			'ir.model.fields', 'End date field',
			domain="['&',('ttype', '=', 'datetime'),('model_id', '=', name)]"
		),
		'duration_field_id': fields.many2one(
			'ir.model.fields', 'Duration field',
			domain="['&',('ttype', '=', 'float'),('model_id', '=', name)]"),
		'user_field_id': fields.many2one(
			'ir.model.fields', 'User field',
			domain="['&',('ttype', '=', 'many2one'),('model_id', '=', name)]"),
		"model_name": fields.function(_get_model_name, string="Name Model", type='char', multi='name_model'),
	}


class super_calendar(orm.Model):
	_name = 'super.calendar'
	_columns = {
		'name': fields.char('Description', size=512, required=True),
		'model_description': fields.char('Model Description',
										 size=128,
										 required=True),
		'date_start': fields.datetime('Start date', required=True),
		'duration': fields.float('Duration'),
		'user_id': fields.many2one('res.users', 'User'),
		'configurator_id': fields.many2one('super.calendar.configurator',
										   'Configurator'),
		'res_id': fields.reference('Resource',
								   selection=_models_get,
								   size=128),
		'model_id': fields.many2one('ir.model', 'Model'),
	}

# **********************************************
# блок для обновления данных в моделях
# **********************************************

	def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
		if context is None:
			context = {}
		fields2 = fields and fields[:] or None
		EXTRAFIELDS = ('user_id', 'duration', 'date_start')
		for f in EXTRAFIELDS:
			if fields and (f not in fields):
				fields2.append(f)
		if isinstance(ids, (str, int, long)):
			select = [ids]
		else:
			select = ids

		# FIXME: find a better way to not push virtual ids in the cache
		# (leading to their prefetching and ultimately a type error when
		# postgres tries to convert '14-3489274297' to an integer)
		self.invalidate_cache(cr, uid, context=context)

		select = map(lambda x: (x, calendar_id2real_id(x)), select)
		result = []
		real_data = super(super_calendar, self).read(cr, uid, [real_id for calendar_id, real_id in select], fields=fields2, context=context, load=load)
		real_data = dict(zip([x['id'] for x in real_data], real_data))

		for calendar_id, real_id in select:
			res = real_data[real_id].copy()
			ls = calendar_id2real_id(calendar_id, with_date=res and res.get('duration', 0) > 0 and res.get('duration') or 1)
			res['id'] = calendar_id
			result.append(res)

		for r in result:
			if r['user_id']:
				user_id = type(r['user_id']) in (tuple, list) and r['user_id'][0] or r['user_id']
				if user_id == uid:
					continue

		for r in result:
			for k in EXTRAFIELDS:
				if (k in r) and (fields and (k not in fields)):
					del r[k]
		if isinstance(ids, (str, int, long)):
			return result and result[0] or False
		return result

	def fields_view_get(self,cr,uid,view_id=None,view_type='form',context=None,toolbar=False,submenu=False):
		if (view_type == 'form'):
			id_obj = context.get('id_edit_obj_for_field')
			id_real = calendar_id2real_id(id_obj)
			cur_obj = self.browse(cr, uid, id_real)
			config = None
			res_obj = self.pool.get("super.calendar.configurator.line")
			res_id = res_obj.search(cr, uid, [('configurator_id', '=', cur_obj.configurator_id.id),('name', '=', cur_obj.model_id.id)], context=None)
			if len(res_id) > 0:
				config = res_obj.browse(cr, uid, res_id[0])
			if (config) and (config.view_id):
				view_id = config.view_id.id
				ed_obj_model= self.pool.get(cur_obj.res_id.__class__.__name__)
				res = super(type(cur_obj.res_id), ed_obj_model).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
				res.update({"model_real_edit": cur_obj.res_id.__class__.__name__,
					"id_real_edit_obj": cur_obj.res_id.id,})
			else:
				res = super(super_calendar, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
		else:
			res = super(super_calendar, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
		return res

	def write(self, cr, uid, ids, vals, context=None):
		res = super(super_calendar, self).write(cr, uid, ids, vals, context=context)
		sc_pool = self.pool.get('super.calendar')
		sc_obj = sc_pool.browse(cr, uid, ids[0])
		if ("date_start" in vals or "duration" in vals):
			base_obj_model = sc_obj.res_id.__class__.__name__
			# проверим, что у нас есть такой объект super.calendar.configurator.line, что
			# его значение name.model == base_obj_model
			sc_configurator_line_pool = self.pool.get('super.calendar.configurator.line')

			configurator_id = sc_obj.configurator_id.id
			configurator_line_pool = self.pool.get('super.calendar.configurator.line')
			line_ids = configurator_line_pool.search(cr, uid, [('configurator_id', '=', configurator_id)])
			line_obj = configurator_line_pool.browse(cr, uid, line_ids)
			# теперь узнаем, какой именно объект строки конфигурации нам нужен
			# почему то простое условие вроде [('name.model', '=', base_obj_model)] не сработало :(
			for line in line_obj:
				if (line.name.model == base_obj_model):
					sc_configurator_line_obj = line

			# ограничение: среди исходных моделей не должно быть дублей в рамках одной настройки супер календаря
			#sc_configurator_line_obj = sc_configurator_line_pool.browse(cr, uid, sc_configurator_line_id[0])
			# теперь по параметрам объекта конфирурации нам необходимо принять решение, как изменить исходный объект
			# возможны три случая:
			# 	1) задана дата начала, дата окончания и продолжительность не задана - в этом случае изменим только дату начала 
			# 	2) задана дата начала и задана дата окончания, продолжительность не задана - в этом случае изменим дату начала и окончания
			# 	3) задана дата начала и продолжительность, дата окончания не задана - в этом случае изменим продолжительность и дату начала
			if sc_configurator_line_obj.date_start_field_id.name is False:
				print "Error!"
			elif sc_configurator_line_obj.date_start_field_id.name is not False:
				base_obj = sc_obj.res_id
				# вариант #1
				if sc_configurator_line_obj.date_stop_field_id.name is False and sc_configurator_line_obj.duration_field_id.name is False:
					date_start_field = sc_configurator_line_obj.date_start_field_id.name
					new_val = {date_start_field : sc_obj.date_start}
					base_obj_pool = self.pool.get(base_obj_model)
					# передаем в контексте специальный параметр, который обозначает, что 
					# метод сохранения был вызван из метода SuperCalendar и сохранения SC не требуется
					context["SC_UPDATE"] = True
					base_obj_pool.write(cr, uid, [base_obj.id], new_val, context)
				# вариант #2
				elif sc_configurator_line_obj.date_stop_field_id.name and sc_configurator_line_obj.duration_field_id.name is False:
					date_start_field = sc_configurator_line_obj.date_start_field_id.name
					date_stop_field  = sc_configurator_line_obj.date_stop_field_id.name
					new_time_stop = datetime.strptime(sc_obj.date_start, "%Y-%m-%d %H:%M:%S") + timedelta(hours=sc_obj.duration)
					new_time_stop_string = new_time_stop.strftime("%Y-%m-%d %H:%M:%S")
					new_val = {date_start_field : sc_obj.date_start, date_stop_field : new_time_stop_string}
					base_obj_pool = self.pool.get(base_obj_model)
					# передаем в контексте специальный параметр, который обозначает, что 
					# метод сохранения был вызван из метода SuperCalendar и сохранения SC не требуется
					context["SC_UPDATE"] = True
					base_obj_pool.write(cr, uid, [base_obj.id], new_val, context)
				# вариант #3
				elif sc_configurator_line_obj.date_stop_field_id.name is False and sc_configurator_line_obj.duration_field_id.name:
					date_start_field = sc_configurator_line_obj.date_start_field_id.name
					duration_field = sc_configurator_line_obj.duration_field_id.name
					new_val = {date_start_field : sc_obj.date_start, duration_field : sc_obj.duration}
					base_obj_pool = self.pool.get(base_obj_model)
					# передаем в контексте специальный параметр, который обозначает, что 
					# метод сохранения был вызван из метода SuperCalendar и сохранения SC не требуется
					context["SC_UPDATE"] = True
					base_obj_pool.write(cr, uid, [base_obj.id], new_val, context)
		return vals

# **********************************************
# блок для обновления данных в super_calendar
# **********************************************


def _regenerate_SC_on_write(self, cr, uid, vals, model_id, obj_id, context):
	obj = self.pool.get('super.calendar')
	ids = obj.search(cr, uid, [('res_id', '=', str(model_id) + "," + str(obj_id))])
	res_obj = obj.browse(cr, uid, ids)
	configurator_id = res_obj.configurator_id
	if (not 'SC_UPDATE' in context):
		configurator_pool = self.pool.get('super.calendar.configurator')
		for configurator in configurator_pool.browse(cr, uid, configurator_id.id):
			for line in configurator.line_ids:
				# если модель в строке совпадает, то можем продолжить
				if(line.name.model == model_id):
					# теперь проверяем назначенные этой строке филды в качетве
					# даты начала, завершения и продолжительности
					start_datetime = line.date_start_field_id.name
					stop_datetime = line.date_stop_field_id.name
					duration = line.duration_field_id.name
					if (start_datetime in vals or stop_datetime in vals or duration in vals):
						# для начала нам нужно удалить старую запись из пула SC
						super_calendar_pool = self.pool.get('super.calendar')
						super_calendar_pool.unlink(cr, uid,
												   ids,
												   context=context)
						configurator._generate_record_from_line_with_id(
																 configurator,
																 line,
																 super_calendar_pool,
																 [obj_id])

def _generate_SC_on_create(self, cr, uid, model_id, obj_id):
		scc_line_pool = self.pool.get("super.calendar.configurator.line")
		ids = scc_line_pool.search(cr, uid, [('name.model', '=', model_id)])
		line_objs = scc_line_pool.browse(cr, uid, ids)

		super_calendar_pool = self.pool.get("super.calendar")
		for line in line_objs:
			configurator = line.configurator_id
			configurator._generate_record_from_line_with_id(
													configurator,
													line,
													super_calendar_pool,
													[obj_id])

def _unlink_SC_on_unlink(self, cr, uid, model_id, ids, context):
		sc_pool = self.pool.get('super.calendar')
		for obj_id in ids:
			sc_ids = sc_pool.search(cr, uid, [('res_id', '=', str(model_id) + "," + str(obj_id))])
			sc_objects = sc_pool.browse(cr, uid, sc_ids)
			for sc in sc_objects:
				sc_pool.unlink(cr, uid, sc.id, context)


def my_write(self, cr, uid, ids, vals, context=None):
	res = BaseModel.write(self, cr, uid, ids, vals, context=context)
	# если пришедшая к нам модель содержится в super.calendar.configurator.line.name.model, то это наш клиент
	model_id =  self.__class__.__name__
	sc_configurator_line_obj = False

	configurator_line_pool = self.pool.get('super.calendar.configurator.line')
	line_ids = configurator_line_pool.search(cr, uid, [])
	line_obj = configurator_line_pool.browse(cr, uid, line_ids)
	# теперь узнаем, какой именно объект строки конфигурации нам нужен
	# почему то простое условие вроде [('name.model', '=', base_obj_model)] не сработало :(
	for line in line_obj:
		if (line.name.model == model_id):
			sc_configurator_line_obj = line

	if sc_configurator_line_obj:
		for id in ids:
			_regenerate_SC_on_write(self, cr, uid, vals, model_id, id, context)
	return res


def my_create(self, cr, uid, vals, context=None):
	res = BaseModel.create(self, cr, uid, vals, context=context)
	model_id = self.__class__.__name__
	sc_configurator_line_obj = False

	configurator_line_pool = self.pool.get('super.calendar.configurator.line')
	line_ids = configurator_line_pool.search(cr, uid, [])
	line_obj = configurator_line_pool.browse(cr, uid, line_ids)
	for line in line_obj:
		if (line.name.model == model_id):
			sc_configurator_line_obj = line

	if sc_configurator_line_obj:
		_generate_SC_on_create(self, cr, uid, model_id, res)
	return res

def my_unlink(self, cr, uid, ids, context=None):
	model_id = self.__class__.__name__
	sc_configurator_line_obj = False

	configurator_line_pool = self.pool.get('super.calendar.configurator.line')
	line_ids = configurator_line_pool.search(cr, uid, [])
	line_obj = configurator_line_pool.browse(cr, uid, line_ids)
	for line in line_obj:
		if (line.name.model == model_id):
			sc_configurator_line_obj = line

	if sc_configurator_line_obj:
		_unlink_SC_on_unlink(self, cr, uid, model_id, ids, context)

	res = BaseModel.unlink(self, cr, uid, ids, context=context)
	return res

Model.write = my_write
Model.create = my_create
Model.unlink = my_unlink