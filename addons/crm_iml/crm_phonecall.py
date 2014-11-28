from openerp.osv import fields, osv

class crm_phonecall(osv.osv):
	_inherit = 'crm.phonecall'

	def redirectToObject(self,cr,uid,ids,context=None): 
		call = self.browse(cr, uid, ids[0], context=context)
		model_data = self.pool.get("ir.model.data")
		# Get res_partner views
		dummy, form_view = model_data.get_object_reference(cr, uid, 'crm', 'crm_case_phone_form_view')

		return {
			'return':True,
			'view_mode': 'form',
			'view_id': "crm.crm_case_phone_form_view",
			'views': [(form_view or False,'form')],
			'view_type': 'form',
			'res_id' : call.id,
			'res_model': 'crm.phonecall',
			'target': 'current',
			'type': 'ir.actions.act_window',
		}