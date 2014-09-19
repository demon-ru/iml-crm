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
import datetime
import sys
from openerp import tools, api
from openerp.tools.translate import _

class res_partner(osv.osv):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = 'res.partner'
    
    
# changed by Alex
# функция, которая возвращает состояние клиента по обслуживанию
    def _client_service_status(self, cr, uid, ids, field_name, arg, context=None):
        sys.stdout.write("TESTING FOR client service status")
        sys.stdout.write("IDS =" + str(ids))
        sys.stdout.write("IDS LENGtH = " + str(len(ids)))
        # initial variables
        is_in_service = False
#        res_s = "Не обслуживается"
        res_s = "Not In Service"
        res = dict()
        # this code should be covered with -try - except - 
        # because user might not have the permission to read -account.analytic.account-
        try:
            account_analytic_obj = self.pool.get('account.analytic.account')
            account_ids = account_analytic_obj.search(cr, uid, [('partner_id', 'in', ids)], context=context)
            account = account_analytic_obj.browse(cr, uid, account_ids)
            sys.stdout.write("Account ids is" + str(account_ids))
            for acc in account:
                # checking condisions to determine client state:
                # 1) contact have a contract
                # 2) contract state is ('open','In Progress')
                # 3) contract expiration date is less or equal to current date
                fmt = '%Y-%m-%d'

                sys.stdout.write(str(acc.date))
                sys.stdout.write("acc.date = " + str(acc.date))
                sys.stdout.write("now is " + str(datetime.datetime.now()))
                sys.stdout.write("name of acc" + acc.name)
                sys.stdout.write("reference is " + acc.code)
                sys.stdout.write("state of acc is " + acc.state)
                if ((acc.date is False) or (datetime.datetime.strptime(acc.date, fmt).date() >= datetime.datetime.now().date())) and (acc.state == 'open'):
                    is_in_service = True
                    sys.stdout.write("acc.date = " + str(acc.date))
                    sys.stdout.write("now is " + str(datetime.datetime.now()))
                    sys.stdout.write("name of acc" + acc.name)
                               
        except:
    #        res_s = "Недоступно"
            res_s = "Unavailable"
            e = sys.exc_info()[0]
            sys.stdout.write("Error occured: " + str(e))
        if is_in_service is True:
#            res_s = "Обслуживается"
            res_s = "In Service"
        # отличное нововведение в oe - если мы выбираем контактное лицо фирмы, то нам в 
        # ids приходит массив - ид фирмы, ид контактного лица
        if len(ids) == 1:
            res = {ids[0]: res_s}
        else:
            for id in ids:
                res.update({id:res_s})
        return res

# changed by Alex
# search function for client service status
# функция для обеспечения поиска по вычислимому полю
# в данном случае по полю client_service_status
# используется для фильтрации списка объектов по данному полю
    def _client_service_status_search(self, cr, uid, obj, name, args, context):

        sys.stdout.write("_client_service_status_search TESTING!!!1")
        # в итоге нам нужно получить список id контактов, которые как бы в состоянии обсл.
        # список нужно представить в виде domain условия
        # 1) шаг номер раз
        # итерируем все объекты account.analytic.account
        # выбираем те документы, которые подходят по условию 
        #(УСЛОВИЕ НЕПЛОХО БЫ ВЫНЕСТИ В ОТД. ФУНКЦИЮ) ибо уже в 2х местах будет одно и то же..
        # 2) шаг номер два заносим в предварительно созданный массив поле partner_id
        # 3) шаг номер три, все это компонуем в нужный вид и возвращаем
        res_array = []
        try:
            # try except нужен, т.к. у пользователя может не быть прав на просмотр документов
            # account.analytic.account
            account_analytic_obj = self.pool.get('account.analytic.account')
            # всех обманем, сделаем отбор через domain
            fmt = '%Y-%d-%m'
            date = datetime.datetime.today().date()
            sys.stdout.write(str(date)) # format is YYYY mm dd
                                        # account.date format is YYYY dd mm
            account_ids = account_analytic_obj.search(cr, uid, ['&', ('state', '=', 'open'), '|',('date', '=', False), ('date', '>=', date)], context=context)
            account = account_analytic_obj.browse(cr, uid, account_ids)
            
            for acc in account:
                sys.stdout.write(str(acc.date))
                sys.stdout.write(str(acc.state))
                sys.stdout.write(str(acc.partner_id.id))
                res_array.append(acc.partner_id.id)
