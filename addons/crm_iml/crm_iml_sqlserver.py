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
		'tableName' : fields.char('Table name', size=255),

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
			db = MySQLdb.connect(self.server, self.user, 
			  self.password, self.dbname, charset="utf8", use_unicode=True)
		except Exception, e:
			raise osv.except_osv(_("Connection failed!"), _("Here is what we got instead:\n %s.") % 					  tools.ustr(e))
		return db
			
	"""	
		Teстовое подключение  к БД
	"""
	def test_iml_crm_sql_server(self,cr, uid, ids, context=None):	
		db = None;	
		try:
			for server in self.browse(cr, uid, ids, context=context):
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
		'lastTestDate': fields.datetime('Date last successful test connect' , readonly=True),
		'lastImportDate': fields.datetime('Date last successful import' , readonly=True),
		'name': fields.char('Name', size=128, required=True),	
		'server': fields.char('SQL Server', size=128, required=True),
		'user': fields.char('User', size=128, required=True),
		'password': fields.char('Password', size=128),
		'dbname': fields.char('Database name', size=128),
		'tableName':fields.char('Table Name', size=128),
		'exchange_type':fields.selection([('partner', 'Partner exchange'), ('holdings', 'Holdings exchange')], 'Exchange type'),
	}

	"""
		Создает подключение к серверу
	"""
	def connectToServer(self):	
		db = None
		try:
			db = MySQLdb.connect(self.server, self.user, 
			  self.password, self.dbname, charset="utf8", use_unicode=True)
		except Exception, e:
			raise osv.except_osv(_("Connection failed!"), _("Here is what we got instead:\n %s.") % 					  tools.ustr(e))
		return db
			
	"""	
		Teстовое подключение  к БД
	"""
	def test_iml_crm_sql_server(self,cr, uid, ids, context=None):	
		db = None;	
		try:
			for server in self.browse(cr, uid, ids, context=context):
				db = server.connectToServer();
		finally:
			if (db):
				db.close()
		server.write({'lastTestDate': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
		return True
	""" 
		Метод вставляет ID клиента в промежуточную базу
		Параметры
			customerID - id заказчика в crm
			IdImport - id в промежуточной базе
			conectuion - подключение к БД
			MakeCommit - делать коммит и закрывать ли подключение или это промежуточная запись
	"""
	def insert_record(self, customerID, IdImport=None, conection=None, MakeCommit=True):
		try:
			if (conection is None): 
				conection = self.connectToServer()
			cursor = conection.cursor()
			wherePart = ""
			if not(IdImport is None):
				wherePart = unicode(" where idimport = " + str(IdImport), "utf-8")				
			else:
				wherePart = " where crm_id = " + str(customerID) 
			query = "select crm_id from " + self.tableName + wherePart
			cursor.execute(query)
			data = cursor.fetchone()
			importdate = time.strftime('%Y-%m-%d %H:%M:%S')
			if ((data == None) and (IdImport is None)) :
				query = "INSERT into " + self.tableName + " (crm_id, CRM_TimeStamp) values (" + str(customerID) +", '" + importdate + "')"
			elif not(data == None):
				query = "update " + self.tableName + " set crm_id = " + str(customerID) + ", CRM_TimeStamp = '" + importdate + "' " + wherePart
			cursor.execute(query)
			if MakeCommit:
				conection.commit()
		except Exception, e:
			raise osv.except_osv(_("Export failed!"), _("Here is what we got instead:\n %s.") %tools.ustr(e))
			result = false
		finally:
			if ((conection) and (MakeCommit)):
				conection.close()
		return True
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
	
	"""
		Находит или создает клиента
		Параметры:
			row - запись из промежуточной базы 
	"""
	def createOrFindResPartner(self, cr, uid, row):
		cur_obj = None
		res_obj = self.pool.get('res.partner')
		vDateAccount = None
		if (row[33]):
			#Хак в случае если год в дате будет меньше 1900
			try:
				vDateAccount = row[33].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
			except ValueError:
				vDateAccount = None
		vRegDate = None
		if (row[35]):
			try:
				vRegDate = row[35].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
			except ValueError:
				vRegDate = None
		vRegion = None
		if (row[7]):
			if (row[7] == unicode("МСКРЦ", "utf-8")):
				vRegion = 'moscow'
			elif (row[7] == unicode("РЕГРЦ", "utf-8")):
				vRegion = 'regions'
		#Поиск склада 
		vStorageShipID = None
		if (row[6]):
			vStorageShip = self.findObject(cr, uid,"crm.shipping_storage", [('nav_id', "in", [row[6]])])
			if (vStorageShip):
				vStorageShipID = vStorageShip.id 
		#Поиск категории товара
		vCategoryOfGoodsID = None
		if (row[5]):
			vCategoryOfGoods = self.findObject(cr, uid,"crm.goodscategory", [('nav_id', "in", [row[5]])])
			if (vCategoryOfGoods):
				vCategoryOfGoodsID = vCategoryOfGoods.id 
		#Определение типа физ/юр лицо		
		vType = None
		if (row[30]):
			if (row[30] == unicode("Физ. лицо", "utf-8")):
				vType = "individual"
			elif (row[30] == unicode("Юр. лицо", "utf-8")):
				vType = "legal_entity"
		#Дата доверенности
		vDoverenostDate = None
		if (row[13]):
			try:
				vDoverenostDate = row[13].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
			except ValueError:
				vDoverenostDate = None
		#Поиск организационной формы компании
		vOrgTypeID = None
		if (row[46]):
			vOrgType = self.findObject(cr, uid,"crm.company_org_type", [('nav_id', "in", [row[46]])])
			if (vOrgType):
				vOrgTypeID = vOrgType.id 	
		vals = {
			#Информация о клиенте
			"name":	row[1],		
			"short_name": row[1],
			"unk": row[2],
			"is_company": True,
			"juridical_name": row[3],
			"website": row[4],
			#Вкладка Основная
			#'category_of_goods': row[5],
			#Юридический адрес
			"juridical_address_index": row[14],
			"juridical_address_city_name": row[15],
			"juridical_address_street_name": row[16],
			"juridical_address_dom": row[17],
			"juridical_address_building": row[18],
			"juridical_address_office": row[19],
			#Фактический адрес
			"actual_address_index": row[20],
			"actual_address_city_name": row[21],
			"actual_address_street_name": row[22],
			"actual_address_dom": row[23],
			"actual_address_building": row[24],
			"actual_address_office": row[25],
			#Коды
			"inn": row[31],
			"registration_reason_code": row[32],
			"OGRN_OGRNIP": row[34],
			"OKVED": row[36],
			"OKPO": row[37],
			"OKATO": row[38],
			#Даты
			"date_of_accounting": vDateAccount,
			"registration_date": vRegDate,
			#Ссылки на объекты
			"type_of_counterparty": vType,
			"company_org_type": vOrgTypeID,
			'category_of_goods' : vCategoryOfGoodsID,
			#Не стандартная часть адреса
			'actual_adress_non_stand_part': row[40],
			'juridical_adress_non_stand_part': row[41],
			}
		if not(row[0] is None):
			cur_obj = self.findObject(cr, uid,"res.partner", [('id',"in", [row[0]])])
			if cur_obj:
				cur_obj.write(vals)
		elif not(row[2] is None):
			cur_obj = self.findObject(cr, uid,"res.partner", [('unk',"in", [row[2]])])
			if cur_obj:
				cur_obj.write(vals)
		if (row[0] is None) and not(cur_obj):
			cur_obj = self.pool.get('res.partner')
			cur_obj = res_obj.browse(cr, uid, cur_obj.create(cr, uid, vals, context=None))
		#Если мы нашли или создали компанию - то пытаемся создать договор и контактное лицо
		if cur_obj:
			if row[39]:
				vStartDate = None
				if (row[47]):
					#Хак в случае если год в дате будет меньше 1900
					try:
						vStartDate = row[47].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
					except ValueError:
						vStartDate = None				
				#Атрибуты договора
				vals_add_obj = {
					'name': row[39],
					'crm_number': row[39],
					'partner_id': cur_obj.id,
					"fio_authorized person_nominative_case": row[8],
					"fio_authorized person_genitive_case": row[9],
					"authorized_person_position_nominative_case": row[10], 
					"authorized_person_position_genetive_case": row[11],
					'region_of_delivery': vRegion,
					"storage_of_shipping": vStorageShipID,
					"number_of_powerOfattorney": row[12],
					"date_of_powerOfattorney": vDoverenostDate,
					"date_start": vStartDate,
				}
				self.findObject(cr, uid,"account.analytic.account", ['&',('crm_number',"in", [row[39]]),('partner_id', 'in',[cur_obj.id])], True, vals_add_obj, True)			
			if row[42]:			
				vals_add_obj = {
					"name": row[42],
					"email": row[43],
					"phone": row[44],
					'parent_id': cur_obj.id
				}
				self.findObject(cr, uid,'res.partner', ["&",('name', 'in' ,[row[42]]),"&",('parent_id', 'in', [cur_obj.id]),("is_company", '=', False)], True, vals_add_obj, True)			
		return cur_obj
	
	"""	
		Импорт из промежуточной базы в crm
	"""
	"""
		К сожалению после select запроса выгружается в массив и к полям нужно обращатся по номерам:
			crm_id - id - 0
			CustomerName - name - 1
			NAV_UNC - unk - 2
			ShopName - internet_shop_name - 3
			WebSite - 4 - website
			GoodsCategory - category_of_goods - 5
			Warehouse_ID - storage_of_shipping - 6
			Region_ID - region_of_delivery - 7
			RespPerson - fio_authorized person_nominative_case - 8
			RespPersonWhom - fio_authorized person_genitive_case - 9
			RespPersonPosition - authorized_person_position_nominative_case - 10
			RespPersonPositionWhom - authorized_person_position_genetive_case - 11
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
			BIC - BIN - 27
			BankName - bank_name - 28
			CorrAccountNo - correspondent_account_number - 29
			PartnerType - type_of_counterparty - 30
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
"""
	def import_records(self,cr, uid, ids, context=None):
		conection = None
		try:
			for server in self.browse(cr, uid, ids, context=context):
				conection = server.connectToServer();
				cursor = conection.cursor()
				wherePart = ''
				if (server.lastImportDate): 
					wherePart = " where nav_timestamp >'" + str(server.lastImportDate) + "'"
				query = "select crm_id, customername, nav_unc, ShopName, WebSite, GoodsCategory, Warehouse_ID, Region_ID, RespPerson, RespPersonWhom, RespPersonPosition, RespPersonPositionWhom, LoA_Number, LoA_Date, AddrZIP, AddrSity, AddrStreet, AddrBuilding, AddrBuilding2, AddrOffice, LocAddrZIP, LocAddrSity, LocAddrStreet, LocAddrBuilding, LocAddrBuilding2, LocAddrOffice, AccountNo, BIC, BankName, CorrAccountNo, PartnerType, ITN, TRRC, TRDate, OGRN, RegistrationDate, OCVED, OCPO, OCATO, AgreementNo, FactAdrStr, JurAdrStr, Contact, Email, Phone, idimport, CompOrgTypeID, AgreementDate from " + server.tableName + wherePart
				cursor.execute(query)
				for row in cursor.fetchall():
					cur_obj = server.createOrFindResPartner(row)
					if (cur_obj is None):
						#TODO Сделать логирование импорта
						sys.stdout.write("ERROR! Not found client in system with id =" + str(row[0]))
					if not(cur_obj is None) and (row[0] is None) and not(row[45] is None): 
						server.insert_record(cur_obj.id, row[45], conection, False);
				conection.commit()
		except Exception, e:
			raise osv.except_osv(_("Import failed!"), _("Here is what we got instead:\n %s.") %tools.ustr(e))
		finally:
			if conection:
				conection.close();
		server.write({'lastImportDate': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
	 	return True

 
					

			




