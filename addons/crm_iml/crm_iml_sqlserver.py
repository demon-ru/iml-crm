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
import chardet

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
		'lastImportDate': fields.datetime('Date last successful import' , readonly=True),
		'name': fields.char('Name', size=128, required=True),
		'lastTestDate': fields.datetime('Date last successful test connect' , readonly=True),
		'tableName':fields.char('Table Name', size=128),
		'exchange_type':fields.selection([('partner', 'Partner exchange'), ('holdings', 'Holdings exchange'), ('commands', 'Commands exchange')], 'Exchange type', required=True),
		'exchange_server':fields.many2one('crm.iml.exchange_server_settings', 'name'),
	}
			
	"""	
		Teстовое подключение  к БД
	"""
	def test_iml_crm_sql_server(self,cr, uid, ids, context=None):	
		db = None;	
		try:
			for server in self.browse(cr, uid, ids, context=context):
				db = server.exchange_server.connectToServer();
		finally:
			if (db):
				db.close()
		server.write({'lastTestDate': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
		return True
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
				conection = self.exchange_server.connectToServer()
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
			vStorageShip = self.findObject(cr, uid,"crm.shipping_storage", [('nav_id', "in", [str(row[6])])])
			if (vStorageShip):
				vStorageShipID = vStorageShip.id 
		#Поиск категории товара
		vCategoryOfGoodsID = None
		if (row[5]):
			vCategoryOfGoods = self.findObject(cr, uid, "crm.goodscategory", [('nav_id', "in", [str(row[5])])])
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
			vOrgType = self.findObject(cr, uid,"crm.company_org_type", [('nav_id', "in", [str(row[46])])])
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
			"active": True,
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
			#'nav_holdingId' : row[48],
			}
		if not(row[0] is None):
			res_obj = self.pool.get("res.partner")
			cur_obj = res_obj.browse(cr, uid, int(row[0]))
			if cur_obj:
				cur_obj.write(vals)
		elif not(row[2] is None):
			cur_obj = self.findObject(cr, uid,"res.partner", [('unk',"in", [str(row[2])])])
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
				self.findObject(cr, uid,"account.analytic.account", ['&',('crm_number',"in", [str(row[39])]),('partner_id', 'in',[cur_obj.id])], True, vals_add_obj, True)			
			if row[42]:			
				vals_add_obj = {
					"name": row[42],
					"email": row[43],
					"phone": row[44],
					'parent_id': cur_obj.id
				}
				self.findObject(cr, uid,'res.partner', ["&",('name', 'in' ,[str(row[42])]),"&",('parent_id', 'in', [cur_obj.id]),("is_company", '=', False)], True, vals_add_obj, True)			
		return cur_obj

	def getQuery_partner(self):
		#TODO Сделать запрос просто собираемым
		query = "select crm_id, customername, nav_unc, ShopName, WebSite, GoodsCategory, Warehouse_ID, Region_ID, RespPerson, RespPersonWhom, RespPersonPosition, RespPersonPositionWhom, LoA_Number, LoA_Date, AddrZIP, AddrSity, AddrStreet, AddrBuilding, AddrBuilding2, AddrOffice, LocAddrZIP, LocAddrSity, LocAddrStreet, LocAddrBuilding, LocAddrBuilding2, LocAddrOffice, AccountNo, BIC, BankName, CorrAccountNo, PartnerType, ITN, TRRC, TRDate, OGRN, RegistrationDate, OCVED, OCPO, OCATO, AgreementNo, FactAdrStr, JurAdrStr, Contact, Email, Phone, idimport, CompOrgTypeID, AgreementDate from " + self.tableName
		return query

	"""	
		Импорт из промежуточной базы в crm
	"""
	"""
		К сожалению после select запроса выгружается в массив и к полям нужно обращатся по номерам:
			crm_id - id - 0
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
			???_ид_холдинга - идентификатор холдинга у клиента - 48
"""

		
	# здесь объявляем обработчики


	def partner_import(self,cr, uid, ids, context=None):
		conection = None
		try:
			for server in self.browse(cr, uid, ids, context=context):
				exchange_server = server.exchange_server
				conection = exchange_server.connectToServer()
				cursor = conection.cursor()
				wherePart = ''
				if (server.lastImportDate): 
					wherePart = " where nav_timestamp >'" + str(server.lastImportDate) + "'"
				query = server.getQuery_partner() + wherePart
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


	def holdings_import(self, cr, uid, ids, context=None):
		try:
			# сперва найдем все холдинги
			for server in self.browse(cr, uid, ids, context=context):
				exchange_server = server.exchange_server
				connection = exchange_server.connectToServer()
				cursor=connection.cursor()
				# будем выбирать только те записи, которые созданы после предидущего импорта
				if (server.lastImportDate):
					wherePart = "where nav_timestamp > '" + str(server.lastImportDate) + "'"
				# название столбцов до конца не известно, пока для информации
				query = "select holding_id, holding_name from " + server.tableName + " " + wherePart
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
						"holdingId" : row[48],
					}
					holding = self.findObject(cr, uid,'res.partner', ["&",('holdingId', 'in' ,[row[48]]),("is_company", '=', True)], True, vals_add_obj, False)
					# находим клиентов, у которых nav_holdingId = ид холдинга
					res_partner_obj = self.pool.get('res.partner')
					res_partner_ids = res_partner_obj.search(cr, uid, [('nav_holdingId', 'in', holding.holdingId)], context=context)
					res_partner = res_partner_obj.browse(cr, uid, res_partner_ids)
		            # итерируем отобранных клиентов и устанавливаем им в качестве parent_id id холдинга
					for partner in res_partner:
						partner.parent_id = holding
		except Exception, e:
			raise osv.except_osv(_("Import failed!"), _("Here is what we got instead:\n %s.") %tools.ustr(e))
		finally:
			if connection:
				connection.close();
	 	write("ok")


	var_field = {
		"CRM_ID": 0,
		"External_ID": 1,
		"Source": 2,
		"Dest" : 3,
		"Command": 4,
		"id": 5,
	}

	def commands_import(self, cr, uid, ids, context=None):
		connection = None
		try:
			for server in self.browse(cr, uid, ids, context=context):
				vFieldParam = ""
				for key in vals:
					if (vFieldParam == ""):
						vFieldParam = key
					else:
						vFieldParam = vFieldParam + ", " + key 
				query = "select  " + vFieldParam + " from " + server.tableName.encode("ascii") + " where DoneTime is null and Dest = 'crm'"
				connection = server.exchange_server.connectToServer()
				cursor=connection.cursor()
				cursor.execute(query)
				for row in cursor.fetchall():
					partner_id = row[var_field["CRM_ID"]]
					res_obj = self.pool.get('res.partner')
					partn = res_obj.browse(cr, uid, partner_id)
					command = row[var_field["Command"]]
					server.processCommand(partn, command, None, var)
		except Exception, e:
			raise osv.except_osv(_("Send commands failed!"), _("Here is what we got instead:\n %s.") %tools.ustr(e))
		finally:
			if connection:
				connection.close()

	def processCommand(self, cr, uid, ids, partner, command, opport=None, added_var=None):
		connection = None
		comm_connection = None
		for server in self.browse(cr, uid, ids, context=None):
			if not(opport):
				opport = self.findObject(cr, uid, 'crm.lead', [('creating_partner','=', partner_id)])
			server_res_partner = self.findObject(cr, uid, "crm.iml.sqlserver", [("exchange_type", 'in', ["partner"])]) 
			if not(server_res_partner):
				sys.stdout.write("ERROR! Пожалуйста настройте таблицу для экспорта/импорта клиентов!")
			query = server_res_partner.getQuery_partner()
			wherePart = ""
			if (command == "UpdateCustomerData"):
				wherePart = " where CRM_ID=" + str(partner.id)
			elif (command == "UpdatedUNC"):
				if (added_var):
					unc = added_var[var_field["External_ID"]]
					wherePart = " where NAV_UNC = " + unc.encode(utf-8) + " and CRM_TimeStamp is null"
			if (wherePart != ""):
				try:
					query = query + wherePart
					connection = server_res_partner.exchange_server.connectToServer()
					comm_connection = server.exchange_server.connectToServer()
					cursor_for_command = comm_connection.cursor()
					cursor=connection.cursor()
					cursor.execute(query)
					for row_part in cursor.fetchall():
						cur_obj = server_res_partner.createOrFindResPartner(row_part)
						if (cur_obj is None):
							#TODO Сделать логирование импорта
							sys.stdout.write("ERROR! Not found client in system with id =" + str(row_part[0]))
						if not(cur_obj is None) and not(row_part[45] is None): 
							server_res_partner.insert_record(cur_obj.id, row_part[45], connection, False);
						if (cur_obj):
							query_command = "update " + server.tableName.encode("ascii") + " set DoneTime = '" + time.strftime('%Y-%m-%d %H:%M:%S') + "' where CRM_ID= " + str(row_part[0]) + " and Command= '" + command + "' and DoneTime is null" 
							print "==========================="
							print query_command
							print "============================"
							cursor_for_command.execute(query_command)
					connection.commit()
					comm_connection.commit()
				finally:
					if (connection):
						connection.close()
					if (comm_connection):
						comm_connection.close()


	def addCondition(self,valueCond, stringCond, KeyValue=None, isStr=False, isDate=False):
		#Перечисление полей, которые являются строкой 
		vStrFields = {
			"External_ID": True,
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

	#Обмен командами с системой
	def commands_exchange(self, cr, uid, ids, vals, needExportCl, partner=None):
		connection = None
		try:
			for server in self.browse(cr, uid, ids, context=None):
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
				"commands": commands_import,
		}

	# развилка в импорте, метод - роутер
	# в данном методе принимаем решение, какой импорт дальше запускать
	# 
	def perform_import(self, cr, uid, ids, context=None):
		for exchange_proc in self.browse(cr, uid, ids, context=context):
			self.exchange_types[exchange_proc.exchange_type](self, cr, uid, ids, context);