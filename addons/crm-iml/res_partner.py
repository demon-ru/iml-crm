from openerp.osv import fields,osv

class res_partner(osv.osv):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = 'res.partner'

    _columns = {
        'categoryClient_id': fields.many2one('crm.clientcategory', 'name'),
    }