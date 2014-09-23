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
		'name': fields.char('mysqlservername', size=128, required=True),	
		'server': fields.char('SQLServer', size=128, required=True),
		'user': fields.char('SQLUser', size=128, required=True),
		'password': fields.char('SQLPass', size=128),
		'dbname': fields.char('SqlDbName', size=128),
		'tableName':fields.char('SqlTableName', size=128),
	}

	"""
		Создает подключение к серверу
	"""
	def connectToServer(self):	
		db = None
		try:
			db = MySQLdb.connect(self.server, self.user, 
			 self.password, self.dbname)
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
				wherePart = " where nav_unc = '" + str(NavUNC) + "'"				
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
	
	"""
		Находит или создает клиента
		Параметры:
			row - запись из промежуточной базы 
	"""
	def createOrFindResPartner(self, cr, uid, row):
		cur_obj = None
		res_obj = self.pool.get('res.partner')
		vals = {"name": row[1],
			"NavUIN": row[2],
			"is_company": True,}
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
	def import_records(self,cr, uid, ids, context=None):
		conection = None
		try:
			for server in self.browse(cr, uid, ids, context=context):
				conection = server.connectToServer();
				cursor = conection.cursor()
				wherePart = ''
				print "-------------------------------------------------"
				print str(time.strptime(server.lastImportDate, "%Y-%m-%d %H:%M:%S"))
				print "-------------------------------------------------"
				if (server.lastImportDate): 
					wherePart = " where nav_timestamp >'" + str(time.strptime(server.lastImportDate, "%Y-%m-%d %H:%M:%S")) + "'"
				query = "select crm_id, customername, nav_unc from " + server.tableName + wherePart
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

 
					

			




