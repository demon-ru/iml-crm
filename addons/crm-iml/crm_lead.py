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
import json
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

    def parse_json(self,description):
        stringText = {}
        stringText = description.split('\n')
        aCount = len(stringText)
        i = 0
        description = ''
        isFind = False
        while not(isFind):
            if ('{' in stringText[i]) and ('}' in stringText[i]):
               description = stringText[i]
               isFind = True
            i = i + 1
            isFind = isFind or i == aCount
        aObj = json.loads(description)
        return aObj
    
    def findOrCreatePartner(self, cr, uid, context, name, phone, email):
        res_partner_obj = self.pool.get('res.partner')
        res_partner_id = res_partner_obj.search(cr, uid, [('name', 'in', [name])], context=context)
        partnerID = 0
        if len(res_partner_id) > 0:
            partner =  res_partner_obj.browse(cr, uid, res_partner_id[0])
        else:
             partner = self.pool.get('res.partner')
             vals =  {'name': name,
                'phone': phone,
                'email': email}
             partner = res_partner_obj.browse(cr, uid, partner.create(cr, uid, vals, context=context))
        return partner

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        aMailBody = html2plaintext(msg.get('body')) if msg.get('body') else ''
        aObj = self.parse_json(aMailBody)
        if custom_values is None:
            custom_values = {}
        vPhone = aObj['phone']
        vEmail = aObj['email']
        partner = self.findOrCreatePartner(cr, uid, context, aObj['name'], vPhone, vEmail); 
        res_partner_obj = self.pool.get('res.partner')
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'email_from': vEmail,
            'email_cc': msg.get('cc'),
            'partner_id': partner.id,
            'phone': vPhone or "",
            'type': 'opportunity',
            'user_id': False,
        }
        if msg.get('author_id'):
            defaults.update(self.on_change_partner_id(cr, uid, None, msg.get('author_id'), context=context)['value'])
        if msg.get('priority') in dict(self.get_AVAILABLE_PRIORITIES()):
            defaults['priority'] = msg.get('priority')
        defaults.update(custom_values)
        return super(crm_lead, self).message_new(cr, uid, msg, custom_values=defaults, context=context)