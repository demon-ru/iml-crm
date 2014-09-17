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

from openerp.osv import fields,osv,orm
from openerp import tools, api
from openerp.tools.translate import _

class crm_iml_sqlserver(osv.osv):
	_name = "crm.iml.sqlserver"
	_description = "Sql server for export/import data from OpenErp to my sql database"
	_columns = {
		'lastTestDate': fields.datetime('Date last successful test connect' , readonly=True),
		'name': fields.char('mysqlservername', size=128, required=True),	
		'server': fields.char('SQLServer', size=128, required=True, help='The sql server.'),
		'user': fields.char('SQLUser', size=128, required=True),
		'password': fields.char('SQLPass', size=128),
		'dbname': fields.char('SqlDbName', size=128),
		'tableName':fields.char('SqlTableName', size=128),
		'IdColumnName':fields.char('SqlIdColumn', size=128)  
	}

	def test_iml_crm_sql_server(self,cr, uid, ids, context=None):	
		db = None;	
		for server in self.browse(cr, uid, ids, context=context):
			try:
				db = MySQLdb.connect(host=server.server, user=server.user, 
				  passwd=server.password, db=server.dbname)
			except Exception, e:
				raise osv.except_osv(_("Connection test failed!"), _("Here is what we got instead:\n %s.") % 					  tools.ustr(e))
			finally:
				if (db):
					db.close()
			server.write({'lastTestDate': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
		return True

	def insert_record(self,cr, uid, ids, server, customerID):
		conection = None
		result = True
		try:
			conection = MySQLdb.connect(host=server.server, user=server.user, 
				  passwd=server.password, db=server.dbname)
			cursor = conection.cursor()
			query = "select " + server.IdColumnName + " from " + server.tableName + " where " + server.IdColumnName + " = '" + str(customerID) + "'"
			cursor.execute(query)
			data = cursor.fetchone()
			if data == None :
				query = "INSERT into " + server.tableName + " (" + server.IdColumnName + ") values ('" + str(customerID) +"')"
			else:
				query = "update " + server.tableName + " set " + server.IdColumnName + "= '" + str(customerID) +"' where " + server.IdColumnName + " = " + str(customerID)
			cursor.execute(query)
			conection.commit()
		except Exception, e:
			raise osv.except_osv(_("Export failed!"), _("Here is what we got instead:\n %s.") %tools.ustr(e))
			result = false
		finally:
			if (conection):
				conection.close()
		return result




