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

from openerp.osv import fields,osv
import collections

class crm_case_section(osv.osv):
	_inherit = 'crm.case.section'


	def write(self, cr, uid, ids, vals, context=None):
		# вообще, следует рассмотреть три случая:
		# а) у нас устанавливается новый менеджер - тут все ок, записываем ему новые данные
		# б) у нас добавляется работник, тут тоже все ок, записываем манагеру новые данные
		# в) у нас удаляется манагер - тут вот нужно подумать, старый ушел - значит, у него данные нужно убрать, 
		# г) у нас удаляется работник - в этом случае, мы должны определить, что за работник это был и удалить его
		# 	новый пришел - ему данные нужно добавить. Все рас***адто в общем
		for partn in self.browse(cr, uid, ids, context=context):
			if ("user_id" in vals):
				# поскольку ответственный может быть новым, то
				# нужно найти текущую команду и всех сотрудников, манагера текущей компании и
				# у текущего манагера выпилить всех сотрудников текущей команды
				# так мы гарантируем правильность данных, если сменится манагер

				# с другой стороны, есть проблема.. ведь у одного манагера может быть 
				# несколько команд и пользователи там могут дублироваться
				# и если мы просто удалим дублирующуюся запись, то мы потеряем связь и с текущей командой
				# и с командой, где запись дублируется
				# решение в первом приближении:
				# пробегать для данного менеджера все команды и следить за повторениями пользователей
				# если есть повторения, то выделить их из списка текущих пользователей команды и не удалять

				# ищем текущего руководителя, мать его

				current_manager_id = partn.user_id.id
				# сперва нужно найти все группы продаж, где пользователь руководитель
				case_sections_obj = self.pool.get('crm.case.section')
				case_sections_ids = case_sections_obj.search(cr, uid, [('user_id', '=', current_manager_id)], context=context)
				case_sections = case_sections_obj.browse(cr, uid, case_sections_ids)

				manager_users = []
				users_with_single_team = []
				current_section_users = []
				# далее, следует пробежаться по всем этим группам и запомнить все ид сотрудников
				for case_section in case_sections:
					for subordinate in  case_section.member_ids:
						manager_users.append(subordinate.id)
				# теперь проводим проверку, кто встречается только один раз
				users_collection = collections.Counter(manager_users)

				for user in manager_users:
					if(users_collection[user] == 1):
						# если встречается ровно один раз, то можно и удалить :)
						users_with_single_team.append(user)
				# теперь находим всех сотрудников текущей команды
				current_case_section_id = ids[0]
				case_sections_obj = self.pool.get('crm.case.section')
				case_section = case_sections_obj.browse(cr, uid, current_case_section_id)
				for user in case_section.member_ids:
					current_section_users.append(user.id)
				# теперь преобразуем тех, кто встречается лишь однажды к Counter
				users_with_single_team_collection = collections.Counter(users_with_single_team)
				# преобразуем наших текущих пользователей к Counter
				current_section_users_collection = collections.Counter(current_section_users)
				# найдем их пересечение, и получим, кто встречается в данной группе у данного менеджера
				# и больше ни в какой другой группе у данного менеджера
				# их и надо удалить. У данного менеджера, еснно
				users_to_delete = users_with_single_team_collection & current_section_users_collection
				# приводим к Массиву или чему нибудь итерируемому

				# обновляем запись у старого мeжнеджера
				for user in current_section_users:
					if(users_to_delete[user] == 1):
						# удаляем безжалостно
						self.pool.get('res.users').write(cr, uid, current_manager_id, {'subordinates' : [(3, user)]})
				# обновляем запись у нового мэнеджера
				new_manager = vals.get("user_id")

				for user in current_section_users:
					self.pool.get('res.users').write(cr, uid, new_manager, {'subordinates' : [(4, user)]})
				# Успех.
				users_obj = self.pool.get("res.users")
				manager_obj = users_obj.browse(cr, uid, current_manager_id)

				new_manager_obj = users_obj.browse(cr, uid, new_manager)


			if ("member_ids" in vals):
				# обновляем ответственного
				res_array = []
				if("user_id" in vals):
					current_manager_id = vals.get("user_id")
				else:
					current_manager_id = partn.user_id.id
				current_case_section_id = ids[0]
				res_array = vals.get("member_ids")[0][2]

				users_obj = self.pool.get("res.users")
				manager = users_obj.browse(cr, uid, current_manager_id)

				# делаем так: находим текущую команду продажников, берем всех сотрудников и удаляем их от манагера
				# так мы гарантируем, что правильно запишем новые значения
				case_sections_obj = self.pool.get('crm.case.section')
				case_section = case_sections_obj.browse(cr, uid, current_case_section_id)
				for user in case_section.member_ids:
					self.pool.get('res.users').write(cr, uid, current_manager_id, {'subordinates' : [(3, user.id)]})
					print user.id
				# обновляем запись у манагера и все :)
				for user in res_array:
					# удаляем связь
					self.pool.get('res.users').write(cr, uid, current_manager_id, {'subordinates' : [(3, user)]})
					# добавляем связь
					self.pool.get('res.users').write(cr, uid, current_manager_id, {'subordinates' : [(4, user)]})
		return super(crm_case_section, self).write(cr, uid, ids, vals, context=context)
