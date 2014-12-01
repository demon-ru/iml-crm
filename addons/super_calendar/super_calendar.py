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
from openerp.tools.safe_eval import safe_eval

# для переназначаемых моделей
from openerp.osv import fields,osv
import string
# для crm.lead
from openerp.addons.base.res.res_partner import format_address

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

		# removing old records
		super_calendar_ids = super_calendar_pool.search(cr, uid, [],
														context=context)

		super_calendar_pool.unlink(cr, uid,
								   super_calendar_ids,
								   context=context)
		# пробегаем по всем объектам календаря, сохраненным у данного
		for configurator in self.browse(cr, uid, configurator_ids, context):
			# пробегаем по строкам у текущей конфигурации
			for line in configurator.line_ids:
				values = self._generate_record_from_line(cr, uid,
														 configurator,
														 line,
														 super_calendar_pool,
														 context)
				#super_calendar_pool.create(cr, uid, values, context=context)
		self._logger.info('Calendar generated')
		return True

	def _generate_record_from_line(self, cr, uid, configurator, line, super_calendar_pool, context):
		current_pool = self.pool.get(line.name.model)
		current_record_ids = current_pool.search(
			cr,
			uid,
			line.domain and safe_eval(line.domain) or [],
			context=context)

		for current_record_id in current_record_ids:
			record = current_pool.browse(cr, uid,
										 current_record_id,
										 context=context)
			if line.user_field_id and \
			   record[line.user_field_id.name] and \
			   record[line.user_field_id.name]._name != 'res.users':
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
				# грязный хак
				super_calendar_pool.create(cr, uid, super_calendar_values, context=context)
		return super_calendar_values

	# метод, который создает запись в SC
	# отличие от предидущего метода - он создает запись только для того объекта,
	# чей ид указан в параметре ids

	def _generate_record_from_line_with_id(self, cr, uid, configurator, line, super_calendar_pool, _ids, context):
		print "================================================"
		print "DEBUG!!! _generate_record_from_line_with_id"
		current_pool = self.pool.get(line.name.model)
		print line.name.model
		print _ids
		current_record_ids = _ids

		for current_record_id in current_record_ids:
			print "current_record_id"
			print current_record_id
			record = current_pool.browse(cr, uid,
										 current_record_id,
										 context=context)
			print "curent record:"
			print record
			print "record[user_id]"
			print record.user_id
			print "line.user_field_id.name"
			print line.user_field_id.name
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
				# грязный хак
				super_calendar_pool.create(cr, uid, super_calendar_values, context=context)
		return super_calendar_values


