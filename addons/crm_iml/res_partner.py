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
import time
import crm_iml_sqlserver

from openerp.osv import fields,osv
from openerp import tools, api
from openerp.tools.translate import _

class res_partner(osv.osv):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = 'res.partner'

    _columns = {
	'categoryClient_id': fields.many2one('crm.clientcategory', 'name'),
	'exportDateToNAV': fields.datetime('crm.iml.export.date.res.partner' , readonly=True),
	'NavUIN': fields.char('crm.iml.nav.uin' , size=512, readonly=True),
    }
    def iml_crm_export_id(self,cr, uid, ids, context=None):
	for partn in self.browse(cr, uid, ids, context=context):
		params = self.pool.get('ir.config_parameter')
		serv = int(params.get_param(cr, uid, 'crm_iml_export_server_id',default='0' ,context=context))
		res_obj = self.pool.get('crm.iml.sqlserver')
		server = res_obj.browse(cr, uid, serv)
		if not(server):
			raise osv.except_osv(('Warning!'), ("Export SQL Server is not specified. Set Export/Import SQL server in General settings!"))
	 	result = server.insert_record(server, partn.id)
		if (result):
			partn.write({'exportDateToNAV': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
	return True

