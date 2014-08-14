# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields,osv
import datetime
import sys


class res_partner(osv.osv):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = 'res.partner'

    def _opportunity_meeting_phonecall_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict(map(lambda x: (x,{'opportunity_count': 0, 'meeting_count': 0}), ids))
        # the user may not have access rights for opportunities or meetings
        try:
            for partner in self.browse(cr, uid, ids, context):
                res[partner.id] = {
                    'opportunity_count': len(partner.opportunity_ids),
                    'meeting_count': len(partner.meeting_ids),
                }
        except:
            pass
        for partner in self.browse(cr, uid, ids, context):
            res[partner.id]['phonecall_count'] = len(partner.phonecall_ids)
        return res

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
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'opportunity_ids': fields.one2many('crm.lead', 'partner_id',\
            'Leads and Opportunities', domain=[('probability', 'not in', ['0', '100'])]),
        'meeting_ids': fields.many2many('calendar.event', 'calendar_event_res_partner_rel','res_partner_id', 'calendar_event_id',
            'Meetings'),
        'phonecall_ids': fields.one2many('crm.phonecall', 'partner_id',\
            'Phonecalls'),
        'opportunity_count': fields.function(_opportunity_meeting_phonecall_count, string="Opportunity", type='integer', multi='opp_meet'),
        'meeting_count': fields.function(_opportunity_meeting_phonecall_count, string="# Meetings", type='integer', multi='opp_meet'),
        'phonecall_count': fields.function(_opportunity_meeting_phonecall_count, string="Phonecalls", type="integer", multi='opp_meet'),
        # changed by Alex
        # added field as a function, indicates service status of client
        # вычислимое поле, отображает состояние клиента по обслуживанию
        'client_in_service': fields.function(_client_service_status, string="Client service status", type="char", fnct_search=_client_service_status_search),
    }

    def redirect_partner_form(self, cr, uid, partner_id, context=None):
        search_view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'view_res_partner_filter')
        value = {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'res.partner',
            'res_id': int(partner_id),
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
            'search_view_id': search_view and search_view[1] or False
        }
        return value

    def make_opportunity(self, cr, uid, ids, opportunity_summary, planned_revenue=0.0, probability=0.0, partner_id=None, context=None):
        categ_obj = self.pool.get('crm.case.categ')
        categ_ids = categ_obj.search(cr, uid, [('object_id.model','=','crm.lead')])
        lead_obj = self.pool.get('crm.lead')
        opportunity_ids = {}
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner_id:
                partner_id = partner.id
            opportunity_id = lead_obj.create(cr, uid, {
                'name' : opportunity_summary,
                'planned_revenue' : planned_revenue,
                'probability' : probability,
                'partner_id' : partner_id,
                'categ_ids' : categ_ids and categ_ids[0:1] or [],
                'type': 'opportunity'
            }, context=context)
            opportunity_ids[partner_id] = opportunity_id
        return opportunity_ids

    def schedule_meeting(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        partner_ids = list(ids)
        partner_ids.append(self.pool.get('res.users').browse(cr, uid, uid).partner_id.id)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'calendar', 'action_calendar_event', context)
        res['context'] = {
            'default_partner_id': ids and ids[0] or False,
            'default_partner_ids': partner_ids,
        }
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