class super_calendar_configurator_line(orm.Model):
	_name = 'super.calendar.configurator.line'
	_columns = {
		'name': fields.many2one('ir.model', 'Model', required=True),
		'description': fields.char('Description', size=128, required=True),
		'domain': fields.char('Domain', size=512),
		'configurator_id': fields.many2one('super.calendar.configurator',
										   'Configurator'),
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
	_models = [
		'crm.lead',
		'calendar.event',
		'crm.phonecall',
		'crm.claim'
		]

	def write(self, cr, uid, ids, vals, context=None):
		# цель следующая - изменить данные в исходном документе, если изменились данные в объекте SC
		# перво наперво нужно определить, какие модели мы будем обслуживать
		# crm.lead, calendar.event, crm.phonecall, crm.claim

		# далее, нужно определить, какие параметры мы будем мониторить
		# 	date_start
		# 	duration
		# записываем изменения
		
		res = super(super_calendar, self).write(cr, uid, ids, vals, context=context)
		obj = self.pool.get('super.calendar')
		res_obj = obj.browse(cr, uid, ids[0])
		
		if ("date_start" in vals or "duration" in vals):
			# это название модели исходного объекта
			base_obj_model = res_obj.res_id.__class__.__name__
			if (base_obj_model in self._models):
				# теперь нам нужно обработать это изменение
				# это и есть исходный объект
				base_obj = res_obj.res_id
				# теперь ищем исходную строчку в super.calendar.configurator.line
				# что бы посмотреть настройки полей
				configurator_id = res_obj.configurator_id.id
				configurator_line_pool = self.pool.get('super.calendar.configurator.line')
				line_ids = configurator_line_pool.search(cr, uid, [('configurator_id', '=', configurator_id)])
				line_obj = configurator_line_pool.browse(cr, uid, line_ids)
				# теперь узнаем, какой именно объект строки конфигурации нам нужен
				# почему то простое условие вроде [('name.model', '=', base_obj_model)] не сработало :(
				for line in line_obj:
					if (line.name.model == base_obj_model):
						correct_line = line
				# проверяем модель
				if base_obj_model == "crm.lead":
					date_start_field = correct_line.date_start_field_id.name

					# теперь ищем исходный документ и меняем у него нужное поле :)
					# т.к. он же у нас уже есть :)
					new_val = {date_start_field : res_obj.date_start}
					# получаем пул нужной нам модели
					base_obj_pool = self.pool.get(base_obj_model)
					# передаем в контексте специальный параметр, который обозначает, что 
					# метод сохранения был вызван из метода SuperCalendar и сохранения SC не требуется
					context["SC_UPDATE"] = True
					base_obj_pool.write(cr, uid, base_obj.id, new_val, context)
				elif base_obj_model == "calendar.event":
					date_start_field = correct_line.date_start_field_id.name
					date_stop_field = correct_line.date_stop_field_id.name
					# вычисляем дату окончания действия объекта
					# алгоритм следующий - нужно поменять только дату у даты окончания, не меняя время
					# приводим datetime к строке, т.к. в базе она хранится именно в таком виде
					# все неправильно, т.к. не учитывает продолжительность события
					new_time_stop = datetime.strptime(res_obj.date_start, "%Y-%m-%d %H:%M:%S") + timedelta(hours=res_obj.duration)
					new_time_stop_string = new_time_stop.strftime("%Y-%m-%d %H:%M:%S")
					# формируем список значений, которые нужно обновить в объекте
					new_val = {date_start_field : res_obj.date_start, date_stop_field : new_time_stop_string}
					# нужно изменить исходный объект calendar.event
					base_obj_pool = self.pool.get(base_obj_model)
					context["SC_UPDATE"] = True
					base_obj_pool.write(cr, uid, [base_obj.id], new_val, context)
				elif base_obj_model == 'crm.phonecall':
					# у звонка нам необходимо изменить следующий параметры:
					# дата звонка + его длительность
					# понадобится нам только дата его начала, т.к. поле длительность просто не меняется
					date_start_field = correct_line.date_start_field_id.name
					duration_field = correct_line.duration_field_id.name
					new_val = {date_start_field : res_obj.date_start, duration_field : res_obj.duration}
					# получаем пул нужной нам модели
					base_obj_pool = self.pool.get(base_obj_model)
					# передаем в контексте специальный параметр, который обозначает, что 
					# метод сохранения был вызван из метода SuperCalendar и сохранения SC не требуется
					context["SC_UPDATE"] = True
					base_obj_pool.write(cr, uid, [base_obj.id], new_val, context)
				elif base_obj_model == 'crm.claim':
					# у объекта обращение нам необходимо изменить только дату следующего действия
					date_start_field = correct_line.date_start_field_id.name
					new_val = {date_start_field : res_obj.date_start}
					# получаем пул нужной нам модели
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
	# model_id, obj_id
	obj = self.pool.get('super.calendar')
	ids = obj.search(cr, uid, [('res_id', '=', str(model_id) + "," + str(obj_id))])
	res_obj = obj.browse(cr, uid, ids)
	configurator_id = res_obj.configurator_id
	if (not 'SC_UPDATE' in context):
		configurator_pool = self.pool.get('super.calendar.configurator')
		for configurator in configurator_pool.browse(cr, uid, configurator_id.id):
			# пробегаем по строкам у текущей конфигурации
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
						# сгенерируем новую запись
						values = configurator._generate_record_from_line_with_id(
																 configurator,
																 line,
																 super_calendar_pool,
																 [obj_id])

# объект 	event	встреча
class calendar_event(osv.Model):
	_inherit = 'calendar.event'

	# перекрываем метод на запись
	def write(self, cr, uid, ids, vals, context=None):
		# если нужное нам значение есть в списке данных для обновления, то нужно обновить SC
		# что бы получить нужный нам объект SU, нам потребуется id исходного объекта и его модель,
		# т.к. id исходных объектов могут повторяться
		obj_id = ids[0]
		# но какая это модель, я уж точно знаю..
		model_id = "calendar.event"

		res = super(calendar_event, self).write(cr, uid, obj_id, vals, context=context) 
		_regenerate_SC_on_write(self, cr, uid, vals, model_id, obj_id, context)
		return vals



# объект 	lead	заявка
class crm_lead(format_address, osv.osv):
	_inherit = 'crm.lead'

	# перекрываем метод на запись
	def write(self, cr, uid, ids, vals, context=None):
		# если нужное нам значение есть в списке данных для обновления, то нужно обновить SC
		# что бы получить нужный нам объект SU, нам потребуется id исходного объекта и его модель,
		# т.к. id исходных объектов могут повторяться
		obj_id = ids[0]
		# но какая это модель, я уж точно знаю..
		model_id = "crm.lead"


		res = super(crm_lead, self).write(cr, uid, obj_id, vals, context=context) 
		_regenerate_SC_on_write(self, cr, uid, vals, model_id, obj_id, context)
		return vals



# объект 	crm.phonecall 	звонок
class crm_phonecall(osv.osv):
	_inherit = 'crm.phonecall'

	# перекрываем метод на запись
	def write(self, cr, uid, ids, vals, context=None):
		# если нужное нам значение есть в списке данных для обновления, то нужно обновить SC
		# что бы получить нужный нам объект SU, нам потребуется id исходного объекта и его модель,
		# т.к. id исходных объектов могут повторяться
		obj_id = ids[0]
		# но какая это модель, я уж точно знаю..
		model_id = "crm.phonecall"

		res = super(crm_phonecall, self).write(cr, uid, obj_id, vals, context=context) 
		_regenerate_SC_on_write(self, cr, uid, vals, model_id, obj_id, context)
		return vals


# объект 	crm.claim		обращение
class crm_claim(osv.osv):
	_inherit = 'crm.claim'

	# перекрываем метод на запись
	def write(self, cr, uid, ids, vals, context=None):
		# если нужное нам значение есть в списке данных для обновления, то нужно обновить SC
		# что бы получить нужный нам объект SU, нам потребуется id исходного объекта и его модель,
		# т.к. id исходных объектов могут повторяться
		obj_id = ids[0]
		# но какая это модель, я уж точно знаю..
		model_id = "crm.claim"

		res = super(crm_claim, self).write(cr, uid, obj_id, vals, context=context) 
		_regenerate_SC_on_write(self, cr, uid, vals, model_id, obj_id, context)
		return vals