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
        'short_name' : fields.char('Short name', size = 255, required = False),
        'unk' : fields.char('Client ID', size = 255, requred = True),
        # ид холдинга в NAV, если аттрибут задан - значит, это холдинг
        'holdingId' : fields.char('Holding ID', size=255),
        # ид холдинга в NAV, если аттрибут задан - значит, клиент состоит в холдинге в NAV
        'nav_holdingId' : fields.char('Client Holding Id in NAV'),
        'company_org_type' : fields.many2one('crm.company_org_type', 'name'),
        'juridical_name' : fields.char('Jurudical company name', size = 255, required = False),
#          'client_service_status' : 
        # Страница "Основное"
        'internet_shop_name' : fields.char('Internet shop name', size = 255),
        'category_of_goods' : fields.many2one('crm.goodscategory', 'Categories of goods'),
        # Страница "Адреса"
        # группа "Юридический адрес"
        "juridical_address_country" : fields.char('Country', size = 255), 
        'juridical_address_index' : fields.char('Post index', size = 255),
        'juridical_address_city_name' : fields.char('City', size = 255),
        'juridical_address_street_name' : fields.char('Street', size = 255),
        'juridical_address_dom' : fields.char('House number', size = 255),
        'juridical_address_building' : fields.char('Building', size = 255),
        'juridical_address_office' : fields.char('Office number', size = 255),
        'juridical_adress_non_stand_part' : fields.char("Non-standard part", size = 255),
        'juridical_adress_region': fields.char("Регион", size = 255),
        'juridical_adress_full_adress': fields.char("Полный адрес:", size = 1000),
        # группа "Фактический адрес"
        "actual_address_country" : fields.char('Country', size = 255), 
        'actual_address_index' : fields.char('Post index', size = 255),
        'actual_address_city_name' : fields.char('City', size = 255),
        'actual_address_street_name' : fields.char('Street', size = 255),
        'actual_address_dom' : fields.char('House number', size = 255),
        'actual_address_building' : fields.char('Building', size = 255),
        'actual_address_office' : fields.char('Office number', size = 255),
        'actual_adress_non_stand_part' : fields.char("Non-standard part", size = 255),
        'actual_adress_region': fields.char('Регион', size = 255),
        'actual_adress_full_adress': fields.char("Полный адрес", size = 1000),
        # Страница "Банк"
        'account_number' : fields.char('Account number', size = 255), 
        'BIN' : fields.char('BIN', size = 255),
        'bank_name' : fields.char('Bank name', size = 255),
        'correspondent_account_number' : fields.char('Correspondent account number', size = 255),
        # Страница "Коды"
        'type_of_counterparty' : fields.selection([('individual', 'Individual'), ('legal_entity', 'Legal Entity')], 'Type of Counterparty'),
        'inn' : fields.char('INN', size = 255),
        'registration_reason_code' : fields.char('Registration Reason Code', size = 255),
        'date_of_accounting' : fields.date('Date of Accounting'),
        'OGRN_OGRNIP' : fields.char('OGRN / OGRNIP', size = 255),
        'registration_date' : fields.date('Registation Date'),
        'OKVED' : fields.char('OKVED', size = 255),
        'OKPO' : fields.char('OKPO', size = 255),
        'OKATO' : fields.char('OKATO', size = 255),
        #Переопределил эти поля  - сделал необязательными
        'property_account_payable': fields.property(
            type='many2one',
            relation='account.account',
            string="Account Payable",
            domain="[('type', '=', 'payable')]",
            help="This account will be used instead of the default one as the payable account for the current partner",
            required=False),
        'property_account_receivable': fields.property(
            type='many2one',
            relation='account.account',
            string="Account Receivable",
            domain="[('type', '=', 'receivable')]",
            help="This account will be used instead of the default one as the receivable account for the current partner",
            required=False),
        
		# работа с NAV
		'exportDateToNAV': fields.datetime('crm.iml.export.date.res.partner' , readonly=True),
        'notify_email': fields.selection([
            ('none', 'Нет'),
            ('always', 'Да'),
            ], 'Receive Inbox Notifications by Email', required=True,
            oldname='notification_email_send'),
    }

    _defaults = {
        "juridical_address_country": "Российская Федерация",
        "actual_address_country": "Российская Федерация",
    }

    def onchange_adress(self, cr, uid, ids, address_index, city_name, street_name, dom, building, office, nonstnpart, adressField):
    	v={}	 
    	vAdress = ""  
    	if (address_index and address_index.strip() != ""):
    		vAdress = vAdress + " " + address_index.strip()
    	if (city_name and city_name.strip() != ""):
    		vAdress = vAdress + " " + city_name.strip()
    	if (street_name and street_name.strip() != ""):
    		vAdress = vAdress + " " + street_name.strip()
    	if (dom and dom.strip() != ""):
    		vAdress = vAdress + unicode(" д.", "utf-8") + dom.strip()
    	if (building and building.strip() != ""):
    		vAdress = vAdress + unicode(" cтроение: ", "utf-8") + building.strip()
    	if (office and office.strip() != ""):
    		vAdress = vAdress + unicode(" офис: ", "utf-8") + office.strip() 
        if (nonstnpart and nonstnpart.strip() != ""):
            vAdress = vAdress + " " + nonstnpart.strip()
    	if (vAdress != "" and adressField):
    		v[adressField] = vAdress.strip()
        return {'value':v}

    def iml_crm_export_id(self,cr, uid, ids, context=None):
        com_vals = {}
        for partn in self.browse(cr, uid, ids, context=context):
            com_vals = {
                "Source": "crm",
                "Dest": "nav",
                "Command": "GetUNC",
                "CRM_ID": unicode(str(partn.id), "utf-8"),
            }
            res_obj = self.pool.get("crm.iml.sqlserver")
            res_id = res_obj.search(cr, uid, [("exchange_type", 'in', ["commands"])], context=context)
            server = None
            if len(res_id) > 0:
                server = res_obj.browse(cr, uid, res_id[0])
            else:
                raise osv.except_osv(_("Нельзя отправить команду!"), _("Не задана таблица для обмена команд. Обратитесь к администратору."))
            res_id = res_obj.search(cr, uid, [("exchange_type", 'in', ["partner"])], context=context)
            server_res_part = None
            if len(res_id) > 0:
                server_res_part = res_obj.browse(cr, uid, res_id[0])
            else:
                raise osv.except_osv(_("Нельзя отправить команду!"), _("Не задана таблица для импорта/экспорта клиентов. Обратитесь к администратору."))
            server.commands_exchange(com_vals)
            server_res_part.export_res_partner(partn)
            partn.write({'exportDateToNAV': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
        return True

    def redirectToContact(self,cr,uid,ids,context=None): 
        partn = self.browse(cr, uid, ids[0], context=context)
        model_data = self.pool.get("ir.model.data")
        # Get res_partner views
        dummy, form_view = model_data.get_object_reference(cr, uid, 'base', 'view_partner_form')

        return {
            'return':True,
            'view_mode': 'form',
            'view_id': "base.view_partner_form",
            'views': [(form_view or False,'form')],
            'view_type': 'form',
            'res_id' : partn.id,
            'res_model': 'res.partner',
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

    def write(self, cr, uid, ids, vals, context=None):
        for partn in self.browse(cr, uid, ids, context=context):
            if ('juridical_address_city_name' in vals or 'juridical_address_index' in vals or 'juridical_address_street_name' in vals or 'juridical_address_dom' in vals or 'juridical_address_building' in vals or 'juridical_address_office' in vals or 'juridical_adress_non_stand_part' in vals):
                vCity = partn.juridical_address_city_name
                if ('juridical_address_city_name' in vals):
                    vCity = vals.get('juridical_address_city_name')
                vIndex = partn.juridical_address_index
                if ('juridical_address_index' in vals):
                    vIndex = vals.get("juridical_address_index")
                vStreet = partn.juridical_address_street_name
                if ("juridical_address_street_name" in vals):
                    vStreet = vals.get("juridical_address_street_name")
                vDom = partn.juridical_address_dom
                if ("juridical_address_dom" in vals):
                    vDom = vals.get("juridical_address_dom")
                vBilding = partn.juridical_address_building
                if ("juridical_address_building" in vals):
                    vBilding = vals.get("juridical_address_building")
                vOfice = partn.juridical_address_office
                if ("juridical_address_office" in vals):
                    vOfice = vals.get("juridical_address_office")
                vNonStandart = partn.juridical_adress_non_stand_part
                if ("juridical_adress_non_stand_part" in vals):
                    vNonStandart = vals.get("juridical_adress_non_stand_part")
                jur_adress = self.onchange_adress(cr, uid, ids, vIndex, vCity, vStreet, vDom, vBilding, vOfice, vNonStandart, "juridical_adress_full_adress")['value']
                vals.update(jur_adress)
            if ('actual_address_city_name' in vals or 'actual_address_index' in vals or 'actual_address_street_name' in vals or 'actual_address_dom' in vals or 'actual_address_building' in vals or 'actual_address_office' in vals or 'actual_adress_non_stand_part' in vals):
                vCity = partn.actual_address_city_name
                if ('actual_address_city_name' in vals):
                    vCity = vals.get('actual_address_city_name')
                vIndex = partn.actual_address_index
                if ('actual_address_index' in vals):
                    vIndex = vals.get("actual_address_index")
                vStreet = partn.actual_address_street_name
                if ("actual_address_street_name" in vals):
                    vStreet = vals.get("actual_address_street_name")
                vDom = partn.actual_address_dom
                if ("actual_address_dom" in vals):
                    vDom = vals.get("actual_address_dom")
                vBilding = partn.actual_address_building
                if ("actual_address_building" in vals):
                    vBilding = vals.get("actual_address_building")
                vOfice = partn.actual_address_office
                if ("jactual_address_office" in vals):
                    vOfice = vals.get("actual_address_office")
                vNonStandart = partn.actual_adress_non_stand_part
                if ("actual_adress_non_stand_part" in vals):
                    vNonStandart = vals.get("actual_adress_non_stand_part")
                actual_adress = self.onchange_adress(cr, uid, ids, vIndex, vCity, vStreet, vDom, vBilding, vOfice, vNonStandart, "actual_adress_full_adress")['value']
                vals.update(actual_adress)
        return super(res_partner, self).write(cr, uid, ids, vals, context=context)

