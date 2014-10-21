from openerp.osv import fields, osv 

class server_config_settings(osv.TransientModel):
    _inherit = 'base.config.settings'

    _columns = {
        'export_sql_server': fields.many2one('crm.iml.sqlserver', 'name'),
        'exchange_settings' : fields.many2one('crm.iml.exchange_server_settings', 'name'),
        'url_pattern': fields.char("Link to cf", size=250)
    }
    _defaults = {
        'export_sql_server': 0,
        'exchange_settings': 0,
        'url_pattern': '',
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

    def set_default_exchange_settings(self,cr,uid,ids,context=None) :
        params = self.pool['ir.config_parameter']
        myself = self.browse(cr,uid,ids[0],context=context)
        server = 0
        url_link = ""
        if myself.exchange_settings:
           server = myself.exchange_settings.id
        if myself.url_pattern:
            url_link = myself.url_pattern
        params.set_param(cr, uid, 'crm_iml_exchange_settings_id', server , groups=['base.group_system'], context=None)
        params.set_param(cr, uid, 'crm_iml_url_pattern', url_link , groups=['base.group_system'], context=None)

    def get_default_exchange_settings(self,cr,uid,ids,context=None) :
        params = self.pool.get('ir.config_parameter')
        serv = params.get_param(cr, uid, 'crm_iml_exchange_settings_id',default='0' ,context=context)
        url_link = params.get_param(cr, uid, 'crm_iml_url_pattern',default='' ,context=context)
        return dict(exchange_settings=int(serv), url_pattern=url_link)
       
