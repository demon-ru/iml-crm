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

from openerp.addons.website.models import website
from openerp.addons.web import http
from openerp.http import request

import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers

class crm_lead(format_address, osv.osv):

	_inherit = 'crm.lead'

	def on_change_user(self, cr, uid, ids, user_id, context=None):
		""" When changing the user, also set a section_id or restrict section id
			to the ones user_id is member of. """
		#section_id = self._get_default_section_id(cr, uid, context=context) or False
		#if user_id and not section_id:
		section_id = None
		section_ids = self.pool.get('crm.case.section').search(cr, uid, ['|', ('user_id', '=', user_id), ('member_ids', '=', user_id)], context=context)
		if section_ids:
			section_id = section_ids[0]
		return {'value': {'section_id': section_id}}

	_columns = {
		"partner_id" : fields.many2one('res.partner', 'Контакт', ondelete='set null', track_visibility='onchange',
            select=True, help="Linked partner (optional). Usually created when converting the lead."),
		'type_of_opport_id' : fields.many2one('crm.iml.opportunities.type', 'Type of opportunities'),
		'function': fields.char('Должность'),
		'creating_partner': fields.many2one('res.partner', 'Клиент'),
		"data_arraved" : fields.boolean("Data arraved"),
		"hash_for_url" : fields.char("Hash", size = 250),
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
			partner = self.findOrCreateObject(cr, uid, context, 'res.partner', 'email', vEmail, vals_obj)
		vType = ""
		if 'type' in aObj:
			vType = aObj['type'].replace(" ", "")
		vUser = None
		vSection = None
		vTypeID = None
		if (vType != ""):
			vals_obj = {'name': vType}
			vTypeObj = self.findOrCreateObject(cr, uid, context, 'crm.iml.opportunities.type', 'name', vType, vals_obj)	
			vTypeID = vTypeObj.id
			if (vTypeObj.user_id):
				vUser = vTypeObj.user_id.id
			elif (vTypeObj.section_id) and (vTypeObj.section_id.user_id):
				vUser = vTypeObj.section_id.user_id.id
				#Если указан отдел мы можем однозначно задать и отдел
				vSection = vTypeObj.section_id.id
		defaults = {
				'name':  msg.get('subject') or _("No Subject"),
				'email_from': vEmail,
				'email_cc': vEmail,
				'partner_id': partner.id,
				'phone': vPhone or "",
				'type': 'opportunity',
				'user_id': vUser,
				"section_id": vSection,
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
			opport.write({"data_arraved": False, "hash_for_url": "",})

	def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
		values = {}
		if partner_id:
			partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
			values = {
				'partner_name': partner.parent_id.name if partner.parent_id else False,
				'contact_name': partner.name if partner else False,
				'street': partner.street,
				'street2': partner.street2,
				'city': partner.city,
				'state_id': partner.state_id and partner.state_id.id or False,
				'country_id': partner.country_id and partner.country_id.id or False,
				'email_from': partner.email,
				'phone': partner.phone,
				'mobile': partner.mobile,
				'fax': partner.fax,
				'zip': partner.zip,
			}
		return {'value': values}
	
	def look_at_information(self,cr, uid, ids, context=None):
		params = self.pool.get('ir.config_parameter')
		url_link = params.get_param(cr, uid, 'crm_iml_url_pattern',default='' ,context=context)
		strHash = ""
		for opport in self.browse(cr, uid, ids, context=context):
			strHash = opport.hash_for_url
		url_link = url_link + "/" +  strHash + "?showclosed=1"
		url_link.encode("utf-8"),
		return {
				'type': 'ir.actions.act_url', 
				'url': url_link.encode("utf-8"),
				'target': 'new',
        	}

	def send_customers_form(self,cr, uid, ids, context=None):
		vals = {}
		cur_obj = None
		my_hash = ""
		ret_vals = {'return':True,}
		res_obj = None
		contact = None
		params = self.pool.get('ir.config_parameter')
		url_link = params.get_param(cr, uid, 'crm_iml_url_pattern',default='' ,context=context)
		opport = self.browse(cr, uid, ids[0], context=context)
		if not(url_link):
			raise osv.except_osv(_("Нельзя отправить бланк клиенту!"), _("Не задан сайт для клиентов. Обратитесь к администратору"))
	    #Если нет почты неизвестно куда посылать бланк, прерываем процесс
		if not(opport.email_from):
			raise osv.except_osv(_("Нельзя отправить бланк клиенту!"), _("Не задана электронная почта заказчика"))
		if not(opport.data_arraved):
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
			#Генерация клиента, пока фиктивного и неактивного
			if (opport.partner_name):
				vals = {
					'name': opport.partner_name,
				}
			else:
				vals = {
					'name': unicode("Заявка от ", "utf-8") + opport.contact_name or _(opport.email_from),
				}
			vals.update({"active": False, "is_company": True,})
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
				"child_ids": [(4, contact.id)],
				"first_contact": contact.id,
			}
			if (vals_contact != {}):
				cur_obj.write(vals_contact)
			#Генерим хэш
			m = hashlib.md5(str(cur_obj.id))
			my_hash = m.hexdigest();
			opport.write({"partner_id" : contact.id,
				"creating_partner": cur_obj.id, 
				"hash_for_url": my_hash})
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
		else:
			if (opport.partner_id):
				contact = opport.partner_id
			else:
				raise osv.except_osv(_("Нельзя отправить бланк клиенту!"), _("Не задано контактное лицо"))
		#Открываем диалог с письмом
		URL = url_link + "/" + opport.hash_for_url
		if (opport.data_arraved):
			URL = u"Добрый день!<br>Прошу Вас уточнить\скорректировать следующие данные в бланке:<br>... <br> Ссылка для заполнения данных: <br>" + URL
		else:
			URL = u"Добрый день!<br><br>Пожалуйста, пройдите по ссылке ниже и заполните реквизиты:<br>" + URL + u"<br>Спасибо!"
		model_data = self.pool.get("ir.model.data")
   		# Get res_partner views
		dummy, form_view = model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')
		vals_mess = {
			"subject": "Карточка клиента",
			"body": URL.encode("utf-8"),
			"partner_ids": [(4, contact.id)],
			"model": "crm.lead",
			"res_id": opport.id,
		}
		opport.write({"data_arraved": True})
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
		return ret_vals