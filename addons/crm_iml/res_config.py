from openerp.osv import fields, osv 

class server_config_settings(osv.TransientModel):
    _inherit = 'base.config.settings'

    _columns = {
        'export_sql_server': fields.many2one('crm.iml.sqlserver', 'name')
    }
    _defaults = {
        'export_sql_server': 0
    }
    def set_crm_export_server(self,cr,uid,ids,context=None) :
        params = self.pool['ir.config_parameter']
        myself = self.browse(cr,uid,ids[0],context=context)
	server = 0
	if myself.export_sql_server:
		server = myself.export_sql_server.id
        params.set_param(cr, uid, 'crm_iml_export_server_id', server , groups=['base.group_system'], context=None)

    def get_default_crm_export_server(self,cr,uid,ids,context=None) :
        params = self.pool.get('ir.config_parameter')
        serv = params.get_param(cr, uid, 'crm_iml_export_server_id',default='0' ,context=context)
        return dict(export_sql_server=int(serv))
     
       
