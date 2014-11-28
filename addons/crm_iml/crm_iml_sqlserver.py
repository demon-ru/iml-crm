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
		'exchange_type':fields.selection([('partner', 'Partner exchange'), ('holdings', 'Holdings exchange'), ('commands_nav', 'Обмен командами с NAV'), ('commands_cf', 'Обмен командами с CF'), ('responsible','Импорт ответственности по клиенту'), ('user','Импорт пользователей')], 'Exchange type', required=True),
		'exchange_server':fields.many2one('crm.iml.exchange_server_settings', 'name'),
	}

	#******************************** Вспомогательные структуры *********************************

	#Поля для запроса таблицы Client из бд NAV
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

	#Поля для запросов из таблицы ClientCard, как в БД NAV так и в CF
	var_cf_cl = ["ID", "Name", "OrgName", "OrgType", "Location",
		"Scheme", "CalculationType", "FIO_IP", "FIO_RP", "Post_IP", 
		"Post_RP", "ProxyNo", "ProxyDate", "INN", "KPP", "StatementDate",
		"OGRN", "RegistrationDate", "RegistrationDate", "OKPO", "OKATO", "OKVED",
		"AddressUr", "AddressFact", "BankName", "BankBIK", "BankNoRC",
		"BankNoKC", "Site", "GoodsCategory", "NalPostRus", "Pack",
		"OrdersCountSeason", "OrdersCountNoSeason", "IndexUr",
		"IndexFact", "HoldingName"]
	#Поля для запросов из таблицы ClientContact, как в БД NAV так и в CF
	var_cf_con_pers = ["ID","Surname","FirstName","MiddleName","Phone",
		"Fax","Email","Post","Main"]

	#Поля для команд из БД NAV
	var_field = {
		"CRM_ID": 0,
		"nav_UNC": 1,
		"Source": 2,
		"Dest" : 3,
		"Command": 4,
		"id": 5,
	}
	#Поля для команд из БД Cf
	var_field_cf = {
		"id_client": 1,
		"hash": 2,
		"Dest" : 3,
		"Command": 4,
	}
	#Структура полей для выгрузки клиента из CRM в NAV
	export_params_partner = {
		"unk": {"Field": "NAV_UNC", "IsStr": True}, 
		"name": {"Field": "CustomerName", "IsStr": True},
		'juridical_name': {"Field": "LegalName", "IsStr": True},
		"website" : {"Field": "WebSite", "IsStr": True},
		"category_of_goods.nav_id" : {"Field": "GoodsCategory", "IsStr": True},
		"juridical_address_index" : {"Field": "AddrZIP", "IsStr": True},
		"juridical_address_city_name" : {"Field": "AddrSity", "IsStr": True},
		"actual_address_index" : {"Field": "LocAddrZIP", "IsStr": True},
		"juridical_address_street_name,juridical_address_dom,juridical_address_building,juridical_address_office,juridical_adress_non_stand_part" : {"Field": "JurAdrStr", "IsStr": True},
		"actual_adress_full_adress" : {"Field": "FactAdrStr", "IsStr": True},
		"inn" : {"Field": "ITN", "IsStr": True},
		"registration_reason_code" : {"Field": "TRRC", "IsStr": True},
		"date_of_accounting" : {"Field": "TRDate", "IsStr": True, "IsDate": True},
		"OGRN_OGRNIP" : {"Field": "OGRN", "IsStr": True},
		"registration_date" : {"Field": "RegistrationDate", "IsStr": True, "IsDate": True},
		"OKVED" : {"Field": "OCVED", "IsStr": True},
		"OKPO" : {"Field": "OCPO", "IsStr": True},
		"OKATO" : {"Field": "OCATO", "IsStr": True},
		"title.ext_code": {"Field":"CompOrgTypeID", "IsStr": True},
		"category_of_goods.nav_id": {"Field": "GoodsCategory", "IsStr": True},
	}
	#Структура полей для выгрузки клиента из CF в NAV
	export_params_row = {
		"Name": {"Field": "Name", "IsStr": True},
		'OrgName': {"Field": "OrgName", "IsStr": True},
		"OrgType" : {"Field": "OrgType", "IsStr": False},
		"Location" : {"Field": "Location", "IsStr": True},
		"Scheme" : {"Field": "Scheme", "IsStr": False},
		"CalculationType" : {"Field": "CalculationType", "IsStr": False},
		"FIO_IP" : {"Field": "FIO_IP", "IsStr": True},
		"FIO_RP" : {"Field": "FIO_RP", "IsStr": True},
		"Post_IP" : {"Field": "Post_IP", "IsStr": True},
		"Post_RP" : {"Field": "Post_RP", "IsStr": True},
		"ProxyNo" : {"Field": "ProxyNo", "IsStr": True},
		"ProxyDate" : {"Field": "ProxyDate", "IsStr": True, "IsDate": True},
		"INN" : {"Field": "INN", "IsStr": True},
		"KPP" : {"Field": "KPP", "IsStr": True},
		"StatementDate" : {"Field": "StatementDate", "IsStr": True, "IsDate": True},
		"OGRN" : {"Field": "OGRN", "IsStr": True},
		"RegistrationDate" : {"Field": "RegistrationDate", "IsStr": True, "IsDate": True},
		"OKVED": {"Field":"OKVED", "IsStr": True},
		"OKPO": {"Field": "OKPO", "IsStr": True},
		"OKATO" : {"Field": "OKATO", "IsStr": True},
		"AddressUr" : {"Field": "AddressUr", "IsStr": True},
		"AddressFact": {"Field":"AddressFact", "IsStr": True},
		"BankName": {"Field": "BankName", "IsStr": True},
		"BankBIK" : {"Field": "BankBIK", "IsStr": True},
		"BankNoRC" : {"Field": "BankNoRC", "IsStr": True},
		"BankNoKC": {"Field":"BankNoKC", "IsStr": True},
		"Site": {"Field": "Site", "IsStr": True},
		"GoodsCategory" : {"Field": "GoodsCategory", "IsStr": True},
		"NalPostRus" : {"Field": "NalPostRus", "IsStr": False, "IsBool": True},
		"Pack": {"Field":"Pack", "IsStr": False, "IsBool": True},
		"OrdersCountSeason": {"Field": "OrdersCountSeason", "IsStr": False},
		"IndexUr" : {"Field": "IndexUr", "IsStr": True},
		"OrdersCountNoSeason" : {"Field": "OrdersCountNoSeason", "IsStr": False},
		"IndexFact": {"Field":"IndexFact", "IsStr": True},
		"HoldingName": {"Field": "HoldingName", "IsStr": True},
	}
	#Структура для выгрузки КЛ из CRM
	export_param_obj_cont_pers = {
		"surname": {"Field": "Surname", "IsStr": True},
		"firstname": {"Field": 'FirstName', "IsStr": True},
		"patronymic": {"Field": "MiddleName", "IsStr": True},
		"phone": {"Field": "Phone", "IsStr": True},
		"fax": {"Field": "Fax", "IsStr": True},
		"email": {"Field": "Email", "IsStr": True},
		"function": {"Field": "Post", "IsStr": True},
	}

	#Структура полей для выгрузки контактного лиц из CF в NAV
	export_params_cont_pers = {
		"FirstName": {"Field": "FirstName", "IsStr": True},
		'Surname': {"Field": "Surname", "IsStr": True},
		"MiddleName" : {"Field": "MiddleName", "IsStr": True},
		"Phone" : {"Field": "Phone", "IsStr": True},
		"Fax" : {"Field": "Fax", "IsStr": True},
		"Email" : {"Field": "Email", "IsStr": True},
		"Post" : {"Field": "Post", "IsStr": True},
		"Main" : {"Field": "Main","IsStr": False, "IsBool": True},
	}
	#Структура для загрузки клиента из таблицы ClientCard 
	import_param_row = {
		"Name": {"Field": "name", "IsStr": True},
		'OrgName': {"Field": "juridical_name", "IsStr": True},
		"OrgType" : {"Field": "title", "IsStr": False},
		"INN": {"Field": "inn", "IsStr": True},
		"KPP": {"Field": "registration_reason_code", "IsStr": True},
		"StatementDate": {"Field": "date_of_accounting", "IsDate": True, "IsStr": True},
		"OGRN": {"Field": "OGRN_OGRNIP", "IsStr": True},
		"RegistrationDate": {"Field": "registration_date", "IsDate": True, "IsStr": True},
		"OKVED": {"Field": "OKVED", "IsStr": True},
		"OKPO": {"Field": "OKPO", "IsStr": True},
		"OKATO": {"Field": "OKATO", "IsStr": True},
		"AddressUr": {"Field": "juridical_adress_non_stand_part", "IsStr": True},
		"AddressFact": {"Field": "actual_adress_non_stand_part", "IsStr": True},
		"Site": {"Field": "website", "IsStr": True},
		"IndexUr": {"Field": "juridical_address_index", "IsStr": True},
		"IndexFact": {"Field": "actual_address_index", "IsStr": True}
	}
	#Структура для загрузки клиента из таблицы ClientContact 
	import_param_row_cont_pers = {
		"Surname": {"Field": "surname", "IsStr": True},
		'FirstName': {"Field": "firstname", "IsStr": True},
		"MiddleName" : {"Field": "patronymic", "IsStr": True},
		"Phone": {"Field": "phone", "IsStr": True},
		"Fax": {"Field": "fax", "IsStr": True},
		"Email": {"Field": "email", "IsStr": True},
		"Post": {"Field": "function", "IsStr": True},
	}
	#*************************************************************************


	#******************************** Методы *********************************

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
				sys.stdout.write(u"Внимание! Не удалось записать строчку в файл лога!\n" + unicode(log_msg, "utf-8"))
		except:
			sys.stdout.write(u"Внимание! Не удалось записать строчку в файл лога!\n" + unicode(log_msg, "utf-8"))

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

	def form_vars_for_write(self,cr, uid, ids, row, fields_struct, array_fields):
		var_obj = {}
		for key in fields_struct:
			vParam = fields_struct[key]
			index = array_fields.index(key)
			var = row[index]
			if "IsDate" in vParam:
				var = self.getDate(var)
			#Захадкорил получение ссылки на объект, пока не придумал другой более удачный вариант
			if key == "OrgType" and var:
				vOrgType = self.findObject(cr, uid,"res.partner.title", [('ext_code', "in", [str(var)])])
				if vOrgType:
					var = vOrgType.id
				else:
					var = None
			if var and (vParam["IsStr"]) and not("IsDate" in vParam):
				var = unicode(var, "utf-8")
			var_obj.update({vParam["Field"]: var})
		return var_obj


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
			if not(query):
				query = u"select holding_id, holding_name from " + unicode(server.tableName, "utf-8") 
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

	def UpdateCustomerData(self, cr, uid, ids, partner, command_var, log_file, connection):
		nav_server = self.findObject(cr, uid, "crm.iml.sqlserver", [("exchange_type", 'in', ["commands_nav"])])
		if not(nav_server):
			log_msg = u"Не задан сервер для обмена командами с NAV, данные не будут выгруженны в NAV"
			type_msg = u"Предупреждение"
			self.write_log(cr, uid, log_file, log_msg, type_msg)
		vIdCl = command_var[self.var_field_cf["id_client"]]
		cl_hash = command_var[self.var_field_cf["hash"]]
		vWhere = " where id = " + str(vIdCl)
		query = self.getQuery_partner(self.var_cf_cl, "ClientCard") + vWhere
		cursor = connection.cursor()
		cursor.execute(query)
		try:
			connection_nav = nav_server.exchange_server.connectToServer()
			cursor_nav = connection_nav.cursor()
			row = cursor.fetchone()
			if (row):
				# Формируем поля которые нужно обновить у клиента
				var = self.form_vars_for_write(cr, uid, ids, row, self.import_param_row, self.var_cf_cl)
				var.update({"is_company": True,
					"active": True,})
				opport = self.findObject(cr, uid, "crm.lead", [("hash_for_url", "in", [cl_hash])])
				partner = None
				#Ищем или создаем клиента
				if (opport and opport.creating_partner):
					opport.creating_partner.write(var)
					partner = opport.creating_partner
				else:
					res_obj = self.pool.get("res.partner")
					partner = self.pool.get("res.partner")
					partner = res_obj.browse(cr, uid, partner.create(cr, uid, var, context=None))
					if (opport):
						opport.write({"creating_partner": partner.id})
						if (opport.partner_id):
							opport.partner_id.write({"parent_id":partner.id, 
								"active": True,})
				#Формируем команду GetUNC
				com_vals = {
					"Source": "CRM",
					"Dest": "NAV",
					"Command": "GetUNC",
					"CRM_ID": str(partner.id),
				}
				id_command = self.commands_exchange(cr, uid, ids, com_vals, False, None, cursor_nav, False)
				#Выгружаем клиента в БД NAV
				self.export_res_partner(row, id_command, "idCommand", cursor_nav, False, True, self.var_cf_cl, "ClientCard")
				query = r"SELECT @@IDENTITY AS 'Identity'"
				cursor_nav.execute(query)
				new_cl_id = cursor_nav.fetchone()[0]
				vWhere = " where ClientID = " + str(vIdCl)
				#Теперь считываем всех контактные лица и сохраняем их в CRM и копируем запись в бд NAV
				query = self.getQuery_partner(self.var_cf_con_pers, "ClientContact") + vWhere
				cursor.execute(query)
				for cont in cursor.fetchall():
					name = cont[self.var_cf_con_pers.index("FirstName")]
					middleName = cont[self.var_cf_con_pers.index("MiddleName")]
					surname = cont[self.var_cf_con_pers.index("Surname")]
					var = self.form_vars_for_write(cr, uid, ids, cont, self.import_param_row_cont_pers, self.var_cf_con_pers)
					var.update({"name": "12", "parent_id":partner.id})
					condition = ["&","&","&",("parent_id", "in", [partner.id]),("firstname", "in", [name]),("surname", "in", [surname]), ("patronymic", "in", [middleName])]
					self.findObject(cr, uid, "res.partner", condition, True, var, True)
					self.export_res_partner(cont, new_cl_id, "id_client", cursor_nav, False, True, self.var_cf_con_pers, "ClientContact", self.export_params_cont_pers)
				connection_nav.commit()
		finally:
			if connection_nav:
				connection_nav.close()

	#Справочник методов обработчиков команд
	var_com_method = {
		"UpdatedUNC": UpdateUNC,
		"UpdatedContactPersons": UpdateContactPersons,
		"UpdatedHolding": UpadeteHolding,
		"UpdatedClient": UpdateClient,
		"UpdatedContracts": UpdateContracts,
		"UpdatedCustomerData": UpdateCustomerData,
	}

	#Метод который определяет, что это за команда и вызывает соответсвующий обработчик
	def processCommand(self, cr, uid, ids, partner, command_var, log_file, connection):
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
			query = "select  " + vFieldParam + " from crm_commands where DoneTime is null and upper(Dest) = 'CRM' Order by CreateTime, id"
			connection = server.exchange_server.connectToServer()
			cursor=connection.cursor()
			cursor.execute(query)
			rows = cursor.fetchall()
			for row in rows:
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
					result = server.processCommand(partn, row, log_file, connection)
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

	def commands_import_from_cf(self, cr, uid, ids, context=None):
		comm_connection = None
		server = self.browse(cr, uid, ids[0], context=None)
		partner_id = 0
		opport_id = 0
		connection = None
		log_file = self.create_log_file(cr, uid, "exchange with CF")
		try:
			server = self.browse(cr, uid, ids[0], context=None)
			vFieldParam = "0, id_client, hash, Dest, Command"
			query = "select  " + vFieldParam + " from crm_commands where DoneTime is null and upper(Dest) = 'CRM' Order by id_client"
			connection = server.exchange_server.connectToServer()
			cursor=connection.cursor()
			cursor.execute(query)
			rows = cursor.fetchall() 
			for row in rows:
				result = server.processCommand(None, row, log_file, connection)
				query = "update crm_commands set DoneTime = '" + time.strftime('%Y-%m-%d %H:%M:%S') + "' where id_client = " + str(row[self.var_field_cf["id_client"]])
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
			"hash": True,
		}
		if (isDate):
			date_object = valueCond
			valueCond = str(date_object)
		if (stringCond) and (stringCond != ""):
			stringCond = stringCond + ", "
		if ((KeyValue) and (KeyValue in vStrFields)) or (isStr):
			stringCond = stringCond + "'" + valueCond + "'"
		else:
			stringCond = stringCond + valueCond
		return stringCond

	"""
		Метод экспорта клиента в промежуточную базу
		Параметры:
			partner - экспортируемый партнер
	"""
	def export_res_partner(self, partner, rec_id=False, name_field_id = "", cursor = None, NeedCommit=True, isRow=False, var_field = [], tableName='Clients', export_params={}):
		connection = None
		if isRow and export_params == {}:
			export_params = self.export_params_row
		elif export_params == {}:
			export_params = self.export_params_partner
		try:
			vSetParams = ""
			vSetValues = ""
			vParam = {}
			for key in export_params:
				vParam = export_params[key]
				vArrayOfAtr = key.split('.')
				value = ""
				var = None
				#Получаем значение параметра в первом случае как из массива во 2-ом как из объекта
				if (isRow):
					index = var_field.index(key)
					var = partner[index]
				else:
					if (len(vArrayOfAtr) > 1):
						vObj = getattr(partner, vArrayOfAtr[0])
						if vObj:
							var = getattr(vObj, vArrayOfAtr[1])
					else:
						#Если поля отделены запятой то мы суммируем эти поля
						vArrayOfSum = key.split(',')
						if len(vArrayOfSum) > 1:
							var = ""
							for field in vArrayOfSum:
								pre_var =  getattr(partner, field)
								var = pre_var if not(var) else var + " " + pre_var
						else:	
							var = getattr(partner, vArrayOfAtr[0])
				if var:
					if (vParam["IsStr"]):
						if (isRow):
							value = var
						else:
							value = var.encode("utf-8")
					else:
						value = str(var)
				if (value != ""):
					vSetParams = self.addCondition(vParam["Field"].encode("utf-8"), vSetParams)
					vSetValues = self.addCondition(value , vSetValues, None, ((vParam['IsStr']) or ("IsBool" in vParam)), "IsDate" in vParam)
			if (name_field_id) and (rec_id):
				vSetParams = self.addCondition(name_field_id.encode("utf-8"), vSetParams)
				vSetValues = self.addCondition(str(rec_id) , vSetValues, None, False, False)
			query = "insert into " + tableName + " (" + vSetParams + ") values(" + vSetValues + ")"
			if not (cursor):
				connection = self.exchange_server.connectToServer()
				cursor = connection.cursor()
			cursor.execute(query)
			if connection and NeedCommit:
				connection.commit()	
		except Exception, e:
			raise osv.except_osv(_("Export failed!"), _("Here is what we got instead:\n %s.") %tools.ustr(e))
		finally:
			if connection and NeedCommit:
				connection.close()

	#Обмен командами c NAV и CF
	def commands_exchange(self, cr, uid, ids, vals, needExportCl, partner=None, cursor=None, NeedCommit=True, IsCF=False):
		connection = None
		id_command = None
		try:
			server = self.browse(cr, uid, ids[0], context=None)
			vSetParams = ""
			vSetValues = ""
			id_cl = None
			if not(cursor):
				exchange_server = server.exchange_server
				connection = exchange_server.connectToServer()
				cursor = connection.cursor()
			if (IsCF):
				id_cl = self.form_query(cr, uid, ids, cursor)
			for key in vals:
				if (vals[key]) and (vals[key] != ""):
					vSetParams = server.addCondition(key, vSetParams)
					vSetValues = server.addCondition(vals[key].encode("utf-8"), vSetValues, key)
			if not("CreateTime" in vals) and not (IsCF):
				vSetParams = server.addCondition("CreateTime", vSetParams)
				vSetValues = server.addCondition(time.strftime('%Y-%m-%d %H:%M:%S'), vSetValues, "CreateTime")
			if (IsCF):
				vSetParams = server.addCondition("id_client", vSetParams)
				vSetValues = server.addCondition(str(id_cl), vSetValues, "id_client")
			query = "insert into crm_commands(" + vSetParams + ") values(" + vSetValues + ")"
			cursor.execute(query)
			query = r"SELECT @@IDENTITY AS 'Identity'"
			cursor.execute(query)
			row = cursor.fetchone()
			id_command = row[0]
			if (needExportCl):
				if not(partner):
					res_obj = self.pool.get("res.partner")
					partner = res_obj.browse(cr, uid, int(vals["CRM_ID"]))
				server.export_res_partner(partner, id_command, "idCommand", cursor, False)
			if IsCF and partner:
				param = self.export_param_obj_cont_pers
				#Если не задано ФИО мы должны выгрузить name объекта в фамилию, вот такая блин херня
				if not(partner.firstname) and not(partner.surname) and not(partner.patronymic):
					param.pop("surname") 
					param.pop("firstname")
					param.pop("patronymic")
					param.update({"name":{"Field": "Surname", "IsStr": True},})
				self.export_res_partner(partner, id_cl, "ClientID", cursor, False, False, [], "ClientContact", param)
			if NeedCommit:
				connection.commit()
		except Exception, e:
			raise osv.except_osv(_("Send commands failed!"), _("Here is what we got instead:\n %s.") %tools.ustr(e))
		finally:
			if connection and NeedCommit:
				connection.close()
			return id_command

	#Формируем пустую строку клиента, что бы связать команду и контактное лица
	def form_query(self, cr, uid, ids,cursor):
		query = "insert into ClientCard (Name) values (NULL)"
		cursor.execute(query)
		query = r"SELECT @@IDENTITY AS 'Identity'"
		id_client = cursor.execute(query).fetchone()[0]
		return id_client
		
	#Метод для планировщика - считывание команд из NAV
	def _import_command(self, cr, uid, ids=False, context=None):
		server = self.findObject(cr, uid, "crm.iml.sqlserver", [("exchange_type", 'in', ["commands_nav"])])
		if (server):
			server.perform_import()

	# словарь, где хранится соответсвие тип обмена - обработчик
	exchange_types = { 
				"partner" : partner_import,
				"holdings": holdings_import,
				"commands_nav": commands_import_from_nav,
				"commands_cf": commands_import_from_cf,
				"responsible": responsible_import,
				'user': user_import,
	}

	# развилка в импорте, метод - роутер
	# в данном методе принимаем решение, какой импорт дальше запускать
	def perform_import(self, cr, uid, ids, context=None):
		for exchange_proc in self.browse(cr, uid, ids, context=context):
			self.exchange_types[exchange_proc.exchange_type](self, cr, uid, ids, context);