﻿# -*- coding: utf-8 -*-
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
import sys, os
import hashlib
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'crm'))
import crm
import json
from crm_iml_html import html2plaintextWithoutLinks  
from datetime import datetime
from operator import itemgetter

import openerp
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools import html2plaintext
from openerp.addons.base.res.res_partner import format_address
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from openerp.tools import email_re

class crm_lead(format_address, osv.osv):

	_inherit = 'crm.lead'
	_name = "crm.lead"

	_columns = {
		'type_of_opport_id' : fields.many2one('crm.iml.opportunities.type', 'Type of opportunities'),
		'function': fields.char('Должность'),
		'creating_partner': fields.many2one('res.partner', 'Creating partner'),
		"data_arraved" : fields.boolean("Data arraved"),
	}
	_defaults = {
		"data_arraved": False,
	}
	def parse_json(self,description):
		stringText = ''
		stringText = description.replace('\r\n', '\n')
		stringText = description.replace('\r', '\n')
		stringText = stringText.replace('\n', ' ')
		stringText = stringText.replace('" ', '"')
		stringText = stringText.replace(' "', '"')
		indexBeginJSON = stringText.rfind('{')
		indexEndJSON = stringText.rfind('}')
		strJSON = ''
		if (indexBeginJSON > -1 and indexEndJSON > -1):         
			strJSON = stringText[indexBeginJSON : indexEndJSON + 1]
		if strJSON != '':
	   	     aObj = json.loads(strJSON)
		return aObj
    
	def findOrCreateObject(self, cr, uid, context, classObj, searchField, searchVal, vals):
		res_obj = self.pool.get(classObj)
		res_id = res_obj.search(cr, uid, [(searchField, 'in', [searchVal])], context=context)
		if len(res_id) > 0:
			cur_obj = res_obj.browse(cr, uid, res_id[0])
		else:
			cur_obj = self.pool.get(classObj)
			cur_obj = res_obj.browse(cr, uid, cur_obj.create(cr, uid, vals, context=context))
		return cur_obj

	def replaceBadQuotes(self, text):
		""" 
			Replace quotes in different coding on &quot
		"""
		text = text.replace('&#8216', '&#8221')
		text = text.replace('&#8217', '&#8221')
		text = text.replace('&#8220', '&#8221')
		text = text.replace('&#8220', '&#8221')
		text = text.replace('&#8222', '&#8221')
		text = text.replace('&#171', '&#8221')
		text = text.replace('&#187', '&#8221')
		text = text.replace('&laquo', '&#8221')
		text = text.replace('&raquo', '&#8221')
		text = text.replace('&#8221', '&quot')
		return text

	def message_new(self, cr, uid, msg, custom_values=None, context=None):
		""" Overrides mail_thread message_new that is called by the mailgateway
			through message_process.
			This override updates the document according to the email.
		"""
		if msg.get('body'):
			aMailBody = html2plaintextWithoutLinks(self.replaceBadQuotes(msg.get('body'))) 
		else: 	
			aMailBody = ""
		aObj = self.parse_json(aMailBody)
		if custom_values is None:
			custom_values = {}
		vPhone = ''
		if 'phone' in aObj:  
			vPhone = aObj['phone']
		vEmail = ''
		if 'email' in aObj: 
			vEmail = aObj['email'].replace(" ", "")
		vName = aObj['name']
		vals_obj = {'name': vName,
				    'phone': vPhone,
				    'email': vEmail}
		if vName != '':	 
			partner = self.findOrCreateObject(cr, uid, context, 'res.partner', 'name', vName, vals_obj)
		vType = ""
		if 'type' in aObj:
			vType = aObj['type']
		vTypeID = 0
		if (vType != ""):
			vals_obj = {'name': vType}
			vTypeObj = self.findOrCreateObject(cr, uid, context, 'crm.iml.opportunities.type', 'name', vType, vals_obj)	
			vTypeID = vTypeObj.id
		defaults = {
				'name':  msg.get('subject') or _("No Subject"),
				'email_from': vEmail,
				'email_cc': vEmail,
				'partner_id': partner.id,
				'phone': vPhone or "",
				'type': 'opportunity',
				'user_id': False,
				'type_of_opport_id': vTypeID, 
			}     
		if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
			defaults['priority'] = msg.get('priority')
		defaults.update(custom_values)
		return super(crm_lead, self).message_new(cr, uid, msg, custom_values=defaults, context=context)	

	def apply_data(self,cr, uid, ids, context=None):
		res_obj = self.pool.get("crm.iml.sqlserver")
		res_id = res_obj.search(cr, uid, [("exchange_type", 'in', ["commands"])], context=context)
		server = None
		if len(res_id) > 0:
			server = res_obj.browse(cr, uid, res_id[0])
		else:
			raise osv.except_osv(_("Нельзя поддтвердить данные!"), _("Не задана таблица для обмена команд. Обратитесь к администратору."))	
		for opport in self.browse(cr, uid, ids, context=context):
			partn = opport.creating_partner
			server.processCommand(partn, "UpdateCustomerData", opport)
			opport.write({"data_arraved": False})


	def send_customers_form(self,cr, uid, ids, context=None):
		vals = {}
		cur_obj = None
		my_hash = ""
		ret_vals = {'return':True,}
		res_obj = None
		for opport in self.browse(cr, uid, ids, context=context):
			# Если не задан созданный по заявке клиент, то мы выгружаем строчку в промежуточную БД
			vNeedExport = True
			if opport.creating_partner:
				vNeedExport = False
		    # Ищем таблицу для обмена команд, если не находим прерываем процесс
			res_obj = self.pool.get("crm.iml.sqlserver")
			res_id = res_obj.search(cr, uid, [("exchange_type", 'in', ["commands"])], context=context)
			server = None
			if len(res_id) > 0:
				server = res_obj.browse(cr, uid, res_id[0])
			else:
				raise osv.except_osv(_("Нельзя отправить бланк клиенту!"), _("Не задана таблица для обмена команд. Обратитесь к администратору."))
		    #Если нет почты неизвестно куда посылать бланк, прерываем процесс
			if not(opport.email_from):
				raise osv.except_osv(_("Нельзя отправить бланк клиенту!"), _("Не задана электронная почта заказчика"))
			#Генерация клиента, пока фиктивного и неактивного
			if (opport.partner_name):
				vals = {
					'name': opport.partner_name,
				}
			else:
				vals = {
					'name': unicode("Заявка от ", "utf-8") + opport.contact_name or _(opport.email_from),
				}
			vals.update({"active": False})
			res_obj = self.pool.get("res.partner")
			if not(opport.creating_partner):
				cur_obj = self.pool.get("res.partner")
				cur_obj = res_obj.browse(cr, uid, cur_obj.create(cr, uid, vals, context=None))
			else:
				cur_obj = opport.creating_partner
			#Создаем контактное лицо, если оно еще не создано
			vals_contact = {}
			contact = None
			if (opport.partner_id):
				contact = opport.partner_id
			else:
				contact = self.pool.get("res.partner")
				contact = res_obj.browse(cr, uid, contact.create(cr, uid, {"name": opport.contact_name  or _(opport.email_from)}, context=None))
			contact.write({"email": opport.email_from,
				"phone": opport.phone,
				"function": opport.function,
				"mobile": opport.mobile,
				"fax": opport.fax,
			})
			vals_contact = {
				"child_ids": [(4, contact.id)]
			}
			opport.write({"partner_id" : contact.id,
				"creating_partner": cur_obj.id})
			if (vals_contact != {}):
				cur_obj.write(vals_contact)
			#Генерим хэш
			m = hashlib.md5(str(cur_obj.id))
			my_hash = m.hexdigest();
			print "==================="
			print cur_obj.name
			print "==-==-==-==-==-==-==-"
			#Создаем команду для записи
			vals = {}
			vals = {
				"Source": "crm",
				"Dest": "cf",
				"Command": "UpdateCustomerData",
				"CRM_ID": unicode(str(cur_obj.id), "utf-8"),
				"External_ID": unicode(my_hash, "utf-8"),
			}
			server.commands_exchange(vals, vNeedExport, cur_obj)
			#Открываем диалог с письмом
			URL = "http://iml.oe-it.ru/cli/" + my_hash
			model_data = self.pool.get("ir.model.data")
       		# Get res_partner views
			dummy, form_view = model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')
			vals_mess = {
				"subject": "Карточка клиента",
				"body": URL,
				"partner_ids": [(4, contact.id)],
				"model": "crm.lead",
				"res_id": opport.id,
			}
			res_obj = self.pool.get("mail.compose.message")
			mess = self.pool.get("mail.compose.message")
			mess = res_obj.browse(cr, uid, mess.create(cr, uid, vals_mess, context=None))
			ret_vals = {
				'return':True,
				'view_mode': 'form',
				'view_id': "mail.email_compose_message_wizard_form",
				'views': [(form_view or False,'form')],
				'view_type': 'form',
				'nodestroy': True,
				'res_model': 'mail.compose.message',
				'type': 'ir.actions.act_window',
				'res_id' : mess.id,
				'target': 'new'
        	}
        	opport.write({"data_arraved": True})
		return ret_vals
