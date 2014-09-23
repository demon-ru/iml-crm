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
			NavUNC - id в NAV
			conectuion - подключение к БД
			MakeCommit - делать коммит и закрывать ли подключение или это промежуточная запись
	"""
	def insert_record(self, customerID, NavUNC=None, conection=None, MakeCommit=True):
		try:
			if (conection is None): 
				conection = self.connectToServer()
			cursor = conection.cursor()
			wherePart = ""
			if not(NavUNC is None):
				wherePart = unicode(" where nav_unc = '" + str(NavUNC) + "'", "utf-8")				
			else:
				wherePart = " where crm_id = " + str(customerID) 
			query = "select crm_id from " + self.tableName + wherePart
			cursor.execute(query)
			data = cursor.fetchone()
			if ((data == None) and (NavUNC is None)) :
				query = "INSERT into " + self.tableName + " (crm_id) values (" + str(customerID) +")"
			elif not(data == None):
				query = "update " + self.tableName + " set crm_id = " + str(customerID) + wherePart
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

	def findObject(self, cr, uid, classObj, searchField, searchVal):
		res_obj = self.pool.get(classObj)
		cur_obj = None
		res_id = res_obj.search(cr, uid, [(searchField, 'in', [searchVal])], context=None)
		if len(res_id) > 0:
			cur_obj = res_obj.browse(cr, uid, res_id[0])
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
			vDateAccount = row[33].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
		vRegDate = None
		if (row[35]):
			vRegDate = row[35].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
		vGoodsCategoryID = None
		if (row[5]):
			vGoodsCategory = self.findObject(cr, uid,"crm.goodscategory", 'nav_id', row[5])
			if (vGoodsCategory):
				vGoodsCategoryID = vGoodsCategory.id 
		vStorageShipID = None
		if (row[6]):
			vStorageShip = self.findObject(cr, uid,"crm.shipping_storage", 'nav_id', row[6])
			if (vStorageShip):
				vStorageShipID = vStorageShip.id 
		vType = None
		if (row[30]):
			if (row[30] == "Физ. лицо"):
				vType = "individual"
			elif (row[30] == "Юр. лицо"):
				vType = "legal_entity"
		vDoverenostDate = None
		if (row[13]):
			vDoverenostDate = row[13].strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
		vals = {
			#Информация о клиенте
			"name":	row[1],		
			"short_name": row[1],
			"NavUIN": row[2],
			"is_company": True,
			"internet_shop_name": row[3],
			"website": row[4],
			#Вкладка Основная
			"fio_authorized person_nominative_case": row[8],
			"fio_authorized person_genitive_case": row[9],
			"authorized_person_position_nominative_case": row[10], 
			"authorized_person_position_genetive_case": row[11],
			#Юридический адрес
			"juridical_address_index": row[14],
			"juridical_address_city_name": row[15],
			"juridical_address_street_name": row[16],
			"juridical_address_dom": row[17],
			"juridical_address_building": row[18],
			"juridical_address_office": row[19],
			"actual_address_index": row[20],
			#Фактический адрес
			"actual_address_city_name": row[21],
			"actual_address_street_name": row[22],
			"actual_address_dom": row[23],
			"actual_address_building": row[24],
			"actual_address_office": row[25],
			"account_number": row[26],
			#Банк
			"BIN": row[27],
			"bank_name": row[28],
			#Коды
			"correspondent_account_number": row[29],
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
			#Не понимаю что делать с категорией товара
			#"category_of_goods" : vGoodsCategoryID,
			"storage_of_shipping": vStorageShipID,
			"type_of_counterparty": vType,
			#Это просто доверенность :)
			"number_of_powerOfattorney": row[12],
			"date_of_powerOfattorney": vDoverenostDate,
			}
		if not(row[0] is None):
			res_id = res_obj.search(cr, uid, [("id", 'in', [int(row[0])])], context=None)
			if len(res_id) > 0:
				cur_obj = res_obj.browse(cr, uid, res_id[0])
				cur_obj.write(vals)
		else:
			cur_obj = self.pool.get('res.partner')
			cur_obj = res_obj.browse(cr, uid, cur_obj.create(cr, uid, vals, context=None))
		return cur_obj
	
	"""	
		Импорт из промежуточной базы в crm
	"""
	"""
		К сожалению после select запроса выгружается в массив и к полям нужно обращатся по номерам:
			crm_id - id - 0
			CustomerName - name - 1
			NAV_UNC - NavUIN - 2
			ShopName - internet_shop_name - 3
			WebSite - 4 - website
			GoodsCategory_ID - category_of_goods - 5
			Warehouse_ID - storage_of_shipping - 6
			Region_ID - 7
			RespPerson - fio_authorized person_nominative_case - 8
			RespPersonWhom - fio_authorized person_genitive_case - 9
			RespPersonPosition - authorized_person_position_nominative_case - 10
			RespPersonPositionWhom - authorized_person_position_genetive_case - 11
			LoA_Number - number_of_powerOfattorney - 12 
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
				query = "select crm_id, customername, nav_unc, ShopName, WebSite, GoodsCategory_ID, Warehouse_ID, Region_ID, RespPerson, RespPersonWhom, RespPersonPosition, RespPersonPositionWhom, LoA_Number, LoA_Date, AddrZIP, AddrSity, AddrStreet, AddrBuilding, AddrBuilding2, AddrOffice, LocAddrZIP, LocAddrSity, LocAddrStreet, LocAddrBuilding, LocAddrBuilding2, LocAddrOffice, AccountNo, BIC, BankName, CorrAccountNo, PartnerType, ITN, TRRC, TRDate, OGRN, RegistrationDate, OCVED, OCPO, OCATO  from " + server.tableName + wherePart
				cursor.execute(query)
				for row in cursor.fetchall():
					cur_obj = server.createOrFindResPartner(row)
					if (cur_obj is None):
						#TODO Сделать логирование импорта
						sys.stdout.write("ERROR! Not found client in system with id =" + row[0])
					if (row[0] is None) and not(row[2] is None): 
						server.insert_record(cur_obj.id, row[2], conection, False);
				conection.commit()
		except Exception, e:
			raise osv.except_osv(_("Import failed!"), _("Here is what we got instead:\n %s.") %tools.ustr(e))
		finally:
			if conection:
				conection.close();
		server.write({'lastImportDate': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
	 	return True

 
					

			




