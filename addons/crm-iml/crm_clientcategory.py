# -*- coding: utf-8 -*-
##############################################################################
#
#    Author Sokolov
#
##############################################################################

from openerp.osv import fields,osv,orm

class crm_clientcategory(osv.osv):

    _name = "crm.clientcategory"
    _description = "Category of client"

    _columns = {
        'name': fields.char('Name', size=64, required=True, help='The name of the segmentation.'),
        'description': fields.text('Description'),
    }
crm_clientcategory()