#            res_array = account_ids
        except:
            # если у пользователя нет прав на просмотр account.analytic.account, вернем.. НИЧЕГО. коварно.
            res_array = []
            e = sys.exc_info()[0]
            sys.stdout.write("Error occured: " + str(e))
        # результат заглушка
        res = [('id', 'in', res_array)]
        
        return res

    _columns = {
        'categoryClient_id': fields.many2one('crm.clientcategory', 'name'),
        # расширение модели партнера в соответствии с требованиями "ВЕДЕНИЕ КЛИЕНТСКОЙ БАЗЫ / КАРТОЧКА КЛИЕНТА"
        # 
        # вычислимое поле, отображает состояние клиента по обслуживанию
        'client_in_service': fields.function(_client_service_status, string="Client service status", type="char", fnct_search=_client_service_status_search),
        'short_name' : fields.char('Short name', size = 255, required = True),
        'unk' : fields.char('Client ID', size = 255, requred = True),
#        'client_service_status' : 
        # Страница "Основное"
        'internet_shop_name' : fields.char('Internet shop name', size = 255, required = True),
        'category_of_goods' : fields.many2one('crm.goodscategory', 'Categories of goods'),
        'storage_of_shipping' : fields.many2one('crm.shipping_storage', 'Storage of shipping') ,
        'region_of_delivery' : fields.selection([('moscow', 'Moscow'), ('regions', 'Regions except Moscow')], 'Delivery region'),
        'fio_authorized person_nominative_case' : fields.char('Full name of authorized person in nominative case', size = 255, required = True),
        'fio_authorized person_genitive_case' : fields.char('Full name of authorized person in genitive case', size = 255, required = True),
        'authorized_person_position_nominative_case' : fields.char('Position of authorized person in nominative case', size = 255, required = True), 
        'authorized_person_position_genetive_case' : fields.char('Position of authorized person in genetive case', size = 255, required = True),
        # Страница "Адреса"
        # группа "Юридический адрес"
        'juridical_address_index' : fields.char('Post index', size = 255, required = True),
        'juridical_address_city_name' : fields.char('City', size = 255, required = True),
        'juridical_address_street_name' : fields.char('Street', size = 255, required = True),
        'juridical_address_dom' : fields.char('House number', size = 255, required = True),
        'juridical_address_building' : fields.char('Building', size = 255, required = True),
        'juridical_address_office' : fields.char('Office number', size = 255, required = True),
        # группа "Фактический адрес"
        'actual_address_index' : fields.char('Post index', size = 255, required = True),
        'actual_address_city_name' : fields.char('City', size = 255, required = True),
        'actual_address_street_name' : fields.char('Street', size = 255, required = True),
        'actual_address_dom' : fields.char('House number', size = 255, required = True),
        'actual_address_building' : fields.char('Building', size = 255, required = True),
        'actual_address_office' : fields.char('Office number', size = 255, required = True),
        # Страница "Банк"
        'account_number' : fields.char('Account number', size = 255, required = True), 
        'BIN' : fields.char('BIN', size = 255, required = True),
        'bank_name' : fields.char('Bank name', size = 255, required = True),
        'correspondent_account_number' : fields.char('Correspondent account number', size = 255, required = True),
        # Страница "Коды"
        'type_of_counterparty' : fields.selection([('individual', 'Individual'), ('legal_entity', 'Legal Entity')], 'Type of Counterparty'),
        'inn' : fields.char('INN', size = 255, required = True),
        'registration_reason_code' : fields.char('Registration Reason Code', size = 255, required = True),
        'date_of_accounting' : fields.char('Date of Accounting', size = 255, required = True),
        'OGRN_OGRNIP' : fields.char('OGRN / OGRNIP', size = 255, required = True),
        'registration_date' : fields.char('Registation Date', size = 255, required = True),
        'OKVED' : fields.char('OKVED', size = 255, required = True),
        'OKPO' : fields.char('OKPO', size = 255, required = True),
        'OKATO' : fields.char('OKATO', size = 255, required = True),
        
		# работа с NAV
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

