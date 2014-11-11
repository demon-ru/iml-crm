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
import MySQLdb
import time
import sys
import pyodbc
import os.path

from openerp.osv import fields,osv,orm
from openerp import tools, api
from openerp.tools.translate import _
from openerp import pooler

class crm_iml_exchangeserver_settings(osv.osv):
	_name = "crm.iml.exchange_server_settings"
	_description = "Settings for importing and exporting data to MySQL database"
	_columns = {
		'lastTestDate': fields.datetime('Date last successful test connect' , readonly=True),
		'name' : fields.char('Name', size=255, required=True),
		'server' : fields.char('SQL server', size=255, required=True),
		'user' : fields.char('User', size=255, required=True),
		'password' : fields.char('Password', size=255),
		'dbname' : fields.char('Database name', size=255),

	}
	_sql_constraints = [
		('name_unique_constrait', 'unique(name)', "Config with this name alredy exists. Name must be unique."),
    ]

	"""
		Создает подключение к серверу
	"""
	def connectToServer(self):	
		db = None
		try:
			con_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (self.server, self.user, self.password, self.dbname)
			db = pyodbc.connect(con_string)
		except Exception, e:
			raise osv.except_osv(_("Connection failed!"), _("Here is what we got instead:\n %s.") % tools.ustr(e))
		return db
			
	"""	
		Teстовое подключение  к БД
	"""
	def test_iml_crm_sql_server(self,cr, uid, ids, context=None):	
		db = None;	
		try:
			server = self.browse(cr, uid, ids[0], context=context)
			db = server.connectToServer();
		finally:
			if (db):
				db.close()
		server.write({'lastTestDate': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
		return True

class crm_iml_sqlserver(osv.osv):
	_name = "crm.iml.sqlserver"
	_description = "Sql server for export/import data from OpenErp to my sql database"
	_columns = {
		'lastImportDate': fields.datetime('Date last successful import' , readonly=True),
		'name': fields.char('Name', size=128, required=True),
		'lastTestDate': fields.datetime('Date last successful test connect' , readonly=True),
		'tableName':fields.char('Table Name', size=128),
		'exchange_type':fields.selection([('partner', 'Partner exchange'), ('holdings', 'Holdings exchange'), ('commands_nav', 'Commands exchange with NAV'), ('responsible','Импорт ответственности по клиенту'), ('user','Импорт пользователей')], 'Exchange type', required=True),
		'exchange_server':fields.many2one('crm.iml.exchange_server_settings', 'name'),
	}

	#Поля из таблицы клиентов
	var_res_partner_fields = [
		"CustomerName", "NAV_UNC", "LegalName", "WebSite",
		"Warehouse_ID", "Region_ID", "RespPerson",
		"RespPersonWhom", "RespPersonPosition", "RespPersonPositionWhom",
		"LoA_Number","LoA_Date", "AddrZIP", 
	 	"ITN", "TRRC", "TRDate",
		"OGRN", "RegistrationDate", "OCVED", "OCPO", "OCATO",
		"AgreementNo", "FactAdrStr", "JurAdrStr", "Contact", "Email", "Phone",
		"idimport", "CompOrgTypeID", "AgreementDate", "AgreementStartDate",
		"Holding_Id", "Responsible_ID", "AgreementName"]
			
	"""	
		Teстовое подключение  к БД
	"""
	def test_iml_crm_sql_server(self,cr, uid, ids, context=None):	
		db = None	
		try:
			server = self.browse(cr, uid, ids, context=context)
			db = server.exchange_server.connectToServer()
		finally:
			if (db):
				db.close()
		server.write({'lastTestDate': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
		return True

	"""
		Создает файл для лога в заданной в настройке директории
	"""
	def create_log_file(self, cr, uid, import_type):
		params = self.pool.get('ir.config_parameter')
		log_path = params.get_param(cr, uid, 'crm_iml_log_path',default='' ,context=None)
		log_file = None
		if not(log_path):
			sys.stdout.write("Внимание! Не задан путь до папки с логами импорт будет произведен без логирования\n")
		else:
			try:
				file_name = "log_import_" + str(import_type) + "_" + str(time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT))
				log_path = os.path.join(log_path, file_name)
				log_file = open(log_path, 'w')
			except:
				sys.stdout.write("Внимание! Не удалось создать файл с логом, возможно вы задали неверную директорию в настройках\n")	
		return log_file

	def write_log(self, cr, uid, log_file, log_msg, type_msg):
		log_msg = u' '.join((time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT), u":", type_msg, u":", log_msg, "\n")).encode('utf-8')
		try:
			if (log_file):
				log_file.write(log_msg)
			else:
				sys.stdout.write(u"Внимание! Не удалось записать строчку в файл лога!\n" + log_msg)  
		except:
			sys.stdout.write(u"Внимание! Не удалось записать строчку в файл лога!\n" + log_msg)  

	"""
		Метод экспорта клиента в промежуточную базу
		Параметры:
			partner - экспортируемый партнер
	"""
	def export_res_partner(self, partner):
		export_params = {
			"id": {"Field": "crm_id", "IsStr": False},
			"name": {"Field": "CustomerName", "IsStr": True},
			"juridical_name" : {"Field": "ShopName", "IsStr": True},
			"website" : {"Field": "WebSite", "IsStr": True},
			"category_of_goods.nav_id" : {"Field": "GoodsCategory", "IsStr": True},
			"juridical_address_index" : {"Field": "AddrZIP", "IsStr": True},
			"juridical_address_city_name" : {"Field": "AddrSity", "IsStr": True},
			"juridical_address_street_name" : {"Field": "AddrStreet", "IsStr": True},
			"juridical_address_dom" : {"Field": "AddrBuilding", "IsStr": True},
			"juridical_address_building" : {"Field": "AddrBuilding2", "IsStr": True},
			"juridical_address_office" : {"Field": "AddrOffice", "IsStr": True},
			"actual_address_index" : {"Field": "LocAddrZIP", "IsStr": True},
			"actual_address_city_name" : {"Field": "LocAddrSity", "IsStr": True},
			"actual_address_street_name" : {"Field": "LocAddrStreet", "IsStr": True},
			"actual_address_dom" : {"Field": "LocAddrBuilding", "IsStr": True},
			"actual_address_building" : {"Field": "LocAddrBuilding2", "IsStr": True},
			"actual_address_office" : {"Field": "LocAddrOffice", "IsStr": True},
			"account_number" : {"Field": "AccountNo", "IsStr": True},
			"inn" : {"Field": "ITN", "IsStr": True},
			"registration_reason_code" : {"Field": "TRRC", "IsStr": True},
			"date_of_accounting" : {"Field": "TRDate", "IsStr": True, "IsDate": True},
			"OGRN_OGRNIP" : {"Field": "OGRN", "IsStr": True},
			"registration_date" : {"Field": "RegistrationDate", "IsStr": True, "IsDate": True},
			"OKVED" : {"Field": "OCVED", "IsStr": True},
			"OKPO" : {"Field": "OCPO", "IsStr": True},
			"OKATO" : {"Field": "OCATO", "IsStr": True},
			"actual_adress_non_stand_part" : {"Field": "FactAdrStr", "IsStr": True},
			"juridical_adress_non_stand_part" : {"Field": "JurAdrStr", "IsStr": True},
			"tech_questions.name" : {"Field": "Contact", "IsStr": True},
			"tech_questions.email": {"Field": "Email", "IsStr": True},
			"tech_questions.phone": {"Field": "Phone", "IsStr": True}, 
		}
		connection = None
		try:
			vSetParams = ""
			vSetValues = ""
			vParam = {}
			for key in export_params:
				vParam = export_params[key]
				vArrayOfAtr = key.split('.')
				value = ""
				var = None
				if (len(vArrayOfAtr) > 1):
					vObj = getattr(partner, vArrayOfAtr[0])
					if vObj:
						var = getattr(vObj, vArrayOfAtr[1])
				else:
					var = getattr(partner, vArrayOfAtr[0])
				if var:
					if (vParam["IsStr"]):
						value = var.encode("utf-8")
					else:
						value = str(var)
				if (value != ""):
					vSetParams = self.addCondition(vParam["Field"].encode("utf-8"), vSetParams)
					vSetValues = self.addCondition(value , vSetValues, None, vParam['IsStr'], "IsDate" in vParam)
			vSetParams = self.addCondition("CRM_TimeStamp", vSetParams)
			vSetValues = self.addCondition(time.strftime('%Y-%m-%d %H:%M:%S'), vSetValues, None, True)
			query = "insert into " + self.tableName.encode("ascii") + " (" + vSetParams + ") values(" + vSetValues + ")"
			connection = self.exchange_server.connectToServer()
			cursor = connection.cursor()	
			cursor.execute(query)
			connection.commit()	
		except Exception, e:
			raise osv.except_osv(_("Export failed!"), _("Here is what we got instead:\n %s.") %tools.ustr(e))
		finally:
			if connection:
				connection.close()

	"""
		Находит или создает объект заданного класса
		Параметры:
			classObj - класс искомого объекта
			condition - условие для поиска
			CreateNewObj - если объект не найден создавать его или нет
			vals - атрибуты объекта
			UpdateSearchingObj - обновить найденный объект или нет
	"""
	def findObject(self, cr, uid, classObj, condition, CreateNewObj=False, vals=None, UpdateSearchingObj=False):
		res_obj = self.pool.get(classObj)
		cur_obj = None
		res_id = res_obj.search(cr, uid, condition, context=None)
		if len(res_id) > 0:
			cur_obj = res_obj.browse(cr, uid, res_id[0])
		if cur_obj:
			if (vals) and (UpdateSearchingObj):
				cur_obj.write(vals)
		elif CreateNewObj: 
			cur_obj = self.pool.get(classObj)
			cur_obj = res_obj.browse(cr, uid, cur_obj.create(cr, uid, vals, context=None))	 	
		return cur_obj

	#Проверяет есть ли эта дата, пытается привести ее к определенному фомату, если не удалось возвращает None
	def getDate(self, date):
		res = None
		if (date):
			#Хак в случае если год в дате будет меньше 1900
			try:
				res = date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
			except ValueError:
				vRegDate = None
		return res

	"""
		Находит или создает клиента
		Параметры:
			row - запись из промежуточной базы 
	"""
	def createOrFindResPartner(self, cr, uid, row, log_file = None):
		cur_obj = None
		log_msg = ""
		type_msg = ""
		added_info = u" при загрузке клиента: " + unicode(row[self.var_res_partner_fields.index("CustomerName")], "utf-8")
		res_obj = self.pool.get('res.partner')
		vDateAccount = self.getDate(row[self.var_res_partner_fields.index("TRDate")])
		vRegDate = self.getDate(row[self.var_res_partner_fields.index("RegistrationDate")])
		#Поиск организационной формы компании
		vOrgTypeID = None
		if (row[self.var_res_partner_fields.index("CompOrgTypeID")]): 
			vOrgType = self.findObject(cr, uid,"res.partner.title", [('ext_code', "in", [str(row[self.var_res_partner_fields.index("CompOrgTypeID")].encode("utf-8"))])])
			if (vOrgType):
				vOrgTypeID = vOrgType.id 
			else:
				type_msg = u"Предупреждение"
				log_msg = u"Не найдена орг форма с внешним ключем " + unicode(row[self.var_res_partner_fields.index("CompOrgTypeID")], "utf-8") + added_info
				self.write_log(cr, uid, log_file, log_msg, type_msg)	
		
		vals = {
			#Информация о клиенте
			"name":	row[self.var_res_partner_fields.index("CustomerName")],		
			"short_name": row[self.var_res_partner_fields.index("CustomerName")],
			"unk": row[self.var_res_partner_fields.index("NAV_UNC")],
			"is_company": True,
			"juridical_name": row[self.var_res_partner_fields.index("LegalName")],
			"website": row[self.var_res_partner_fields.index("WebSite")], 
			"active": True,
			#Юридический адрес
			"juridical_address_index": row[self.var_res_partner_fields.index("AddrZIP")],
			#Коды
			"inn": row[self.var_res_partner_fields.index("ITN")],
			"registration_reason_code": row[self.var_res_partner_fields.index("TRRC")],
			"OGRN_OGRNIP": row[self.var_res_partner_fields.index("OGRN")],
			"OKVED": row[self.var_res_partner_fields.index("OCVED")],
			"OKPO": row[self.var_res_partner_fields.index("OCPO")],
			"OKATO": row[self.var_res_partner_fields.index("OCATO")],
			#Даты
			"date_of_accounting": vDateAccount,
			"registration_date": vRegDate,
			"title" : vOrgTypeID,
			#Не стандартная часть адреса
			'actual_adress_non_stand_part': row[self.var_res_partner_fields.index("FactAdrStr")],  
			'juridical_adress_non_stand_part': row[self.var_res_partner_fields.index("JurAdrStr")],
			#ID холдинга
			'nav_holdingId' : row[self.var_res_partner_fields.index("Holding_Id")], 
			}
		cur_obj = self.pool.get('res.partner')
		cur_obj = res_obj.browse(cr, uid, cur_obj.create(cr, uid, vals, context=None))
		#Если мы нашли или создали компанию - то пытаемся создать договор и контактное лицо
		if cur_obj:
			if row[self.var_res_partner_fields.index("AgreementNo")]: 
				self.createContracts(cr, uid, row, self.var_res_partner_fields, cur_obj, log_file) 			
			if row[self.var_res_partner_fields.index("Contact")]:			
				vals_add_obj = {
					"name":  row[self.var_res_partner_fields.index("Contact")],
					"email": row[self.var_res_partner_fields.index("Email")],
					"phone": row[self.var_res_partner_fields.index("Phone")],
					'parent_id': cur_obj.id
				}
				contact = self.findObject(cr, uid,'res.partner', ["&","&",('name', 'in' ,[row[self.var_res_partner_fields.index("Contact")]]),('parent_id', 'in', [cur_obj.id]),("is_company", '=', False)], True, vals_add_obj, True)			
				cur_obj.write({"first_contact": contact.id,})
		return cur_obj

	def createContracts(self, cr, uid, row, var_field, cur_obj, log_file = None):
		log_msg = ""
		type_msg = ""
		added_info = u" при загрузке клиента: " + unicode(cur_obj.name)
		#Дата доверенности
		vDoverenostDate = self.getDate(row[var_field.index("LoA_Date")])
		vRegion = None
		if (row[var_field.index("Region_ID")]):
			vRegionObj = self.findObject(cr, uid,"crm.settlement_center", [('nav_id', "in", [str(row[var_field.index("Region_ID")].encode("utf-8"))])])
			if vRegionObj:
				vRegion = vRegionObj.id if vRegionObj else None
			else:
				type_msg = u"Предупреждение"
				log_msg = u"Не найден регион доставки с внешним ключем " + unicode(row[var_field.index("Region_ID")], "utf-8") + added_info
				self.write_log(cr, uid, log_file, log_msg, type_msg)
		#Поиск склада 
		vStorageShipID = None
		if (row[var_field.index("Warehouse_ID")]): 
			vStorageShip = self.findObject(cr, uid,"crm.shipping_storage", [('nav_id', "in", [str(row[var_field.index("Warehouse_ID")].encode("utf-8"))])])
			if (vStorageShip):
				vStorageShipID = vStorageShip.id 
			else: 
				type_msg = u"Предупреждение"
				log_msg = u"Не найден  Склад отправления с внешним ключем " + unicode(row[var_field.index("Warehouse_ID")], "utf-8") + added_info
				self.write_log(cr, uid, log_file, log_msg, type_msg)
		vStartDate = self.getDate(row[var_field.index("AgreementStartDate")])
		vAgreementDate = self.getDate(row[var_field.index("AgreementDate")])
		vRespPers = None
		# Ответственны по договору
		if (row[var_field.index("Responsible_ID")]): 
			vRespPersObj = self.findObject(cr, uid,"res.users", [('nav_id', "in", [str(row[var_field.index("Responsible_ID")].encode("utf-8"))])])
			vRespPers = vRespPersObj.id if vRespPersObj else None
			if not vRespPersObj:
				type_msg = u"Предупреждение"
				log_msg = u"Не найдена пользователь с внешним ключем " + unicode(row[var_field.index("Responsible_ID")], "utf-8") + added_info
				self.write_log(cr, uid, log_file, log_msg, type_msg)		
		#Атрибуты договора
		vals_add_obj = {
			'name': row[var_field.index("AgreementName")],
			'crm_number': row[var_field.index("AgreementNo")],
			'partner_id': cur_obj.id,
			"fio_authorized person_nominative_case": row[var_field.index("RespPerson")], 
			"fio_authorized person_genitive_case": row[var_field.index("RespPersonWhom")],
			"authorized_person_position_nominative_case": row[var_field.index("RespPersonPosition")], 
			"authorized_person_position_genetive_case": row[var_field.index("RespPersonPositionWhom")],
			'region_of_delivery': vRegion,
			"storage_of_shipping": vStorageShipID,
			"number_of_powerOfattorney": row[var_field.index("LoA_Number")], 
			"date_of_powerOfattorney": vDoverenostDate,
			"date_start": vStartDate,
			"dateOfContracts": vAgreementDate,
			"manager_id": vRespPers, 
		}
		self.findObject(cr, uid,"account.analytic.account", ['&',('crm_number',"in", [unicode(row[var_field.index("AgreementNo")], "utf-8")]),('partner_id', 'in',[cur_obj.id])], True, vals_add_obj, True)


	def getQuery_partner(self, var_field, tableName):
		vFields = ""
		for elem in var_field:
			vFields = vFields +  "," if vFields != "" else "" 
			vFields = vFields + elem
		query = "select " + vFields + " from " + tableName
		return query

	"""	
		Первичный импорт
	"""
	"""
		Структура:
			CustomerName - name - 1
			NAV_UNC - unk - 2
			ShopName - internet_shop_name - juridical_name - 3
			WebSite - 4 - website
			GoodsCategory - category_of_goods - 5
			Warehouse_ID - storage_of_shipping - 6
			Region_ID - region_of_delivery - 7
			RespPerson - fio_authorized person_nominative_case - 8
			RespPersonWhom - fio_authorized person_genitive_case - 9
			RespPersonPosition - authorized_person_position_nominative_case - 10
			RespPersonPositionWhom - authorized_person_position_genetive_case - 11
			LoA_Number - Номер доверенности - 12
			LoA_Date - date_of_powerOfattorney - 13 
			AddrZIP - juridical_address_index - 14
			AddrSity - juridical_address_city_name - 15
			AddrStreet - juridical_address_street_name - 16
			AddrBuilding - juridical_address_dom - 17
			AddrBuilding2 - juridical_address_building - 18
			AddrOffice - juridical_address_office - 19
			LocAddrZIP - actual_address_index - 20
			LocAddrSity - actual_address_city_name - 21
			LocAddrStreet - actual_address_street_name - 22
			LocAddrBuilding - actual_address_dom - 23
			LocAddrBuilding2 - actual_address_building - 24
			LocAddrOffice - actual_address_office - 25
			AccountNo - account_number - 26
			--Не грузим -------------
			BIC - BIN - 27
			BankName - bank_name - 28
			CorrAccountNo - correspondent_account_number - 29
			PartnerType - type_of_counterparty - 30
			------------------------------------------
			ITN - inn - 31
			TRRC - registration_reason_code - 32
			TRDate - date_of_accounting - 33
			OGRN - OGRN_OGRNIP - 34
			RegistrationDate -  registration_date - 35
			OCVED - OKVED - 36
			OCPO - OKPO - 37
			OCATO - OKATO - 38
			AgreementNo - name in account.analytic.account - 39
			FactAdrStr - actual_adress_non_stand_part - фактически адрес строкой - 40 
			JurAdrStr - juridical_adress_non_stand_part - юридический адрес строкой - 41
			Contact - ФИО контактого лица - 42
			Email - email - 43
			Phone - phone - 44
			idimport - уникальный ключ для поиска записи импорта - 45
			CompOrgTypeID - company_org_type - 46
			AgreementDate - дата договора date_start у договора- 47
			nav_holdingId - идентификатор холдинга у клиента - 48
	"""

		
	# здесь объявляем обработчики


	def partner_import(self,cr, uid, ids, context=None):
		conection = None
		type_msg = ""
		log_msg = ""
		server = self.browse(cr, uid, ids[0], context=context)
		try: 
			log_file = self.create_log_file(cr, uid, server.exchange_type)
			exchange_server = server.exchange_server
			conection = exchange_server.connectToServer()
			cursor = conection.cursor()
			query = server.getQuery_partner(self.var_res_partner_fields, server.tableName)
			cursor.execute(query)
			for row in cursor.fetchall():
				cur_obj = server.createOrFindResPartner(row, log_file)
				if (cur_obj is None):
					log_msg = u"Клиент " + unicode(row[self.var_res_partner_fields.index("CustomerName")], "utf-8") + u" не создан в системе!"
					type_msg = u"Ошибка"
					self.write_log(cr, uid, log_file, log_msg, type_msg)
			conection.commit()
		except Exception, e:
			log_msg = tools.ustr(e)
			type_msg = u"Ошибка"
			self.write_log(cr, uid, log_file, log_msg, type_msg)
		finally:
			if conection:
				conection.close()
			if log_file:
				log_file.close()
		server.write({'lastImportDate': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
	 	return True


	def holdings_import(self, cr, uid, ids, context=None, query = None, connection = None, log_file = None, NeedCloseConnect = True):
		try:
			if not(log_file):
				log_file = self.create_log_file(cr, uid, "holding")
			# сперва найдем все холдинги
			if not(connection):
				server = self.browse(cr, uid, ids[0], context=context)
				exchange_server = server.exchange_server
				connection = exchange_server.connectToServer()
			cursor=connection.cursor()
			#Убираем это условие посколько этот алгорим будет пока только для первичного импорт 
			#будем выбирать только те записи, которые созданы после предидущего импорта
			#if (server.lastImportDate):
			#	wherePart = "where nav_timestamp > '" + str(server.lastImportDate) + "'"
			# название столбцов до конца не известно, пока для информации
			if not(query):
				query = u"select holding_id, holding_name from " + unicode(server.tableName, "utf-8") 
			#+ " " + wherePart
			cursor.execute(query)
			# итерируем холдинги
			for row in cursor.fetchall():
				# находим или создаем холдинг
				# подготавливаем данные для создаваемого (в случае чего, холдинга)
				vals_add_obj = {
					#Информация о клиенте
					"name":	row[1],		
					"short_name": row[1],
					"is_company": True,
					# аттрибут холдинга
					"holdingId" : row[0],
				}
				holding = self.findObject(cr, uid,'res.partner', ["&",('holdingId', 'in' ,[unicode(row[0], "utf-8")]),("is_company", '=', True)], True, vals_add_obj, False)
				# находим клиентов, у которых nav_holdingId = ид холдинга
				res_partner_obj = self.pool.get('res.partner')
				res_partner_ids = res_partner_obj.search(cr, uid, [('nav_holdingId', 'in', [holding.holdingId])], context=context)
				res_partner = res_partner_obj.browse(cr, uid, res_partner_ids)
	            # итерируем отобранных клиентов и устанавливаем им в качестве parent_id id холдинга
				for partner in res_partner:
					partner.write({"parent_id": holding.id})
		except Exception, e:
			log_msg = tools.ustr(e)
			type_msg = u"Ошибка"
			self.write_log(cr, uid, log_file, log_msg, type_msg)
		finally:
			if connection and NeedCloseConnect:
				connection.close()
			if log_file and NeedCloseConnect:
				log_file.close()

	def responsible_import(self, cr, uid, ids, context=None):
		try:
			log_file = self.create_log_file(cr, uid, "responsible")
			log_msg = ""
			type_msg = ""
			for server in self.browse(cr, uid, ids, context=context):
				exchange_server = server.exchange_server
				connection = exchange_server.connectToServer()
				cursor=connection.cursor() 
				query = "select Client_UNK, Client_Responsible  from " + server.tableName
				cursor.execute(query)
				for row in cursor.fetchall():
					partner = self.findObject(cr, uid,u'res.partner', [(u"unk", u"in", [unicode(row[0], "utf-8")])])
					resp_user = self.findObject(cr, uid,u'res.users', [(u"nav_id", u"in", [unicode(row[1], "utf-8")])]) 
					if (partner and resp_user):
						partner.write({"user_id": resp_user.id})
					elif not(partner):
						log_msg = u"Не найден клиент с внешним ключем " + unicode(row[0], "utf-8") 
						type_msg = u"Ошибка"
						self.write_log(cr, uid, log_file, log_msg, type_msg)
					elif not(resp_user):
						log_msg = u"Не найден пользоватьель с внешним ключем " + unicode(row[1], "utf-8") 
						type_msg = u"Ошибка"
						self.write_log(cr, uid, log_file, log_msg, type_msg)

		except Exception, e:
			log_msg = tools.ustr(e)
			type_msg = u"Ошибка"
			self.write_log(cr, uid, log_file, log_msg, type_msg)
		finally:
			if connection:
				connection.close()
			if log_file:
				log_file.close()

	def user_import(self, cr, uid, ids, context=None):
		try:
			log_file = self.create_log_file(cr, uid, "user")
			for server in self.browse(cr, uid, ids, context=context):
				exchange_server = server.exchange_server
				connection = exchange_server.connectToServer()
				cursor=connection.cursor() 
				query = "select employee_login, employee_code  from " + server.tableName
				cursor.execute(query)
				for row in cursor.fetchall():
					vals = {
						"name": row[0],
						"login": row[0],
						"notify_email": "always",
					}
					user = self.findObject(cr, uid,u'res.users', [(u"login", u"in", [unicode(row[0], "utf-8")])], True, vals) 
					if (user):
						user.write({"nav_id": row[1]})
					else:
						log_msg = u"Пользователь " + unicode(row[0], "utf-8") + u" не создан в системе!"
						type_msg = u"Ошибка"
						self.write_log(cr, uid, log_file, log_msg, type_msg)
		except Exception, e:
			log_msg = tools.ustr(e)
			type_msg = u"Ошибка"
			self.write_log(cr, uid, log_file, log_msg, type_msg)
		finally:
			if connection:
				connection.close()
			if log_file:
				log_file.close()



	var_field = {
		"CRM_ID": 0,
		"nav_UNC": 1,
		"Source": 2,
		"Dest" : 3,
		"Command": 4,
		"id": 5,
	}

	#Обновляем unk клиента - unk приходит из NAV
	def UpdateUNC(self, cr, uid, ids, partner, command_var, log_file, connection):
		result = True
		unk = command_var[self.var_field["nav_UNC"]]
		partner.write({"unk": unicode(unk, "utf-8")})
		if (partner.user_id) and (partner.user_id.email):
			msg_subject = u"Клиенту присвоен УНК"
			msg_body = u"Клиенту " + partner.name + u" присвоен УНК " + unicode(unk, "utf-8") + u"<br>Можно приступать к созданию договора и согласования его условий с клиентом."
			post_vars = {
				"partner_ids":[4,partner.user_id.partner_id.id],
				"body": msg_body,
				"subject": msg_subject,}
			self.send_email(cr, uid, ids, post_vars, None, partner, "res.partner")
		return result

	#Обновляем контактных лиц
	def UpdateContactPersons(self, cr, uid, ids, partner, command_var, log_file, connection):
		var_role = {
			'1': 'first_contact',
			'2': 'signer',
			'3': 'logistics_respons_person',
			'4': 'financial_resp_per',
			'5': 'tech_questions',
		}
		result = True
		idCommand = command_var[self.var_field["id"]]
		unk = str(command_var[self.var_field["nav_UNC"]])
		query = "select Role, Contact, Email, Phone, Fax from ContactPersons where idCommand = " + str(idCommand)
		cursor = connection.cursor()
		cursor.execute(query)
		for row in cursor.fetchall():
			vals_add_obj = {
				"name":  row[1],
				"email": row[2],
				"phone": row[3],
				'fax': row[4],
				'parent_id': partner.id,
			}
			contact = self.findObject(cr, uid,'res.partner', ["&","&",('name', 'in' ,[row[1]]),('parent_id', 'in', [partner.id]),("is_company", '=', False)], True, vals_add_obj, True)
			if (row[0]) and (row[0] != ""):
				if (row[0] in var_role):
					partner.write({str(var_role[row[0]]): contact.id,})
				else:
					log_msg = u"Не найдена роль КЛ с внешним ключем =" + unicode(row[0], "utf-8") + u"при загрузке КЛ " + unicode(row[1])
					type_msg = u"Предупреждение"
					self.write_log(cr, uid, log_file, log_msg, type_msg)

	#Обновляем холдинги
	def UpadeteHolding(self, cr, uid, ids, partner, command_var, log_file, connection):
		idCommand = command_var[self.var_field["id"]]
		query = u"select Holding_ID, Holding_Name from Holding where idCommand= " + str(idCommand)
		self.holdings_import(cr, uid, ids, None, query, connection, log_file, False)

	#Обновляем клиента
	def UpdateClient(self, cr, uid, ids, partner, command_var, log_file, connection):
		idCommand = command_var[self.var_field["id"]]
		query = "select Holding_Id from Clients where idCommand = " + str(idCommand) 
		cursor = connection.cursor()
		cursor.execute(query)
		row = cursor.fetchone()
		if (row[0]):
			partner.write({"nav_holdingId":row[0]})
			holding = self.findObject(cr, uid,'res.partner', ["&",('holdingId', 'in' ,[unicode(row[0], "utf-8")]),("is_company", '=', True)])
			if (holding):
				partner.write({"parent_id": holding.id})
			else: 
				log_msg = u"Не найден холдинг с внешним ключем = " + unicode(row[0], "utf-8")
				type_msg = u"Предупреждение"
				self.write_log(cr, uid, log_file, log_msg, type_msg)
		else:
			log_msg = u"Не найден внешний ключ при обновлении холдинга клиента - " + unicode(partner.name, "utf-8")
			type_msg = u"Ошибка"
			self.write_log(cr, uid, log_file, log_msg, type_msg)

	def UpdateContracts(self, cr, uid, ids, partner, command_var, log_file, connection):
		idCommand = command_var[self.var_field["id"]]
		field_account = ["AgreementNo", "AgreementName", 
			"RespPerson", "RespPersonWhom", "RespPersonPosition",
			"RespPersonPositionWhom", "Warehouse_ID", "Region_ID",
			"LoA_Number", "LoA_Date", "AgreementDate", "AgreementStartDate", "Responsible_ID"]
		query = self.getQuery_partner(field_account, "Contracts") + u" where idCommand = " + str(idCommand)
		cursor = connection.cursor()
		cursor.execute(query)
		for row in cursor.fetchall():
			self.createContracts(cr, uid, row, field_account, partner, log_file)


	#Справочник методов обработчиков команд
	var_com_method = {
		"UpdatedUNC": UpdateUNC,
		"UpdatedContactPersons": UpdateContactPersons,
		"UpdatedHolding": UpadeteHolding,
		"UpdatedClient": UpdateClient,
		"UpdatedContracts": UpdateContracts,
	}

	#Метод который определяет, что это за команда и вызывает соответсвующий обработчик
	def processCommand_nav(self, cr, uid, ids, partner, command_var, log_file, connection):
		Command = command_var[self.var_field["Command"]]
		result = False
		if (Command.strip() in self.var_com_method):
			result = self.var_com_method[Command.strip()](self, cr, uid, ids, partner, command_var, log_file, connection)
		else:
			type_msg = u"Ошибка"
			log_msg = u"Не найден обработчик для команды :" + Command
			self.write_log(cr, uid, log_file, log_msg, type_msg)
		return result	



	def commands_import_from_nav(self, cr, uid, ids, context=None):
		partner_id = 0
		connection = None
		log_file = self.create_log_file(cr, uid, "exchange with NAV")
		try:
			server = self.browse(cr, uid, ids[0], context=context)
			vFieldParam = "CRM_ID, nav_UNC, Source, Dest, Command, id"
			query = "select  " + vFieldParam + " from crm_commands where DoneTime is null and Dest = 'crm' Order by id"
			connection = server.exchange_server.connectToServer()
			cursor=connection.cursor()
			cursor.execute(query)
			for row in cursor.fetchall():
				if (row[self.var_field["CRM_ID"]]): 
					partner_id = row[self.var_field["CRM_ID"]]
					res_obj = self.pool.get('res.partner')
					partn = res_obj.browse(cr, uid, partner_id)
				elif (row[self.var_field["nav_UNC"]]):
					partn = server.findObject('res.partner', [("unk", 'in', [unicode(row[self.var_field["nav_UNC"]], "utf-8")])])
				command = row[self.var_field["Command"]]
				if not(partn) and (command.strip() != "UpdatedHolding"):
					type_msg = u"Ошибка"
					log_msg = u"Клиента с ID " + unicode(str(row[self.var_field["CRM_ID"]]), "utf-8") + u" не найден в crm, при выполнении команды: " + unicode(row[self.var_field["Command"]], "utf-8")
					self.write_log(cr, uid, log_file, log_msg, type_msg)
				else:
					command = row[self.var_field["Command"]]
					result = server.processCommand_nav(partn, row, log_file, connection)
				query = "update crm_commands set DoneTime = '" + time.strftime('%Y-%m-%d %H:%M:%S') + "' where id = " + str(row[self.var_field["id"]])
				cursor.execute(query)
			connection.commit()
		except Exception, e:
			log_msg = tools.ustr(e)
			type_msg = u"Ошибка"
			self.write_log(cr, uid, log_file, log_msg, type_msg)
		finally:
			if connection:
				connection.close()
			if log_file:
				log_file.close()

	def processCommand_cf(self, cr, uid, ids, partner, command, opport=None, added_var=None):
		connection = None
		comm_connection = None
		server = self.browse(cr, uid, ids[0], context=None)
		if not(opport):
			opport = self.findObject(cr, uid, 'crm.lead', [('creating_partner','=', partner.id)])
		if (command != "UpdatedCustomerData"):
			server_res_partner = self.findObject(cr, uid, "crm.iml.sqlserver", [("exchange_type", 'in', ["partner"])]) 
			if not(server_res_partner):
				sys.stdout.write("ERROR! Пожалуйста настройте таблицу для экспорта/импорта клиентов!")
			query = server_res_partner.getQuery_partner(self.var_res_partner_fields, server_res_partner.tableName)
			wherePart = ""
			if (command == "UpdateCustomerData"):
				wherePart = " where CRM_ID=" + str(partner.id)
			elif (command == "UpdatedUNC"):
				if (added_var):
					unc = added_var[self.var_field["nav_UNC"]]
					wherePart = " where NAV_UNC = " + unc.encode(utf-8) + " and CRM_TimeStamp is null"
			if (wherePart != ""):
				try:
					query = query + wherePart
					connection = server_res_partner.exchange_server.connectToServer()
					cursor=connection.cursor()
					cursor.execute(query)
					for row_part in cursor.fetchall():
						cur_obj = server_res_partner.createOrFindResPartner(row_part)
						if (cur_obj is None):
							#TODO Сделать логирование импорта
							sys.stdout.write("ERROR! Not found client in system with id =" + str(row_part[0]))
						if (cur_obj) and (command=="UpdateCustomerData"):
							cur_obj.iml_crm_export_id()
					connection.commit()
				finally:
					if (connection):
						connection.close()
					if (comm_connection):
						comm_connection.close()
		else:	
			if (opport) and (opport.user_id) and (opport.user_id.partner_id) and (opport.user_id.partner_id.email):
				customer_name = ""
				if (opport.partner_id):
					customer_name = opport.partner_id.name
				elif (opport.contact_name):
					customer_name = opport.contact_name
				params = self.pool.get('ir.config_parameter')
				url_link = params.get_param(cr, uid, 'crm_iml_url_pattern',default='' ,context=None)
				url = url_link + "/" + opport.hash_for_url + "?showclosed=1"
				model_data = self.pool.get("ir.model.data")
				dummy, form_view = model_data.get_object_reference(cr, uid, 'crm', 'crm_case_category_act_oppor11')
				url_opport = params.get_param(cr, uid,"web.base.url").encode("utf-8") + u"/web#id=" + str(opport.id).encode("utf-8") + u"&view_type=form&model=crm.lead"
				url_opport = url_opport + "&action=" + str(form_view)
				body = customer_name.encode("utf-8")  + u" заполнил анкету с контактной информацией:<br>".encode("utf-8") + url.encode("utf-8") + u" <br> Информация запрашивалась в рамках Заявки: ".encode("utf-8") + opport.name.encode("utf-8") + u"(".encode("utf-8") + url_opport.encode("utf-8") + u")<br> Перейдите в заявку и изучите заполненные данные!".encode("utf-8")	
				post_vars = {'subject': u"Клиент заполнил анкету",
					"body" :body,
					'partner_ids': [(4, opport.user_id.partner_id.id)],
					} 
				self.send_email(cr, uid, ids, post_vars)

	def send_email(self,cr, uid, ids, post_vars, context=None, thread = False, model='mail.thread'):
		thread_pool = self.pool.get(model)
		thread_pool.message_post(
			cr, uid, thread.id,
			type="notification",
			subtype="mt_comment",
			context=context,
			**post_vars)

	def addCondition(self,valueCond, stringCond, KeyValue=None, isStr=False, isDate=False):
		#Перечисление полей, которые являются строкой 
		#TODO сделать как в экспорте бул параметр это строка
		vStrFields = {
			"nav_UNC": True,
			"Source": True,
			"Dest":  True,
			"Command": True,
			"TextMessage": True,
			"CreateTime": True,
		}
		if (isDate):
			date_object = valueCond
			valueCond = str(date_object)
		if (stringCond) and (stringCond != ""):
			stringCond = stringCond + ", "
		if ((KeyValue) and (KeyValue in vStrFields)) or (isStr):
			stringCond = stringCond + "'".encode("ascii") + valueCond + "'".encode("ascii")
		else:
			stringCond = stringCond + valueCond
		return stringCond

	#Обмен командами
	def commands_exchange(self, cr, uid, ids, vals, needExportCl, partner=None):
		connection = None
		try:
			server = self.browse(cr, uid, ids[0], context=None)
			vSetParams = ""
			vSetValues = ""
			for key in vals:
				if (vals[key]) and (vals[key] != ""):
					vSetParams = server.addCondition(key, vSetParams)
					vSetValues = server.addCondition(str(vals[key]), vSetValues, key)
			if not("CreateTime" in vals):
				vSetParams = server.addCondition("CreateTime", vSetParams)
				vSetValues = server.addCondition(time.strftime('%Y-%m-%d %H:%M:%S'), vSetValues, "CreateTime")
			query = "insert into " + server.tableName + " (" + vSetParams + ") values(" + vSetValues + ")"
			exchange_server = server.exchange_server
			connection = exchange_server.connectToServer()	
			cursor = connection.cursor()	
			cursor.execute(query)
			connection.commit()	
			export_server = None
			if (needExportCl and "CRM_ID" in vals):
				export_server = server.findObject("crm.iml.sqlserver", [('exchange_type',"=", "partner")])
				if not(partner):
					partner = server.findObject("res.partner", [('id',"in", [int(vals["CRM_ID"])])])
				if not export_server:
					raise osv.except_osv(_("Send commands failed!"), _("Не задан сервер для импорта клиентов! Обратитесь к администратору."))
				export_server.export_res_partner(partner)				
		except Exception, e:
			raise osv.except_osv(_("Send commands failed!"), _("Here is what we got instead:\n %s.") %tools.ustr(e))
		finally:
			if connection:
				connection.close()
		

 
	# словарь, где хранится соответсвие тип обмена - обработчик
	exchange_types = { 
				"partner" : partner_import,
				"holdings": holdings_import,
				"commands_nav": commands_import_from_nav,
				"responsible": responsible_import,
				'user': user_import,
		}

	# развилка в импорте, метод - роутер
	# в данном методе принимаем решение, какой импорт дальше запускать
	# 
	def perform_import(self, cr, uid, ids, context=None):
		for exchange_proc in self.browse(cr, uid, ids, context=context):
			self.exchange_types[exchange_proc.exchange_type](self, cr, uid, ids, context);